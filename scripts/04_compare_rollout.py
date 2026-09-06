"""Stage 0.5 step 5: comparison of empirical, HMF, and 3-coupling rollout x_c.

Rollout: paper's fitted three-coupling logistic rule (res/couplings.json,
objective), stochastic discrete_rollout from the observed single-vote s(0)
of every objective episode, 20 stochastic replicates each, T=8.
Committor from rollout outcomes vs x0 = share of s(0) on the correct side
(single-vote convention; the empirical curve uses the mean-of-5 convention).

Outputs: results/xc_rollout.csv, results/comparison.csv, fig/xc_comparison.png
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(ROOT, "external", "physics-of-agents")
sys.path.insert(0, os.path.join(REPO, "res"))
from utils import pca3, static_field, discrete_rollout  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module  # noqa: E402
c2 = import_module("02_committor" .replace(".py", ""))  # fit_logistic etc.

MODEL_DIRS = {"gpt-4o-mini": "gpt", "gemma-3n-e4b-it": "gma",
              "qwen3.5-9b": "qwn", "meta-llama-3-8b-instruct": "lma"}
FAMILIES = ["random", "square", "triangular"]
DELTA = 0.10
N_REP = 20
RNG = np.random.default_rng(1)


def family(gid):
    return gid if gid in ("square", "triangular") else "random"


def load_bank():
    bank = {}
    for split in ("train", "test"):
        with open(os.path.join(REPO, "data", "obj", f"{split}.jsonl")) as f:
            for line in f:
                q = json.loads(line)
                bank[q["qid"]] = {
                    "q3": np.array(q["embedding_pca10"][:3], dtype=float),
                    "y": 1 if q["answer"] == "A" else -1}
    return bank


def main():
    bank = load_bank()
    items = sorted(json.load(open(os.path.join(
        REPO, "data", "obj", "persona_embeddings.json")))["items"],
        key=lambda it: it["idx"])
    P_obj = pca3(np.array([it["embedding"] for it in items], dtype=float))
    couplings = json.load(open(os.path.join(REPO, "res", "couplings.json")))

    roll_rows = []
    for mdir, mcode in MODEL_DIRS.items():
        three = couplings["params"][mcode]["objective"]["three"]
        w = np.array(three["field"]
                     + [three["betas"]["beta_pos"], three["betas"]["beta_neg"],
                        three["betas"]["beta_0"]])
        files = [f for f in sorted(glob.glob(os.path.join(
            REPO, "data", "models", mdir, "objective_energy", "*.json")))
            if not f.endswith("manifest.json")]
        phi_l, J_l, s0_l, y_l, fam_l = [], [], [], [], []
        for fp in files:
            name = os.path.basename(fp)[:-5]
            qid, gid, _ = name.rsplit("__", 2)
            d = json.load(open(fp))
            phi_l.append(static_field(P_obj, bank[qid]["q3"]))
            J_l.append(np.array(d["J"], dtype=float))
            s0_l.append(np.array(d["spins_history"][0], dtype=float))
            y_l.append(bank[qid]["y"])
            fam_l.append(family(gid))
        phi = np.array(phi_l)
        J = np.array(J_l)
        s0 = np.array(s0_l)
        y = np.array(y_l)[:, None]
        fam = np.array(fam_l)
        x0 = (s0 == y).mean(axis=1)
        for r in range(N_REP):
            traj = discrete_rollout(phi, J, s0, w, k=3, T=8,
                                    mode="stochastic", rng=RNG)
            xT = (traj[:, -1] == y).mean(axis=1)
            for e in range(len(files)):
                roll_rows.append({"model": mcode, "family": fam[e],
                                  "rep": r, "x0": x0[e], "xT": xT[e]})
        print(f"{mcode}: rolled {len(files)} episodes x {N_REP} reps")

    roll = pd.DataFrame(roll_rows)
    roll["correct"] = (roll.xT >= 0.5 + DELTA).astype(float)

    xc_roll_rows = []
    for mcode in MODEL_DIRS.values():
        for famname in FAMILIES:
            sub = roll[(roll.model == mcode) & (roll.family == famname)]
            wfit = c2.fit_logistic(sub.x0.to_numpy(), sub.correct.to_numpy())
            a, b = wfit
            xc = -a / b if b != 0 else np.nan
            xc_roll_rows.append({"model": mcode, "family": famname,
                                 "n": len(sub), "a": a, "b": b,
                                 "xc_rollout": xc})
            print(f"rollout {mcode}/{famname}: xc={xc:.3f}")
    xc_roll = pd.DataFrame(xc_roll_rows)
    xc_roll.to_csv(os.path.join(ROOT, "results", "xc_rollout.csv"),
                   index=False)

    emp = pd.read_csv(os.path.join(ROOT, "results", "xc_empirical.csv"))
    emp = emp[emp.delta == DELTA]
    hmf = pd.read_csv(os.path.join(ROOT, "results", "xc_hmf.csv"))
    h1 = hmf[hmf.w_T_label == "1"].set_index(["model", "family"])["xc_hmf"]
    h3 = hmf[hmf.w_T_label == "table3"].set_index(["model", "family"])["xc_hmf"]
    xr = xc_roll.set_index(["model", "family"])["xc_rollout"]

    comp_rows = []
    for _, r in emp.iterrows():
        key = (r.model, r.family)
        comp_rows.append({
            "model": r.model, "family": r.family, "n_groups": r.n,
            "xc_empirical": r.xc, "xc_emp_ci_lo": r.xc_ci_lo,
            "xc_emp_ci_hi": r.xc_ci_hi,
            "xc_hmf_wT1": h1.get(key, np.nan),
            "xc_hmf_wTtable3": h3.get(key, np.nan),
            "xc_rollout_3coupling": xr.get(key, np.nan),
        })
    comp = pd.DataFrame(comp_rows)
    comp["dxc_wT1"] = comp.xc_empirical - comp.xc_hmf_wT1
    comp["dxc_wTtable3"] = comp.xc_empirical - comp.xc_hmf_wTtable3
    comp["dxc_rollout"] = comp.xc_empirical - comp.xc_rollout_3coupling
    comp.to_csv(os.path.join(ROOT, "results", "comparison.csv"), index=False)
    print(comp.round(3).to_string())

    # scatter
    fig, ax = plt.subplots(figsize=(6, 6))
    markers = {"random": "o", "square": "s", "triangular": "^"}
    colors = {"gpt": "tab:blue", "gma": "tab:orange", "qwn": "tab:green",
              "lma": "tab:red"}
    for _, r in comp.iterrows():
        ax.errorbar(r.xc_hmf_wTtable3, r.xc_empirical,
                    yerr=[[max(r.xc_empirical - r.xc_emp_ci_lo, 0)],
                          [max(r.xc_emp_ci_hi - r.xc_empirical, 0)]],
                    fmt=markers[r.family], color=colors[r.model],
                    capsize=3, ms=8)
        ax.plot(r.xc_hmf_wT1, r.xc_empirical, markers[r.family],
                color=colors[r.model], mfc="none", ms=8, alpha=0.5)
    ax.plot([0, 1], [0, 1], "k--", lw=1)
    from matplotlib.lines import Line2D
    handles = ([Line2D([], [], marker="o", ls="", color=c, label=m)
                for m, c in colors.items()]
               + [Line2D([], [], marker=mk, ls="", color="gray", label=f)
                  for f, mk in markers.items()]
               + [Line2D([], [], marker="o", ls="", color="gray",
                         label="w_T=Table3 (filled)"),
                  Line2D([], [], marker="o", ls="", color="gray", mfc="none",
                         label="w_T=1 (open)")])
    ax.legend(handles=handles, fontsize=7, loc="upper left")
    ax.set_xlabel("x_c HMF")
    ax.set_ylabel("x_c empirical (delta=0.1)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "fig", "xc_comparison.png"), dpi=150)


if __name__ == "__main__":
    main()
