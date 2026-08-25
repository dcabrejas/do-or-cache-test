# OpenRouter Cache Locality Test

Tests whether OpenRouter's prompt-cache / provider-sticky-routing degrades after a period of
inactivity, and how that depends on the model's backend provider pool.

For each request both harnesses record TTFT (via streaming), total latency, and pull authoritative
cache-hit / provider / cost stats from OpenRouter's `/generation` endpoint.

Requires `OPENROUTER_API_KEY` in a `.env` file in this directory (not committed).

## Test 1 — `cache_test.py`

Sends a fixed, cache-friendly prompt prefix (~13k tokens) to `openai/gpt-4o-mini`, across two
workloads (synthetic coding and legal text) and 3 concurrent sessions each. Per session:

1. 4 baseline requests ~45s apart.
2. ~6 minutes idle, then a request.
3. ~5 more minutes (~11 min total idle), then a request.

```bash
python3 cache_test.py
```

~14 minutes end-to-end. Writes `results_coding.csv`, `results_legal.csv`, `SUMMARY.md`.

**Result:** no provider switching and no cache degradation at either gap.

## Test 2 — `cache_test_2.py`

Follow-up addressing test 1's main limitation: `gpt-4o-mini` has only 2 backend providers, both
cache-capable, so it can barely exhibit provider switching. Test 2 adds
`meta-llama/llama-3.3-70b-instruct` (12 providers, only 5 cache-capable) as a stress test, keeps
`gpt-4o-mini` as a control, extends the gaps to 15 and 20 minutes, and alternates a long (~13k
token) and short (~4k token) prefix to probe mixed context lengths.

```bash
python3 cache_test_2.py
```

~25 minutes end-to-end. Writes `results2.csv` and `SUMMARY2.md`.

**Result:** on the contested provider pool, 6/7 sessions switched provider across the idle gap and
6/7 saw cache hit rate collapse to near zero — including reroutes onto providers with no caching
support at all. The `gpt-4o-mini` control switched 0/7 times across the idle gap.

Both models do switch providers under active traffic, though: `gpt-4o-mini` moved once on the
first request and then pinned permanently, while every `llama-3.3-70b` session touched three
distinct providers in six requests.

**Takeaway:** what matters is not whether a model switches providers but whether its whole pool
supports caching — 100% of `gpt-4o-mini`'s pool caches vs 42% of `llama-3.3-70b`'s, so only the
latter's switches are destructive.

Note when reading `SUMMARY2.md`: the `baseline hit` column is a mean across baseline requests that
were still warming (alternating contexts spaced consecutive same-context requests ~90s apart), so
it understates steady state. Idle probes exceeding it on the control reflect that, not a cache
improving while idle.

## Results

See `SUMMARY.md` and `SUMMARY2.md` for per-run data and verdicts.
