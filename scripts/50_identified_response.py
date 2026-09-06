"""R1 (post-review): identified response models.

Usage: python scripts/50_identified_response.py [PROJECT_ROOT]

A. Stage 1 (llama3.1:8b, main_obs.parquet): joint per-k model with claim
   fixed effects anchored by the k=0 cells,
       logit p = FE_claim [+ theta*self_correct] + sum_k 1[k](bT_k l + bF_k (k-l)),
   for variants A (no self line) and B (self line). Claim-cluster bootstrap
   CIs. Rank of the design matrix is checked and reported. Also reports the
   alpha* implied by the identified per-k rule (power and flat extrapolation).
   -> results/r1_stage1_identified_perk.csv, results/r1_stage1_alpha_star.csv

B. Per-claim reduced models (identified because k varies within claim):
       logit p = c0_q + g(k)[delta_q k + beta_bar_q (2l-k)] [+ theta_q self],
   g = 1 (constant) and g = 1/(1+0.9k) (divisive, gamma from Stage 1 CV),
   for: the four Stage 2 claims (Stage 1 data, variants A and B), Stage 2b
   (7 claims), Stage 2c (20 claims), Stage 2d (11 claims).
   -> results/r1_claim_models.csv

C. Rank audit of the legacy per-k fits (fixed k, columns [1, l, k-l]) and
   the discrepancy between the legacy prediction (pooled intercept + per-k
   slopes) and the identified per-k probabilities at measured (k, l).
   -> results/r1_legacy_perk_audit.csv
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hmf_lib as H  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
GAMMA = 0.9
N_BOOT = 200
STAGE2_CLAIMS = [2070, 382, 6, 1569]


def stage1_joint(df, variant):
    ws = variant == "B"
    sub = df[df.self_state == "none"] if variant == "A" else df[df.self_state != "none"]
    claim_ids = sorted(sub.claim_id.unique())
    X, names = H.design_joint_perk(sub, claim_ids, ws)
    r, p = H.check_rank(X)
    print(f"[A] variant {variant}: n={len(sub)}, design rank {r}/{p}")
    assert r == p, "joint per-k design not full rank"
    y = sub.y.to_numpy(float)
    b = H.fit_logit_ridge(X, y)
    est = dict(zip(names, b))
    rng = np.random.default_rng(1)
    groups = {c: sub[sub.claim_id == c] for c in claim_ids}
    boots = []
    for _ in range(N_BOOT):
        cs = rng.choice(claim_ids, len(claim_ids), replace=True)
        sb = pd.concat([groups[c] for c in cs]).copy()
        sb["claim_id"] = np.repeat(np.arange(len(cs)), [len(groups[c]) for c in cs])
        Xb, nb = H.design_joint_perk(sb, list(range(len(cs))), ws)
        boots.append(dict(zip(nb, H.fit_logit_ridge(Xb, sb.y.to_numpy(float)))))
    B = pd.DataFrame(boots)
    fe = np.array([est[f"FE_{c}"] for c in claim_ids])
    rows = []
    for kk in H.KS_STAGE1:
        rows.append({"variant": variant, "k": kk,
                     "bT": est[f"bT_{kk}"], "bT_lo": B[f"bT_{kk}"].quantile(.025),
                     "bT_hi": B[f"bT_{kk}"].quantile(.975),
                     "bF": est[f"bF_{kk}"], "bF_lo": B[f"bF_{kk}"].quantile(.025),
                     "bF_hi": B[f"bF_{kk}"].quantile(.975),
                     "swing": est[f"bT_{kk}"] - est[f"bF_{kk}"],
                     "drift": est[f"bT_{kk}"] + est[f"bF_{kk}"],
                     "c0_meanFE": fe.mean(),
                     "theta": est.get("theta", np.nan),
                     "n_obs": len(sub), "n_boot": N_BOOT})
    fe_rows = [{"variant": variant, "claim_id": c, "FE": est[f"FE_{c}"]} for c in claim_ids]
    return pd.DataFrame(rows), pd.DataFrame(fe_rows), est


def alpha_star_scan(pfun, with_self=False, grid=np.arange(0.20, 2.001, 0.01)):
    """Largest alpha at which a wrong basin (>=2 stable roots) still exists,
    scanned upward; returns the first alpha with a single stable root."""
    prev = None
    for a in grid:
        fps = H.fixed_points(a, pfun, with_self, n_grid=2001, n_bisect=30)
        n_st = sum(p["stable"] for p in fps)
        if prev is not None and prev >= 2 and n_st == 1:
            return float(a)
        prev = n_st
    return np.nan


def fit_reduced(sub, gamma, with_self):
    X, names = H.design_reduced(sub, gamma, with_self)
    r, p = H.check_rank(X)
    b = H.fit_logit_ridge(X, sub.y.to_numpy(float), ridge=1e-3)
    return dict(zip(names, b)), (r, p)


def main():
    os.makedirs(RES, exist_ok=True)
    df = pd.read_parquet(os.path.join(ROOT, "data", "stage1", "main_obs.parquet"))

    # ---------------- A. Stage 1 joint per-k
    perk, fes, ests = [], [], {}
    for v in ["A", "B"]:
        t, f, est = stage1_joint(df, v)
        perk.append(t); fes.append(f); ests[v] = est
    perk = pd.concat(perk); fes = pd.concat(fes)
    perk.to_csv(os.path.join(RES, "r1_stage1_identified_perk.csv"), index=False)
    fes.to_csv(os.path.join(RES, "r1_stage1_identified_FE.csv"), index=False)
    print(perk.round(3).to_string(index=False))

    ast_rows = []
    a_perk = perk[perk.variant == "A"]
    for extrap in ["power", "flat"]:
        pf = H.response_perk(a_perk.c0_meanFE.iloc[0], a_perk.k, a_perk.bT, a_perk.bF, extrap)
        ast_rows.append({"rule": f"identified per-k (variant A), c0=mean FE, {extrap}",
                         "alpha_star": alpha_star_scan(pf)})
    # legacy-style mismatch for the record: per-k slopes with pooled c0=0.725
    pf = H.response_perk(0.725, a_perk.k, a_perk.bT, a_perk.bF, "power")
    ast_rows.append({"rule": "identified per-k slopes + pooled c0=0.725 (mismatch, for record)",
                     "alpha_star": alpha_star_scan(pf)})
    # pooled constant (identified) for reference
    co = pd.read_csv(os.path.join(RES, "stage1_coeffs.csv"))
    ca = co[co.variant == "A"].set_index("coef").estimate
    pf = H.response_reduced([ca.c0, (ca.beta_T + ca.beta_F) / 2, (ca.beta_T - ca.beta_F) / 2], None)
    ast_rows.append({"rule": "pooled constant (Stage 1 coefficients)", "alpha_star": alpha_star_scan(pf)})
    ast = pd.DataFrame(ast_rows)
    ast.to_csv(os.path.join(RES, "r1_stage1_alpha_star.csv"), index=False)
    print(ast.to_string(index=False))

    # ---------------- B. per-claim reduced models
    rows = []
    datasets = {
        "stage2_A": df[(df.self_state == "none") & df.claim_id.isin(STAGE2_CLAIMS)],
        "stage2_B": df[(df.self_state != "none") & df.claim_id.isin(STAGE2_CLAIMS)],
    }
    for st in ["stage2b", "stage2c", "stage2d"]:
        p = os.path.join(ROOT, "data", st, "single_obs.parquet")
        if os.path.exists(p):
            datasets[st] = pd.read_parquet(p)
    for name, d in datasets.items():
        ws = name.endswith("_B")
        for cid, sub in d.groupby("claim_id"):
            for gamma, gname in [(None, "constant"), (GAMMA, "divisive")]:
                est, (r, p) = fit_reduced(sub, gamma, ws)
                rows.append({"dataset": name, "claim_id": cid, "model": gname,
                             "gamma": gamma if gamma is not None else 0.0,
                             "with_self": ws, "rank": r, "n_par": p, "n_obs": len(sub),
                             "k_levels": ",".join(map(str, sorted(sub.k.unique()))),
                             **est})
    cm = pd.DataFrame(rows)
    cm.to_csv(os.path.join(RES, "r1_claim_models.csv"), index=False)
    print(cm.round(3).to_string(index=False))

    # ---------------- C. legacy per-k audit
    audit = []
    for st in ["stage2b", "stage2c", "stage2d"]:
        p = os.path.join(ROOT, "data", st, "single_obs.parquet")
        cpath = os.path.join(RES, f"{st}_single_coeffs.csv")
        if not (os.path.exists(p) and os.path.exists(cpath)):
            continue
        obs = pd.read_parquet(p)
        co = pd.read_csv(cpath, dtype={"k": str})
        for cid, sub in obs.groupby("claim_id"):
            cs = co[co.claim_id == cid]
            if not (cs.k == "pooled").any():
                continue
            c0p = float(cs[cs.k == "pooled"].c0.iloc[0])
            for k, sk in sub.groupby("k"):
                X3 = np.column_stack([np.ones(len(sk)), sk.l, (sk.k - sk.l)]).astype(float)
                r3, _ = H.check_rank(X3)
                X2 = np.column_stack([np.ones(len(sk)), sk.l]).astype(float)
                b2 = H.fit_logit_ridge(X2, sk.y.to_numpy(float), ridge=1e-6)
                ls = np.arange(k + 1)
                p_id = H.sig(b2[0] + b2[1] * ls)
                row = cs[cs.k == str(k)]
                if len(row):
                    p_code = H.sig(c0p + row.bT.iloc[0] * ls + row.bF.iloc[0] * (k - ls))
                    gap = float(np.max(np.abs(p_code - p_id)))
                else:
                    gap = np.nan
                audit.append({"dataset": st, "claim_id": cid, "k": k, "n": len(sk),
                              "rank_3col": r3, "A_k": b2[0], "B_k": b2[1],
                              "max_abs_gap_legacy_vs_identified": gap})
    au = pd.DataFrame(audit)
    au.to_csv(os.path.join(RES, "r1_legacy_perk_audit.csv"), index=False)
    print("\nlegacy per-k audit: rank_3col ==2 in",
          int((au.rank_3col == 2).sum()), "of", len(au), "fits;",
          "median max|gap| =", round(float(au.max_abs_gap_legacy_vs_identified.median()), 3),
          "max =", round(float(au.max_abs_gap_legacy_vs_identified.max()), 3))


if __name__ == "__main__":
    main()
