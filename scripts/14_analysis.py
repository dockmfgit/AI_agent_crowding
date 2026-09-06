"""Stage 1 step 4: analysis of the randomized-inbox measurement.

1. Basic coefficients per variant (A: no self line; B: self line):
   logit P(correct answer) = claim FE + [theta*1(self=correct)] + b_T*l + b_F*(k-l)
   Cluster (claim) pairs bootstrap for CIs; w_T = b_T/|b_F| with null w_T=1.
2. Attention decay: null additive vs position decay / load decay / top-K /
   divisive normalization. 5-fold CV over claims (test mean log-lik) + AIC.
3. alpha*: fold point of the logistic HMF with attention-degree P_alpha(k),
   using measured (h, theta, b_T, b_F). Window check [0.3, 1.5].

Outputs: data/stage1/main_obs.parquet, results/stage1_coeffs.csv,
results/stage1_decay_models.csv, results/stage1_alpha_star.csv,
fig/stage1_beta_vs_k.png
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import binom
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(3)
N_BOOT = 1000
N_AGENTS = 32


# ---------- data ----------

def load_obs():
    path = os.path.join(ROOT, "data", "stage1", "raw", "13_main.jsonl")
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("parsed") not in ("A", "B"):
                continue
            c = r["condition"]
            chosen = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                      else "FALSE")
            rows.append({
                "claim_id": c["claim_id"], "truth": c["truth"],
                "k": c["k"], "l": c["l"], "self_state": c["self_state"],
                "assign": c["assign"], "order": c["order"],
                "chose_A": r["parsed"] == "A",
                "y": int(chosen == c["truth"]),
            })
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(ROOT, "data", "stage1", "main_obs.parquet"),
                  index=False)
    return df


# ---------- logistic MLE ----------

def fit_logit(X, y, w_init=None):
    """Unpenalized logistic MLE, Newton with fallback; returns coef vector."""
    n, p = X.shape
    b = np.zeros(p) if w_init is None else w_init.copy()
    for _ in range(60):
        z = np.clip(X @ b, -30, 30)
        mu = 1 / (1 + np.exp(-z))
        g = X.T @ (mu - y)
        W = mu * (1 - mu) + 1e-9
        H = (X * W[:, None]).T @ X
        try:
            step = np.linalg.solve(H + 1e-8 * np.eye(p), g)
        except np.linalg.LinAlgError:
            break
        b -= step
        if np.max(np.abs(step)) < 1e-9:
            break
    return b


def loglik(X, y, b):
    z = np.clip(X @ b, -30, 30)
    return float(y @ z - np.logaddexp(0, z).sum())


def design(df, claim_ids, drive_c, drive_w, with_self):
    """[claim dummies | (self dummy) | S_C | S_W]"""
    cid_idx = {c: i for i, c in enumerate(claim_ids)}
    n = len(df)
    p_fe = len(claim_ids)
    cols = p_fe + (1 if with_self else 0) + 2
    X = np.zeros((n, cols))
    X[np.arange(n), df.claim_id.map(cid_idx).to_numpy()] = 1.0
    j = p_fe
    if with_self:
        X[:, j] = (df.self_state == "self_correct").to_numpy(float)
        j += 1
    X[:, j] = drive_c
    X[:, j + 1] = drive_w
    return X


def counts_drives(df):
    return df.l.to_numpy(float), (df.k - df.l).to_numpy(float)


# ---------- decay weight schemes ----------

def weighted_drives(df, scheme, param):
    """S_C, S_W with per-position weights from the scheme."""
    S_C = np.zeros(len(df))
    S_W = np.zeros(len(df))
    orders = df.order.to_numpy()
    ks = df.k.to_numpy()
    for i, (o, k) in enumerate(zip(orders, ks)):
        if k == 0:
            continue
        pos = np.arange(k)
        if scheme == "null":
            w = np.ones(k)
        elif scheme == "pos_decay":
            w = np.exp(-param * pos)
        elif scheme == "load_decay":
            w = np.full(k, np.exp(-param * k))
        elif scheme == "topk":
            w = (pos < param).astype(float)
        elif scheme == "divisive":
            w = np.full(k, 1.0 / (1.0 + param * k))
        stances = np.frombuffer(o.encode(), dtype=np.uint8)
        S_C[i] = w[stances == ord("C")].sum()
        S_W[i] = w[stances == ord("W")].sum()
    return S_C, S_W


SCHEMES = {
    "null": [0.0],
    "pos_decay": np.round(np.arange(0.0, 1.51, 0.05), 3),
    "load_decay": np.round(np.arange(0.0, 0.41, 0.02), 3),
    "topk": [1, 2, 3, 5, 8, 12],
    "divisive": np.round(np.arange(0.0, 2.01, 0.1), 3),
}


def fit_scheme(df, claim_ids, scheme, grid, folds):
    """Profile the scheme parameter on full data; 5-fold CV over claims."""
    best = None
    for prm in grid:
        S_C, S_W = weighted_drives(df, scheme, prm)
        X = design(df, claim_ids, S_C, S_W, with_self=True)
        b = fit_logit(X, df.y.to_numpy(float))
        ll = loglik(X, df.y.to_numpy(float), b)
        if best is None or ll > best["ll"]:
            best = {"scheme": scheme, "param": float(prm), "ll": ll, "b": b,
                    "n_par": X.shape[1] + (1 if scheme != "null" else 0)}
    # CV at the profiled parameter (parameter re-profiled inside each fold)
    cv_ll = []
    y = df.y.to_numpy(float)
    for te_claims in folds:
        tr = ~df.claim_id.isin(te_claims).to_numpy()
        te = ~tr
        b_ll, b_prm = None, None
        for prm in grid:
            S_C, S_W = weighted_drives(df, scheme, prm)
            X = design(df, claim_ids, S_C, S_W, with_self=True)
            btr = fit_logit(X[tr], y[tr])
            lltr = loglik(X[tr], y[tr], btr)
            if b_ll is None or lltr > b_ll:
                b_ll, b_prm, b_b, b_X = lltr, prm, btr, X
        if te.sum() > 0:
            cv_ll.append(loglik(b_X[te], y[te], b_b) / te.sum())
    return best, float(np.mean(cv_ll)) if cv_ll else np.nan


# ---------- HMF alpha* ----------

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


def F_vec(xs, Pk, c0, theta, bT, bF):
    """P(next correct); message drive m = bT*l + bF*(k-l), bF fitted (<0)."""
    xs = np.atleast_1d(np.asarray(xs, dtype=float))
    out = np.zeros_like(xs)
    for k, pk in enumerate(Pk):
        if pk < 1e-13:
            continue
        ls = np.arange(k + 1)
        m = bT * ls + bF * (k - ls)
        s_up = sig(c0 + theta + m)
        s_dn = sig(c0 + m)
        W = binom.pmf(ls[None, :], k, xs[:, None])
        out += pk * (W @ s_up * xs + W @ s_dn * (1 - xs))
    return out


def n_unstable(Pk, c0, theta, bT, bF, grid=1200):
    xs = np.linspace(1e-6, 1 - 1e-6, grid)
    f = F_vec(xs, Pk, c0, theta, bT, bF) - xs
    n_u = 0
    for i in range(grid - 1):
        if f[i] * f[i + 1] < 0:
            slope = (f[i + 1] - f[i]) / (xs[i + 1] - xs[i]) + 1
            if slope > 1:
                n_u += 1
    return n_u


def alpha_star(c0, theta, bT, bF, lo=0.05, hi=4.0):
    """Largest alpha with an unstable interior FP; None if none anywhere."""
    alphas = np.arange(lo, hi + 1e-9, 0.05)
    has = [n_unstable(p_alpha_k(a), c0, theta, bT, bF) > 0 for a in alphas]
    if not any(has):
        return None, alphas, has
    if all(has):
        return np.inf, alphas, has
    last = max(i for i, h in enumerate(has) if h)
    if last == len(alphas) - 1:
        return np.inf, alphas, has
    a_lo, a_hi = alphas[last], alphas[last + 1]
    for _ in range(20):
        mid = (a_lo + a_hi) / 2
        if n_unstable(p_alpha_k(mid), c0, theta, bT, bF) > 0:
            a_lo = mid
        else:
            a_hi = mid
    return (a_lo + a_hi) / 2, alphas, has


# ---------- main ----------

def main():
    df = load_obs()
    claim_ids = sorted(df.claim_id.unique())
    n_claims = len(claim_ids)
    print(f"{len(df)} parsed observations, {n_claims} claims")
    print(df.groupby("self_state").size())

    # ----- 1. basic coefficients per variant -----
    coeff_rows = []
    fits = {}
    for variant, sub in [("A", df[df.self_state == "none"]),
                         ("B", df[df.self_state != "none"])]:
        with_self = variant == "B"
        S_C, S_W = counts_drives(sub)
        X = design(sub, claim_ids, S_C, S_W, with_self)
        y = sub.y.to_numpy(float)
        b = fit_logit(X, y)
        p_fe = n_claims
        theta = b[p_fe] if with_self else np.nan
        bT, bF = b[-2], b[-1]
        c0 = b[:p_fe].mean()
        h = c0 + (theta / 2 if with_self else 0.0)
        wT = bT / abs(bF) if bF != 0 else np.nan
        fits[variant] = dict(c0=c0, theta=theta, bT=bT, bF=bF, h=h, wT=wT)

        # precompute per-claim design blocks for the pairs cluster bootstrap
        blocks = {}
        for ci, c in enumerate(claim_ids):
            m = (sub.claim_id == c).to_numpy()
            Xc = X[m].copy()
            blocks[c] = (Xc[:, n_claims:], y[m])  # non-FE cols, y
        boots = {k: [] for k in ("theta", "bT", "bF", "wT", "h", "c0")}
        for _ in range(N_BOOT):
            cl = RNG.choice(claim_ids, n_claims, replace=True)
            sizes = [len(blocks[c][1]) for c in cl]
            ntot = sum(sizes)
            p_rest = X.shape[1] - n_claims
            Xb = np.zeros((ntot, n_claims + p_rest))
            yb = np.zeros(ntot)
            at = 0
            for slot, c in enumerate(cl):
                Xr, yr = blocks[c]
                nn = len(yr)
                Xb[at:at + nn, slot] = 1.0     # duplicates get their own FE
                Xb[at:at + nn, n_claims:] = Xr
                yb[at:at + nn] = yr
                at += nn
            bb = fit_logit(Xb, yb)
            th = bb[n_claims] if with_self else np.nan
            bTb, bFb = bb[-2], bb[-1]
            c0b = bb[:n_claims].mean()
            boots["theta"].append(th)
            boots["bT"].append(bTb)
            boots["bF"].append(bFb)
            boots["wT"].append(bTb / abs(bFb) if bFb != 0 else np.nan)
            boots["c0"].append(c0b)
            boots["h"].append(c0b + (th / 2 if with_self else 0.0))
        for name, est in [("c0", c0), ("h", h), ("theta", theta),
                          ("beta_T", bT), ("beta_F", bF), ("w_T", wT)]:
            key = {"beta_T": "bT", "beta_F": "bF", "w_T": "wT"}.get(name, name)
            arr = np.array(boots[key], dtype=float)
            arr = arr[np.isfinite(arr)]
            lo, hi = (np.percentile(arr, [2.5, 97.5]) if len(arr) > 50
                      else (np.nan, np.nan))
            coeff_rows.append({"variant": variant, "coef": name,
                               "estimate": est, "ci_lo": lo, "ci_hi": hi,
                               "n_obs": len(sub)})
            print(f"variant {variant} {name}: {est:.3f} [{lo:.3f}, {hi:.3f}]")

    pd.DataFrame(coeff_rows).to_csv(
        os.path.join(ROOT, "results", "stage1_coeffs.csv"), index=False)

    # ----- 2. decay model comparison -----
    perm = RNG.permutation(claim_ids)
    folds = [list(perm[i::5]) for i in range(5)]
    decay_rows = []
    for scheme, grid in SCHEMES.items():
        best, cv = fit_scheme(df, claim_ids, scheme, grid, folds)
        n_par = best["n_par"]
        aic = 2 * n_par - 2 * best["ll"]
        decay_rows.append({"scheme": scheme, "param": best["param"],
                           "loglik": best["ll"], "n_par": n_par, "aic": aic,
                           "cv_loglik_per_obs": cv})
        print(f"scheme {scheme}: param={best['param']} ll={best['ll']:.1f} "
              f"AIC={aic:.1f} CV={cv:.5f}")
    dm = pd.DataFrame(decay_rows).sort_values("cv_loglik_per_obs",
                                              ascending=False)
    dm.to_csv(os.path.join(ROOT, "results", "stage1_decay_models.csv"),
              index=False)

    # ----- beta vs k figure -----
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    sub = df[df.self_state == "none"]
    ks = sorted(sub.k.unique())
    bT_k, bF_k = {}, {}
    for k in ks:
        if k == 0:
            continue
        sk = sub[sub.k == k]
        S_C, S_W = counts_drives(sk)
        X = design(sk, claim_ids, S_C, S_W, with_self=False)
        keep = X.sum(0) > 0
        b = fit_logit(X[:, keep], sk.y.to_numpy(float))
        bT_k[k], bF_k[k] = b[-2], b[-1]
    ax[0].plot(list(bT_k), list(bT_k.values()), "o-", label="beta_T(k)")
    ax[0].plot(list(bF_k), list(bF_k.values()), "s-", label="beta_F(k)")
    best_row = dm.iloc[0]
    ax[0].set_xlabel("k (inbox size)")
    ax[0].set_ylabel("per-message coefficient")
    ax[0].axhline(0, color="gray", lw=0.5)
    ax[0].legend()
    ax[0].set_title("per-k separate fits (variant A)")
    # empirical P(correct) vs l for each k
    for k in ks:
        sk = sub[sub.k == k]
        g = sk.groupby("l").y.agg(["mean", "size"])
        ax[1].plot(g.index / max(k, 1), g["mean"], "o-", label=f"k={k}")
    ax[1].set_xlabel("l/k (share of correct-side messages)")
    ax[1].set_ylabel("P(correct answer)")
    ax[1].legend(fontsize=7)
    ax[1].set_title(f"best decay: {best_row.scheme} "
                    f"(param={best_row.param})")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "fig", "stage1_beta_vs_k.png"), dpi=150)

    # ----- 3. alpha* -----
    astar_rows = []
    for variant, f in fits.items():
        th = 0.0 if variant == "A" else f["theta"]
        a_star, alphas, has = alpha_star(f["c0"], th, f["bT"], f["bF"])
        in_win = (a_star is not None and np.isfinite(a_star)
                  and 0.3 <= a_star <= 1.5)
        astar_rows.append({
            "variant": variant, "c0": f["c0"], "theta": th,
            "beta_T": f["bT"], "beta_F": f["bF"], "h": f["h"],
            "alpha_star": a_star if a_star is not None else np.nan,
            "bistable_at_0.3": bool(has[np.argmin(np.abs(alphas - 0.3))]),
            "bistable_at_1.5": bool(has[np.argmin(np.abs(alphas - 1.5))]),
            "in_window": in_win})
        print(f"variant {variant}: alpha* = {a_star} (in [0.3,1.5]: {in_win})")
    # sensitivity: small-|h_q| claim subset (variant B)
    claims_cal = pd.read_csv(os.path.join(ROOT, "results",
                                          "stage1_claims.csv"))
    small = claims_cal[claims_cal.selected & (claims_cal.h_q.abs() < 0.2)]
    subB = df[(df.self_state != "none")
              & df.claim_id.isin(small.claim_id)]
    if len(subB) > 1000:
        cids = sorted(subB.claim_id.unique())
        S_C, S_W = counts_drives(subB)
        X = design(subB, cids, S_C, S_W, with_self=True)
        b = fit_logit(X, subB.y.to_numpy(float))
        c0s, ths, bTs, bFs = (b[:len(cids)].mean(), b[len(cids)],
                              b[-2], b[-1])
        a_star_s, alphas, has = alpha_star(c0s, ths, bTs, bFs)
        astar_rows.append({
            "variant": "B_small_hq", "c0": c0s, "theta": ths,
            "beta_T": bTs, "beta_F": bFs, "h": c0s + ths / 2,
            "alpha_star": a_star_s if a_star_s is not None else np.nan,
            "bistable_at_0.3": bool(has[np.argmin(np.abs(alphas - 0.3))]),
            "bistable_at_1.5": bool(has[np.argmin(np.abs(alphas - 1.5))]),
            "in_window": (a_star_s is not None and np.isfinite(a_star_s)
                          and 0.3 <= a_star_s <= 1.5)})
        print(f"B_small_hq ({len(cids)} claims): alpha* = {a_star_s}")
    pd.DataFrame(astar_rows).to_csv(
        os.path.join(ROOT, "results", "stage1_alpha_star.csv"), index=False)

    # parse failure bookkeeping
    n_lines = sum(1 for _ in open(os.path.join(
        ROOT, "data", "stage1", "raw", "13_main.jsonl")))
    print(f"\nlog lines (incl. retries): {n_lines}, parsed obs: {len(df)}")
    print("label-bias check: P(chose A) =", round(df.chose_A.mean(), 4))


if __name__ == "__main__":
    main()
