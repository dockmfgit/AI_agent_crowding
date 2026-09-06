"""Stage 2b blind predictions: per-claim HMF fixed points from the mini
single-call coefficients, frozen BEFORE the group experiments.

Rule: P(next correct | k, l) = sigmoid(c0_q + bT(k) l + bF(k) (k-l)),
coefficients log-log interpolated over measured k in {2,5,8}, power-law
extrapolated outside; k=0 -> sigmoid(c0_q pooled).
Network: P_alpha(k), N=32 (same as scripts/29).

Output: results/stage2b_blind_predictions.csv (+ printed table for notes).
"""
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import binom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N_AGENTS = 32


def p_alpha_k(alpha, n=N_AGENTS):
    m = n - 1
    P = np.zeros(m + 1)
    P[0] = 1.0
    acc = np.exp(-alpha * np.arange(m + 1))
    for _ in range(m):
        Q = P * (1 - acc)
        Q[1:] += P[:-1] * acc[:-1]
        P = Q
    return P


def sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def make_coef(sub):
    """sub: per-k rows for one claim (k in {2,5,8})."""
    ks = np.array([2.0, 5.0, 8.0])
    bT = np.array([float(sub[sub.k == str(int(k))].bT.iloc[0])
                   if str(int(k)) in set(sub.k) else
                   float(sub[sub.k == int(k)].bT.iloc[0]) for k in ks])
    bF = np.array([float(sub[sub.k == str(int(k))].bF.iloc[0])
                   if str(int(k)) in set(sub.k) else
                   float(sub[sub.k == int(k)].bF.iloc[0]) for k in ks])
    bT = np.maximum(bT, 1e-3)
    bF = np.minimum(bF, -1e-3)
    lks, lT, lF = np.log(ks), np.log(bT), np.log(-bF)

    def coef(k):
        if k <= 0:
            return 0.0, 0.0
        lk = np.log(k)
        if k < 2:
            sT = (lT[1] - lT[0]) / (lks[1] - lks[0])
            sF = (lF[1] - lF[0]) / (lks[1] - lks[0])
            return (float(np.exp(lT[0] + sT * (lk - lks[0]))),
                    -float(np.exp(lF[0] + sF * (lk - lks[0]))))
        if k > 8:
            sT = (lT[2] - lT[1]) / (lks[2] - lks[1])
            sF = (lF[2] - lF[1]) / (lks[2] - lks[1])
            return (float(np.exp(lT[2] + sT * (lk - lks[2]))),
                    -float(np.exp(lF[2] + sF * (lk - lks[2]))))
        return (float(np.exp(np.interp(lk, lks, lT))),
                -float(np.exp(np.interp(lk, lks, lF))))
    return coef


def fixed_points(alpha, c0, coef, grid=1200):
    Pk = p_alpha_k(alpha)
    xs = np.linspace(1e-6, 1 - 1e-6, grid)
    F = np.zeros_like(xs)
    for k, pk in enumerate(Pk):
        if pk < 1e-13:
            continue
        if k == 0:
            F += pk * sig(c0)
            continue
        bT, bF = coef(k)
        ls = np.arange(k + 1)
        s = sig(c0 + bT * ls + bF * (k - ls))
        W = binom.pmf(ls[None, :], k, xs[:, None])
        F += pk * (W @ s)
    f = F - xs
    fps = []
    for i in range(grid - 1):
        if f[i] * f[i + 1] < 0:
            r = xs[i] + f[i] * (xs[i + 1] - xs[i]) / (f[i] - f[i + 1])
            slope = (f[i + 1] - f[i]) / (xs[i + 1] - xs[i]) + 1
            fps.append((round(float(r), 3),
                        "unstable" if slope > 1 else "stable"))
    return fps


def main():
    co = pd.read_csv(os.path.join(ROOT, "results",
                                  "stage2b_single_coeffs.csv"),
                     dtype={"k": str})
    claims = pd.read_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"))
    rows = []
    for cid, sub in co.groupby("claim_id"):
        c0 = float(sub[sub.k == "pooled"].c0.iloc[0])
        cset = claims[claims.claim_id == cid]["set"].iloc[0]
        coef = make_coef(sub[sub.k != "pooled"])
        alphas = [0.30, 0.55] if cset == "A1_supports" else [0.30]
        for a in alphas:
            fps = fixed_points(a, c0, coef)
            rows.append({"claim_id": cid, "set": cset, "alpha": a,
                         "c0_pooled": round(c0, 3),
                         "fixed_points": "; ".join(
                             f"{r}({s})" for r, s in fps),
                         "n_stable": sum(1 for _, s in fps if s == "stable"),
                         "separation_flag": bool(
                             (sub[sub.k != "pooled"].bT > 5).any())})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(ROOT, "results",
                            "stage2b_blind_predictions.csv"), index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
