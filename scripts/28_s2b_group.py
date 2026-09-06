"""Stage 2b group experiments driver (protocol identical to Stage 2 arm A).

A-1: 3 SUPPORTS claims x alpha {0.30, 0.55} x x0 {4,12,20,28} x 12 reps = 288
A-2: 4 paraphrase claims x alpha 0.30 x x0 {4,12,20,28} x 12 reps = 192
     (gated behind --approved: do not run before user approval)

Usage: python 28_s2b_group.py --set A1 [--set A2 --approved]
"""
import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
_s = importlib.util.spec_from_file_location(
    "drv", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "22_stage2_driver.py"))
drv = importlib.util.module_from_spec(_s)
_s.loader.exec_module(drv)
engine, ROOT = drv.engine, drv.ROOT

X0 = [4, 12, 20, 28]
N_REP = 12


def load_claims(cset):
    df = pd.read_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"))
    df["truth"] = df.truth.map({True: "TRUE", False: "FALSE",
                                "TRUE": "TRUE", "FALSE": "FALSE"})
    return df[df["set"] == cset].reset_index(drop=True)


def build(cset, alphas):
    claims = load_claims(cset)
    eps = []
    for _, c in claims.iterrows():
        for alpha in alphas:
            for x0 in X0:
                for r in range(N_REP):
                    eps.append({
                        "name": (f"S2b_{cset}_c{c.claim_id}_a{alpha:.2f}"
                                 f"_x{x0:02d}_r{r:02d}"),
                        "block": f"S2b_{cset}", "arm": "A",
                        "alpha": float(alpha), "x0_n": int(x0),
                        "claim_id": int(c.claim_id), "rep": int(r), "rho": 0,
                        "spin_samples": 1,
                        "seed": drv.stable_seed("S2b", cset, c.claim_id,
                                                alpha, x0, r)})
    eps.sort(key=lambda e: (e["rep"], e["alpha"], e["x0_n"], e["claim_id"]))
    return claims, eps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="cset", required=True,
                    choices=["A1", "A2"])
    ap.add_argument("--approved", action="store_true")
    args = ap.parse_args()
    if args.cset == "A2" and not args.approved:
        sys.exit("A2 group runs require --approved (user approval gate)")
    cset = "A1_supports" if args.cset == "A1" else "A2_paraphrase"
    alphas = [0.30, 0.55] if args.cset == "A1" else [0.30]
    claims, eps = build(cset, alphas)
    todo = [e for e in eps if not os.path.exists(
        os.path.join(engine.EP_DIR, e["name"] + ".json"))]
    print(f"{len(eps)} episodes, {len(todo)} to run "
          f"({len(claims)} claims: {list(claims.claim_id)})")
    t0 = time.time()
    done = [0]

    def work(e):
        dt = engine.run_episode(e, claims)
        done[0] += 1
        el = time.time() - t0
        eta = el / done[0] * (len(todo) - done[0]) / 3600
        print(f"[{done[0]}/{len(todo)}] {e['name']} {dt:.0f}s ETA {eta:.1f}h",
              flush=True)

    with ThreadPoolExecutor(drv.EP_WORKERS) as ex:
        list(ex.map(work, todo))
    print(f"done in {(time.time() - t0) / 3600:.2f}h")


if __name__ == "__main__":
    main()
