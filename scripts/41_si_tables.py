"""Generate SI table fragments (LaTeX) from results/*.csv.
Output: manuscript/tex/tables/*.tex  (no new analysis; formatting only)"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "manuscript", "tex", "tables")
os.makedirs(OUT, exist_ok=True)


def w(name, body):
    with open(os.path.join(OUT, name + ".tex"), "w") as f:
        f.write(body)
    print("wrote", name)


def tab(cols, rows, align=None):
    align = align or "l" * len(cols)
    out = ["\\begin{tabular}{%s}" % align, "\\toprule",
           " & ".join(cols) + " \\\\", "\\midrule"]
    for r in rows:
        out.append(" & ".join(str(x) for x in r) + " \\\\")
    out += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(out)


def f3(v):
    return "" if pd.isna(v) else f"{v:.3f}"


# S: stage 1 coefficients
co = pd.read_csv(os.path.join(RES, "stage1_coeffs.csv"))
rows = []
for _, r in co.iterrows():
    nm = r.coef.replace("beta_T", "$\\beta_T$").replace(
        "beta_F", "$\\beta_F$").replace("theta", "$\\theta$").replace(
        "w_T", "$w_T$").replace("c0", "$c_0$")
    rows.append([r.variant, nm, f3(r.estimate),
                 f"[{f3(r.ci_lo)}, {f3(r.ci_hi)}]", int(r.n_obs)])
w("t_stage1_coeffs", tab(
    ["variant", "coefficient", "estimate", "95\\% CI (claim cluster)",
     "$n_{\\mathrm{obs}}$"], rows, "llccr"))

# S: decay model comparison
dm = pd.read_csv(os.path.join(RES, "stage1_decay_models.csv"))
dm["scheme"] = dm.scheme.fillna("null (additive)")
rows = [[r.scheme.replace("_", "\\_"), r.param, f"{r.loglik:.1f}",
         f"{r.aic:.1f}", f"{r.cv_loglik_per_obs:.5f}"]
        for _, r in dm.iterrows()]
w("t_decay", tab(["scheme", "parameter", "log-lik", "AIC",
                  "CV log-lik/obs"], rows, "lrrrr"))

# S: stage 2 committor (arm A, rho=0)
com = pd.read_csv(os.path.join(RES, "stage2_committor.csv"))
A = com[(com.arm == "A") & (com.rho == 0)].sort_values(["alpha", "x0_n"])
rows = [[f"{r.alpha:g}", int(r.x0_n), int(r.n), f3(r.q),
         f"[{f3(r.wilson_lo)}, {f3(r.wilson_hi)}]",
         f3(r.undecided), f3(r.q_d05), f3(r.q_d2), f3(r.q_excl_und)]
        for _, r in A.iterrows()]
w("t_s2_committor", tab(
    ["$\\alpha$", "$32x_0$", "$n$", "$q$", "Wilson 95\\%",
     "undec.", "$q_{\\delta=.05}$", "$q_{\\delta=.2}$", "$q_{\\text{excl}}$"],
    rows, "rrrrccccc"))

# S: empirical alpha* rates
ae = pd.read_csv(os.path.join(RES, "stage2_alpha_star_emp.csv"))
rows = [[f"{r.alpha:g}", int(r.n), f3(r.wrong_rate),
         f"[{f3(r.ci_lo)}, {f3(r.ci_hi)}]"] for _, r in ae.iterrows()]
w("t_s2_alphastar", tab(
    ["$\\alpha$", "$n$ (episodes, $x_0\\le 8/32$)", "wrong-consensus rate",
     "claim-cluster 95\\% CI"], rows, "rrcc"))

# S: arm B
rb = pd.read_csv(os.path.join(RES, "stage2_rule_discrimination.csv"))
rows = [[f"{r.alpha:g}", int(r.n), f3(r.wrong_rate_lowx0),
         f"[{f3(r.ci_lo)}, {f3(r.ci_hi)}]", str(bool(r.absorbing))]
        for _, r in rb.iterrows()]
w("t_s2_armB", tab(["$\\alpha$", "$n$", "wrong rate ($x_0\\le 10/32$)",
                    "95\\% CI", "wrong basin retained"], rows, "rrccc"))

# S: rho control
rho = pd.read_csv(os.path.join(RES, "stage2_rho_control.csv"))
rows = [[int(r.x0_n), int(r.n_rho0), f3(r.q_rho0), int(r.n_rho1),
         f3(r.q_rho1), f"{r.dq:+.4f}"] for _, r in rho.iterrows()]
w("t_s2_rho", tab(["$32x_0$", "$n_{\\rho=0}$", "$q_{\\rho=0}$",
                   "$n_{\\rho=1}$", "$q_{\\rho=1}$", "$\\Delta q$"],
                  rows, "rrrrrr"))

# S: one-step calibration
oc = pd.read_csv(os.path.join(RES, "stage2_onestep_calibration.csv"))
rows = [[f"{r.alpha:g}", int(r.n_transitions), f"{r.brier:.4f}",
         f"{r.brier_climatology:.4f}", f"{r.ece:.4f}"]
        for _, r in oc.iterrows()]
w("t_s2_onestep", tab(["$\\alpha$", "transitions", "Brier",
                       "Brier (climatology)", "ECE"], rows, "rrrrr"))

# S: stage 2b groups A1/A2
grp = pd.read_csv(os.path.join(RES, "stage2b_group.csv"))
a1 = grp[grp["set"] == "A1"]
piv = a1.pivot_table(index=["claim_id", "alpha"], columns="x0_n",
                     values="x8", aggfunc="mean")
rows = [[int(cid), f"{al:g}"] + [f3(piv.loc[(cid, al), c]) for c in
                                 piv.columns]
        for (cid, al) in piv.index]
w("t_s2b_a1", tab(["claim", "$\\alpha$"] +
                  [f"$32x_0={int(c)}$" for c in piv.columns], rows))
a2 = grp[grp["set"] == "A2"]
piv2 = a2.pivot_table(index="claim_id", columns="x0_n", values="x8",
                      aggfunc="mean")
orig = {90006: (6, [0.231, 0.203, 0.412]), 90382: (382, [0.000, 0.000, 0.003]),
        91569: (1569, [0.109, 0.125, 0.434]),
        92070: (2070, [0.019, 0.039, 0.028])}
rows = []
for cid in piv2.index:
    oid, om = orig[cid]
    rows.append([int(cid), int(oid)] +
                [f3(piv2.loc[cid, c]) for c in piv2.columns] +
                [f3(np.mean(om))])
w("t_s2b_a2", tab(["rewrite", "original"] +
                  [f"$32x_0={int(c)}$" for c in piv2.columns] +
                  ["orig.\\ mean $\\bar x_8$ ($x_0\\le 20/32$)"], rows))

# S: qwen predictions vs observed
bp = pd.read_csv(os.path.join(RES, "stage2d_blind_predictions.csv"))
d1 = pd.read_csv(os.path.join(RES, "stage2d_group.csv"))
rows = []
for _, r in bp[bp.claim_id.isin([6, 1569, 91569, 1239])].iterrows():
    sub = d1[(d1.claim_id == r.claim_id) & (d1.alpha == r.alpha)]
    obs = " / ".join(
        f3(sub[sub.x0_n == x].x8.mean()) for x in (4, 12, 20, 28))
    fp = r.fixed_points if isinstance(r.fixed_points, str) else "none (flows to boundary)"
    rows.append([int(r.claim_id), f"{r.alpha:g}", f3(r.c0), fp, obs])
w("t_qwen_pred_obs", tab(
    ["claim", "$\\alpha$", "$c_0$", "frozen fixed points",
     "observed $\\bar x_8$ ($32x_0=4/12/20/28$)"], rows, "rrrll"))

# S: 70B coefficients
sb = pd.read_csv(os.path.join(RES, "stage2d_70b_coeffs.csv"))
rows = [[int(r.claim_id), f3(r.c0), f3(r.bT), f3(r.bF), int(r.n),
         f3(r.p_true_k0)] for _, r in sb.iterrows()]
w("t_70b", tab(["claim", "$c_0$", "$\\beta_T$", "$\\beta_F$", "$n$",
                "$P(\\text{TRUE})$ at $k=0$"], rows, "rrrrrr"))

# S: E-block tables
em = pd.read_csv(os.path.join(RES, "stage2b_E_messages.csv"))
rows = [[int(r.claim_id), r.side, int(r.n), f"{r.words:.1f}",
         f"{r.hedges_per_msg:.3f}"] for _, r in em.iterrows()]
w("t_E_messages", tab(["claim", "side", "messages", "words/msg",
                       "hedges/msg"], rows, "rlrrr"))
ep = pd.read_csv(os.path.join(RES, "stage2b_E_probes.csv"))
rows = [[int(r.claim_id), r.side, r.source, f3(r["mean"]), int(r["size"])]
        for _, r in ep.iterrows()]
w("t_E_probes", tab(["claim", "side", "message source", "$P$(correct)",
                     "$n$"], rows, "rllcr"))
eb = pd.read_csv(os.path.join(RES, "stage2b_E_branching.csv"))
rows = [[f"{r.alpha:g}", int(r.n_flip_events), f3(r.sigma)]
        for _, r in eb.iterrows()]
w("t_E_branching", tab(["$\\alpha$", "flip events", "$\\sigma$ (mean "
                        "downstream flips)"], rows, "rrr"))
ec = pd.read_csv(os.path.join(RES, "stage2b_E_async_cascades.csv"))
ec.columns = ["size", "count"]
rows = [[int(r["size"]), int(r["count"])] for _, r in ec.iterrows()]
w("t_E_async", tab(["cascade size", "count"], rows, "rr"))
ef = pd.read_csv(os.path.join(RES, "stage2b_E_finitetime.csv"))
rows = [[f"{r.alpha:g}", int(r.x0_n), int(r.n), f"{r.mean_slope:+.3f}",
         f3(r.frac_interior), f3(r.frac_still_moving)]
        for _, r in ef.iterrows()]
w("t_E_finitetime", tab(
    ["$\\alpha$", "$32x_0$", "$n$", "mean $x_8-x_7$", "frac.\\ interior",
     "frac.\\ still moving"], rows, "rrrrrr"))

print("done")
