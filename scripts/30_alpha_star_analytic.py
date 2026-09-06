"""Analytic alpha* for the attention-network HMF (notes/08).

Chain (all closed-form, no simulation):
  1. Mean degree closure  K(alpha) = (1/alpha) ln(1 + alpha (N-1))
     (deterministic continuum of the acceptance recursion; -3..-11% low vs
     the exact recursion mean, which can be used instead for a tighter chain).
  2. Reduced one-dimensional map (Gaussian-logistic smoothing of the exact
     binomial sum, degree replaced by K):
       G(x;K) = x s(z_up) + (1-x) s(z_dn)
       z_s = (c0 + theta*1[s=up] + K*delta + 2 bbar K (x-1/2)) / sqrt(1 + (pi/8) s2)
       s2  = 4 bbar^2 K x(1-x)
     bbar = (bT - bF)/2 (per-input swing), delta = (bT + bF)/2 (per-input drift).
     A degree-dependent coupling g(k) (e.g. divisive 1/(1+gamma k)) multiplies
     bT, bF and passes through unchanged.
  3. alpha* = the alpha at which the interior unstable fixed point of G
     disappears (fold: G = x and G' = 1), obtained as the threshold degree K*
     followed by inversion of K(alpha).

Interpretable symmetric-limit criterion (locates the mechanism, biased high):
  lambda(K) = [s(z_up) - s(z_dn)]              (persistence gain, theta)
            + 2 bbar K sbar' / sqrt(1+(pi/8) bbar^2 K)   (social gain)
  evaluated at x = 1/2; bistability requires lambda > 1 before field
  corrections.  See notes/08 for the derivation and validation table.
"""
import numpy as np

N = 32
LAM = np.pi / 8


def sig(z):
    return 1 / (1 + np.exp(-np.clip(z, -60, 60)))


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


def EK_exact(alpha):
    return float(np.arange(N) @ p_alpha_k(alpha))


def K_closed(alpha, n=N):
    return np.log(1 + alpha * (n - 1)) / alpha


def G_map(xs, K, h, th, bT, bF, gK=1.0):
    xs = np.atleast_1d(np.asarray(xs, float))
    bbar = gK * (bT - bF) / 2
    dlt = gK * (bT + bF) / 2
    c0 = h - th / 2
    mu = K * dlt + 2 * bbar * K * (xs - 0.5)
    den = np.sqrt(1 + LAM * 4 * bbar**2 * K * xs * (1 - xs))
    return xs * sig((c0 + th + mu) / den) + (1 - xs) * sig((c0 + mu) / den)


def bistable_G(K, h, th, bT, bF, gK=1.0, grid=800):
    xs = np.linspace(1e-5, 1 - 1e-5, grid)
    f = G_map(xs, K, h, th, bT, bF, gK) - xs
    for i in np.where(f[:-1] * f[1:] < 0)[0]:
        r = (xs[i] + xs[i + 1]) / 2
        e = 3e-4
        sl = (G_map(r + e, K, h, th, bT, bF, gK)[0]
              - G_map(r - e, K, h, th, bT, bF, gK)[0]) / (2 * e)
        if sl > 1:
            return True
    return False


def alpha_star(h, th, bT, bF, gfun=None, closed_K=False):
    """Analytic alpha*: threshold degree K*, then invert the degree closure."""
    Ks = np.arange(1.2, 26, 0.05)
    bis = [bistable_G(K, h, th, bT, bF, 1.0 if gfun is None else gfun(K))
           for K in Ks]
    if not any(bis):
        return None, None
    Kstar = Ks[np.where(bis)[0][0]]
    Kfun = K_closed if closed_K else EK_exact
    lo, hi = 0.05, 3.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if Kfun(mid) > Kstar:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2, Kstar


def lam(K, h, th, bT, bF, gK=1.0):
    """Symmetric-point linear gain (interpretable criterion lambda = 1)."""
    bbar = gK * (bT - bF) / 2
    dlt = gK * (bT + bF) / 2
    c0 = h - th / 2
    den = np.sqrt(1 + LAM * bbar**2 * K)
    zp = (c0 + th + K * dlt) / den
    z0 = (c0 + K * dlt) / den
    sp = (sig(zp) * (1 - sig(zp)) + sig(z0) * (1 - sig(z0))) / 2
    return (sig(zp) - sig(z0)) + 2 * bbar * K * sp / den


if __name__ == "__main__":
    # Stage 1 measured sets (h = c0 + theta/2)
    sets = {
        "variant A (const)": dict(h=0.725, th=0.0, bT=0.419, bF=-0.568),
        "variant B (const)": dict(h=0.196, th=1.909, bT=0.291, bF=-0.326),
        "variant A (divisive)": dict(h=1.398, th=0.0, bT=1.445, bF=-3.031,
                                     gfun=lambda k: 1 / (1 + 0.526 * k)),
        "variant B (divisive)": dict(h=0.552, th=2.152, bT=2.711, bF=-4.140,
                                     gfun=lambda k: 1 / (1 + 1.318 * k)),
    }
    for name, p in sets.items():
        gf = p.pop("gfun", None)
        a1, K1 = alpha_star(**p, gfun=gf)
        a2, _ = alpha_star(**p, gfun=gf, closed_K=True)
        print(f"{name:22s} K*={K1:.2f}  alpha*(exact E[K])={a1:.3f}  "
              f"alpha*(closed form)={a2:.3f}")
