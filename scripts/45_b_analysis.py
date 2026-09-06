"""Stage 2c Part B-4: frozen predictions vs observed boundaries.

Per claim x alpha: monotone logistic fit of P(correct outcome, delta=0.1)
vs x0 -> 50% crossing + episode bootstrap 95% CI; all-same-sign cells are
classified monostable. Agreement table + threshold scatter + Spearman rank
correlation (>=4 bistable points).
Outputs: results/stage2c_group.csv, results/stage2c_thresholds.csv
"""
import glob
import json
import os

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import spearmanr

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP = os.path.join(ROOT, "data", "stage2", "episodes")
RNG = np.random.default_rng(53)


def fit_cross(x, y):
    """2-parameter logistic MLE; returns crossing -a/b or None."""
    if y.min() == y.max():
        return None

    def nll(w):
        z = np.clip(w[0] + w[1] * x, -30, 30)
        p = np.clip(1 / (1 + np.exp(-z)), 1e-12, 1 - 1e-12)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
    best = None
    for x0 in ([0.0, 5.0], [0.0, 20.0], [-2.0, 10.0]):
        r = minimize(nll, np.array(x0), method="BFGS")
        if best is None or r.fun < best.fun:
            best = r
    a, b = best.x
    return None if b == 0 else -a / b


def main():
    rows = []
    for fp in sorted(glob.glob(os.path.join(EP, "B3c_*.json"))):
        d = json.load(open(fp))
        m = d["meta"]
        x8 = float(np.mean(d["stance_history"][8]))
        rows.append({"claim_id": m["claim_id"], "alpha": m["alpha"],
                     "x0_n": m["x0_n"], "x0": m["x0_n"] / 32, "rep": m["rep"],
                     "x8": x8, "fails": m["n_parse_fail"]})
    df = pd.DataFrame(rows)
    print(f"{len(df)} episodes, parse fails {df.fails.sum()}")
    df["correct"] = (df.x8 >= 0.6).astype(float)
    df["wrong"] = (df.x8 <= 0.4).astype(float)
    df.to_csv(os.path.join(ROOT, "results", "stage2c_group.csv"), index=False)

    bp = pd.read_csv(os.path.join(ROOT, "results",
                                  "stage2c_blind_predictions.csv"))
    out = []
    for (cid, a), sub in df.groupby(["claim_id", "alpha"]):
        pr = bp[(bp.claim_id == cid) & (bp.alpha == a)].iloc[0]
        pred_cls = pr["class"]
        x, y = sub.x0.to_numpy(), sub.correct.to_numpy()
        if y.min() == y.max():
            obs_cls = "mono_correct" if y.min() == 1 else (
                "mono_wrong" if sub.wrong.min() == 1 else "mono_undecided")
            cross, lo, hi = np.nan, np.nan, np.nan
        else:
            cross = fit_cross(x, y)
            boots = []
            n = len(sub)
            for _ in range(1000):
                idx = RNG.integers(0, n, n)
                c = fit_cross(x[idx], y[idx])
                if c is not None and -1 < c < 2:
                    boots.append(c)
            lo, hi = (np.percentile(boots, [2.5, 97.5])
                      if len(boots) > 100 else (np.nan, np.nan))
            obs_cls = (f"bistable(cross={cross:.3f})"
                       if cross is not None and 0 < cross < 1 else "mixed")
        pred_xc = (float(pred_cls.split("=")[1].rstrip(")"))
                   if pred_cls.startswith("bistable") else np.nan)
        match = (
            "hit" if (pred_cls.startswith("bistable")
                      and obs_cls.startswith("bistable")) or
                     (pred_cls == obs_cls) else
            "partial" if (pred_cls.startswith("bistable")
                          != obs_cls.startswith("bistable")
                          and "mono" in pred_cls + obs_cls) else "miss")
        out.append({"claim_id": cid, "alpha": a, "pred_class": pred_cls,
                    "pred_xc": pred_xc, "obs_class": obs_cls,
                    "obs_cross": cross if cross is not None else np.nan,
                    "cross_ci_lo": lo, "cross_ci_hi": hi,
                    "n_correct": int(sub.correct.sum()),
                    "n_wrong": int(sub.wrong.sum()),
                    "n_undecided": int(((sub.x8 > 0.4)
                                        & (sub.x8 < 0.6)).sum()),
                    "match": match})
    th = pd.DataFrame(out)
    th.to_csv(os.path.join(ROOT, "results", "stage2c_thresholds.csv"),
              index=False)
    print(th.to_string(index=False))

    both = th[th.pred_xc.notna() & th.obs_cross.notna()
              & th.obs_class.str.startswith("bistable")]
    if len(both) >= 4:
        r, p = spearmanr(both.pred_xc, both.obs_cross)
        print(f"\nSpearman rank corr (n={len(both)} bistable cells): "
              f"rho={r:.3f}, p={p:.4f}")
    print("\nagreement counts:", th.match.value_counts().to_dict())


if __name__ == "__main__":
    main()
