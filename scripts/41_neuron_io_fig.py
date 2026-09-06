"""Fig 3: the single agent as a stochastic binary neuron.

Usage: python scripts/41_neuron_io_fig.py [PROJECT_ROOT] [OUT_DIR]
Panel (a) is the author-drawn schematic manuscript/tex/figs/fig3_panel_a.png.

(a) schematic of the measured update rule; (b) observed choice rate per
design cell against the fitted net input, with the logistic curve, under
divisive normalization of the per-message weights; (c) the same with
constant (un-normalized) weights, where cells fan out by inbox size.

Reads data/stage1/main_obs.parquet (31,824 single-shot queries).
"""
import os, sys
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
import statsmodels.api as sm

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "manuscript", "tex", "figs")
BLUE, RED, GRAY = "#2E6FB7", "#C8442C", "#8a8a8a"
plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5,
    "legend.fontsize": 7.2, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42})
GAMMA = 0.9  # divisive normalization constant selected in Section 4

df = pd.read_parquet(os.path.join(ROOT, "data/stage1/main_obs.parquet"))
df["variant"] = np.where(df.self_state == "none", "A", "B")
df["s"] = (df.self_state == "self_correct").astype(float)
df["m"] = df.k - df.l  # wrong-side messages


def design(d, g):
    """Design matrix: claim fixed effects + (theta) + g(k)*l + g(k)*(k-l)."""
    X = pd.get_dummies(d.claim_id.astype(str), prefix="c", dtype=float)
    gk = g(d.k.values)
    X["bT"] = gk * d.l.values
    X["bF"] = gk * d.m.values
    if (d.variant == "B").all():
        X["theta"] = d.s.values
    return X


def fit(d, g):
    X = design(d, g)
    res = sm.Logit(d.y.values, X.values).fit(disp=0, maxiter=200)
    p = res.predict(X.values)
    return res, X.columns.tolist(), p


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def cells(d, p):
    """Per design cell (variant, k, l, s): observed rate and model-implied
    logit of the mean predicted probability (so a perfect fit lies on sigma)."""
    t = d.assign(p=p)
    g = t.groupby(["variant", "k", "l", "s"]).agg(n=("y", "size"), y=("y", "mean"),
                                                 pbar=("p", "mean")).reset_index()
    g["x"] = np.log(g.pbar / (1 - g.pbar))
    lo, hi = wilson(g.y * g.n, g.n)
    g["lo"], g["hi"] = lo, hi
    return g


g_div = lambda k: 1.0 / (1.0 + GAMMA * k)
g_const = lambda k: np.ones_like(k, dtype=float)

rows = {}
for name, g in [("divisive", g_div), ("constant", g_const)]:
    parts, ll = [], 0.0
    for v in ["A", "B"]:
        d = df[df.variant == v].reset_index(drop=True)
        res, cols, p = fit(d, g)
        ll += res.llf
        parts.append(cells(d, p))
        coef = dict(zip(cols, res.params))
        print(name, v, {k: round(coef[k], 3) for k in cols if not k.startswith("c_")},
              "llf", round(res.llf, 1))
    rows[name] = (pd.concat(parts, ignore_index=True), ll)
    print(name, "total log-lik", round(ll, 1))

# ----------------------------------------------------------------- figure
fig = plt.figure(figsize=(7.2, 3.1))
gs = fig.add_gridspec(1, 3, width_ratios=[1.2, 1.1, 1.1], wspace=0.35)

# (a) schematic (author-drawn panel, fig8_panel_a.png) ------------------
import matplotlib.image as mpimg
ax = fig.add_subplot(gs[0]); ax.set_axis_off()
img = mpimg.imread(os.path.join(OUT, "fig3_panel_a.png"))
ax.imshow(img, interpolation="none")  # "none": vector backends embed the PNG at full resolution
ax.set_anchor("N")
ax.set_title("(a) measured update rule", loc="left")

# (b),(c) collapse plots ------------------------------------------------
cmap = plt.get_cmap("viridis")
ks = sorted(df.k.unique())
kcol = {k: cmap(i / max(1, len(ks) - 1)) for i, k in enumerate(ks)}
uu = np.linspace(-4.5, 4.5, 300)
for gi, (name, title) in enumerate([("divisive", "(b) divisive normalization"),
                                    ("constant", "(c) constant weights")], start=1):
    ax = fig.add_subplot(gs[gi])
    g, ll = rows[name]
    ax.plot(uu, 1 / (1 + np.exp(-uu)), color="black", lw=1.1, zorder=1)
    for _, r in g.iterrows():
        mk = "o" if r.variant == "A" else "s"
        ax.errorbar(r.x, r.y, yerr=[[r.y - r.lo], [r.hi - r.y]], fmt="none",
                    ecolor=kcol[r.k], elinewidth=0.6, alpha=0.7, zorder=2)
        ax.plot(r.x, r.y, mk, ms=3.4, color=kcol[r.k], mec="white", mew=0.3, zorder=3)
    ax.set_xlim(-4.5, 4.5); ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("fitted net input $u$")
    if gi == 1:
        ax.set_ylabel("observed P(correct side)")
    ax.set_title(title, loc="left")
    # residual summary
    resid = np.sqrt(np.mean((g.y - 1 / (1 + np.exp(-g.x))) ** 2))
    ax.text(0.03, 0.93, f"RMS deviation {resid:.3f}\nlog-lik {ll:.0f}",
            transform=ax.transAxes, fontsize=6.6, va="top")
    if gi == 2:
        handles = [plt.Line2D([], [], marker="o", ls="", color=kcol[k], ms=3.6, label=f"$k={k}$") for k in ks]
        handles += [plt.Line2D([], [], marker="o", ls="", mfc="none", mec="black", ms=3.6, label="variant A"),
                    plt.Line2D([], [], marker="s", ls="", mfc="none", mec="black", ms=3.6, label="variant B")]
        fig.legend(handles=handles, loc="lower center", ncol=9, frameon=False, fontsize=6.4,
                   handletextpad=0.25, columnspacing=1.0, bbox_to_anchor=(0.56, -0.13))

fig.savefig(os.path.join(OUT, "fig3_neuron.pdf"), bbox_inches="tight")
fig.savefig(os.path.join(OUT, "fig3_neuron.png"), dpi=300, bbox_inches="tight")
print("saved")
