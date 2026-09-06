"""Stage 0.5 step 3: empirical committor q(x0) per model x graph family.

- bins of width 0.1 with Wilson 95% CI
- logistic fit logit q = a + b*x0, x_c = -a/b, bootstrap 95% CI (1000 resamples
  at the group level)
- outputs: fig/committor_{model}_{family}.png, fig/x0_hist.png,
  results/xc_empirical.csv, results/committor_bins.csv
"""
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import minimize

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RNG = np.random.default_rng(0)
BINS = np.linspace(0, 1, 11)
MODELS = ["gpt", "gma", "qwn", "lma"]
FAMILIES = ["random", "square", "triangular"]
DELTAS = {"05": 0.05, "1": 0.10, "2": 0.20}


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return p, c - hw, c + hw


def fit_logistic(x, y):
    """MLE for P(y=1) = sigmoid(a + b x); returns (a, b) or None."""
    def nll(w):
        z = np.clip(w[0] + w[1] * x, -30, 30)
        p = 1 / (1 + np.exp(-z))
        p = np.clip(p, 1e-12, 1 - 1e-12)
        return -(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()
    best = None
    for x0 in ([0.0, 1.0], [0.0, 5.0], [-2.0, 10.0]):
        r = minimize(nll, np.array(x0), method="BFGS")
        if best is None or r.fun < best.fun:
            best = r
    return best.x if best is not None else None


def xc_from_fit(x, y, n_boot=1000):
    """Point estimate and bootstrap percentile 95% CI for x_c = -a/b."""
    w = fit_logistic(x, y)
    a, b = w
    xc = -a / b if b != 0 else np.nan
    boots = []
    n = len(x)
    for _ in range(n_boot):
        idx = RNG.integers(0, n, n)
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        wb = fit_logistic(x[idx], yb)
        if wb is None or wb[1] == 0:
            continue
        boots.append(-wb[0] / wb[1])
    boots = np.array(boots)
    # keep only interior crossings; out-of-range x_c means no crossing in [0,1]
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if len(boots) > 50
              else (np.nan, np.nan))
    return a, b, xc, lo, hi, len(boots)


def main():
    df = pd.read_parquet(os.path.join(ROOT, "data", "groups.parquet"))
    os.makedirs(os.path.join(ROOT, "fig"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)

    # x0 histograms per model x family
    fig, axes = plt.subplots(4, 3, figsize=(12, 12), sharex=True)
    for i, m in enumerate(MODELS):
        for j, fam in enumerate(FAMILIES):
            sub = df[(df.model == m) & (df.family == fam)]
            axes[i, j].hist(sub.x0, bins=BINS, color="steelblue",
                            edgecolor="white")
            axes[i, j].set_title(f"{m} / {fam} (n={len(sub)})", fontsize=9)
    fig.suptitle("x0 distribution (share initially correct)")
    fig.supxlabel("x0")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "fig", "x0_hist.png"), dpi=150)
    plt.close(fig)

    bin_rows, xc_rows = [], []
    for dtag, delta in DELTAS.items():
        out_col = f"outcome_d{dtag}"
        for m in MODELS:
            for fam in FAMILIES:
                sub = df[(df.model == m) & (df.family == fam)]
                x = sub.x0.to_numpy()
                y = (sub[out_col] == "correct").to_numpy().astype(float)
                # binned committor
                for bi in range(10):
                    lo_e, hi_e = BINS[bi], BINS[bi + 1]
                    mask = ((x >= lo_e) & (x < hi_e)) if bi < 9 else (
                        (x >= lo_e) & (x <= hi_e))
                    n = int(mask.sum())
                    k = int(y[mask].sum())
                    p, lo, hi = wilson(k, n)
                    bin_rows.append({
                        "delta": delta, "model": m, "family": fam,
                        "bin_lo": lo_e, "bin_hi": hi_e, "n": n, "k": k,
                        "q": p, "ci_lo": lo, "ci_hi": hi})
                # logistic fit + bootstrap
                a, b, xc, blo, bhi, nboot = xc_from_fit(x, y)
                xc_rows.append({
                    "delta": delta, "model": m, "family": fam, "n": len(sub),
                    "a": a, "b": b, "xc": xc,
                    "xc_ci_lo": blo, "xc_ci_hi": bhi, "n_boot_ok": nboot})
                print(f"d={delta} {m}/{fam}: a={a:.2f} b={b:.2f} "
                      f"xc={xc:.3f} [{blo:.3f},{bhi:.3f}] nboot={nboot}")

    bins_df = pd.DataFrame(bin_rows)
    bins_df.to_csv(os.path.join(ROOT, "results", "committor_bins.csv"),
                   index=False)
    xc_df = pd.DataFrame(xc_rows)
    xc_df.to_csv(os.path.join(ROOT, "results", "xc_empirical.csv"),
                 index=False)

    # committor figures (delta = 0.1)
    xs = np.linspace(0, 1, 200)
    for m in MODELS:
        for fam in FAMILIES:
            bsub = bins_df[(bins_df.delta == 0.10) & (bins_df.model == m)
                           & (bins_df.family == fam) & (bins_df.n > 0)]
            xrow = xc_df[(xc_df.delta == 0.10) & (xc_df.model == m)
                         & (xc_df.family == fam)].iloc[0]
            fig, ax = plt.subplots(figsize=(5, 4))
            mid = (bsub.bin_lo + bsub.bin_hi) / 2
            yerr = [np.clip(bsub.q - bsub.ci_lo, 0, None),
                    np.clip(bsub.ci_hi - bsub.q, 0, None)]
            ax.errorbar(mid, bsub.q, yerr=yerr,
                        fmt="o", color="k", capsize=3, label="binned (Wilson 95%)")
            for _, r in bsub.iterrows():
                ax.annotate(f"{r.n}", ((r.bin_lo + r.bin_hi) / 2, 0.02),
                            ha="center", fontsize=7, color="gray")
            p = 1 / (1 + np.exp(-(xrow.a + xrow.b * xs)))
            ax.plot(xs, p, "-", color="crimson",
                    label=f"logistic; x_c={xrow.xc:.3f}")
            if np.isfinite(xrow.xc_ci_lo):
                ax.axvspan(xrow.xc_ci_lo, xrow.xc_ci_hi, color="crimson",
                           alpha=0.12)
            ax.axvline(xrow.xc, color="crimson", ls="--", lw=1)
            ax.axhline(0.5, color="gray", ls=":", lw=1)
            ax.set_xlabel("x0 (initial correct share)")
            ax.set_ylabel("q(x0) = P(correct consensus)")
            ax.set_title(f"{m} / {fam} (delta=0.1, n={int(xrow.n)})")
            ax.set_ylim(-0.02, 1.02)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(os.path.join(ROOT, "fig",
                                     f"committor_{m}_{fam}.png"), dpi=150)
            plt.close(fig)


if __name__ == "__main__":
    main()
