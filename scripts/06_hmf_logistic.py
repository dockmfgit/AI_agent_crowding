"""Logistic-response HMF for attention-generated networks.

Update rule (reduced form, w_T = 1 null):
  P(next correct | own state s in {0,1}, l of k inputs correct)
    = sigmoid( h + (theta/2)*(2s-1) + beta*(2l-k) )
  with h = c0 + theta/2 (the theta indicator 1[s=correct] decomposes into
  a constant field theta/2 plus a symmetric self term).

Coefficients: message-level regression on El et al. raw data
(scripts/05c, question-clustered), random family, agree-label channel,
beta symmetrized to enforce the w_T = 1 null.

Network: in-degree from finite attention (accept next input w.p. e^{-alpha r}
after r accepted), N = 32 -> m = 31 candidates. Recursion:
  P_m(k) = P_{m-1}(k) (1 - e^{-alpha k}) + P_{m-1}(k-1) e^{-alpha (k-1)}.

Outputs: xc_hmf_logistic.csv (all fixed points per alpha x model).
"""
import numpy as np
import pandas as pd
from scipy.stats import binom

N = 32

PARAMS = {
    "gpt": dict(theta=0.658, c0=-0.191, beta=(3.038 + 2.879) / 2),
    "gma": dict(theta=1.276, c0=-0.535, beta=(1.215 + 1.031) / 2),
    "qwn": dict(theta=0.389, c0=+0.593, beta=(1.702 + 1.891) / 2),
    "lma": dict(theta=0.886, c0=-0.444, beta=(1.939 + 1.695) / 2),
}


def p_alpha_k(alpha, n=N):
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


def F_vec(xs, Pk, theta, c0, beta):
    """HMF map evaluated on a vector of x values."""
    xs = np.atleast_1d(np.asarray(xs, dtype=float))
    h = c0 + theta / 2
    out = np.zeros_like(xs)
    for k, pk in enumerate(Pk):
        if pk < 1e-13:
            continue
        ls = np.arange(k + 1)
        m = beta * (2 * ls - k)
        s_up = sig(h + theta / 2 + m)     # own state correct
        s_dn = sig(h - theta / 2 + m)     # own state incorrect
        W = binom.pmf(ls[None, :], k, xs[:, None])   # (grid, l)
        out += pk * (W @ s_up * xs + W @ s_dn * (1 - xs))
    return out


def fixed_points(Pk, theta, c0, beta, grid=1500):
    xs = np.linspace(1e-6, 1 - 1e-6, grid)
    f = F_vec(xs, Pk, theta, c0, beta) - xs
    fps = []
    for i in range(grid - 1):
        if f[i] * f[i + 1] < 0 or f[i] == 0.0:
            lo, hi, flo = xs[i], xs[i + 1], f[i]
            for _ in range(60):
                mid = (lo + hi) / 2
                fmid = float(F_vec(mid, Pk, theta, c0, beta)[0]) - mid
                if flo * fmid <= 0:
                    hi = mid
                else:
                    lo, flo = mid, fmid
            r = (lo + hi) / 2
            eps = 1e-5
            slope = float(F_vec(r + eps, Pk, theta, c0, beta)[0]
                          - F_vec(r - eps, Pk, theta, c0, beta)[0]) / (2 * eps)
            fps.append((r, "unstable" if slope > 1 else "stable"))
    return fps


def main():
    alphas = np.round(np.arange(0.10, 3.01, 0.05), 2)
    rows = []
    for m, p in PARAMS.items():
        for a in alphas:
            Pk = p_alpha_k(a)
            Ek = float(np.arange(len(Pk)) @ Pk)
            for r, s in fixed_points(Pk, p["theta"], p["c0"], p["beta"]):
                rows.append(dict(model=m, alpha=a, Ek=Ek, x=r, stability=s,
                                 h=p["c0"] + p["theta"] / 2, beta=p["beta"]))
        print(m, "done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv("xc_hmf_logistic.csv", index=False)

    print("\nmodel  h       beta  | alpha range w/ unstable FP | "
          "x_c at 0.3/0.9/1.5 | span")
    for m, p in PARAMS.items():
        sub = df[(df.model == m) & (df.stability == "unstable")]
        if len(sub) == 0:
            print(f"{m}: no unstable FP at any alpha")
            continue

        def xc_at(a):
            s = sub[np.isclose(sub.alpha, a)]
            return float(s.x.iloc[0]) if len(s) else np.nan
        x03, x09, x15 = xc_at(0.30), xc_at(0.90), xc_at(1.50)
        vals = [v for v in (x03, x09, x15) if np.isfinite(v)]
        span = (max(vals) - min(vals)) if vals else np.nan
        print(f"{m}   {p['c0']+p['theta']/2:+.3f}  {p['beta']:.2f}  | "
              f"[{sub.alpha.min():.2f}, {sub.alpha.max():.2f}] | "
              f"{x03:.3f} / {x09:.3f} / {x15:.3f} | {span:.3f}")

    print("\nE[K]: alpha=0.3 ->", round(float(np.arange(N) @ p_alpha_k(0.3)), 2),
          "  log(32)/0.3 =", round(np.log(32) / 0.3, 2),
          " | alpha=1.5 ->", round(float(np.arange(N) @ p_alpha_k(1.5)), 2))


if __name__ == "__main__":
    main()
