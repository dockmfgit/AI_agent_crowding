"""Shared HMF utilities for the post-review re-analysis (R1/R2).

- p_alpha_k: in-degree distribution of the crowding process (exact recursion).
- identified response models:
    * joint per-k model (Stage 1): logit p = FE_claim [+ theta*self] +
      sum_k 1[k] (bT_k l + bF_k (k-l)); identified because k=0 rows anchor FE.
    * reduced per-claim model: logit p = c0 + g(k) [delta k + beta_bar (2l-k)]
      [+ theta*self]; g = 1 (constant) or 1/(1+gamma k) (divisive).
- fixed_points: endpoint-inclusive bracketing on a fine grid, bisection
  refinement, stability by |F'(x)| < 1, no rounding of internal values.
- classify: phase from ALL fixed points (any interior unstable root ->
  bistable); selection rules for experiments are applied separately.
"""
import numpy as np
from scipy.stats import binom

N_AGENTS = 32
KS_STAGE1 = [1, 2, 3, 5, 8, 12]


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


# ---------------------------------------------------------------- fitting
def fit_logit_ridge(X, y, ridge=1e-4, maxiter=200, tol=1e-9):
    """Newton (IRLS) logistic MLE with a small L2 penalty (all columns).
    The penalty only regularizes separated cells; it does not create
    identification (call check_rank first)."""
    b = np.zeros(X.shape[1])
    for _ in range(maxiter):
        z = np.clip(X @ b, -30, 30)
        mu = 1 / (1 + np.exp(-z))
        g = X.T @ (mu - y) + 2 * ridge * b
        H = (X * (mu * (1 - mu))[:, None]).T @ X + 2 * ridge * np.eye(X.shape[1])
        step = np.linalg.solve(H, g)
        b -= step
        if np.max(np.abs(step)) < tol:
            break
    return b


def check_rank(X):
    return int(np.linalg.matrix_rank(X)), X.shape[1]


def design_joint_perk(df, claim_ids, with_self, ks=KS_STAGE1):
    """[claim dummies | (self) | for k in ks: 1[k] l, 1[k] (k-l)]"""
    n = len(df)
    cid = {c: i for i, c in enumerate(claim_ids)}
    cols, names = [], []
    X = np.zeros((n, len(claim_ids)))
    X[np.arange(n), df.claim_id.map(cid).to_numpy()] = 1.0
    cols.append(X)
    names += [f"FE_{c}" for c in claim_ids]
    if with_self:
        cols.append((df.self_state == "self_correct").to_numpy(float)[:, None])
        names.append("theta")
    k = df.k.to_numpy(float)
    l = df.l.to_numpy(float)
    for kk in ks:
        m = (k == kk).astype(float)
        cols.append((m * l)[:, None])
        cols.append((m * (k - l))[:, None])
        names += [f"bT_{kk}", f"bF_{kk}"]
    return np.hstack(cols), names


def design_reduced(df, gamma, with_self):
    """[1 | g(k) k | g(k) (2l-k) | (self)] -> (c0, delta, beta_bar[, theta])"""
    k = df.k.to_numpy(float)
    l = df.l.to_numpy(float)
    g = 1.0 / (1.0 + gamma * k) if gamma is not None else np.ones_like(k)
    cols = [np.ones_like(k), g * k, g * (2 * l - k)]
    names = ["c0", "delta", "beta_bar"]
    if with_self:
        cols.append((df.self_state == "self_correct").to_numpy(float))
        names.append("theta")
    return np.column_stack(cols), names


# ------------------------------------------------------------ response fns
def response_reduced(b, gamma, with_self=False):
    """Returns pfun(k, ls, s) -> P(correct side) for inbox (k, l) and own
    state s in {0,1} (s ignored when with_self is False)."""
    c0, dl, bb = b[:3]
    th = b[3] if with_self else 0.0

    def pfun(k, ls, s=0):
        g = 1.0 / (1.0 + gamma * k) if gamma is not None else 1.0
        return sig(c0 + th * s + g * (dl * k + bb * (2 * ls - k)))
    return pfun


def response_perk(c0, ks, bT, bF, extrap="power", theta=0.0):
    """Per-k rule with log-log interpolation inside [min k, max k] and
    power-law (or flat) extrapolation beyond; k=0 -> sig(c0)."""
    ks = np.asarray(ks, float); bT = np.asarray(bT); bF = np.asarray(bF)
    lks = np.log(ks)

    def coef(k):
        if k <= 0:
            return 0.0, 0.0
        lk = np.log(k)
        if ks[0] <= k <= ks[-1]:
            return (float(np.exp(np.interp(lk, lks, np.log(bT)))),
                    -float(np.exp(np.interp(lk, lks, np.log(-bF)))))
        i0, i1 = (0, 1) if k < ks[0] else (-2, -1)
        if extrap == "flat":
            j = 0 if k < ks[0] else -1
            return float(bT[j]), float(bF[j])
        st = (np.log(bT[i1]) - np.log(bT[i0])) / (lks[i1] - lks[i0])
        sf = (np.log(-bF[i1]) - np.log(-bF[i0])) / (lks[i1] - lks[i0])
        return (float(np.exp(np.log(bT[i1]) + st * (lk - lks[i1]))),
                -float(np.exp(np.log(-bF[i1]) + sf * (lk - lks[i1]))))

    def pfun(k, ls, s=0):
        t, f = coef(k)
        return sig(c0 + theta * s + t * ls + f * (k - ls))
    pfun.coef = coef
    return pfun


# ------------------------------------------------------------- HMF map
def hmf_map(xs, alpha, pfun, with_self=False, Pk=None):
    """F(x) for the HMF map. with_self: own state correct w.p. x."""
    xs = np.atleast_1d(np.asarray(xs, float))
    if Pk is None:
        Pk = p_alpha_k(alpha)
    F = np.zeros_like(xs)
    for k, pk in enumerate(Pk):
        if pk < 1e-13:
            continue
        ls = np.arange(k + 1)
        W = binom.pmf(ls[None, :], k, xs[:, None])
        if with_self:
            F += pk * (xs * (W @ pfun(k, ls, 1)) + (1 - xs) * (W @ pfun(k, ls, 0)))
        else:
            F += pk * (W @ pfun(k, ls, 0))
    return F


def fixed_points(alpha, pfun, with_self=False, n_grid=4001, n_bisect=60):
    """All fixed points of F on [0, 1] (endpoints included in the bracket
    grid), refined by bisection; stability from the numerical derivative.
    Returns list of dicts: x, deriv, stable, residual."""
    Pk = p_alpha_k(alpha)
    xs = np.linspace(0.0, 1.0, n_grid)
    f = hmf_map(xs, alpha, pfun, with_self, Pk) - xs
    out = []
    for i in range(n_grid - 1):
        if f[i] == 0.0 or f[i] * f[i + 1] < 0:
            a, b = xs[i], xs[i + 1]
            fa = f[i]
            for _ in range(n_bisect):
                m = 0.5 * (a + b)
                fm = hmf_map(m, alpha, pfun, with_self, Pk)[0] - m
                if fm * fa <= 0:
                    b = m
                else:
                    a, fa = m, fm
            r = 0.5 * (a + b)
            h = 1e-5
            lo, hi = max(r - h, 0.0), min(r + h, 1.0)
            d = (hmf_map(hi, alpha, pfun, with_self, Pk)[0]
                 - hmf_map(lo, alpha, pfun, with_self, Pk)[0]) / (hi - lo)
            res = abs(hmf_map(r, alpha, pfun, with_self, Pk)[0] - r)
            out.append({"x": float(r), "deriv": float(d),
                        "stable": bool(abs(d) < 1.0), "residual": float(res)})
    # endpoint attractors: F(0) > 0 and F(1) < 1 always for finite logits, so
    # 0 and 1 are never fixed points; boundary-adjacent roots are found above.
    return out


def classify(fps):
    """Phase from ALL fixed points. bistable: any unstable interior root;
    mono_correct / mono_wrong: the single stable root above / below 0.5."""
    un = [p["x"] for p in fps if not p["stable"]]
    st = [p["x"] for p in fps if p["stable"]]
    if un:
        return "bistable", un[0]
    if len(st) == 1:
        return ("mono_correct" if st[0] > 0.5 else "mono_wrong"), None
    if len(st) > 1:
        return "multistable_no_unstable_found", None
    return "no_fixed_point_found", None


def fps_str(fps):
    return "; ".join(f"{p['x']:.4f}({'s' if p['stable'] else 'u'})" for p in fps)
