"""Stage 0.5 step 4: HMF unstable fixed point x_c per (model, family, w_T).

Threshold model with empirical P(k): each of the k inputs is independently
on the correct side with prob x; a correct-side input counts w_T, an
incorrect-side input counts 1; ties count 1/2. k = sum_j |J_ij| (edge signs
ignored — see notes). Outputs results/xc_hmf.csv.
"""
import os
from math import comb

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W_T = {"gpt": 2.294 / 1.979, "gma": 0.342 / 0.200,
       "qwn": 1.028 / 0.772, "lma": 1.152 / 0.837}
MODELS = ["gpt", "gma", "qwn", "lma"]
FAMILIES = ["random", "square", "triangular"]


def p_correct_next(k, x, w_T):
    tot = 0.0
    for l in range(k + 1):
        w = comb(k, l) * x**l * (1 - x)**(k - l)
        if w_T * l > (k - l):
            tot += w
        elif w_T * l == (k - l):
            tot += 0.5 * w
    return tot


def hmf_map(x, ks, ps, w_T):
    y = 0.0
    for k, pk in zip(ks, ps):
        y += pk * (x if k == 0 else p_correct_next(int(k), x, w_T))
    return y


def interior_roots(ks, ps, w_T, grid=4000):
    xs = np.linspace(0.0005, 0.9995, grid)
    f = np.array([hmf_map(x, ks, ps, w_T) - x for x in xs])
    roots = []
    for i in range(grid - 1):
        if f[i] == 0.0:
            roots.append((xs[i], None))
        elif f[i] * f[i + 1] < 0:
            # bisection refine
            lo, hi = xs[i], xs[i + 1]
            for _ in range(60):
                mid = (lo + hi) / 2
                if (hmf_map(lo, ks, ps, w_T) - lo) * (hmf_map(mid, ks, ps, w_T) - mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            root = (lo + hi) / 2
            # stability from slope of f = F(x) - x
            eps = 1e-4
            slope = ((hmf_map(root + eps, ks, ps, w_T)
                      - hmf_map(root - eps, ks, ps, w_T)) / (2 * eps))
            roots.append((root, "unstable" if slope > 1 else "stable"))
    return roots


def main():
    pk = pd.read_parquet(os.path.join(ROOT, "data", "pk_empirical.parquet"))
    rows = []
    for m in MODELS:
        for fam in FAMILIES:
            sub = pk[(pk.model == m) & (pk.family == fam)].sort_values("k")
            ks, ps = sub.k.to_numpy(), sub.p.to_numpy()
            for wt_label, wt in [("1", 1.0), ("table3", W_T[m])]:
                roots = interior_roots(ks, ps, wt)
                unstable = [r for r, s in roots if s == "unstable"]
                xc = unstable[0] if len(unstable) == 1 else (
                    np.nan if not unstable else unstable[0])
                rows.append({
                    "model": m, "family": fam, "w_T_label": wt_label,
                    "w_T": wt, "xc_hmf": xc,
                    "n_interior_roots": len(roots),
                    "n_unstable": len(unstable),
                    "all_roots": ";".join(f"{r:.4f}({s})" for r, s in roots)})
                print(f"{m}/{fam} w_T={wt:.3f}: roots="
                      f"{[f'{r:.4f}({s})' for r, s in roots]}")
    df = pd.DataFrame(rows)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    df.to_csv(os.path.join(ROOT, "results", "xc_hmf.csv"), index=False)

    # P(k) summary for notes
    print("\nP(k) per family (model gpt; graphs shared across models):")
    for fam in FAMILIES:
        sub = pk[(pk.model == "gpt") & (pk.family == fam)].sort_values("k")
        print(fam, {int(r.k): round(r.p, 4) for _, r in sub.iterrows()})


if __name__ == "__main__":
    main()
