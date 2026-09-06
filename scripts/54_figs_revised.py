"""Revised manuscript figures after the identified re-analysis (CSV-driven).

  fig4_collective : (a) observed q(x0) per alpha (arm A, rho=0) with the
                    finite-horizon surrogate of the BLIND pooled rule (dashed,
                    from results/r34_surrogate_cells.csv, rule=blind_pooled);
                    (b) arm B: observed low-x0 mean x8 against surrogate
                    rollouts of the identified rules (perk17, claim_div,
                    claim_const).
  fig6_generality : qwen3:8b heatmaps with stars at the identified (divisive)
                    predicted unstable fixed points; 70B asymmetry bar.
  fig7_calibration: predicted vs observed thresholds for every qwen cell
                    observed bistable (eight-claim campaign, circles; four-claim
                    campaign, squares), identified divisive predictions.
  si_fig_perk     : identified per-k coefficients (Stage 1, variants A and B).

Usage: python scripts/54_figs_revised.py [PROJECT_ROOT] [fig4|fig6|fig7|si ...]
"""
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("fig") and sys.argv[1] != "si" else os.path.dirname(HERE)
WHICH = [a for a in sys.argv[1:] if a.startswith("fig") or a == "si"] or ["fig2", "fig4", "fig6", "fig7", "si"]
RES = os.path.join(ROOT, "results")
OUT = os.path.join(ROOT, "manuscript", "tex", "figs")
BLUE, RED, GRAY, GREEN = "#2E6FB7", "#C8442C", "#8a8a8a", "#3A8F5C"
plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "legend.fontsize": 7.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white", "pdf.fonttype": 42})


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    fig.savefig(os.path.join(OUT, name + ".pdf"), bbox_inches="tight")
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote", name)


def fig4():
    com = pd.read_csv(os.path.join(RES, "stage2_committor.csv"))
    cells = pd.read_csv(os.path.join(RES, "r34_surrogate_cells.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0), gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axes[0]
    A = com[(com.arm == "A") & (com.rho == 0)]
    cmap = plt.cm.viridis(np.linspace(0, 0.9, A.alpha.nunique()))
    blind = cells[(cells.rule == "blind_pooled") & (cells.arm == "A") & (cells.rho == 0)]
    for c, (alpha, sub) in zip(cmap, A.groupby("alpha")):
        sub = sub.sort_values("x0_n")
        ax.errorbar(sub.x0, sub.q, yerr=[np.clip(sub.q - sub.wilson_lo, 0, None), np.clip(sub.wilson_hi - sub.q, 0, None)],
                    fmt="o-", color=c, capsize=2, ms=3, lw=1.2, label=f"α={alpha:g}")
        b = blind[np.isclose(blind.alpha, alpha)].sort_values("x0")
        if len(b):
            ax.plot(b.x0, b.pred_q, "--", color=c, lw=0.9, alpha=0.6)
    ax.axhline(0.5, color=GRAY, lw=0.6, ls=":")
    ax.annotate("blind pooled rule, eight-round\nsurrogate (dashed)", xy=(0.30, 0.66), fontsize=7, color=GRAY)
    ax.annotate("observed: $q < 0.5$\nfrom every start", xy=(0.42, 0.10), fontsize=7, color="k")
    ax.set_xlabel("initial correct fraction $x_0$")
    ax.set_ylabel("correct-outcome probability $q$ (8 rounds)")
    ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=6.5)
    ax.set_title("(a) outcome family (1,414 episodes)")

    ax = axes[1]
    B = cells[(cells.arm == "B") & (cells.x0_n <= 10)]
    g = B.groupby(["rule", "alpha"]).agg(obs=("obs_mean_x8", "mean"), pred=("pred_mean_x8", "mean")).reset_index()
    alphas = sorted(g.alpha.unique())
    xp = np.arange(len(alphas))
    styles = {"claim_const": ("s--", GRAY, "constant rule"), "claim_div": ("o-", BLUE, "normalized rule"),
              "perk17": ("^-", GREEN, "normalized rule, 17-claim weights")}
    for rname, (fmt, col, lab) in styles.items():
        r = g[g.rule == rname].sort_values("alpha")
        if len(r):
            ax.plot(xp, r.pred, fmt, color=col, label=lab, ms=4)
    obs = g[g.rule == "claim_div"].sort_values("alpha").obs if (g.rule == "claim_div").any() else g.groupby("alpha").obs.mean()
    ax.plot(xp + 0.08, obs, "D", color=RED, ms=5, label="observed")
    ax.set_xticks(xp, [f"α={a:g}" for a in alphas])
    ax.set_ylabel("low-$x_0$ final correct fraction $\\bar x_8$")
    ax.set_ylim(0, max(0.5, float(g.pred.max()) + 0.05))
    ax.legend(frameon=False, fontsize=6.5)
    ax.set_title("(b) discrimination arm (variant B):\neight-round surrogates vs observed")
    fig.tight_layout()
    save(fig, "fig4_collective")


def fig6():
    d1 = pd.read_csv(os.path.join(RES, "stage2d_group.csv"))
    rp = pd.read_csv(os.path.join(RES, "r23_repred_stage2d.csv"))
    fig = plt.figure(figsize=(7.0, 3.0))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 0.9], wspace=0.5)
    claims = [6, 1569, 91569, 1239]
    x0s = [4, 12, 20, 28]
    alphas = [0.30, 0.55, 1.00]
    for ci, cid in enumerate(claims):
        ax = fig.add_subplot(gs[0, ci])
        sub = d1[d1.claim_id == cid]
        M = np.zeros((len(alphas), len(x0s)))
        for i, a in enumerate(alphas):
            for j, x0 in enumerate(x0s):
                M[i, j] = sub[(np.isclose(sub.alpha, a)) & (sub.x0_n == x0)].x8.mean()
        ax.imshow(M, vmin=0, vmax=1, cmap="RdBu", aspect="auto", origin="lower")
        ax.set_xticks(range(4), [f"{x}" for x in x0s], fontsize=6.5)
        ax.set_yticks(range(3), [f"{a:g}" for a in alphas], fontsize=6.5)
        if ci == 0:
            ax.set_ylabel("α")
        ax.set_xlabel("$32x_0$", fontsize=7)
        kind = "orig." if cid in (6, 1569) else "rewrite" if cid == 91569 else "SUPPORTS"
        ax.set_title(f"{'(a) ' if ci == 0 else ''}claim {cid}\n({kind})", fontsize=7.5)
        for i, a in enumerate(alphas):
            r = rp[(rp.claim_id == cid) & np.isclose(rp.alpha, a)]
            if len(r) and r.id_divisive_class.iloc[0] == "bistable":
                thr = float(r.id_divisive_xc.iloc[0]) * 32
                xpos = np.interp(thr, x0s, range(4))
                ax.plot(xpos, i + 0.30, "*", color="#111111", ms=8, mew=0.5, mec="white")
        for i in range(3):
            for j in range(4):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=5.6,
                        color="white" if abs(M[i, j] - 0.5) > 0.3 else "k")
    axb = fig.add_subplot(gs[0, 4])
    # same eight claims, same message bank, claim-FE polarity regression;
    # claim-cluster bootstrap intervals from scripts/57 (results/r8_70b_polarity_ci.csv)
    r8 = pd.read_csv(os.path.join(RES, "r8_70b_polarity_ci.csv")).set_index("quantity")
    ratios = [float(r8.loc["ratio_8b_same8", "estimate"]), float(r8.loc["ratio_70b", "estimate"])]
    los = [float(r8.loc["ratio_8b_same8", "ci_lo"]), float(r8.loc["ratio_70b", "ci_lo"])]
    his = [float(r8.loc["ratio_8b_same8", "ci_hi"]), float(r8.loc["ratio_70b", "ci_hi"])]
    xs = [0, 1.5]
    axb.bar(xs, ratios, color=[RED, BLUE], width=0.55)
    axb.errorbar(xs, ratios, yerr=[np.subtract(ratios, los), np.subtract(his, ratios)], fmt="none",
                 ecolor="#333333", elinewidth=0.9, capsize=3)
    axb.set_xticks(xs, ["llama\n3.1:8b", "llama\n3.3:70b"], fontsize=6.0)
    axb.set_xlim(-0.75, 2.25)
    axb.axhline(1.0, color=GRAY, lw=0.8, ls=":")
    axb.set_ylim(0.0, 3.0)
    axb.set_yticks([0, 1, 2, 3], ["0", "1", "2", "3"], fontsize=6.5)
    axb.set_title("(b) assertion\nasymmetry", fontsize=7.5)
    for i, v, h in zip(xs, ratios, his):
        axb.text(i, h + 0.06, f"{v:.2f}", ha="center", fontsize=7)
    fig.tight_layout()
    save(fig, "fig6_generality")


def fig7():
    c = pd.read_csv(os.path.join(RES, "r23_repred_stage2c.csv"))
    d = pd.read_csv(os.path.join(RES, "r23_repred_stage2d.csv"))
    r5 = pd.read_csv(os.path.join(RES, "r5_prediction_intervals.csv"))
    r5["alpha"] = r5.alpha.round(2)
    c["alpha"] = c.alpha.round(2); d["alpha"] = d.alpha.round(2)
    fig, ax = plt.subplots(figsize=(3.6, 3.4))
    ax.plot([-0.1, 1], [-0.1, 1], ":", color=GRAY, lw=0.8)
    for df, mk, col, lab in [(c, "o", BLUE, "eight-claim campaign (11 cells)"), (d, "s", GREEN, "four-claim campaign (6 cells)")]:
        b = df[(df.obs_class == "bistable") & (df.id_divisive_class == "bistable")].copy()
        # prediction-side intervals (single-agent bootstrap, scripts/55)
        b = b.merge(r5[["claim_id", "alpha", "xc_lo", "xc_hi"]], on=["claim_id", "alpha"], how="left")
        xerr = [np.clip(b.id_divisive_xc.astype(float) - b.xc_lo, 0, None).fillna(0),
                np.clip(b.xc_hi - b.id_divisive_xc.astype(float), 0, None).fillna(0)]
        ax.errorbar(b.id_divisive_xc.astype(float), b.obs_cross, xerr=xerr,
                    yerr=[np.clip(b.obs_cross - b.obs_ci_lo, 0, None), np.clip(b.obs_ci_hi - b.obs_cross, 0, None)],
                    fmt=mk, color=col, ms=4.5, capsize=2, lw=0.9, label=f"{lab}")
        for _, r in b.iterrows():
            ax.annotate(f"{int(r.claim_id)}", (float(r.id_divisive_xc), r.obs_cross), fontsize=5.5,
                        xytext=(3, 3), textcoords="offset points", color=col)
    ax.set_xlim(0, 0.85); ax.set_ylim(-0.10, 0.85)
    ax.set_xlabel("predicted threshold (unstable fixed point)")
    ax.set_ylabel("observed threshold (50% crossing, 8 rounds)")
    ax.legend(frameon=False, fontsize=6.5, loc="upper left")
    ax.set_aspect("equal")
    fig.tight_layout()
    save(fig, "fig7_calibration")


def si_fig():
    p = pd.read_csv(os.path.join(RES, "r1_stage1_identified_perk.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9), sharey=True)
    for ax, v in zip(axes, ["A", "B"]):
        s = p[p.variant == v]
        ax.errorbar(s.k, s.bT, yerr=[s.bT - s.bT_lo, s.bT_hi - s.bT], fmt="o-", color=BLUE, capsize=2, ms=4, label="$\\beta_T(k)$")
        ax.errorbar(s.k, s.bF, yerr=[s.bF - s.bF_lo, s.bF_hi - s.bF], fmt="s-", color=RED, capsize=2, ms=4, label="$\\beta_F(k)$")
        kk = np.linspace(1, 12, 100)
        ax.axhline(0, color=GRAY, lw=0.6, ls=":")
        ax.set_xscale("log"); ax.set_xticks([1, 2, 3, 5, 8, 12]); ax.set_xticklabels(["1", "2", "3", "5", "8", "12"])
        ax.set_xlabel("inbox size $k$")
        ttl = "(a) variant A (no own-state line)" if v == "A" else "(b) variant B (own-state line)"
        ax.set_title(ttl)
        ax.text(0.97, 0.95, f"$c_0$ (mean FE) = {s.c0_meanFE.iloc[0]:.2f}" + (f", $\\theta$ = {s.theta.iloc[0]:.2f}" if v == "B" else ""),
                transform=ax.transAxes, ha="right", va="top", fontsize=7)
    axes[0].set_ylabel("per-message coefficient")
    axes[0].legend(frameon=False, fontsize=7, loc="upper right", bbox_to_anchor=(1.0, 0.9))
    fig.tight_layout()
    save(fig, "figS1_perk_identified")


def fig2():
    """Fig. 2: (a) bifurcation of the reduced map (as in scripts/40);
    (b) validation of the two closure levels against the precise fold of the
    full map, from results/r6_fold_precision.csv (scripts/56)."""
    df = pd.read_csv(os.path.join(RES, "xc_hmf_logistic.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    ax = axes[0]
    names = {"gpt": ("GPT-4o-mini", BLUE), "gma": ("Gemma-3n", GRAY),
             "qwn": ("Qwen3.5-9B", RED), "lma": ("Llama-3-8B", "#5a5a5a")}
    for m, (lab, c) in names.items():
        sub = df[df.model == m]
        st = sub[sub.stability == "stable"]
        un = sub[sub.stability == "unstable"]
        ax.scatter(st.alpha, st.x, s=2.0, color=c, alpha=0.9, lw=0)
        ax.scatter(un.alpha, un.x, s=5.0, facecolors="none", edgecolors=c, lw=0.5, alpha=0.9)
        astar = sub[sub.stability == "unstable"].alpha.max()
        if np.isfinite(astar) and astar < 2.95:
            ax.axvline(astar, color=c, lw=0.6, alpha=0.4)
            ax.annotate("$\\alpha^*$", xy=(astar, 0.95), color=c, fontsize=7, ha="center")
        ax.plot([], [], "-", color=c, label=lab)
    ax.set_xlim(0.1, 3.0)
    ax.set_xlabel("crowding parameter $\\alpha$")
    ax.set_ylabel("fixed points $x$")
    ax.legend(loc="center right", frameon=False)
    ax.set_title("(a) bifurcation of the reduced map\n(measured coefficient sets; open = unstable)")

    ax = axes[1]
    r6 = pd.read_csv(os.path.join(RES, "r6_fold_precision.csv"))
    measured = r6.set_index("set").index.str.contains("measured").tolist()
    ax.plot([0.3, 1.7], [0.3, 1.7], ":", color=GRAY, lw=0.8)
    for (_, r), me in zip(r6.iterrows(), measured):
        ax.plot(r.alpha_F_fold, r.alpha_G_exactEK, "o", color=BLUE, ms=6 if me else 4, mfc=BLUE if me else "none")
        ax.plot(r.alpha_F_fold, r.alpha_G_closed, "s", color=RED, ms=6 if me else 4, mfc=RED if me else "none")
    m1, m2 = 100 * r6.rel_err_exactEK.median(), 100 * r6.rel_err_closed.median()
    ax.plot([], [], "o", color=BLUE, label=f"$G$-fold, exact $E[K]$ (median {m1:.1f}%)")
    ax.plot([], [], "s", color=RED, label=f"fully closed form (median {m2:.1f}%)")
    ax.plot([], [], "o", color=GRAY, mfc=GRAY, label="filled = measured coefficient sets")
    ax.set_xlabel("exact $\\alpha^*$ (fold of the full map $F$)")
    ax.set_ylabel("reduced-map $\\alpha^*$")
    ax.legend(loc="upper left", frameon=False, fontsize=6.8)
    ax.set_title("(b) reduced map vs. exact numerics\n(11 coefficient sets)")
    fig.tight_layout()
    save(fig, "fig2_theory")


if __name__ == "__main__":
    for w in WHICH:
        {"fig2": fig2, "fig4": fig4, "fig6": fig6, "fig7": fig7, "si": si_fig}[w]()
