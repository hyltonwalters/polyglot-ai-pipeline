package main

import (
	"context"
	"testing"
	"time"
)

type testAI struct{}

func (testAI) Enrich(_ context.Context, p Product) (Enrichment, error) {
	return Enrichment{Category: "test", Summary: p.Title}, nil
}

func TestProcessBatchPreservesOrder(t *testing.T) {
	cfg := Config{MaxWorkers: 2, JobTimeout: time.Second}
	batch := BatchRequest{Products: []Product{{ID: 1, Title: "A", RawDescription: "a"}, {ID: 2, Title: "B", RawDescription: "b"}, {ID: 3, Title: "C", RawDescription: "c"}}}
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
