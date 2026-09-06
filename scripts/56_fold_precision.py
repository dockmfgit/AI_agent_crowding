"""Precise fold of the reduced map G and of the full HMF map F (R6).

For every coefficient set of SI Section 3 (seven synthetic sets and the four
measured ones) this script solves the fold conditions of the reduced map
jointly,  G(x;K) = x  and  G_x(x;K) = 1,  reports the non-degeneracy terms
G_xx and G_K at the fold and the residuals, converts K* to alpha* both by
inverting the exact mean degree E[K](alpha) and by the closed form (1), and
locates the fold of the full map F (all P_alpha(k), exact binomial sums) by
bisection in alpha to 1e-4.  It also tabulates the exact mean degree against
the closed form (1) and the alpha at which the two diverge qualitatively.

Output: results/r6_fold_precision.csv, results/r6_mean_degree.csv,
        manuscript/tex/tables/t_fold_precision.tex
Usage: python scripts/56_fold_precision.py [PROJECT_ROOT]
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import fsolve

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hmf_lib as H  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
TAB = os.path.join(ROOT, "manuscript", "tex", "tables")
spec = importlib.util.spec_from_file_location("s30", os.path.join(HERE, "30_alpha_star_analytic.py"))
s30 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s30)

SETS = [
    ("$h{=}.10,\\ \\theta{=}.6,\\ \\bar\\beta{=}.5$", dict(h=0.10, th=0.6, bT=0.5, bF=-0.5), None),
    ("$h{=}.10,\\ \\theta{=}.6,\\ \\bar\\beta{=}1$", dict(h=0.10, th=0.6, bT=1.0, bF=-1.0), None),
    ("$h{=}.30,\\ \\theta{=}.6,\\ \\bar\\beta{=}1$", dict(h=0.30, th=0.6, bT=1.0, bF=-1.0), None),
    ("$h{=}.70,\\ \\theta{=}.6,\\ \\bar\\beta{=}1$", dict(h=0.70, th=0.6, bT=1.0, bF=-1.0), None),
    ("$h{=}.10,\\ \\theta{=}0,\\ \\bar\\beta{=}1$", dict(h=0.10, th=0.0, bT=1.0, bF=-1.0), None),
    ("$h{=}.10,\\ \\theta{=}2,\\ \\bar\\beta{=}.5$", dict(h=0.10, th=2.0, bT=0.5, bF=-0.5), None),
    ("$h{=}.30,\\ \\theta{=}2,\\ \\bar\\beta{=}1$", dict(h=0.30, th=2.0, bT=1.0, bF=-1.0), None),
    ("variant A, measured (constant)", dict(h=0.725, th=0.0, bT=0.419, bF=-0.568), None),
    ("variant B, measured (constant)", dict(h=0.196, th=1.909, bT=0.291, bF=-0.326), None),
    ("variant A, measured (divisive, $\\gamma{=}0.526$)", dict(h=1.398, th=0.0, bT=1.445, bF=-3.031), 0.526),
    ("variant B, measured (divisive, $\\gamma{=}1.318$)", dict(h=0.552, th=2.152, bT=2.711, bF=-4.140), 1.318),
]


def gK(gamma, K):
    return 1.0 if gamma is None else 1.0 / (1.0 + gamma * K)


def G(x, K, p, gamma):
    return s30.G_map(x, K, p["h"], p["th"], p["bT"], p["bF"], gK(gamma, K))[0]


def Gx(x, K, p, gamma, e=1e-6):
    return (G(x + e, K, p, gamma) - G(x - e, K, p, gamma)) / (2 * e)


def fold_G(p, gamma):
    """Solve G = x, G_x = 1 jointly; start from the coarse K* of script 30."""
    a0, K0 = s30.alpha_star(**p, gfun=None if gamma is None else (lambda K: gK(gamma, K)))
    if K0 is None:
        return None
    # unstable root at K slightly above K0 as the starting x
    xs = np.linspace(0.001, 0.999, 2001)
    f = np.array([G(x, K0 + 0.05, p, gamma) for x in xs]) - xs
    idx = np.where(f[:-1] * f[1:] < 0)[0]
    x0 = xs[idx[len(idx) // 2]] if len(idx) else 0.5
    sol, info, ier, msg = fsolve(lambda v: [G(v[0], v[1], p, gamma) - v[0], Gx(v[0], v[1], p, gamma) - 1.0],
                                 [x0, K0], full_output=True, xtol=1e-12)
    x, K = float(sol[0]), float(sol[1])
    e = 1e-4
    Gxx = (Gx(x + e, K, p, gamma) - Gx(x - e, K, p, gamma)) / (2 * e)
    GK = (G(x, K + e, p, gamma) - G(x, K - e, p, gamma)) / (2 * e)
    return dict(K_star=K, x_fold=x, res_G=abs(G(x, K, p, gamma) - x), res_Gx=abs(Gx(x, K, p, gamma) - 1.0),
                G_xx=Gxx, G_K=GK, converged=(ier == 1), K_star_coarse=K0)


def invert(Kfun, Kstar):
    lo, hi = 0.02, 4.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if Kfun(mid) > Kstar:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def pfun_full(p, gamma):
    c0 = p["h"] - p["th"] / 2

    def pf(k, ls, s=0):
        g = gK(gamma, k)
        return H.sig(c0 + p["th"] * s + g * (p["bT"] * ls + p["bF"] * (k - ls)))
    return pf


def fold_F(p, gamma, with_self):
    pf = pfun_full(p, gamma)

    def bist(a):
        return H.classify(H.fixed_points(a, pf, with_self=with_self, n_grid=2001))[0] == "bistable"
    lo, hi = 0.05, 3.0
    if not bist(lo):
        return np.nan
    if bist(hi):
        return np.inf
    for _ in range(16):  # 3/2^16 ~ 5e-5
        mid = 0.5 * (lo + hi)
        if bist(mid):
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    rows = []
    for name, p, gamma in SETS:
        fg = fold_G(p, gamma)
        aF = fold_F(p, gamma, with_self=p["th"] != 0)
        r = {"set": name, "alpha_F_fold": aF}
        if fg:
            r.update(fg)
            r["alpha_G_exactEK"] = invert(s30.EK_exact, fg["K_star"])
            r["alpha_G_closed"] = invert(s30.K_closed, fg["K_star"])
            r["alpha_G_coarse_exactEK"] = invert(s30.EK_exact, fg["K_star_coarse"])
        rows.append(r)
        print({k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    df = pd.DataFrame(rows)
    df["rel_err_exactEK"] = (df.alpha_G_exactEK - df.alpha_F_fold).abs() / df.alpha_F_fold
    df["rel_err_closed"] = (df.alpha_G_closed - df.alpha_F_fold).abs() / df.alpha_F_fold
    df.to_csv(os.path.join(RES, "r6_fold_precision.csv"), index=False)
    print("median rel err exact E[K]:", df.rel_err_exactEK.median(), " closed:", df.rel_err_closed.median(),
          " max:", df.rel_err_exactEK.max(), df.rel_err_closed.max())

    # mean degree table
    al = [0.2, 0.3, 0.435, 0.55, 1.0, 2.0, 5.0, 20.0]
    md = pd.DataFrame({"alpha": al, "EK_exact": [s30.EK_exact(a) for a in al],
                       "K_closed": [s30.K_closed(a) for a in al]})
    md["underestimate"] = 1 - md.K_closed / md.EK_exact
    md.to_csv(os.path.join(RES, "r6_mean_degree.csv"), index=False)
    print(md.round(4).to_string())

    os.makedirs(TAB, exist_ok=True)
    with open(os.path.join(TAB, "t_fold_precision.tex"), "w") as f:
        f.write("\\begin{tabular}{lcccc}\n\\toprule\n")
        f.write("parameter set & fold of $F$ (exact $\\astar$) & $G$-fold, exact $E[K]$ & $G$-fold, closed form & $K^*$ \\\\\n\\midrule\n")
        for _, r in df.iterrows():
            f.write(f"{r.set} & {r.alpha_F_fold:.3f} & {r.alpha_G_exactEK:.3f} & {r.alpha_G_closed:.3f} & {r.K_star:.2f} \\\\\n")
        f.write("\\bottomrule\n\\end{tabular}\n")
    print("wrote t_fold_precision.tex")


if __name__ == "__main__":
    main()
