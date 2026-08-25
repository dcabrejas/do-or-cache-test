#!/usr/bin/env python3
"""OpenRouter cache locality — test 2.

Addresses three limitations of test 1:
  1. Contested provider pool: meta-llama/llama-3.3-70b-instruct has ~13 providers
     (only ~5 support cache reads) vs gpt-4o-mini's 2 first-party providers.
  2. Idle gaps beyond 11 min: probes at 15 and 20 minutes.
  3. Mixed context lengths: alternates a long (~13k tok) and short (~4k tok) prefix,
     where the short prefix is a strict prefix of the long one (mirrors an agent
     whose context grows across turns).

gpt-4o-mini is re-run at the same gaps as a control, so any degradation can be
attributed to the provider pool rather than to the longer gap alone.
"""
import json
import os
import threading
import time
import urllib.request
import urllib.error

from cache_test import API_KEY, gen_coding_prefix, http_get_json

API_BASE = "https://openrouter.ai/api/v1"

MODELS = {
    "llama-3.3-70b": "meta-llama/llama-3.3-70b-instruct",
    "gpt-4o-mini": "openai/gpt-4o-mini",
}

GAPS_MIN = [15, 20]
SESSIONS_PER_COMBO = 2
BASELINE_REQUESTS = 4
BASELINE_INTERVAL_S = 45
MAX_TOKENS = 60

# Long prefix is reused verbatim from test 1 for comparability. Short prefix is a
# strict prefix of it, cut on a function boundary at ~4k tokens.
_LONG = gen_coding_prefix()
_CHUNKS = _LONG.split("\n\n")


def _build_short(target_chars=17700):
    out, n = [], 0
    for c in _CHUNKS:
        if n >= target_chars:
            break
        out.append(c)
        n += len(c) + 2
    return "\n\n".join(out) + "\n\n"


PREFIXES = {"long": _LONG, "short": _build_short()}

QUESTIONS = [
    "Summarize the overall structure above in two sentences.",
    "What pattern repeats most often in the content above?",
    "Give a one-sentence takeaway from the content above.",
    "Identify any numeric value that appears above and restate it.",
    "In one sentence, what would you check first if reviewing the above?",
    "State one word that best characterizes the tone of the above.",
]

CSV_HEADER = [
    "timestamp", "model", "gap_min", "session_id", "scenario", "ctx",
    "gap_before_s", "ttft_ms", "total_ms", "provider_name", "provider_caches",
    "cached_tokens", "prompt_tokens", "cache_hit_rate", "total_cost",
    "cache_discount", "error",
]

CSV_PATH = "results2.csv"
SUMMARY_PATH = "SUMMARY2.md"


def fetch_cache_capable_providers(model_id):
    """Providers for this model that advertise cache-read pricing."""
    try:
        d = http_get_json(f"{API_BASE}/models/{model_id}/endpoints")["data"]
        eps = d.get("endpoints", [])
        capable = {
            e["provider_name"]
            for e in eps
            if float((e.get("pricing") or {}).get("input_cache_read") or 0) > 0
        }
        return capable, {e.get("provider_name") for e in eps}
    except Exception:
        return set(), set()


CACHE_CAPABLE = {}
ALL_PROVIDERS = {}


def send_request(model_id, prefix, question):
    payload = {
        "model": model_id,
        "stream": True,
        "max_tokens": MAX_TOKENS,
        "usage": {"include": True},
        "messages": [{"role": "user", "content": prefix + "\n\n" + question}],
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    start = time.time()
    ttft = None
    gen_id = None
    err = None
    try:
        resp = urllib.request.urlopen(req, timeout=180)
        for raw in resp:
            line = raw.decode("utf-8", errors="ignore").strip()
            if not line or not line.startswith("data:"):
                continue
            content = line[len("data:"):].strip()
            if content == "[DONE]":
                break
            if ttft is None:
                ttft = (time.time() - start) * 1000
            try:
                obj = json.loads(content)
                if gen_id is None and obj.get("id"):
                    gen_id = obj["id"]
            except json.JSONDecodeError:
                pass
        resp.close()
    except urllib.error.HTTPError as e:
        err = f"HTTPError {e.code}: {e.read().decode(errors='ignore')[:200]}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    return {
        "ttft_ms": ttft,
        "total_ms": (time.time() - start) * 1000,
        "generation_id": gen_id,
        "error": err,
    }


def fetch_generation_stats(gen_id, retries=8, delay=3.0):
    for _ in range(retries):
        try:
            d = http_get_json(f"{API_BASE}/generation?id={gen_id}")
            d = d.get("data", d)
            return {
                "provider_name": d.get("provider_name"),
                "cached_tokens": d.get("native_tokens_cached", d.get("cached_tokens")),
                "prompt_tokens": d.get("native_tokens_prompt", d.get("tokens_prompt")),
                "total_cost": d.get("total_cost"),
                "cache_discount": d.get("cache_discount"),
            }
        except Exception:
            time.sleep(delay)
    return {}


_csv_lock = threading.Lock()


def csv_row(row):
    with _csv_lock:
        is_new = not os.path.exists(CSV_PATH)
        with open(CSV_PATH, "a") as f:
            if is_new:
                f.write(",".join(CSV_HEADER) + "\n")
            f.write(",".join(str(row.get(h, "")) for h in CSV_HEADER) + "\n")


_print_lock = threading.Lock()


def log(msg):
    with _print_lock:
        print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


def run_one(model_key, model_id, gap_min, session_id, scenario, ctx, q_idx, gap_before_s):
    res = send_request(model_id, PREFIXES[ctx], QUESTIONS[q_idx % len(QUESTIONS)])
    stats = {}
    if res["generation_id"] and not res["error"]:
        stats = fetch_generation_stats(res["generation_id"])

    cached = stats.get("cached_tokens")
    prompt = stats.get("prompt_tokens")
    hit = None
    if cached is not None and prompt:
        hit = round(cached / prompt, 4)

    prov = stats.get("provider_name")
    caches = ""
    if prov:
        caches = "yes" if prov in CACHE_CAPABLE.get(model_key, set()) else "no"

    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": model_key,
        "gap_min": gap_min,
        "session_id": session_id,
        "scenario": scenario,
        "ctx": ctx,
        "gap_before_s": gap_before_s,
        "ttft_ms": round(res["ttft_ms"]) if res["ttft_ms"] else "",
        "total_ms": round(res["total_ms"]),
        "provider_name": prov or "",
        "provider_caches": caches,
        "cached_tokens": cached if cached is not None else "",
        "prompt_tokens": prompt if prompt is not None else "",
        "cache_hit_rate": hit if hit is not None else "",
        "total_cost": stats.get("total_cost") if stats.get("total_cost") is not None else "",
        "cache_discount": stats.get("cache_discount") if stats.get("cache_discount") is not None else "",
        "error": (res["error"] or "").replace(",", ";").replace("\n", " "),
    }
    csv_row(row)
    log(f"[{model_key} g{gap_min} s{session_id}] {scenario}/{ctx} "
        f"gap={gap_before_s}s ttft={row['ttft_ms']} prov={row['provider_name']}"
        f"({caches}) hit={row['cache_hit_rate']} cost={row['total_cost']} {row['error']}")
    return row


def run_session(model_key, model_id, gap_min, session_id):
    idx = 0
    # Baseline alternates long/short to create the mixed-context condition.
    for i in range(BASELINE_REQUESTS):
        ctx = "long" if i % 2 == 0 else "short"
        run_one(model_key, model_id, gap_min, session_id, "baseline", ctx,
                idx, 0 if i == 0 else BASELINE_INTERVAL_S)
        idx += 1
        if i < BASELINE_REQUESTS - 1:
            time.sleep(BASELINE_INTERVAL_S)

    last = time.time()
    target = gap_min * 60
    elapsed = time.time() - last
    if elapsed < target:
        time.sleep(target - elapsed)

    scen = f"idle_{gap_min}min"
    actual_gap = round(time.time() - last)
    run_one(model_key, model_id, gap_min, session_id, scen, "long", idx, actual_gap)
    idx += 1
    # Immediately probe the short prefix too: did the shorter shared prefix
    # survive the same gap?
    t = time.time()
    time.sleep(5)
    run_one(model_key, model_id, gap_min, session_id, scen, "short", idx,
            round(time.time() - t))


def avg(rows, field):
    vals = [float(r[field]) for r in rows if r.get(field) not in ("", None)]
    return round(sum(vals) / len(vals), 4) if vals else None


def summarize():
    import csv as csv_mod
    if not os.path.exists(CSV_PATH):
        print("no results")
        return
    with open(CSV_PATH) as f:
        rows = list(csv_mod.DictReader(f))

    out = ["# OpenRouter Cache Locality — Test 2\n",
           "Extends test 1 with a contested provider pool, idle gaps beyond 11 minutes, "
           "and mixed context lengths.\n"]

    out.append("\n## Provider pools\n")
    out.append("| model | providers available | cache-capable |")
    out.append("|---|---|---|")
    for mk in MODELS:
        out.append(f"| {mk} | {len(ALL_PROVIDERS.get(mk, []))} | "
                   f"{len(CACHE_CAPABLE.get(mk, []))} |")

    for mk in MODELS:
        mrows = [r for r in rows if r["model"] == mk]
        if not mrows:
            continue
        out.append(f"\n## {mk}\n")
        out.append("| gap | session | scenario | ctx | provider | caches? | cached tok | hit | TTFT ms | cost | error |")
        out.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for r in mrows:
            out.append(
                f"| {r['gap_min']} | {r['session_id']} | {r['scenario']} | {r['ctx']} | "
                f"{r['provider_name']} | {r['provider_caches']} | {r['cached_tokens']} | "
                f"{r['cache_hit_rate']} | {r['ttft_ms']} | {r['total_cost']} | {r['error']} |")

        out.append(f"\n**{mk} — baseline vs idle, per session**\n")
        out.append("| gap | session | ctx | baseline hit | idle hit | baseline provider | idle provider | switched? |")
        out.append("|---|---|---|---|---|---|---|---|")
        switches = 0
        drops = 0
        comparable = 0
        for gap in GAPS_MIN:
            for sid in range(SESSIONS_PER_COMBO):
                for ctx in ("long", "short"):
                    base = [r for r in mrows if r["gap_min"] == str(gap)
                            and r["session_id"] == str(sid) and r["scenario"] == "baseline"
                            and r["ctx"] == ctx]
                    idle = [r for r in mrows if r["gap_min"] == str(gap)
                            and r["session_id"] == str(sid)
                            and r["scenario"].startswith("idle") and r["ctx"] == ctx]
                    if not base or not idle:
                        continue
                    bh, ih = avg(base, "cache_hit_rate"), avg(idle, "cache_hit_rate")
                    bp = base[-1]["provider_name"] or None
                    ip = idle[0]["provider_name"] or None
                    if bp and ip:
                        comparable += 1
                        sw = bp != ip
                        if sw:
                            switches += 1
                        if bh is not None and ih is not None and bh > 0 and ih < bh * 0.8:
                            drops += 1
                        swtxt = "**YES**" if sw else "no"
                    else:
                        swtxt = "n/a (missing data)"
                    out.append(f"| {gap} | {sid} | {ctx} | {bh} | {ih} | {bp} | {ip} | {swtxt} |")

        out.append(f"\n**{mk} rollup:** {switches}/{comparable} comparisons changed provider "
                   f"after the idle gap; {drops}/{comparable} showed a cache-hit drop >20%. "
                   f"(Comparisons with missing provider data are excluded, not counted as degraded.)\n")

    with open(SUMMARY_PATH, "w") as f:
        f.write("\n".join(out))
    print(f"\nWrote {SUMMARY_PATH}")


def main():
    for mk, mid in MODELS.items():
        cap, allp = fetch_cache_capable_providers(mid)
        CACHE_CAPABLE[mk] = cap
        ALL_PROVIDERS[mk] = allp
        log(f"{mk}: {len(allp)} providers, {len(cap)} cache-capable")

    log(f"prefix sizes: long={len(PREFIXES['long'])} chars, short={len(PREFIXES['short'])} chars")

    threads = []
    for mk, mid in MODELS.items():
        for gap in GAPS_MIN:
            for sid in range(SESSIONS_PER_COMBO):
                t = threading.Thread(target=run_session, args=(mk, mid, gap, sid))
                t.start()
                threads.append(t)
    log(f"started {len(threads)} sessions")
    for t in threads:
        t.join()
    summarize()


if __name__ == "__main__":
    main()
