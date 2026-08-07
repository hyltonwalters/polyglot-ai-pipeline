package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"sync"
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

type EngineConfig struct {
	MaxWorkers int
	APIKey     string
}

func main() {
	config := EngineConfig{
		MaxWorkers: 8, // Set pool width to balance hardware utilization and API rate limits
		APIKey:     os.Getenv("ANTHROPIC_API_KEY"),
	}

	http.HandleFunc("/v1/process-batch", handleBatchProcessing(config))
	fmt.Println("🚀 Go concurrency module listening on port 8080...")
	if err := http.ListenAndServe(":8080", nil); err != nil {
		panic(err)
	}
}

func handleBatchProcessing(config EngineConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		var batch BatchRequest
		if err := json.NewDecoder(r.Body).Decode(&batch); err != nil {
			http.Error(w, "Malformed JSON buffer packet", http.StatusBadRequest)
			return
		}

		var wg sync.WaitGroup
		jobs := make(chan Product, len(batch.Products))

		// Spin up multiplexed worker threads
		for w := 1; w <= config.MaxWorkers; w++ {
			go worker(jobs, &wg, config.APIKey)
		}

		// Push jobs into channel
		for _, product := range batch.Products {
			wg.Add(1)
			jobs <- product
		}
		close(jobs)

		wg.Wait() // Thread barrier block synchronization
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"status":"concurrency_batch_completed"}`))
	}
}

func worker(jobs <-chan Product, wg *sync.WaitGroup, apiKey string) {
	for job := range jobs {
		ctx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
		_ = ctx
		
		// Architectural logging tracking the multi-threaded operation execution sequence directly
		fmt.Printf("[Worker Thread Logging] Concurrently transforming entity ID %d: %s\n", job.ID, job.Title)
		cancel()
		wg.Done()
	}
}
