"""Prediction-side uncertainty of the claim-level fixed-point predictions.

For every claim used in the qwen3:8b collectives (stage 2d: 6, 1239, 1569,
91569; stage 2c: the eight selected claims) the per-claim reduced divisive
response  logit p = c0 + g(k)[delta k + beta_bar (2l - k)],  g = 1/(1+0.9k),
is refitted on B design-fixed bootstrap resamples of that claim's single-shot
queries (outcomes resampled with replacement within each (k, l) cell, so the
randomized design is held fixed), and the fixed points of the mean-field map
are recomputed for every resample.  Output per (claim, alpha):

  results/r5_prediction_intervals.csv
     point prediction (class, x_c), bootstrap fraction of resamples in each
     class, percentile interval of x_c among bistable resamples, and the
     observed threshold/CI from results/r23_repred_stage2{c,d}.csv.

Usage: python scripts/55_prediction_intervals.py [PROJECT_ROOT] [B=200]
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hmf_lib as H  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
B = int(sys.argv[2]) if len(sys.argv) > 2 else 200
RES = os.path.join(ROOT, "results")
DATA = os.path.join(ROOT, "data")
GAMMA, RIDGE = 0.9, 1e-3
RNG = np.random.default_rng(55)

CAMPAIGNS = {
    "stage2c": {"claims": [97, 184, 590, 656, 832, 1013, 1146, 1151], "alphas": [0.30, 0.55]},
    "stage2d": {"claims": [6, 1239, 1569, 91569], "alphas": [0.30, 0.55, 1.00]},
}


def fit(df):
    X, _ = H.design_reduced(df, GAMMA, False)
    return H.fit_logit_ridge(X, df.y.to_numpy(float), ridge=RIDGE)


def phase(b, alpha):
    fps = H.fixed_points(alpha, H.response_reduced(b, GAMMA), n_grid=2001)
    return H.classify(fps)


def main():
    rows = []
    for st, spec in CAMPAIGNS.items():
        obs = pd.read_parquet(os.path.join(DATA, st, "single_obs.parquet"))
        rep = pd.read_csv(os.path.join(RES, f"r23_repred_{st}.csv"))
        for cid in spec["claims"]:
            d = obs[obs.claim_id == cid].reset_index(drop=True)
            b0 = fit(d)
            cells = d.groupby(["k", "l"]).indices
            boots = []
            for _ in range(B):
                idx = np.concatenate([RNG.choice(ix, len(ix), replace=True) for ix in cells.values()])
                boots.append(fit(d.iloc[idx]))
            for a in spec["alphas"]:
                cl0, xc0 = phase(b0, a)
                cls, xcs = [], []
                for b in boots:
                    c, x = phase(b, a)
                    cls.append(c)
                    if x is not None:
                        xcs.append(x)
                cls = pd.Series(cls)
                o = rep[(rep.claim_id == cid) & (np.isclose(rep.alpha, a))].iloc[0]
                rows.append({
                    "campaign": st, "claim_id": cid, "alpha": a, "n_queries": len(d), "n_boot": B,
                    "pred_class": cl0, "pred_xc": xc0,
                    "frac_bistable": float((cls == "bistable").mean()),
                    "frac_mono_correct": float((cls == "mono_correct").mean()),
                    "frac_mono_wrong": float((cls == "mono_wrong").mean()),
                    "xc_lo": float(np.percentile(xcs, 2.5)) if len(xcs) >= 10 else np.nan,
                    "xc_hi": float(np.percentile(xcs, 97.5)) if len(xcs) >= 10 else np.nan,
                    "xc_median": float(np.median(xcs)) if xcs else np.nan,
                    "obs_class": o.obs_class, "obs_cross": o.obs_cross,
                    "obs_ci_lo": o.obs_ci_lo, "obs_ci_hi": o.obs_ci_hi,
                })
                print(rows[-1], flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, "r5_prediction_intervals.csv"), index=False)
    print(out.round(3).to_string())


if __name__ == "__main__":
    main()
