"""Manuscript figures 1-6 (build task; no new analysis — plots documented
values from results/*.csv and notes/05,08,12,13,14).

Style: blue #2E6FB7 / red-orange #C8442C / gray #8a8a8a, light background,
direct labels, PDF + 300 dpi PNG into manuscript/tex/figs/.
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrow, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "manuscript", "tex", "figs")
BLUE, RED, GRAY = "#2E6FB7", "#C8442C", "#8a8a8a"
plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "legend.fontsize": 7.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "savefig.facecolor": "white"})
N = 32


def save(fig, name):
    fig.savefig(os.path.join(OUT, name + ".pdf"))
    fig.savefig(os.path.join(OUT, name + ".png"), dpi=300)
    plt.close(fig)
    print("wrote", name)


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


# ---------------- Fig 1: framework ----------------

def fig1():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.7),
                             gridspec_kw={"width_ratios": [1, 1.45]})
    ax = axes[0]
    label_pos = {0.30: (11.0, 0.20, "left"), 0.45: (6.2, 0.545, "center"),
                 1.00: (2.6, 0.50, "right")}
    for alpha, c in [(0.30, BLUE), (0.45, GRAY), (1.00, RED)]:
        Pk = p_alpha_k(alpha)
        ax.plot(range(len(Pk)), Pk, "-", color=c, lw=1.5)
        Ek = float(np.arange(len(Pk)) @ Pk)
        lx, ly, ha = label_pos[alpha]
        ax.annotate(f"α={alpha:g}\n(E[K]={Ek:.1f})", xy=(lx, ly),
                    color=c, fontsize=7, ha=ha, va="top")
    ax.set_xlim(0, 16); ax.set_ylim(0, 0.56)
    ax.set_xlabel("in-degree $k$"); ax.set_ylabel("$P_{\\alpha,N}(k)$")
    ax.set_title("(a) crowding-generated in-degree, $N=32$")
    axin = ax.inset_axes([0.70, 0.60, 0.29, 0.36])
    r = np.arange(0, 12)
    for alpha, c in [(0.30, BLUE), (1.00, RED)]:
        axin.plot(r, np.exp(-alpha * r), "o-", color=c, ms=2, lw=0.8)
    axin.set_xlabel("$r$ accepted", fontsize=6.5)
    axin.set_ylabel("$e^{-\\alpha r}$", fontsize=6.5)
    axin.tick_params(labelsize=6)

    ax = axes[1]; ax.axis("off")
    boxes = [
        (0.005, "single-agent\nmeasurement\n$h,\\ \\theta,\\ \\beta_T,\\ \\beta_F$\n(31,824 queries)"),
        (0.255, "reduction\n$\\bar\\beta,\\ \\delta,\\ \\beta(k)$\nclaim fields $h_q$"),
        (0.505, "mean-field map\n$G(x;\\bar K(\\alpha))$\nfold $\\Rightarrow \\alpha^*\\!,\\ K^*$"),
        (0.755, "collective runs\ncommittor $q(x_0)$\nfrozen\npredictions"),
    ]
    BW, BY, BH = 0.235, 0.24, 0.54
    for x0b, txt in boxes:
        ax.add_patch(Rectangle((x0b, BY), BW, BH, fill=True,
                               facecolor="#eef3fa", edgecolor=BLUE, lw=1.1))
        ax.text(x0b + BW/2, BY + BH/2, txt, ha="center", va="center",
                fontsize=6.3, linespacing=1.35)
    for x0b in (0.243, 0.493, 0.743):
        ax.add_patch(FancyArrow(x0b, BY + BH/2, 0.008, 0, width=0.010,
                                head_width=0.045, head_length=0.010,
                                color=GRAY))
    ax.text(0.5, 0.08, "no quantity fitted to collective data",
            ha="center", fontsize=7.5, color=RED)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_title("(b) prediction pipeline")
    fig.tight_layout()
    save(fig, "fig1_framework")

def fig2():
    df = pd.read_csv(os.path.join(ROOT, "results", "xc_hmf_logistic.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    ax = axes[0]
    names = {"gpt": ("GPT-4o-mini", BLUE), "gma": ("Gemma-3n", GRAY),
             "qwn": ("Qwen3.5-9B", RED), "lma": ("Llama-3-8B", "#5a5a5a")}
    for m, (lab, c) in names.items():
        sub = df[df.model == m]
        st = sub[sub.stability == "stable"]
        un = sub[sub.stability == "unstable"]
        ax.scatter(st.alpha, st.x, s=2.0, color=c, alpha=0.9, lw=0)
        ax.scatter(un.alpha, un.x, s=5.0, facecolors="none", edgecolors=c,
                   lw=0.5, alpha=0.9)
        astar = sub[sub.stability == "unstable"].alpha.max()
        if np.isfinite(astar) and astar < 2.95:
            ax.axvline(astar, color=c, lw=0.6, alpha=0.4)
            ax.annotate(f"$\\alpha^*$", xy=(astar, 0.95), color=c,
                        fontsize=7, ha="center")
        ax.plot([], [], "-", color=c, label=lab)
    ax.set_xlim(0.1, 3.0)
    ax.set_xlabel("crowding parameter $\\alpha$")
    ax.set_ylabel("fixed points $x$")
    ax.legend(loc="center right", frameon=False)
    ax.set_title("(a) bifurcation of the reduced map\n"
                 "(measured coefficient sets; open = unstable)")

    ax = axes[1]
    # notes/08 section 5 validation table (documented values)
    exact = [0.62, 1.40, 1.12, 0.84, 1.18, 0.90, 1.54, 0.42, 0.46, 0.46, 1.26]
    gfold = [0.640, 1.415, 1.172, 0.882, 1.199, 0.899, 1.568, 0.435, 0.470,
             0.502, 1.284]
    closed = [0.593, 1.248, 1.048, 0.804, 1.070, 0.818, 1.372, 0.409, 0.440,
              0.469, 1.141]
    measured = [False] * 7 + [True] * 4
    ax.plot([0.3, 1.7], [0.3, 1.7], ":", color=GRAY, lw=0.8)
    for ex, gf, cl, me in zip(exact, gfold, closed, measured):
        ax.plot(ex, gf, "o", color=BLUE, ms=6 if me else 4,
                mfc=BLUE if me else "none")
        ax.plot(ex, cl, "s", color=RED, ms=6 if me else 4,
                mfc=RED if me else "none")
    ax.plot([], [], "o", color=BLUE, label="G-fold, exact $E[K]$ (median 2.1%)")
    ax.plot([], [], "s", color=RED, label="fully closed form (median 6.4%)")
    ax.plot([], [], "o", color=GRAY, mfc=GRAY,
            label="filled = measured coefficient sets")
    ax.set_xlabel("exact $\\alpha^*$ (full $P(k)$ sum)")
    ax.set_ylabel("closed-form $\\alpha^*$")
    ax.legend(loc="upper left", frameon=False, fontsize=6.8)
    ax.set_title("(b) closed form vs. exact numerics\n(11 coefficient sets)")
    fig.tight_layout()
    save(fig, "fig2_theory")


# ---------------- Fig 3: single-agent measurement ----------------

def fig3():
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9))
    ax = axes[0]
    ks = np.array([1, 2, 3, 5, 8, 12])
    bT = np.array([3.074, 1.706, 1.126, 0.640, 0.450, 0.327])   # notes/05 s5
    bF = np.array([-0.779, -0.763, -0.743, -0.537, -0.416, -0.331])
    kk = np.linspace(1, 13, 200)
    for form, ls, lab in [(lambda k, c: c / (1 + 0.9 * k), "-",
                           "divisive $\\beta/(1+0.9k)$"),
                          (lambda k, c: c * np.exp(-0.14 * k), "--",
                           "load decay $\\beta e^{-0.14k}$")]:
        cT = np.sum(form(ks, 1) * bT) / np.sum(form(ks, 1) ** 2)
        ax.plot(kk, form(kk, cT), ls, color=GRAY, lw=1.0)
        ax.annotate(lab, xy=(6.7, form(6.7, cT) + 0.11), fontsize=6.6,
                    color=GRAY)
    ax.plot(ks, bT, "o", color=BLUE, label="$\\beta_T(k)$ (correct-side)")
    ax.plot(ks, -bF, "s", color=RED, label="$|\\beta_F(k)|$ (wrong-side)")
    ax.set_xlabel("inbox size $k$")
    ax.set_ylabel("per-message coefficient")
    ax.legend(frameon=False)
    ax.set_title("(a) load attenuation of per-message influence")

    ax = axes[1]
    co = pd.read_csv(os.path.join(ROOT, "results", "stage1_coeffs.csv"))
    show = [("A", "h"), ("A", "beta_T"), ("A", "beta_F"), ("A", "w_T"),
            ("B", "h"), ("B", "theta"), ("B", "beta_T"), ("B", "beta_F"),
            ("B", "w_T")]
    labels, vals, los, his, cols = [], [], [], [], []
    for var, coef in show:
        r = co[(co.variant == var) & (co.coef == coef)].iloc[0]
        labels.append(f"{coef}\n({var})")
        vals.append(r.estimate)
        los.append(r.estimate - r.ci_lo)
        his.append(r.ci_hi - r.estimate)
        cols.append(BLUE if var == "A" else RED)
    xp = np.arange(len(labels))
    for x, v, lo, hi, c in zip(xp, vals, los, his, cols):
        ax.errorbar([x], [v], yerr=[[lo], [hi]], fmt="none", ecolor=c,
                    capsize=3, lw=1.2)
    ax.scatter(xp, vals, c=cols, s=18, zorder=3)
    ax.axhline(0, color=GRAY, lw=0.6)
    ax.axhline(1, color=GRAY, lw=0.5, ls=":")
    ax.set_xticks(xp, [s.replace("beta_T", "$\\beta_T$")
                       .replace("beta_F", "$\\beta_F$")
                       .replace("theta", "$\\theta$")
                       .replace("w_T", "$w_T$") for s in labels], fontsize=7)
    ax.set_ylabel("estimate (95% claim-cluster CI)")
    ax.set_title("(b) response coefficients, A (blue) / B (red)", fontsize=8)
    fig.tight_layout()
    save(fig, "fig3_single_agent")


# ---------------- Fig 4: first collective wave ----------------

def fig4():
    com = pd.read_csv(os.path.join(ROOT, "results", "stage2_committor.csv"))
    roll = pd.read_csv(os.path.join(ROOT, "results",
                                    "stage2_surrogate_roll.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 3.0),
                             gridspec_kw={"width_ratios": [1.4, 1]})
    ax = axes[0]
    A = com[(com.arm == "A") & (com.rho == 0)]
    cmap = plt.cm.viridis(np.linspace(0, 0.9, A.alpha.nunique()))
    for c, (alpha, sub) in zip(cmap, A.groupby("alpha")):
        sub = sub.sort_values("x0_n")
        ax.errorbar(sub.x0, sub.q,
                    yerr=[np.clip(sub.q - sub.wilson_lo, 0, None),
                          np.clip(sub.wilson_hi - sub.q, 0, None)],
                    fmt="o-", color=c, capsize=2, ms=3, lw=1.2,
                    label=f"α={alpha:g}")
        rs = roll[(roll.alpha == alpha) & (roll.rho == 0)].groupby(
            "x0_n").q_roll.mean()
        ax.plot(rs.index / 32, rs.values, "--", color=c, lw=0.9, alpha=0.55)
    ax.axhline(0.5, color=GRAY, lw=0.6, ls=":")
    ax.annotate("pooled-coefficient prediction\n(dashed): rejected",
                xy=(0.36, 0.62), fontsize=7, color=GRAY)
    ax.annotate("observed committor:\nwrong consensus everywhere",
                xy=(0.42, 0.12), fontsize=7, color="k")
    ax.set_xlabel("initial correct fraction $x_0$")
    ax.set_ylabel("correct-consensus probability $q$")
    ax.legend(frameon=False, ncol=2, loc="upper left", fontsize=6.5)
    ax.set_title("(a) committor family (1,414 episodes)")

    ax = axes[1]
    alphas = [0.60, 0.90, 1.30]
    const_pred = [0.157, 0.338, 0.438]        # notes/12 section 3
    div_pred = [0.051, 0.067, 0.093]
    obs_lo = [0.028, 0.061, 0.092]
    obs_hi = [0.095, 0.072, 0.097]
    xp = np.arange(3)
    ax.plot(xp, const_pred, "s--", color=GRAY, label="constant rule")
    ax.plot(xp, div_pred, "o-", color=BLUE, label="normalized rule")
    ax.errorbar(xp + 0.08,
                [(a + b) / 2 for a, b in zip(obs_lo, obs_hi)],
                yerr=[[(a + b) / 2 - a for a, b in zip(obs_lo, obs_hi)],
                      [b - (a + b) / 2 for a, b in zip(obs_lo, obs_hi)]],
                fmt="D", color=RED, capsize=3, ms=4, label="observed")
    ax.set_xticks(xp, [f"α={a:g}" for a in alphas])
    ax.set_ylabel("wrong-basin attractor position $x^*$")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("(b) discrimination arm:\nattractor positions (variant B)")
    fig.tight_layout()
    save(fig, "fig4_collective")


# ---------------- Fig 5: polarity discrimination ----------------

def fig5():
    grp = pd.read_csv(os.path.join(ROOT, "results", "stage2b_group.csv"))
    # originals at alpha=0.30, matched x0 (from Stage 2 episodes; documented
    # per-claim means in notes/13 section 5)
    orig_means = {6: [0.231, 0.203, 0.412],       # x0 = 4, 12, 20 /32
                  382: [0.000, 0.000, 0.003],
                  1569: [0.109, 0.125, 0.434],
                  2070: [0.019, 0.039, 0.028]}
    para_of = {90006: 6, 90382: 382, 91569: 1569, 92070: 2070}
    fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.9),
                             gridspec_kw={"width_ratios": [1.15, 1]})
    ax = axes[0]
    ypos = np.arange(4)
    for i, (pid, oid) in enumerate(para_of.items()):
        o = np.mean(orig_means[oid])
        p = grp[(grp["set"] == "A2") & (grp.claim_id == pid)].x8.mean()
        ax.annotate("", xy=(p, i), xytext=(o, i),
                    arrowprops=dict(arrowstyle="->", color=GRAY, lw=1.2))
        ax.plot(o, i, "o", color=RED, ms=7)
        ax.plot(p, i, "o", color=BLUE, ms=7)
        ax.text(-0.05, i, f"claim {oid}", ha="right", va="center", fontsize=7)
    ax.plot([], [], "o", color=RED, label="original (denying side correct)")
    ax.plot([], [], "o", color=BLUE, label="negated rewrite (affirming side correct)")
    ax.axvline(0.5, color=GRAY, lw=0.6, ls=":")
    ax.set_yticks([])
    ax.set_xlim(-0.28, 1.05)
    ax.set_xlabel("mean final correct-side fraction $\\bar x_8$ (α=0.30)")
    ax.set_ylim(-1.6, 3.6)
    ax.legend(frameon=False, fontsize=6.6, loc="lower center", ncol=1)
    ax.set_title("(a) drift follows the assertion:\noriginal vs. negated rewrite")

    ax = axes[1]
    a1 = grp[grp["set"] == "A1"]
    markers = {993: "o", 1103: "s", 1239: "^"}
    for cid, sub in a1[a1.alpha == 0.30].groupby("claim_id"):
        m = sub.groupby("x0_n").x8.mean()
        ax.plot(m.index / 32, m.values, "-", marker=markers[cid],
                color=BLUE, ms=4, lw=1.0, alpha=0.85)
        dy = {993: -0.045, 1103: 0.02, 1239: 0.02}[cid]
        ax.annotate(f"{cid}", xy=(0.10, m.iloc[0] + dy), fontsize=6.5,
                    ha="right", color=BLUE)
    for cid, sub in a1[a1.alpha == 0.55].groupby("claim_id"):
        m = sub.groupby("x0_n").x8.mean()
        ax.plot(m.index / 32, m.values, "--", marker=markers[cid],
                color=RED, ms=4, lw=1.0, alpha=0.85)
    ax.plot([], [], "-", color=BLUE, label="α=0.30")
    ax.plot([], [], "--", color=RED, label="α=0.55")
    ax.plot([0, 1], [0, 1], ":", color=GRAY, lw=0.7)
    ax.set_xlabel("initial correct fraction $x_0$")
    ax.set_ylabel("$\\bar x_8$")
    ax.legend(frameon=False, fontsize=7, loc="lower right")
    ax.set_title("(b) true (SUPPORTS) claims:\ncorrect = affirming side")
    fig.tight_layout()
    save(fig, "fig5_polarity")


# ---------------- Fig 6: model generality ----------------

def fig6():
    d1 = pd.read_csv(os.path.join(ROOT, "results", "stage2d_group.csv"))
    ufp = {6: {0.30: 0.149, 0.55: 0.121, 1.00: 0.043},
           1239: {0.30: 0.661, 0.55: 0.653, 1.00: 0.621},
           1569: None, 91569: None}
    fig = plt.figure(figsize=(7.0, 3.0))
    gs = fig.add_gridspec(1, 5, width_ratios=[1, 1, 1, 1, 0.9], wspace=0.5)
    claims = [6, 1569, 91569, 1239]
    x0s = [4, 12, 20, 28]; alphas = [0.30, 0.55, 1.00]
    for ci, cid in enumerate(claims):
        ax = fig.add_subplot(gs[0, ci])
        sub = d1[d1.claim_id == cid]
        M = np.zeros((len(alphas), len(x0s)))
        for i, a in enumerate(alphas):
            for j, x0 in enumerate(x0s):
                M[i, j] = sub[(sub.alpha == a) & (sub.x0_n == x0)].x8.mean()
        ax.imshow(M, vmin=0, vmax=1, cmap="RdBu", aspect="auto", origin="lower")
        ax.set_xticks(range(4), [f"{x}" for x in x0s], fontsize=6.5)
        ax.set_yticks(range(3), [f"{a:g}" for a in alphas], fontsize=6.5)
        if ci == 0:
            ax.set_ylabel("α")
        ax.set_xlabel("$32x_0$", fontsize=7)
        kind = ("orig." if cid in (6, 1569) else
                "rewrite" if cid == 91569 else "SUPPORTS")
        pre = "(a) " if ci == 0 else ""
        ax.set_title(f"{pre}claim {cid}\n({kind})", fontsize=7.5)
        if ufp.get(cid):
            for i, a in enumerate(alphas):
                thr = ufp[cid][a] * 32
                xpos = np.interp(thr, x0s, range(4))
                ax.plot(xpos, i + 0.30, "*", color="#111111", ms=8,
                        mew=0.5, mec="white")
        for i in range(3):
            for j in range(4):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                        fontsize=5.6,
                        color="white" if abs(M[i, j] - 0.5) > 0.3 else "k")
    axb = fig.add_subplot(gs[0, 4])
    ratios = [1.44, 1.03]
    axb.bar([0, 1.5], ratios, color=[RED, BLUE], width=0.55)
    axb.set_xticks([0, 1.5], ["llama\n3.1:8b", "llama\n3.3:70b"], fontsize=6.0)
    axb.set_xlim(-0.75, 2.25)
    axb.axhline(1.0, color=GRAY, lw=0.8, ls=":")
    axb.set_ylim(0.9, 1.58)
    axb.set_yticks([1.0, 1.2, 1.4], ["1.0", "1.2", "1.4"], fontsize=6.5)
    axb.set_title("(b) assertion\nasymmetry", fontsize=7.5)
    for i, v in zip([0, 1.5], ratios):
        axb.text(i, v + 0.015, f"{v:.2f}", ha="center", fontsize=7)
    fig.tight_layout()
    save(fig, "fig6_generality")

fig1(); fig6()
