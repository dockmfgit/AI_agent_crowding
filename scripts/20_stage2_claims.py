"""Stage 2 step 1: claim selection from the variant-A fixed effects.

No re-calibration with bare prompts (05 section 7-2). Refit the variant-A
model on Stage 1 main_obs and select claims with |FE| < 0.4 (relax to 0.6
if fewer than 10). Output: results/stage2_claims.csv
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "a14", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "14_analysis.py"))
a14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a14)
ROOT = a14.ROOT


def main():
    df = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                      "main_obs.parquet"))
    claim_ids = sorted(df.claim_id.unique())
    sub = df[df.self_state == "none"]
    S_C, S_W = a14.counts_drives(sub)
    X = a14.design(sub, claim_ids, S_C, S_W, with_self=False)
    b = a14.fit_logit(X, sub.y.to_numpy(float))
    fe = b[:len(claim_ids)]

    cal = pd.read_csv(os.path.join(ROOT, "results", "stage1_claims.csv"))
    cal["truth"] = cal.truth.map({True: "TRUE", False: "FALSE",
                                  "TRUE": "TRUE", "FALSE": "FALSE"})
    cal = cal.set_index("claim_id")

    rows = []
    for cid, f in zip(claim_ids, fe):
        rows.append({"claim_id": cid, "claim": cal.loc[cid, "claim"],
                     "label": cal.loc[cid, "label"],
                     "truth": cal.loc[cid, "truth"],
                     "h_q_bare": cal.loc[cid, "h_q"], "FE": f})
    out = pd.DataFrame(rows).sort_values("FE")
    for thr in (0.4, 0.6):
        out["selected"] = out.FE.abs() < thr
        n = int(out.selected.sum())
        print(f"|FE| < {thr}: {n} claims")
        if n >= 10:
            out["threshold"] = thr
            break
    out.to_csv(os.path.join(ROOT, "results", "stage2_claims.csv"), index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
