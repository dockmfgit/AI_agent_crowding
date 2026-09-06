"""Stage 2c Part B-3: qwen collective episodes against frozen predictions.

8 claims x alpha {0.30, 0.55} x x0 {2,6,10,14,18,22,26,30}/32 x 2 reps
= 256 episodes. Protocol identical to D-1. Run with
S2_MODEL=qwen3:8b S2_NOTHINK=1 (engine URL is 11435).
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

assert os.environ.get("S2_MODEL") == "qwen3:8b"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_s = importlib.util.spec_from_file_location(
    "drv", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "22_stage2_driver.py"))
drv = importlib.util.module_from_spec(_s)
_s.loader.exec_module(drv)
engine, ROOT = drv.engine, drv.ROOT

ALPHAS = [0.30, 0.55]
X0 = [2, 6, 10, 14, 18, 22, 26, 30]
N_REP = 2


def main():
    claims = pd.read_csv(os.path.join(ROOT, "data", "stage2c", "claims.csv"))
    claims["truth"] = claims.truth.map({True: "TRUE", False: "FALSE",
                                        "TRUE": "TRUE", "FALSE": "FALSE"})
    eps = []
    for cid in claims.claim_id:
        for a in ALPHAS:
            for x0 in X0:
                for r in range(N_REP):
                    eps.append({
                        "name": f"B3c_c{cid}_a{a:.2f}_x{x0:02d}_r{r:02d}",
                        "block": "B3c", "arm": "A", "alpha": float(a),
                        "x0_n": int(x0), "claim_id": int(cid),
                        "rep": int(r), "rho": 0, "spin_samples": 1,
                        "seed": drv.stable_seed("B3c", cid, a, x0, r)})
    eps.sort(key=lambda e: (e["rep"], e["alpha"], e["x0_n"], e["claim_id"]))
    todo = [e for e in eps if not os.path.exists(
        os.path.join(engine.EP_DIR, e["name"] + ".json"))]
    print(f"{len(eps)} episodes, {len(todo)} to run")
    t0 = time.time()
    done = [0]

    def work(e):
        dt = engine.run_episode(e, claims)
        done[0] += 1
        eta = (time.time() - t0) / done[0] * (len(todo) - done[0]) / 3600
        print(f"[{done[0]}/{len(todo)}] {e['name']} {dt:.0f}s ETA {eta:.1f}h",
              flush=True)

    with ThreadPoolExecutor(drv.EP_WORKERS) as ex:
        list(ex.map(work, todo))
    print(f"done in {(time.time() - t0) / 3600:.2f}h")


if __name__ == "__main__":
    main()
