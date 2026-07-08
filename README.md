# Autonomous PostgreSQL Query Optimizer Agent

An agentic system that takes a slow PostgreSQL query, reads its real execution plan, and produces optimizations that are **empirically benchmarked before they're recommended** — so every suggestion reflects measured latency gains, not a model's assertion.

Built as a 7-node [LangGraph](https://github.com/langchain-ai/langgraph) pipeline driving a locally-hosted `qwen2.5-coder` model via [Ollama](https://ollama.com/).

---

## Key Results

On a benchmark of **50 realistic queries** against a **3.5M-row e-commerce database**, the agent delivered a measured latency improvement on **76% of queries**.

Crucially, that number is grounded in real measurement: each candidate optimization is applied and benchmarked against the unoptimized baseline, so the reported improvements are what the database actually does — not what the model predicts it will do.

---

## What It Does

Query tuning normally means a human reads an `EXPLAIN ANALYZE` plan, spots the expensive operations, hypothesizes a fix, applies it, and re-measures. This agent automates that loop end to end:

- **Reads the real plan** — captures `EXPLAIN (ANALYZE, BUFFERS)` output to see where time is actually spent.
- **Recommends indexes** — the core of query optimization: identifying the access paths that turn sequential scans into targeted lookups.
- **Attempts equivalent rewrites** — generates semantically-equivalent query rewrites as an additional optimization avenue.
- **Verifies correctness** — every rewrite is checked for result-correctness against the benchmark data before it's accepted.
- **Proves the win** — each candidate is benchmarked against the baseline, so only measured improvements are surfaced.

The verification-first design is what makes the output trustworthy: the system measures rather than trusts.

---

## Architecture

The system is a directed graph of 7 nodes orchestrated by LangGraph. State (the query, its plan, candidate optimizations, and benchmark results) flows through the pipeline:

```
Input Query
    │
    ▼
┌─────────────────┐
│ 1. Plan Capture │  Run EXPLAIN (ANALYZE, BUFFERS) to get the real execution plan
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Plan Analysis│  Identify expensive operations (seq scans, sorts, nested loops)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. Index Advisor│  Propose candidate indexes based on the plan + schema
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. Query Rewrite│  Generate a semantically-equivalent alternative formulation
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. Validation   │  Verify rewrites preserve result correctness
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. Benchmark    │  Apply each candidate, measure latency vs. baseline
└────────┬────────┘
         ▼
┌─────────────────┐
│ 7. Report       │  Rank candidates by measured improvement, emit recommendation
└─────────────────┘
```


---

## Tech Stack

| Layer | Choice |
|---|---|
| Orchestration | LangGraph |
| LLM | `qwen2.5-coder` served locally via Ollama |
| Database | PostgreSQL |
| Benchmark dataset | 3.5M-row synthetic e-commerce schema (custom data generator) |
| Language | Python |

Serving the model locally via Ollama means zero per-query API cost and full control over the inference environment — a deliberate choice for a system that issues many LLM calls per query.

---

## Benchmark Harness

The project ships with everything needed to reproduce the numbers, not just the agent:

- **Data generator** — builds a 3.5M-row e-commerce database (orders, products, users) with realistic cardinality and distributions, so the planner faces meaningful choices rather than toy tables.
- **Query suite** — 50 queries spanning common patterns (filtered scans, joins, aggregations, sorts) that exercise a range of optimization opportunities.
- **Benchmark runner** — applies each candidate optimization and records its measured latency delta against the baseline. This is the source of truth for every result the agent reports.

---

## Design Notes

- **Correctness is verified empirically.** Rewrites are validated by matching results against the benchmark dataset — a practical correctness check rather than a formal proof of equivalence for all possible inputs.
- **Read-latency focus.** Index recommendations optimize query read latency; write-workload maintenance cost is a natural extension.
- **Single-query scope.** Each run optimizes one query in isolation, which keeps the feedback loop tight and every recommendation directly attributable.

---

## Roadmap

- Weight index recommendations by write-workload cost, not just read latency.
- Extend validation toward stronger equivalence guarantees beyond sample-data matching.
- Move from single-query tuning to workload-level index selection under a shared budget.

---

## License

Vishal
