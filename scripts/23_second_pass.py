"""Stage 2 arm A second pass (adaptive), per instructions section 4.

For each alpha: pick the 3 x0 levels whose first-pass q is closest to 0.5
and add 24 episodes each. Exception: for alpha in {0.45, 0.55, 1.00}, if q
exceeds 0.8 at every x0 level, put the additional episodes on the lowest
x0 levels (4, 8) instead, 36 each, to sharpen the low-x0 convergence check.

Run only after B1 (and B4 if included) are complete:
  python 23_second_pass.py [--alphas 0.30,0.38,0.45,0.55]
"""
import argparse
import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_s = importlib.util.spec_from_file_location(
    "drv", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "22_stage2_driver.py"))
drv = importlib.util.module_from_spec(_s)
_s.loader.exec_module(drv)
engine, ROOT = drv.engine, drv.ROOT

X0_A = drv.X0_A
N_ADD = 24
DELTA = 0.10


def first_pass_q(alpha):
    qs = {}
    for x0 in X0_A:
        xs = []
        for fp in glob.glob(os.path.join(
                engine.EP_DIR, f"B[14]_armA_a{alpha:.2f}_x{x0:02d}_r*.json")):
            d = json.load(open(fp))
            if d["meta"].get("rho", 0):
                continue
            x8 = float(np.mean(d["stance_history"][8]))
            xs.append(x8 >= 0.5 + DELTA)
        qs[x0] = (np.mean(xs) if xs else np.nan, len(xs))
    return qs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--alphas", default="0.30,0.38,0.45,0.55,0.20,1.00")
    args = ap.parse_args()
    claims = drv.load_claims()
    eps = []
    for alpha in [float(a) for a in args.alphas.split(",")]:
        qs = first_pass_q(alpha)
        print(f"alpha={alpha}: q per x0 =",
              {k: (round(v[0], 2) if np.isfinite(v[0]) else None, v[1])
               for k, v in qs.items()})
        valid = {k: v[0] for k, v in qs.items() if np.isfinite(v[0])}
        if len(valid) < len(X0_A):
            print(f"  first pass incomplete, skipping alpha={alpha}")
            continue
        if alpha in (0.45, 0.55, 1.00) and min(valid.values()) > 0.8:
            targets = {4: 36, 8: 36}
            mode = "low-x0 sharpening (all q > 0.8)"
        else:
            picked = sorted(valid, key=lambda k: abs(valid[k] - 0.5))[:3]
            targets = {x0: N_ADD for x0 in picked}
            mode = f"closest-to-0.5: {sorted(picked)}"
        print(f"  -> {mode}")
        for x0, n_add in targets.items():
            cl = drv.assign_claims(claims, "A2", alpha, x0, n_add)
            for r in range(n_add):
                rep = 100 + r      # second-pass reps start at 100
                eps.append({
                    "name": f"B6_armA_a{alpha:.2f}_x{x0:02d}_r{rep:03d}",
                    "block": "B6", "arm": "A", "alpha": float(alpha),
                    "x0_n": int(x0), "claim_id": int(cl[r]), "rep": rep,
                    "rho": 0, "spin_samples": 1,
                    "seed": drv.stable_seed("B6", "A", alpha, x0, rep),
                })
    todo = [e for e in eps if not os.path.exists(
        os.path.join(engine.EP_DIR, e["name"] + ".json"))]
    print(f"{len(eps)} second-pass episodes, {len(todo)} to run")
    t0 = time.time()
    done = [0]

    def work(e):
        dt = engine.run_episode(e, claims)
        done[0] += 1
        print(f"[{done[0]}/{len(todo)}] {e['name']} {dt:.0f}s", flush=True)

    with ThreadPoolExecutor(drv.EP_WORKERS) as ex:
        list(ex.map(work, todo))
    print(f"done in {(time.time() - t0) / 3600:.2f}h")


if __name__ == "__main__":
    main()
