"""Stage 2b final analysis: hypothesis-table answers, per-claim tables,
blind-prediction comparison, polarity figure.

Inputs: data/stage2/episodes/S2b_*.json (groups), Stage 2 originals for the
paraphrase contrast, results/stage2b_blind_predictions.csv.
Outputs: results/stage2b_group.csv, fig/stage2b_polarity.png,
printed tables for notes/13.
"""
import glob
import json
import os

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP_DIR = os.path.join(ROOT, "data", "stage2", "episodes")
DELTA = 0.10
PARA_OF = {90006: 6, 91569: 1569, 90382: 382, 92070: 2070}


def load(prefix):
    rows = []
    for fp in sorted(glob.glob(os.path.join(EP_DIR, prefix + "*.json"))):
        d = json.load(open(fp))
        m = d["meta"]
        x = [float(np.mean(s)) for s in d["stance_history"]]
        rows.append({"claim_id": m["claim_id"], "alpha": m["alpha"],
                     "x0_n": m["x0_n"], "rep": m["rep"], "x8": x[8],
                     "n_parse_fail": m["n_parse_fail"]})
    return pd.DataFrame(rows)


def cell_table(df, label):
    if not len(df):
        print(f"{label}: no episodes yet")
        return None
    t = df.pivot_table(index=["claim_id", "alpha"], columns="x0_n",
                       values="x8", aggfunc="mean").round(3)
    n = df.pivot_table(index=["claim_id", "alpha"], columns="x0_n",
                       values="x8", aggfunc="size")
    q = df.assign(c=(df.x8 >= 0.5 + DELTA).astype(float)).pivot_table(
        index=["claim_id", "alpha"], columns="x0_n", values="c",
        aggfunc="mean").round(3)
    print(f"\n=== {label}: mean x8 per cell ===\n{t.to_string()}")
    print(f"n per cell:\n{n.to_string()}")
    print(f"q (P(x8 >= 0.6)):\n{q.to_string()}")
    return t


def main():
    a1 = load("S2b_A1")
    a2 = load("S2b_A2")
    print(f"A1 episodes: {len(a1)}, A2 episodes: {len(a2)}, "
          f"parse fails: {a1.n_parse_fail.sum() if len(a1) else 0} / "
          f"{a2.n_parse_fail.sum() if len(a2) else 0}")
    t1 = cell_table(a1, "A-1 SUPPORTS")
    t2 = cell_table(a2, "A-2 paraphrases (alpha=0.30)")

    # Stage 2 originals at alpha=0.30, matching x0 levels
    orig = []
    for fp in glob.glob(os.path.join(EP_DIR, "B[16]_*.json")):
        d = json.load(open(fp))
        m = d["meta"]
        if (m["alpha"] == 0.30 and not m.get("rho", 0)
                and m.get("spin_samples", 1) == 1
                and m["x0_n"] in (4, 12, 20, 28)):
            orig.append({"claim_id": m["claim_id"], "x0_n": m["x0_n"],
                         "x8": float(np.mean(d["stance_history"][8]))})
    od = pd.DataFrame(orig)
    print("\n=== Stage 2 originals (alpha=0.30, matching x0) mean x8 ===")
    to = od.pivot_table(index="claim_id", columns="x0_n", values="x8",
                        aggfunc="mean").round(3)
    print(to.to_string())

    pd.concat([a1.assign(set="A1"), a2.assign(set="A2")]).to_csv(
        os.path.join(ROOT, "results", "stage2b_group.csv"), index=False)

    # hypothesis answers (direction of drift from x0=0.5 line):
    # drift measured as mean x8 at x0=12 and 20 (interior levels)
    print("\n=== hypothesis table quantities ===")
    if len(a1):
        for (cid, alpha), sub in a1.groupby(["claim_id", "alpha"]):
            mid = sub[sub.x0_n.isin([12, 20])]
            print(f"A-1 claim {cid} alpha={alpha}: mean x8 (x0=12/32)="
                  f"{sub[sub.x0_n == 12].x8.mean():.3f}, (x0=20/32)="
                  f"{sub[sub.x0_n == 20].x8.mean():.3f}")
    if len(a2):
        for cid, sub in a2.groupby("claim_id"):
            oc = od[od.claim_id == PARA_OF[cid]]
            print(f"A-2 {cid} (orig {PARA_OF[cid]}): para x8(12)="
                  f"{sub[sub.x0_n == 12].x8.mean():.3f} vs orig "
                  f"{oc[oc.x0_n == 12].x8.mean():.3f}; para x8(20)="
                  f"{sub[sub.x0_n == 20].x8.mean():.3f} vs orig "
                  f"{oc[oc.x0_n == 20].x8.mean():.3f}")

    # figure: polarity contrast
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), sharey=True)
    x0s = [4, 12, 20, 28]
    if len(a1):
        for (cid, alpha), sub in a1.groupby(["claim_id", "alpha"]):
            m = sub.groupby("x0_n").x8.mean()
            axes[0].plot(m.index / 32, m.values,
                         "o-" if alpha == 0.30 else "s--",
                         label=f"{cid} α={alpha}")
    axes[0].set_title("A-1 SUPPORTS claims (correct = affirm)")
    if len(a2):
        for cid, sub in a2.groupby("claim_id"):
            m = sub.groupby("x0_n").x8.mean()
            axes[1].plot(m.index / 32, m.values, "o-",
                         label=f"{cid}")
    axes[1].set_title("A-2 paraphrases α=0.30 (correct = affirm)")
    for cid, sub in od.groupby("claim_id"):
        m = sub.groupby("x0_n").x8.mean()
        axes[2].plot(m.index / 32, m.values, "o-", label=f"{cid}")
    axes[2].set_title("Stage 2 originals α=0.30 (correct = negate)")
    for ax in axes:
        ax.plot([0, 1], [0, 1], "k:", lw=1)
        ax.axhline(0.5, color="gray", lw=0.5)
        ax.set_xlabel("x0")
        ax.legend(fontsize=7)
    axes[0].set_ylabel("mean x8 (correct-side share)")
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "fig", "stage2b_polarity.png"), dpi=150)
    print("\nfigure written")


if __name__ == "__main__":
    main()
