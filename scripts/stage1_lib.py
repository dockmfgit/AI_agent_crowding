"""Shared infrastructure for Stage 1: ollama client, JSONL logging, parsing.

All calls go through run_batch(), which appends one JSONL record per call to
data/stage1/raw/<log_name>.jsonl: prompt sha256, condition metadata, seed,
raw response, parse result, timing.
"""
import hashlib
import json
import os
import re
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "stage1", "raw")
URL = os.environ.get("S2_URL", "http://localhost:11434/api/generate")
MODEL = os.environ.get("S2_MODEL", "llama3.1:8b")
TEMPERATURE = 0.7
CONCURRENCY = 8

_lock = threading.Lock()


def parse_ab(response):
    """El et al. _parse_spin_objective convention; 'A'/'B' or None."""
    text = response.strip().upper()
    if text in ("A", "B"):
        return text
    tokens = set(re.findall(r"\b([AB])\b", text))
    if tokens == {"A"}:
        return "A"
    if tokens == {"B"}:
        return "B"
    return None


def _call_once(prompt, seed, num_predict):
    payload = {
        "model": MODEL, "prompt": prompt, "stream": False,
        "options": {"temperature": TEMPERATURE, "num_predict": num_predict,
                    "seed": seed},
    }
    if os.environ.get("S2_NOTHINK"):
        payload["think"] = False
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["response"]


def run_batch(calls, log_name, num_predict=3, parse=parse_ab,
              conc=CONCURRENCY, retries=2):
    """calls: list of dicts with keys 'prompt', 'seed', 'condition' (jsonable).
    Returns list of records (same order). Appends each to the JSONL log."""
    os.makedirs(RAW_DIR, exist_ok=True)
    log_path = os.path.join(RAW_DIR, log_name + ".jsonl")
    logf = open(log_path, "a")
    t_start = time.time()
    done = [0]

    def work(idx_call):
        idx, call = idx_call
        last_err = None
        for attempt in range(retries + 1):
            try:
                t0 = time.time()
                resp = _call_once(call["prompt"], call["seed"] + attempt * 10**6,
                                  num_predict)
                rec = {
                    "idx": idx,
                    "prompt_sha256": hashlib.sha256(
                        call["prompt"].encode()).hexdigest(),
                    "condition": call["condition"],
                    "seed": call["seed"], "attempt": attempt,
                    "response": resp,
                    "parsed": parse(resp) if parse else None,
                    "latency_s": round(time.time() - t0, 4),
                }
                if parse is None or rec["parsed"] is not None:
                    break
                last_err = f"unparseable: {resp!r}"
            except Exception as e:  # noqa: BLE001
                last_err = str(e)
                rec = {"idx": idx, "condition": call["condition"],
                       "seed": call["seed"], "attempt": attempt,
                       "response": None, "parsed": None, "error": last_err}
                time.sleep(1.0)
        with _lock:
            logf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            done[0] += 1
            if done[0] % 500 == 0:
                rate = done[0] / (time.time() - t_start)
                print(f"  {done[0]}/{len(calls)} ({rate:.1f} calls/s)",
                      flush=True)
        return rec

    with ThreadPoolExecutor(conc) as ex:
        out = list(ex.map(work, enumerate(calls)))
    logf.close()
    return out
