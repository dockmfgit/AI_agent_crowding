"""Stage 2 driver: enumerate episodes by block priority, run resumably.

Blocks (priority order per instructions section 8):
  B1 arm A core:   alpha {0.30,0.38,0.45,0.55} x x0 {4,8,12,16,20,24} x 16
  B2 arm B:        alpha {0.60,0.90,1.30} x x0 {4,10,16,22,28} x 20
  B3 rho control:  alpha 0.30, rho=1, x0 {4..24} x 16
  B4 arm A anchor: alpha {0.20,1.00} x x0 {4..24} x 16
  B5 fidelity:     alpha 0.30, x0 16, 5-sample spins, 10 eps
(second adaptive pass is launched separately once B1 committors exist)

Usage: python 22_stage2_driver.py [--blocks B1,B2] [--trial]
Episodes are skipped if their JSON already exists. 3 episodes run
concurrently; per-episode timing appended to data/stage2/timing.csv.
"""
import argparse
import hashlib
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec_ = importlib.util.spec_from_file_location(
    "engine", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "21_stage2_engine.py"))
engine = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(engine)
ROOT = engine.ROOT

EP_WORKERS = 3

X0_A = [4, 8, 12, 16, 20, 24]
X0_B = [4, 10, 16, 22, 28]


def stable_seed(*parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).digest()
    return int.from_bytes(h[:6], "big")


def load_claims():
    df = pd.read_csv(os.path.join(ROOT, "results", "stage2_claims.csv"))
    df["truth"] = df.truth.map({True: "TRUE", False: "FALSE",
                                "TRUE": "TRUE", "FALSE": "FALSE"})
    return df[df.selected].reset_index(drop=True)


def assign_claims(claims, arm, alpha, x0, n_reps):
    """Cycle a cell-seeded shuffle of claims across reps (stratified)."""
    rng = np.random.default_rng(stable_seed("claims", arm, alpha, x0))
    ids = list(claims.claim_id)
    order = []
    while len(order) < n_reps:
        idx = list(rng.permutation(len(ids)))
        order += [ids[i] for i in idx]
    return order[:n_reps]


def build_block(block, claims):
    eps = []
    if block == "B1":
        arms, alphas, x0s, reps, rho, ss = "A", [0.30, 0.38, 0.45, 0.55], X0_A, 16, 0, 1
    elif block == "B2":
        arms, alphas, x0s, reps, rho, ss = "B", [0.60, 0.90, 1.30], X0_B, 20, 0, 1
    elif block == "B3":
        arms, alphas, x0s, reps, rho, ss = "A", [0.30], X0_A, 16, 1, 1
    elif block == "B4":
        arms, alphas, x0s, reps, rho, ss = "A", [0.20, 1.00], X0_A, 16, 0, 1
    elif block == "B5":
        arms, alphas, x0s, reps, rho, ss = "A", [0.30], [16], 10, 0, 5
    else:
        raise ValueError(block)
    for alpha in alphas:
        for x0 in x0s:
            cl = assign_claims(claims, arms, alpha, x0, reps)
            for r in range(reps):
                tag = f"{block}_arm{arms}_a{alpha:.2f}_x{x0:02d}_r{r:02d}"
                if rho:
                    tag += "_rho1"
                if ss > 1:
                    tag += "_5s"
                eps.append({
                    "name": tag, "block": block, "arm": arms,
                    "alpha": float(alpha), "x0_n": int(x0),
                    "claim_id": int(cl[r]), "rep": int(r), "rho": int(rho),
                    "spin_samples": int(ss),
                    "seed": stable_seed(block, arms, alpha, x0, r, rho, ss),
                })
    # order by rep first so partial data is balanced across cells
    eps.sort(key=lambda e: (e["rep"], e["alpha"], e["x0_n"]))
    return eps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blocks", default="B1,B2,B3,B4,B5")
    ap.add_argument("--trial", action="store_true")
    args = ap.parse_args()
    claims = load_claims()
    print(f"{len(claims)} claims: {list(claims.claim_id)}")

    if args.trial:
        eps = []
        for r in range(3):
            eps.append({"name": f"trial_a0.30_x16_r{900 + r}", "block": "trial",
                        "arm": "A", "alpha": 0.30, "x0_n": 16,
                        "claim_id": int(claims.claim_id[r % len(claims)]),
                        "rep": 900 + r, "rho": 0, "spin_samples": 1,
                        "seed": stable_seed("trial", r)})
    else:
        eps = []
        for b in args.blocks.split(","):
            eps += build_block(b.strip(), claims)
    todo = [e for e in eps
            if not os.path.exists(os.path.join(engine.EP_DIR,
                                               e["name"] + ".json"))]
    print(f"{len(eps)} episodes in plan, {len(todo)} to run")

    timing_path = os.path.join(ROOT, "data", "stage2", "timing.csv")
    os.makedirs(os.path.dirname(timing_path), exist_ok=True)
    t0 = time.time()
    done = [0]

    def work(e):
        dt = engine.run_episode(e, claims)
        done[0] += 1
        with open(timing_path, "a") as f:
            f.write(f"{e['name']},{dt:.1f}\n")
        el = time.time() - t0
        rate = el / done[0]
        eta_h = rate * (len(todo) - done[0]) / 3600
        print(f"[{done[0]}/{len(todo)}] {e['name']} {dt:.0f}s "
              f"(avg {rate:.0f}s/ep, ETA {eta_h:.1f}h)", flush=True)
        return dt

    with ThreadPoolExecutor(EP_WORKERS) as ex:
        list(ex.map(work, todo))
    print(f"finished {len(todo)} episodes in {(time.time() - t0) / 3600:.2f}h")


if __name__ == "__main__":
    main()
