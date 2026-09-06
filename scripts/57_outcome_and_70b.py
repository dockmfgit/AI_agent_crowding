"""Post-review v2.0 items R4 and W3 (GX10).

2.1 R4: distribution of x8 after eight rounds, per campaign
    -> results/r4_outcome_distribution.csv (+ pooled |x8-0.5| histogram rows)

2.2 W3: polarity-ratio interval for llama3.3:70b on the 8 common claims
    (4 originals + 4 approved rewrites), with a paired 8b comparator built
    from the SAME claims and the SAME message banks (Stage 1 singles for the
    originals, Stage 2b singles for the rewrites). Claim-cluster bootstrap
    (2,000 resamples of the 8 claims, shared draws across models) for the
    ratio, the difference (8b - 70B) and the ratio of ratios (8b / 70B).
    -> results/r8_70b_polarity_ci.csv

Note: the instruction sheet quotes n = 5,984 for 8b; that is the D-3 arm-A2
17-claim measurement. The same-8-claim comparator used here has 3,840
observations; both are reported.

Usage: python scripts/57_outcome_and_70b.py [PROJECT_ROOT]
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
EP_DIR = os.path.join(ROOT, "data", "stage2", "episodes")
RNG = np.random.default_rng(61)

ORIGINALS = [6, 382, 1569, 2070]          # content wrong -> truth FALSE
REWRITES = [90006, 90382, 91569, 92070]   # content right -> truth TRUE
RIDGE = 1e-3


# ------------------------------------------------------------ 2.1  R4
def campaign_of(name, block, rho):
    if block in ("B1", "B4", "B6"):
        return "stage2_armA_rho0"
    if block == "B3":
        return "stage2_armA_rho1"
    if block == "B2":
        return "stage2_armB"
    if block == "B5":
        return None                        # five-sample fidelity, excluded
    if name.startswith("S2b_A1"):
        return "stage2b_A1"
    if name.startswith("S2b_A2"):
        return "stage2b_A2"
    if name.startswith("B3c_"):
        return "stage2c"
    if name.startswith("D1_"):
        return "stage2d"
    return None


def r4_outcomes():
    rows = []
    for fp in sorted(glob.glob(os.path.join(EP_DIR, "*.json"))):
        name = os.path.basename(fp)[:-5]
        if name.startswith("trial"):
            continue
        d = json.load(open(fp))
        m = d["meta"]
        if m.get("spin_samples", 1) != 1:
            continue
        camp = campaign_of(name, m.get("block", ""), m.get("rho", 0))
        if camp is None:
            continue
        x8 = float(np.mean(d["stance_history"][8]))
        rows.append({"campaign": camp, "x8": x8})
    df = pd.DataFrame(rows)
    out = []
    for camp, sub in df.groupby("campaign"):
        dev = (sub.x8 - 0.5).abs()
        decided = sub[dev >= 0.1]
        corr = decided[decided.x8 > 0.5]
        wrong = decided[decided.x8 < 0.5]
        out.append({
            "campaign": camp, "n_episodes": len(sub),
            "n_decided": len(decided),
            "frac_decided": round(len(decided) / len(sub), 4),
            "n_undecided": len(sub) - len(decided),
            "frac_decided_beyond_0.4": round(
                float(((decided.x8 - 0.5).abs() > 0.4).mean()), 4)
            if len(decided) else np.nan,
            "n_correct_decided": len(corr),
            "correct_median_x8": round(float(corr.x8.median()), 4)
            if len(corr) else np.nan,
            "correct_p10_x8": round(float(corr.x8.quantile(0.10)), 4)
            if len(corr) else np.nan,
            "n_wrong_decided": len(wrong),
            "wrong_median_x8": round(float(wrong.x8.median()), 4)
            if len(wrong) else np.nan,
            "wrong_p90_x8": round(float(wrong.x8.quantile(0.90)), 4)
            if len(wrong) else np.nan,
        })
    outdf = pd.DataFrame(out).sort_values("campaign")
    # pooled |x8-0.5| histogram, 0.05 bins
    dev = (df.x8 - 0.5).abs()
    edges = np.arange(0, 0.5001, 0.05)
    hist, _ = np.histogram(dev, bins=edges)
    hrows = [{"campaign": f"ALL_hist_|x8-0.5|_[{edges[i]:.2f},{edges[i+1]:.2f})",
              "n_episodes": int(hist[i])} for i in range(len(hist))]
    outdf = pd.concat([outdf, pd.DataFrame(hrows)], ignore_index=True)
    outdf.to_csv(os.path.join(RES, "r4_outcome_distribution.csv"), index=False)
    print("== R4 outcome distribution ==")
    print(outdf.to_string(index=False))
    return outdf


# ------------------------------------------------------------ 2.2  W3
def fit_ridge_logit(X, y, ridge=RIDGE):
    b = np.zeros(X.shape[1])
    for _ in range(100):
        z = np.clip(X @ b, -30, 30)
        mu = 1 / (1 + np.exp(-z))
        g = X.T @ (mu - y) + ridge * b
        H = (X * (mu * (1 - mu) + 1e-9)[:, None]).T @ X \
            + ridge * np.eye(X.shape[1])
        try:
            step = np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            return None
        b -= step
        if np.max(np.abs(step)) < 1e-10:
            break
    return b


def polarity_frame_70b():
    df = pd.read_parquet(os.path.join(ROOT, "data", "stage2d",
                                      "d2_70b_obs.parquet"))
    truth_true = df.claim_id.isin(REWRITES)
    S_T = np.where(truth_true, df.l, df.k - df.l)
    S_F = np.where(truth_true, df.k - df.l, df.l)
    return pd.DataFrame({"claim_id": df.claim_id, "S_T": S_T, "S_F": S_F,
                         "chose_true": df.chose_true.astype(float)})


def polarity_frame_8b():
    s1 = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                      "main_obs.parquet"))
    s1 = s1[(s1.self_state == "none") & s1.claim_id.isin(ORIGINALS)]
    # originals: truth FALSE -> chose_true = 1 - y; TRUE-side msgs = wrong = k-l
    a = pd.DataFrame({"claim_id": s1.claim_id,
                      "S_T": (s1.k - s1.l).astype(float),
                      "S_F": s1.l.astype(float),
                      "chose_true": 1.0 - s1.y})
    s2 = pd.read_parquet(os.path.join(ROOT, "data", "stage2b",
                                      "single_obs.parquet"))
    s2 = s2[s2.claim_id.isin(REWRITES)]
    # rewrites: truth TRUE -> chose_true = y; TRUE-side msgs = correct = l
    b = pd.DataFrame({"claim_id": s2.claim_id, "S_T": s2.l.astype(float),
                      "S_F": (s2.k - s2.l).astype(float),
                      "chose_true": s2.y.astype(float)})
    return pd.concat([a, b], ignore_index=True)


def ratio_of(frame, claim_slots):
    """claim_slots: list of claim_ids (with repetition); each draw gets its
    own fixed effect. Returns |b_T|/|b_F| and the raw coefficients."""
    parts = []
    for slot, cid in enumerate(claim_slots):
        g = frame[frame.claim_id == cid]
        if not len(g):
            continue
        gg = g.copy()
        gg["slot"] = slot
        parts.append(gg)
    d = pd.concat(parts, ignore_index=True)
    slots = sorted(d.slot.unique())
    sidx = {s: i for i, s in enumerate(slots)}
    X = np.zeros((len(d), len(slots) + 2))
    X[np.arange(len(d)), d.slot.map(sidx)] = 1
    X[:, -2] = d.S_T
    X[:, -1] = d.S_F
    b = fit_ridge_logit(X, d.chose_true.to_numpy())
    if b is None or b[-1] == 0:
        return None
    return abs(b[-2]) / abs(b[-1]), b[-2], b[-1]


def w3_70b(n_boot=2000):
    f70 = polarity_frame_70b()
    f8 = polarity_frame_8b()
    claims = ORIGINALS + REWRITES
    r70 = ratio_of(f70, claims)
    r8 = ratio_of(f8, claims)
    print("== W3 point estimates (ridge %.0e, claim FE) ==" % RIDGE)
    print(f"70B: ratio={r70[0]:.4f} (bT={r70[1]:+.4f}, bF={r70[2]:+.4f}), "
          f"n={len(f70)}")
    print(f"8b (same 8 claims/banks): ratio={r8[0]:.4f} "
          f"(bT={r8[1]:+.4f}, bF={r8[2]:+.4f}), n={len(f8)}")
    boots = {"r70": [], "r8": [], "diff": [], "rr": []}
    n_fail = 0
    for _ in range(n_boot):
        draw = list(RNG.choice(claims, len(claims), replace=True))
        a = ratio_of(f70, draw)
        b = ratio_of(f8, draw)
        if a is None or b is None:
            n_fail += 1
            continue
        boots["r70"].append(a[0])
        boots["r8"].append(b[0])
        boots["diff"].append(b[0] - a[0])
        boots["rr"].append(b[0] / a[0])
    rows = []
    for key, est in [("ratio_70b", r70[0]), ("ratio_8b_same8", r8[0]),
                     ("diff_8b_minus_70b", r8[0] - r70[0]),
                     ("ratio_8b_over_70b", r8[0] / r70[0])]:
        arr = np.array(boots[{"ratio_70b": "r70",
                              "ratio_8b_same8": "r8",
                              "diff_8b_minus_70b": "diff",
                              "ratio_8b_over_70b": "rr"}[key]])
        lo, hi = np.percentile(arr, [2.5, 97.5])
        rows.append({"quantity": key, "estimate": round(est, 4),
                     "ci_lo": round(float(lo), 4),
                     "ci_hi": round(float(hi), 4),
                     "n_boot_ok": len(arr), "n_boot_failed": n_fail,
                     "n_obs_70b": len(f70), "n_obs_8b": len(f8),
                     "ridge": RIDGE})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, "r8_70b_polarity_ci.csv"), index=False)
    print(out.to_string(index=False))
    print("note: the published D-3 instruct arm-A2 ratio (17 claims, "
          "n=5,984) is 1.437 [1.250, 1.651]; the 8b comparator above uses "
          "the same 8 claims and message banks as the 70B probe.")


if __name__ == "__main__":
    r4_outcomes()
    w3_70b()
