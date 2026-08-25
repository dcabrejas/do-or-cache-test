# OpenRouter Cache Locality Test

Tests whether OpenRouter's prompt-cache / provider-sticky-routing degrades after ~5 minutes of
inactivity or holds through the documented ~10-minute window.

## What it does

`cache_test.py` sends a fixed, cache-friendly prompt prefix (~13-15k tokens) to
`openai/gpt-4o-mini` via the OpenRouter API, across two workloads (synthetic coding and legal
text) and 3 concurrent sessions each. Per session it:

1. Sends 4 baseline requests ~45s apart.
2. Waits ~6 minutes idle, sends a request.
3. Waits ~5 more minutes (~11 min total idle), sends a request.

For each request it records TTFT (via streaming), total latency, and pulls authoritative
cache-hit/provider/cost stats from OpenRouter's `/generation` endpoint.

## Usage

Requires `OPENROUTER_API_KEY` in a `.env` file in this directory (not committed).

```bash
python3 cache_test.py
```

Takes ~14 minutes end-to-end due to the required idle gaps. Writes `results_coding.csv`,
`results_legal.csv`, and a `SUMMARY.md` rollup.

## Results

See `SUMMARY.md` for the latest run's data and verdict.
