#!/usr/bin/env python3
"""OpenRouter cache-locality test: does cache/provider affinity degrade at ~5min or ~10min idle?"""
import json
import os
import threading
import time
import urllib.request
import urllib.error

MODEL = "openai/gpt-4o-mini"
API_BASE = "https://openrouter.ai/api/v1"


def load_api_key():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY"):
                _, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                if val:
                    return val
    raise RuntimeError("OPENROUTER_API_KEY not found or empty in .env")


API_KEY = load_api_key()


def gen_coding_prefix(target_tokens=15000):
    # ~4 chars/token heuristic. Synthetic, deterministic Python-like code, not copied from any real source.
    funcs = []
    for i in range(target_tokens // 76):
        funcs.append(
            f"def process_item_{i}(data, config=None):\n"
            f"    \"\"\"Synthetic helper #{i} for benchmarking cache locality.\"\"\"\n"
            f"    result = []\n"
            f"    for idx, value in enumerate(data):\n"
            f"        if value % {(i % 7) + 2} == 0:\n"
            f"            result.append(value * {(i % 5) + 1} - idx)\n"
            f"        else:\n"
            f"            result.append(value + idx)\n"
            f"    return result\n\n"
        )
    return "".join(funcs)


def gen_legal_prefix(target_tokens=15000):
    clauses = []
    for i in range(target_tokens // 92):
        clauses.append(
            f"Clause {i+1}.{(i % 9) + 1}: The party of the first part, hereinafter referred to as "
            f"'Licensee-{i}', agrees that the terms enumerated in Section {i % 12 + 1} shall govern "
            f"the disposition of any synthetic asset described herein, subject to the limitations "
            f"set forth in Appendix {chr(65 + (i % 6))}, and shall remain in full force and effect "
            f"until such time as either party provides written notice of termination.\n\n"
        )
    return "".join(clauses)


WORKLOADS = {
    "coding": gen_coding_prefix(),
    "legal": gen_legal_prefix(),
}

QUESTIONS = [
    "Summarize the overall structure above in two sentences.",
    "What pattern repeats most often in the content above?",
    "Give a one-sentence takeaway from the content above.",
    "Identify any numeric value that appears above and restate it.",
    "In one sentence, what would you check first if reviewing the above?",
    "State one word that best characterizes the tone of the above.",
]


def http_post_json(url, payload, stream=False):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
    )
    return urllib.request.urlopen(req, timeout=120)


def http_get_json(url):
    req = urllib.request.Request(
        url, method="GET", headers={"Authorization": f"Bearer {API_KEY}"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def send_request(prefix, question):
    """Returns dict with ttft_ms, total_ms, generation_id, error."""
    payload = {
        "model": MODEL,
        "stream": True,
        "usage": {"include": True},
        "messages": [
            {"role": "user", "content": prefix + "\n\n" + question},
        ],
    }
    start = time.time()
    ttft = None
    gen_id = None
    err = None
    try:
        resp = http_post_json(f"{API_BASE}/chat/completions", payload, stream=True)
        for raw_line in resp:
            line = raw_line.decode("utf-8", errors="ignore").strip()
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
        err = f"HTTPError {e.code}: {e.read().decode(errors='ignore')[:300]}"
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    total_ms = (time.time() - start) * 1000
    return {"ttft_ms": ttft, "total_ms": total_ms, "generation_id": gen_id, "error": err}


def fetch_generation_stats(gen_id, retries=8, delay=3.0):
    for _ in range(retries):
        try:
            data = http_get_json(f"{API_BASE}/generation?id={gen_id}")
            d = data.get("data", data)
            return {
                "provider_name": d.get("provider_name"),
                "cached_tokens": d.get("native_tokens_cached", d.get("cached_tokens")),
                "prompt_tokens": d.get("native_tokens_prompt", d.get("tokens_prompt")),
                "total_cost": d.get("total_cost"),
                "cache_discount": d.get("cache_discount"),
            }
        except Exception:
            time.sleep(delay)
    return {"provider_name": None, "cached_tokens": None, "prompt_tokens": None,
             "total_cost": None, "cache_discount": None}


_csv_locks = {}
_csv_locks_guard = threading.Lock()


def _lock_for(csv_path):
    with _csv_locks_guard:
        if csv_path not in _csv_locks:
            _csv_locks[csv_path] = threading.Lock()
        return _csv_locks[csv_path]


def csv_row(csv_path, row, header):
    lock = _lock_for(csv_path)
    with lock:
        is_new = not os.path.exists(csv_path)
        with open(csv_path, "a") as f:
            if is_new:
                f.write(",".join(header) + "\n")
            f.write(",".join(str(row.get(h, "")) for h in header) + "\n")


CSV_HEADER = [
    "timestamp", "workload", "session_id", "scenario", "gap_before_s", "ttft_ms", "total_ms",
    "provider_name", "cached_tokens", "prompt_tokens", "cache_hit_rate",
    "total_cost", "cache_discount", "error",
]


def run_one(workload_name, session_id, prefix, scenario, question_idx, gap_before_s, csv_path, log):
    q = QUESTIONS[question_idx % len(QUESTIONS)]
    result = send_request(prefix, q)
    stats = {}
    if result["generation_id"] and not result["error"]:
        stats = fetch_generation_stats(result["generation_id"])
    cache_hit_rate = None
    if stats.get("cached_tokens") is not None and stats.get("prompt_tokens"):
        try:
            cache_hit_rate = round(stats["cached_tokens"] / stats["prompt_tokens"], 4)
        except ZeroDivisionError:
            cache_hit_rate = None
    row = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "workload": workload_name,
        "session_id": session_id,
        "scenario": scenario,
        "gap_before_s": gap_before_s,
        "ttft_ms": round(result["ttft_ms"]) if result["ttft_ms"] else "",
        "total_ms": round(result["total_ms"]),
        "provider_name": stats.get("provider_name") or "",
        "cached_tokens": stats.get("cached_tokens") if stats.get("cached_tokens") is not None else "",
        "prompt_tokens": stats.get("prompt_tokens") if stats.get("prompt_tokens") is not None else "",
        "cache_hit_rate": cache_hit_rate if cache_hit_rate is not None else "",
        "total_cost": stats.get("total_cost") if stats.get("total_cost") is not None else "",
        "cache_discount": stats.get("cache_discount") if stats.get("cache_discount") is not None else "",
        "error": (result["error"] or "").replace(",", ";").replace("\n", " "),
    }
    csv_row(csv_path, row, CSV_HEADER)
    log(f"[{workload_name}/s{session_id}] {scenario} gap={gap_before_s}s ttft={row['ttft_ms']}ms "
        f"total={row['total_ms']}ms provider={row['provider_name']} "
        f"cache_hit={row['cache_hit_rate']} cost={row['total_cost']} err={row['error']}")
    return row


def run_workload(workload_name, session_id, prefix, csv_path, log):
    idx = 0

    # Baseline: 4 requests ~45s apart
    for i in range(4):
        run_one(workload_name, session_id, prefix, "baseline", idx, 45 if i > 0 else 0, csv_path, log)
        idx += 1
        if i < 3:
            time.sleep(45)

    last_request_time = time.time()

    # ~6 minute idle gap
    target_gap_1 = 360
    elapsed = time.time() - last_request_time
    if elapsed < target_gap_1:
        time.sleep(target_gap_1 - elapsed)
    gap1 = time.time() - last_request_time
    run_one(workload_name, session_id, prefix, "idle_6min", idx, round(gap1), csv_path, log)
    idx += 1
    last_request_time_2 = time.time()

    # ~11 minutes total idle since the pre-gap baseline request (5 more minutes from here)
    target_gap_2 = 300
    elapsed2 = time.time() - last_request_time_2
    if elapsed2 < target_gap_2:
        time.sleep(target_gap_2 - elapsed2)
    total_gap = time.time() - last_request_time
    run_one(workload_name, session_id, prefix, "idle_11min", idx, round(total_gap), csv_path, log)


def make_logger(prefix):
    lock = threading.Lock()
    def log(msg):
        with lock:
            print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)
    return log


SESSIONS_PER_WORKLOAD = 3


def summarize():
    import csv as csv_mod
    lines = ["# OpenRouter Cache Locality Test — Summary\n"]
    for name, path in [("Coding", "results_coding.csv"), ("Legal Research", "results_legal.csv")]:
        if not os.path.exists(path):
            continue
        with open(path) as f:
            rows = list(csv_mod.DictReader(f))
        session_ids = sorted(set(r["session_id"] for r in rows), key=lambda x: int(x))
        lines.append(f"\n## {name} workload ({len(session_ids)} sessions)\n")
        lines.append("| session | scenario | gap_before_s | ttft_ms | total_ms | provider | cache_hit_rate | total_cost | error |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            lines.append(
                f"| {r['session_id']} | {r['scenario']} | {r['gap_before_s']} | {r['ttft_ms']} | {r['total_ms']} | "
                f"{r['provider_name']} | {r['cache_hit_rate']} | {r['total_cost']} | {r['error']} |"
            )

        def avg(rs, field):
            vals = [float(r[field]) for r in rs if r[field] not in ("", None)]
            return round(sum(vals) / len(vals), 4) if vals else None

        lines.append("\n**Per-session comparison (baseline = last warm request before idle gap):**\n")
        lines.append("| session | baseline_hit | 6min_hit | 11min_hit | baseline_provider | 6min_provider | 11min_provider | 6min_missing_data | 11min_missing_data |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        degrade_6_count = 0
        degrade_11_count = 0
        valid_6_count = 0
        valid_11_count = 0
        for sid in session_ids:
            srows = [r for r in rows if r["session_id"] == sid]
            baseline = [r for r in srows if r["scenario"] == "baseline"]
            idle6 = [r for r in srows if r["scenario"] == "idle_6min"]
            idle11 = [r for r in srows if r["scenario"] == "idle_11min"]
            b_hit = avg(baseline, "cache_hit_rate")
            s6_hit = avg(idle6, "cache_hit_rate")
            s11_hit = avg(idle11, "cache_hit_rate")
            b_prov = baseline[-1]["provider_name"] if baseline and baseline[-1]["provider_name"] else None
            p6 = idle6[0]["provider_name"] if idle6 and idle6[0]["provider_name"] else None
            p11 = idle11[0]["provider_name"] if idle11 and idle11[0]["provider_name"] else None
            missing_6 = p6 is None or s6_hit is None
            missing_11 = p11 is None or s11_hit is None
            if not missing_6:
                valid_6_count += 1
                if b_hit is not None and (s6_hit < b_hit * 0.8 or p6 != b_prov):
                    degrade_6_count += 1
            if not missing_11:
                valid_11_count += 1
                if b_hit is not None and (s11_hit < b_hit * 0.8 or p11 != b_prov):
                    degrade_11_count += 1
            lines.append(
                f"| {sid} | {b_hit} | {s6_hit} | {s11_hit} | {b_prov} | {p6} | {p11} | {missing_6} | {missing_11} |"
            )

        lines.append(
            f"\n**{name} rollup:** degradation seen in {degrade_6_count}/{valid_6_count} sessions with valid data "
            f"at ~6min idle, and {degrade_11_count}/{valid_11_count} sessions with valid data at ~11min idle "
            f"(sessions with missing/failed generation-stats lookups excluded from these counts, not counted as degraded).\n"
        )
        if valid_6_count == 0 and valid_11_count == 0:
            verdict = "Insufficient valid data to draw a conclusion — generation-stats lookups failed across all sessions."
        elif degrade_6_count > 0 and degrade_6_count >= valid_6_count / 2:
            verdict = "Degradation consistently observed by ~6 min idle."
        elif degrade_11_count > 0 and degrade_11_count >= valid_11_count / 2:
            verdict = "No degradation at ~6 min, but observed by ~11 min in most sessions — consistent with OpenRouter's documented ~10min window."
        elif degrade_6_count == 0 and degrade_11_count == 0:
            verdict = "No degradation observed at ~6min or ~11min across any session — cache/provider affinity held steady."
        else:
            verdict = "Mixed/inconsistent results across sessions — provider switching appears intermittent rather than a fixed timeout."
        lines.append(f"**Verdict ({name}):** {verdict}\n")

    with open("SUMMARY.md", "w") as f:
        f.write("\n".join(lines))
    print("\nWrote SUMMARY.md")


def main():
    threads = []
    for name, prefix, csv_path in [
        ("coding", WORKLOADS["coding"], "results_coding.csv"),
        ("legal", WORKLOADS["legal"], "results_legal.csv"),
    ]:
        for session_id in range(SESSIONS_PER_WORKLOAD):
            log = make_logger(f"{name}")
            t = threading.Thread(
                target=run_workload, args=(name, session_id, prefix, csv_path, log)
            )
            t.start()
            threads.append(t)
    for t in threads:
        t.join()
    summarize()


if __name__ == "__main__":
    main()
