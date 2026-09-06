"""Stage 1 step 0: throughput measurement for ollama/llama3.1:8b.

100 single-token calls, sequential and at several concurrency levels.
"""
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

URL = "http://localhost:11434/api/generate"
MODEL = "llama3.1:8b"
PROMPT = ("# Problem\nYou are one member of an expert panel judging the "
          "following claim.\nClaim: \"The sky is blue on a clear day.\"\n"
          "Options:\nA) TRUE\nB) FALSE\n# Instruction\nGive your direct "
          "answer on which option is correct. Do NOT work through the "
          "problem, show any steps, compute, or explain — just commit to a "
          "snap judgement.\n## Response Format\nRespond with a single "
          "character, A or B, and nothing else.")


def call(seed):
    body = json.dumps({
        "model": MODEL, "prompt": PROMPT, "stream": False,
        "options": {"temperature": 0.7, "num_predict": 2, "seed": seed},
    }).encode()
    req = urllib.request.Request(URL, data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    return time.time() - t0, d["response"].strip()


def main():
    call(0)  # warmup
    # sequential 100
    t0 = time.time()
    resp = [call(i)[1] for i in range(100)]
    seq = (time.time() - t0) / 100
    from collections import Counter
    print(f"sequential: {seq:.3f} s/call; responses: {Counter(resp)}")
    for conc in (2, 4, 8, 16):
        t0 = time.time()
        with ThreadPoolExecutor(conc) as ex:
            list(ex.map(call, range(1000, 1000 + 100)))
        par = (time.time() - t0) / 100
        print(f"concurrency {conc}: {par:.3f} s/call effective")


if __name__ == "__main__":
    main()
