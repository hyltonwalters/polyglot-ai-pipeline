package main

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

type testAI struct{}

func (testAI) Enrich(_ context.Context, p Product) (Enrichment, error) {
	return Enrichment{Category: "test", Summary: p.Title}, nil
}

type timeoutAI struct{}

func (timeoutAI) Enrich(ctx context.Context, _ Product) (Enrichment, error) {
	<-ctx.Done()
	return Enrichment{}, ctx.Err()
}

type failingAI struct{}

func (failingAI) Enrich(_ context.Context, _ Product) (Enrichment, error) {
	return Enrichment{}, errors.New("provider unavailable")
}

func TestProcessBatchPreservesOrder(t *testing.T) {
	cfg := Config{MaxWorkers: 2, JobTimeout: time.Second}
	batch := BatchRequest{Products: []Product{
		{ID: 1, Title: "A", RawDescription: "a"},
		{ID: 2, Title: "B", RawDescription: "b"},
		{ID: 3, Title: "C", RawDescription: "c"},
	}}

	got := processBatch(context.Background(), batch, cfg, testAI{})
	if got.Processed != 3 || got.Failed != 0 {
		t.Fatalf("unexpected counts: %+v", got)
	}
	for i, want := range []int{1, 2, 3} {
		if got.Results[i].Product.ID != want {
			t.Fatalf("result order changed at %d: got %d", i, got.Results[i].Product.ID)
		}
	}
}

func TestMockAIClientCategorizesProducts(t *testing.T) {
	tests := []struct {
		name string
		p    Product
		want string
	}{
		{name: "footwear", p: Product{Title: "Trail Boot", RawDescription: "Waterproof footwear"}, want: "footwear"},
		{name: "apparel", p: Product{Title: "Utility Jacket", RawDescription: "Canvas jacket"}, want: "apparel"},
		{name: "electronics", p: Product{Title: "Laptop", RawDescription: "Portable computer"}, want: "electronics"},
		{name: "general", p: Product{Title: "Coffee Mug", RawDescription: "Ceramic cup"}, want: "general"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := (MockAIClient{}).Enrich(context.Background(), tt.p)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got.Category != tt.want {
				t.Fatalf("category = %q, want %q", got.Category, tt.want)
			}
			if got.Summary == "" {
				t.Fatal("expected non-empty summary")
			}
		})
	}
}

func TestProcessBatchHonorsJobTimeout(t *testing.T) {
	cfg := Config{MaxWorkers: 1, JobTimeout: 5 * time.Millisecond}
	batch := BatchRequest{Products: []Product{{ID: 1, Title: "Slow", RawDescription: "Slow provider"}}}

	got := processBatch(context.Background(), batch, cfg, timeoutAI{})
	if got.Processed != 0 || got.Failed != 1 {
		t.Fatalf("unexpected counts: %+v", got)
	}
	if len(got.Errors) != 1 || !strings.Contains(got.Errors[0], "deadline exceeded") {
		t.Fatalf("unexpected errors: %#v", got.Errors)
	}
}

func TestHealthHandler(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rec := httptest.NewRecorder()

	healthHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusOK)
	}
	if got := strings.TrimSpace(rec.Body.String()); got != `{"status":"ok"}` {
		t.Fatalf("body = %s", got)
	}
}

func TestBatchHandlerValidation(t *testing.T) {
	products := make([]Product, 101)
	tooMany, err := json.Marshal(BatchRequest{Products: products})
	if err != nil {
		t.Fatal(err)
	}

	tests := []struct {
		name   string
		method string
		body   string
		want   int
	}{
		{name: "method", method: http.MethodGet, body: "", want: http.StatusMethodNotAllowed},
		{name: "invalid json", method: http.MethodPost, body: "{", want: http.StatusBadRequest},
		{name: "empty batch", method: http.MethodPost, body: `{"products":[]}`, want: http.StatusBadRequest},
		{name: "invalid product", method: http.MethodPost, body: `{"products":[{"id":0,"title":"","raw_description":""}]}`, want: http.StatusBadRequest},
		{name: "too many", method: http.MethodPost, body: string(tooMany), want: http.StatusBadRequest},
	}

	handler := batchHandler(Config{MaxWorkers: 1, JobTimeout: time.Second}, MockAIClient{})
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			req := httptest.NewRequest(tt.method, "/v1/process-batch", strings.NewReader(tt.body))
			rec := httptest.NewRecorder()
			handler.ServeHTTP(rec, req)
			if rec.Code != tt.want {
				t.Fatalf("status = %d, want %d; body=%s", rec.Code, tt.want, rec.Body.String())
			}
		})
	}
}

func TestBatchHandlerReturnsBadGatewayWhenAllJobsFail(t *testing.T) {
	handler := batchHandler(Config{MaxWorkers: 1, JobTimeout: time.Second}, failingAI{})
	req := httptest.NewRequest(
		http.MethodPost,
		"/v1/process-batch",
		strings.NewReader(`{"products":[{"id":1,"title":"Boot","raw_description":"Leather boot"}]}`),
	)
	rec := httptest.NewRecorder()

	handler.ServeHTTP(rec, req)

	if rec.Code != http.StatusBadGateway {
		t.Fatalf("status = %d, want %d; body=%s", rec.Code, http.StatusBadGateway, rec.Body.String())
	}
	var response BatchResponse
	if err := json.Unmarshal(rec.Body.Bytes(), &response); err != nil {
		t.Fatalf("decode response: %v", err)
	}
	if response.Processed != 0 || response.Failed != 1 {
		t.Fatalf("unexpected response: %+v", response)
	}
}

func TestOpenAICompatibleClient(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/chat/completions" {
			t.Fatalf("path = %q", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer test-key" {
			t.Fatalf("authorization = %q", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(w, `{"choices":[{"message":{"content":"{\"category\":\"footwear\",\"summary\":\"Trail boot\"}"}}]}`)
	}))
	defer server.Close()

	client := OpenAICompatibleClient{
		BaseURL: server.URL,
		APIKey:  "test-key",
		Model:   "test-model",
		Client:  server.Client(),
	}

	got, err := client.Enrich(context.Background(), Product{ID: 1, Title: "Trail Boot", RawDescription: "Waterproof boot"})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if got.Category != "footwear" || got.Summary != "Trail boot" {
		t.Fatalf("unexpected enrichment: %+v", got)
	}
}
