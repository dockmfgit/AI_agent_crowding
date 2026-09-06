"""Rank check: full 4-coefficient logistic rule + actual signed P(k+,k-)
from El et al. J matrices -> predicted x_c per model, vs empirical x_c.

Rule: P(next correct | s, a, b, c, e)
  = sigmoid(c0 + theta*s + cTp*a + cFp*b + cTn*c + cFn*e)
a,b = correct/incorrect messages via agree-label edges (a ~ Bin(k+, x)),
c,e = correct/incorrect via disagree-label edges (c ~ Bin(k-, x)).
Coefficients: scripts/05c (question-clustered point estimates).
"""
import json
import numpy as np
from math import comb

COEF = {
    "gpt": (-0.191, 0.658, 3.038, -2.879, 0.244, -0.203),
    "gma": (-0.535, 1.276, 1.215, -1.031, 0.675, -0.525),
    "qwn": (+0.593, 0.389, 1.702, -1.891, 0.501, -0.509),
    "lma": (-0.444, 0.886, 1.939, -1.695, 0.558, -0.446),
}
EMP_XC = {"gpt": 0.494, "gma": 0.285, "qwn": 0.142, "lma": 0.459}

JM = {d["id"]: np.array(d["J"], dtype=int) for d in json.load(open(
    "external/physics-of-agents/"
    "data/J_matrices.json"))["graphs"]}
RAND = [k for k in JM if k not in ("square", "triangular")]


def joint_pk(ids):
    from collections import Counter
    cnt, tot = Counter(), 0
    for gid in ids:
        J = JM[gid]
        kp, km = (J > 0).sum(1), (J < 0).sum(1)
        for a, b in zip(kp, km):
            cnt[(int(a), int(b))] += 1
            tot += 1
    return {k: v / tot for k, v in cnt.items()}


def sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60, 60)))


def F(x, P, coef):
    c0, th, cTp, cFp, cTn, cFn = coef
    out = 0.0
    for (kp, km), p in P.items():
        acc = 0.0
        for a in range(kp + 1):
            wa = comb(kp, a) * x**a * (1 - x)**(kp - a)
            for c in range(km + 1):
                wc = comb(km, c) * x**c * (1 - x)**(km - c)
                z = c0 + cTp * a + cFp * (kp - a) + cTn * c + cFn * (km - c)
                acc += wa * wc * (x * sig(z + th) + (1 - x) * sig(z))
        out += p * acc
    return out


def fps(P, coef, grid=1500):
    xs = np.linspace(1e-6, 1 - 1e-6, grid)
    f = np.array([F(x, P, coef) - x for x in xs])
    out = []
    for i in range(grid - 1):
        if f[i] * f[i + 1] < 0 or f[i] == 0:
            lo, hi, flo = xs[i], xs[i + 1], f[i]
            for _ in range(60):
                mid = (lo + hi) / 2
                fm = F(mid, P, coef) - mid
                if flo * fm <= 0:
                    hi = mid
                else:
                    lo, flo = mid, fm
            r = (lo + hi) / 2
            e = 1e-5
            sl = (F(r + e, P, coef) - F(r - e, P, coef)) / (2 * e)
            out.append((r, "unstable" if sl > 1 else "stable"))
    return out


P = joint_pk(RAND)
print("model | fixed points (random family, signed P(k+,k-)) | "
      "predicted x_c | empirical x_c")
pred = {}
for m, coef in COEF.items():
    r = fps(P, coef)
    uns = [x for x, s in r if s == "unstable"]
    pred[m] = uns[0] if len(uns) == 1 else (uns if uns else None)
    print(f"{m}: {[(round(x,3), s) for x, s in r]} | "
          f"{pred[m] if pred[m] is not None else 'none'} | {EMP_XC[m]}")

order_pred = sorted([m for m in pred if isinstance(pred[m], float)],
                    key=lambda m: pred[m])
order_emp = sorted(EMP_XC, key=lambda m: EMP_XC[m])
print("\npredicted order (low->high x_c):", order_pred)
print("empirical order (low->high x_c):", order_emp)
