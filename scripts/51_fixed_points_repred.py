"""R2 + R3 (single-agent part): fixed points and phase classification recomputed
for every claim x alpha of Stages 2b, 2c, 2d, and for the four Stage 2 claims.

Usage: python scripts/51_fixed_points_repred.py [PROJECT_ROOT]

Three prediction versions per cell:
  frozen      : the class recorded at freeze time (from the blind-prediction
                files / notes), unchanged.
  searchfix   : the legacy response (pooled intercept + legacy per-k slopes,
                scripts/27) with only the fixed-point search and the phase
                classification corrected (endpoints, bisection, |F'|<1, all
                roots). Isolates the effect of R2.
  identified  : per-claim reduced models from scripts/50 (constant and
                divisive g), corrected search. Isolates R1 + R2 together.
Observed classes/crossings from the group CSVs (outcome rule delta = 0.1;
crossing = 50% correct-outcome point by linear interpolation over the x0
grid; bootstrap CI over episodes within cell).

Outputs: results/r23_repred_stage2b.csv, _stage2c.csv, _stage2d.csv,
         results/r23_stage2_armAB_fixed_points.csv, results/r23_summary.txt
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hmf_lib as H  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
spec = importlib.util.spec_from_file_location("pred27", os.path.join(HERE, "27_s2b_predict.py"))
pred27 = importlib.util.module_from_spec(spec); spec.loader.exec_module(pred27)

DELTA = 0.1
ALPHAS = {"stage2b": None, "stage2c": [0.30, 0.55], "stage2d": [0.30, 0.55, 1.00]}


def legacy_pfun(cs):
    c0p = float(cs[cs.k == "pooled"].c0.iloc[0])
    coef = pred27.make_coef(cs[cs.k != "pooled"])

    def pfun(k, ls, s=0):
        if k == 0:
            return np.full(len(ls), H.sig(c0p))
        bT, bF = coef(k)
        return H.sig(c0p + bT * ls + bF * (k - ls))
    return pfun


def fit_cross(x, y, ridge=0.002):
    """Logistic fit of P(correct outcome) on x0 with a weak L2 penalty (IRLS),
    so that separated cells have a finite estimate; the slope is required to
    be positive (monotone). Returns the 50% crossing, or None if the outcome
    is constant or the fitted slope is not positive."""
    if y.min() == y.max():
        return None
    X = np.column_stack([np.ones_like(x), x])
    w = np.zeros(2)
    for _ in range(100):
        z = np.clip(X @ w, -30, 30)
        mu = 1 / (1 + np.exp(-z))
        g = X.T @ (mu - y) + 2 * ridge * w
        Hm = (X * (mu * (1 - mu))[:, None]).T @ X + 2 * ridge * np.eye(2)
        step = np.linalg.solve(Hm, g)
        w -= step
        if np.max(np.abs(step)) < 1e-8:
            break
    a, b = w
    if b <= 0:
        return None
    return float(-a / b)


def observed_class(g, rng, n_boot=500):
    """g: episodes of one (claim, alpha) with columns x0_n, x8. Same rule as
    scripts/45: outcome delta = 0.1; all-same-sign -> monostable; otherwise a
    monotone logistic 50% crossing with an episode bootstrap CI."""
    g = g.copy()
    g["x0"] = g.x0_n / 32
    g["correct"] = (g.x8 >= 0.5 + DELTA).astype(float)
    g["wrong"] = (g.x8 <= 0.5 - DELTA).astype(float)
    cells = g.groupby("x0").agg(n=("x8", "size"), pc=("correct", "mean"), pw=("wrong", "mean"),
                                mx8=("x8", "mean")).reset_index()
    x, y = g.x0.to_numpy(), g.correct.to_numpy()
    if y.min() == y.max():
        if y.min() == 1:
            return "mono_correct", np.nan, np.nan, np.nan, cells
        if g.wrong.min() == 1:
            return "mono_wrong", np.nan, np.nan, np.nan, cells
        return "mono_undecided", np.nan, np.nan, np.nan, cells
    xc = fit_cross(x, y)
    boots = []
    n = len(g)
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        c = fit_cross(x[idx], y[idx])
        if c is not None and -1 < c < 2:
            boots.append(c)
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if len(boots) > 100 else (np.nan, np.nan))
    cls = "bistable" if 0 < xc < 1 else "mixed"
    return cls, float(xc), float(lo), float(hi), cells


def repred_stage(st, cm, rng):
    obs_path = os.path.join(ROOT, "data", st, "single_obs.parquet")
    co = pd.read_csv(os.path.join(RES, f"{st}_single_coeffs.csv"), dtype={"k": str})
    grp = pd.read_csv(os.path.join(RES, f"{st}_group.csv"))
    frozen = pd.read_csv(os.path.join(RES, f"{st}_blind_predictions.csv"))
    rows = []
    for cid, g_all in grp.groupby("claim_id"):
        cs = co[co.claim_id == cid]
        if not len(cs):
            continue
        pf_leg = legacy_pfun(cs)
        for a, g in g_all.groupby("alpha"):
            fr = frozen[(frozen.claim_id == cid) & (np.isclose(frozen.alpha, a))]
            frozen_fps = fr.fixed_points.iloc[0] if len(fr) else ""
            frozen_cls = fr["class"].iloc[0] if (len(fr) and "class" in fr.columns) else ""
            fps_leg = H.fixed_points(a, pf_leg)
            cls_leg, xc_leg = H.classify(fps_leg)
            row = {"stage": st, "claim_id": cid, "alpha": a,
                   "frozen_fixed_points": frozen_fps, "frozen_class": frozen_cls,
                   "searchfix_fps": H.fps_str(fps_leg), "searchfix_class": cls_leg, "searchfix_xc": xc_leg}
            for gname in ["constant", "divisive"]:
                m = cm[(cm.dataset == st) & (cm.claim_id == cid) & (cm.model == gname)].iloc[0]
                pf = H.response_reduced([m.c0, m.delta, m.beta_bar], None if gname == "constant" else m.gamma)
                fps = H.fixed_points(a, pf)
                cls, xc = H.classify(fps)
                row.update({f"id_{gname}_fps": H.fps_str(fps), f"id_{gname}_class": cls, f"id_{gname}_xc": xc})
            ocls, oxc, olo, ohi, cells = observed_class(g, rng)
            row.update({"obs_class": ocls, "obs_cross": oxc, "obs_ci_lo": olo, "obs_ci_hi": ohi,
                        "obs_n_episodes": len(g),
                        "obs_cells": "; ".join(f"x0={r.x0:.3f}:pc={r.pc:.2f}(n={r.n})" for r in cells.itertuples())})
            min_x0 = float(g.x0_n.min()) / 32
            # a crossing below the lowest seeded fraction cannot be resolved by the grid
            below_grid = (ocls == "mixed" and np.isfinite(oxc) and oxc < min_x0)
            row["obs_below_grid"] = below_grid
            for v in ["searchfix", "id_constant", "id_divisive"]:
                pc, xc = row[f"{v}_class"], row[f"{v}_xc"]
                strict = (pc == ocls)
                grid_ok = strict or (
                    (below_grid or ocls == "mono_correct") and
                    (pc == "mono_correct" or (pc == "bistable" and xc is not None and xc < min_x0)))
                row[f"{v}_match"] = "hit" if strict else ("grid_consistent" if grid_ok else "miss")
                row[f"{v}_in_ci"] = (bool(olo <= xc <= ohi) if (ocls == "bistable" and xc is not None and np.isfinite(olo)) else np.nan)
            rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, f"r23_repred_{st}.csv"), index=False)
    return out


def stage2_armAB(cm):
    """Fixed points for the four Stage 2 claims from identified models and the
    identified joint per-k rule (variant A), at the experimental alphas."""
    perk = pd.read_csv(os.path.join(RES, "r1_stage1_identified_perk.csv"))
    rows = []
    for arm, alphas, ws, ds in [("A", [0.20, 0.30, 0.38, 0.45, 0.55, 1.00], False, "stage2_A"),
                                ("B", [0.60, 0.90, 1.30], True, "stage2_B")]:
        for cid in sorted(cm[cm.dataset == ds].claim_id.unique()):
            for gname in ["constant", "divisive"]:
                m = cm[(cm.dataset == ds) & (cm.claim_id == cid) & (cm.model == gname)].iloc[0]
                b = [m.c0, m.delta, m.beta_bar] + ([m.theta] if ws else [])
                pf = H.response_reduced(b, None if gname == "constant" else m.gamma, ws)
                for a in alphas:
                    fps = H.fixed_points(a, pf, ws)
                    cls, xc = H.classify(fps)
                    st = [p["x"] for p in fps if p["stable"]]
                    rows.append({"arm": arm, "claim_id": cid, "model": f"identified {gname} (per claim)",
                                 "alpha": a, "fps": H.fps_str(fps), "class": cls, "xc": xc,
                                 "lowest_stable": min(st) if st else np.nan})
        # pooled-over-4-claims reduced models and joint per-k rule (variant of the arm)
        pk = perk[perk.variant == arm]
        pf = H.response_perk(pk.c0_meanFE.iloc[0], pk.k, pk.bT, pk.bF, "power",
                             theta=(pk.theta.iloc[0] if ws else 0.0))
        for a in alphas:
            fps = H.fixed_points(a, pf, ws)
            cls, xc = H.classify(fps)
            st = [p["x"] for p in fps if p["stable"]]
            rows.append({"arm": arm, "claim_id": "all17", "model": "identified joint per-k (Stage 1, 17 claims)",
                         "alpha": a, "fps": H.fps_str(fps), "class": cls, "xc": xc,
                         "lowest_stable": min(st) if st else np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, "r23_stage2_armAB_fixed_points.csv"), index=False)
    return out


def main():
    cm = pd.read_csv(os.path.join(RES, "r1_claim_models.csv"))
    rng = np.random.default_rng(7)
    lines = []
    for st in ["stage2b", "stage2c", "stage2d"]:
        if not os.path.exists(os.path.join(RES, f"{st}_group.csv")):
            continue
        out = repred_stage(st, cm, rng)
        n = len(out)
        lines.append(f"== {st}: {n} claim x alpha cells")
        for v in ["searchfix", "id_constant", "id_divisive"]:
            hits = int((out[f"{v}_match"] == "hit").sum())
            gc = int((out[f"{v}_match"] == "grid_consistent").sum())
            bis = out[out.obs_class == "bistable"]
            inci = bis[f"{v}_in_ci"].dropna()
            lines.append(f"   {v:12s}: strict class hits {hits}/{n} (+{gc} consistent within the seeding grid); "
                         f"threshold in CI {int(inci.sum())}/{len(inci)} (observed bistable cells: {len(bis)})")
        cols = ["claim_id", "alpha", "searchfix_class", "searchfix_match", "id_constant_class", "id_constant_xc", "id_constant_match",
                "id_divisive_class", "id_divisive_xc", "id_divisive_match", "obs_class", "obs_cross", "obs_ci_lo", "obs_ci_hi"]
        lines.append(out[cols].round(3).to_string(index=False))
    ab = stage2_armAB(cm)
    lines.append("== Stage 2 arms A/B fixed points (identified models)")
    lines.append(ab.round(3).to_string(index=False))
    txt = "\n".join(lines)
    open(os.path.join(RES, "r23_summary.txt"), "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
