package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

type Product struct {
	ID             int    `json:"id"`
	Title          string `json:"title"`
	RawDescription string `json:"raw_description"`
}

type BatchRequest struct {
	Products []Product `json:"products"`
}

type Enrichment struct {
	Category string `json:"category"`
	Summary  string `json:"summary"`
}

type ProcessedProduct struct {
	Product    Product    `json:"product"`
	Enrichment Enrichment `json:"enrichment"`
	WorkerID   int        `json:"worker_id"`
	DurationMS int64      `json:"duration_ms"`
}

type BatchResponse struct {
	Status       string             `json:"status"`
	Processed    int                `json:"processed"`
	Failed       int                `json:"failed"`
	Results      []ProcessedProduct `json:"results"`
	Errors       []string           `json:"errors,omitempty"`
	ProcessingMS int64              `json:"processing_ms"`
}

type AIClient interface {
	Enrich(context.Context, Product) (Enrichment, error)
}

type MockAIClient struct{}

func (MockAIClient) Enrich(_ context.Context, p Product) (Enrichment, error) {
	text := strings.ToLower(p.Title + " " + p.RawDescription)
	category := "general"
	switch {
	case strings.Contains(text, "boot") || strings.Contains(text, "shoe") || strings.Contains(text, "footwear"):
		category = "footwear"
	case strings.Contains(text, "jacket") || strings.Contains(text, "shirt") || strings.Contains(text, "jersey"):
		category = "apparel"
	case strings.Contains(text, "phone") || strings.Contains(text, "laptop") || strings.Contains(text, "computer"):
		category = "electronics"
	}
	return Enrichment{Category: category, Summary: fmt.Sprintf("%s: %s", p.Title, p.RawDescription)}, nil
}

type OpenAICompatibleClient struct {
	BaseURL string
	APIKey  string
	Model   string
	Client  *http.Client
}

func (c OpenAICompatibleClient) Enrich(ctx context.Context, p Product) (Enrichment, error) {
	prompt := fmt.Sprintf(`Return JSON only with exactly two string fields: category and summary. Categorize and summarize this product.
Title: %s
Description: %s`, p.Title, p.RawDescription)

	body := map[string]any{
		"model": c.Model,
		"messages": []map[string]string{
			{"role": "system", "content": "You are a concise product enrichment service. Output valid JSON only."},
			{"role": "user", "content": prompt},
		},
		"temperature": 0.1,
	}
	encoded, err := json.Marshal(body)
	if err != nil {
		return Enrichment{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(c.BaseURL, "/")+"/chat/completions", bytes.NewReader(encoded))
	if err != nil {
		return Enrichment{}, err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+c.APIKey)

	resp, err := c.Client.Do(req)
	if err != nil {
		return Enrichment{}, err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return Enrichment{}, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Enrichment{}, fmt.Errorf("AI provider returned HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(raw)))
	}

	var envelope struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(raw, &envelope); err != nil {
		return Enrichment{}, fmt.Errorf("decode AI response: %w", err)
	}
	if len(envelope.Choices) == 0 {
		return Enrichment{}, fmt.Errorf("AI provider returned no choices")
	}

	var result Enrichment
	if err := json.Unmarshal([]byte(envelope.Choices[0].Message.Content), &result); err != nil {
		return Enrichment{}, fmt.Errorf("decode AI content as JSON: %w", err)
	}
	if result.Category == "" || result.Summary == "" {
		return Enrichment{}, fmt.Errorf("AI response missing category or summary")
	}
	return result, nil
}

type Config struct {
	Port       int
	MaxWorkers int
	JobTimeout time.Duration
	AIMode     string
	AIBaseURL  string
	AIKey      string
	AIModel    string
}

func loadConfig() Config {
	workers := envInt("MAX_WORKERS", 4)
	if workers < 1 || workers > 32 {
		workers = 4
	}
	timeoutMS := envInt("JOB_TIMEOUT_MS", 5000)
	if timeoutMS < 100 || timeoutMS > 60000 {
		timeoutMS = 5000
	}
	mode := strings.ToLower(os.Getenv("AI_MODE"))
	if mode == "" {
		mode = "mock"
	}
	return Config{
		Port: envInt("PORT", 8080), MaxWorkers: workers, JobTimeout: time.Duration(timeoutMS) * time.Millisecond,
		AIMode: mode, AIBaseURL: envOr("AI_BASE_URL", "https://api.openai.com/v1"),
		AIKey: os.Getenv("AI_API_KEY"), AIModel: envOr("AI_MODEL", "gpt-4o-mini"),
	}
}

func envInt(key string, fallback int) int {
	v, err := strconv.Atoi(os.Getenv(key))
	if err != nil {
		return fallback
	}
	return v
}
func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func newAIClient(cfg Config) AIClient {
	if cfg.AIMode == "openai-compatible" && cfg.AIKey != "" {
		return OpenAICompatibleClient{BaseURL: cfg.AIBaseURL, APIKey: cfg.AIKey, Model: cfg.AIModel, Client: &http.Client{Timeout: 15 * time.Second}}
	}
	return MockAIClient{}
}

func processBatch(ctx context.Context, batch BatchRequest, cfg Config, ai AIClient) BatchResponse {
	started := time.Now()
	if len(batch.Products) == 0 {
		return BatchResponse{Status: "completed", Results: []ProcessedProduct{}, ProcessingMS: time.Since(started).Milliseconds()}
	}

	type job struct {
		index   int
		product Product
	}
	type result struct {
		index int
		value ProcessedProduct
		err   error
	}
	jobs := make(chan job)
	results := make(chan result, len(batch.Products))

	var wg sync.WaitGroup
	for workerID := 1; workerID <= cfg.MaxWorkers; workerID++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			for j := range jobs {
				jobStarted := time.Now()
				jobCtx, cancel := context.WithTimeout(ctx, cfg.JobTimeout)
				enrichment, err := ai.Enrich(jobCtx, j.product)
				cancel()
				if err != nil {
					results <- result{index: j.index, err: fmt.Errorf("product %d: %w", j.product.ID, err)}
					continue
				}
				results <- result{index: j.index, value: ProcessedProduct{Product: j.product, Enrichment: enrichment, WorkerID: id, DurationMS: time.Since(jobStarted).Milliseconds()}}
			}
		}(workerID)
	}

	go func() {
		for i, p := range batch.Products {
			jobs <- job{index: i, product: p}
		}
		close(jobs)
		wg.Wait()
		close(results)
	}()

	ordered := make([]ProcessedProduct, len(batch.Products))
	errors := make([]string, 0)
	processed := 0
	for r := range results {
		if r.err != nil {
			errors = append(errors, r.err.Error())
			continue
		}
		ordered[r.index] = r.value
		processed++
	}

	response := BatchResponse{Status: "completed", Processed: processed, Failed: len(errors), Results: ordered, Errors: errors, ProcessingMS: time.Since(started).Milliseconds()}
	return response
}

func healthHandler(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func batchHandler(cfg Config, ai AIClient) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
		defer r.Body.Close()
		var batch BatchRequest
		decoder := json.NewDecoder(r.Body)
		if err := decoder.Decode(&batch); err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "invalid JSON payload"})
			return
		}
		if len(batch.Products) == 0 {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "products must contain at least one item"})
			return
		}
		if len(batch.Products) > 100 {
			writeJSON(w, http.StatusBadRequest, map[string]string{"error": "maximum batch size is 100"})
			return
		}
		for _, p := range batch.Products {
			if p.ID <= 0 || strings.TrimSpace(p.Title) == "" || strings.TrimSpace(p.RawDescription) == "" {
				writeJSON(w, http.StatusBadRequest, map[string]string{"error": "each product requires a positive id, title and raw_description"})
				return
			}
		}
		response := processBatch(r.Context(), batch, cfg, ai)
		status := http.StatusOK
		if response.Processed == 0 {
			status = http.StatusBadGateway
		}
		writeJSON(w, status, response)
	}
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func main() {
	cfg := loadConfig()
	ai := newAIClient(cfg)
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", healthHandler)
	mux.HandleFunc("/v1/process-batch", batchHandler(cfg, ai))
	server := &http.Server{Addr: fmt.Sprintf(":%d", cfg.Port), Handler: mux, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 10 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second}

	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		log.Printf("worker service listening on %s (workers=%d, ai_mode=%s)", server.Addr, cfg.MaxWorkers, cfg.AIMode)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatal(err)
		}
	}()
	<-stop
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = server.Shutdown(ctx)
}
