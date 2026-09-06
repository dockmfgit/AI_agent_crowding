"""Stage 0.5 preprocessing: raw episode JSONs -> data/groups.parquet.

One row per group (model, question, graph, episode), objective questions only.
x(t) = share of agents whose sign(mean of 5 raw samples) equals y_gt.
"""
import json
import glob
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(ROOT, "external", "physics-of-agents")

MODEL_DIRS = {
    "gpt-4o-mini": "gpt",
    "gemma-3n-e4b-it": "gma",
    "qwen3.5-9b": "qwn",
    "meta-llama-3-8b-instruct": "lma",
}
DELTAS = [0.05, 0.10, 0.20]


def graph_family(gid: str) -> str:
    if gid in ("square", "triangular"):
        return gid
    return "random"


def load_ground_truth():
    gt = {}
    for split in ("train", "test"):
        with open(os.path.join(REPO, "data", "obj", f"{split}.jsonl")) as f:
            for line in f:
                q = json.loads(line)
                gt[q["qid"]] = 1 if q["answer"] == "A" else -1
    return gt


def main():
    gt = load_ground_truth()
    rows = []
    degree_rows = []
    for mdir, mcode in MODEL_DIRS.items():
        files = sorted(glob.glob(os.path.join(
            REPO, "data", "models", mdir, "objective_energy", "*.json")))
        files = [f for f in files if not f.endswith("manifest.json")]
        for fp in files:
            name = os.path.basename(fp)[:-5]
            qid, gid, rep = name.rsplit("__", 2)
            rep = int(rep.replace("rep", ""))
            with open(fp) as f:
                d = json.load(f)
            y = gt[qid]
            raw = np.asarray(d["spins_raw_history"], dtype=float)  # (9, 32, 5)
            obar = raw.mean(axis=2)                                # (9, 32)
            sgn = np.sign(obar)
            x = (sgn == y).mean(axis=1)                            # (9,)
            n_zero_sign = int((sgn == 0).sum())
            n_zero_raw = int((raw == 0).sum())
            J = np.asarray(d["J"], dtype=int)
            k_i = np.abs(J).sum(axis=1)
            frac_neg_edges = float((J < 0).sum() / max((J != 0).sum(), 1))
            row = {
                "model": mcode, "model_dir": mdir, "qid": qid,
                "split": qid.split("_")[1], "graph": gid,
                "family": graph_family(gid), "rep": rep, "y_gt": y,
                "x0": x[0], "xT": x[8],
                "n_zero_sign": n_zero_sign, "n_zero_raw": n_zero_raw,
                "frac_neg_edges": frac_neg_edges,
            }
            for t in range(9):
                row[f"x{t}"] = x[t]
            for delta in DELTAS:
                tag = str(delta).replace("0.", "")
                if x[8] >= 0.5 + delta:
                    out = "correct"
                elif x[8] <= 0.5 - delta:
                    out = "false"
                else:
                    out = "undecided"
                row[f"outcome_d{tag}"] = out
            rows.append(row)
            degree_rows.append({
                "model": mcode, "graph": gid, "family": graph_family(gid),
                "degrees": k_i.tolist(),
            })
    df = pd.DataFrame(rows)
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    df.to_parquet(os.path.join(ROOT, "data", "groups.parquet"), index=False)

    # empirical P(k) per (model, family) — degrees pooled over that family's graphs
    deg = pd.DataFrame(degree_rows).drop_duplicates(subset=["model", "graph"])
    pk_rows = []
    for (mcode, fam), sub in deg.groupby(["model", "family"]):
        ks = np.concatenate([np.array(v) for v in sub["degrees"]])
        vals, cnts = np.unique(ks, return_counts=True)
        for v, c in zip(vals, cnts):
            pk_rows.append({"model": mcode, "family": fam, "k": int(v),
                            "p": c / len(ks), "n_nodes": len(ks)})
    pd.DataFrame(pk_rows).to_parquet(
        os.path.join(ROOT, "data", "pk_empirical.parquet"), index=False)

    print("groups:", len(df))
    print(df.groupby(["model", "family"]).size())
    print("\nx0 summary:\n", df["x0"].describe())
    print("\nzero-sign agents total:", df["n_zero_sign"].sum(),
          " zero raw samples total:", df["n_zero_raw"].sum())
    for delta in DELTAS:
        tag = str(delta).replace("0.", "")
        print(f"\noutcome_d{tag}:\n", df[f"outcome_d{tag}"].value_counts())


if __name__ == "__main__":
    main()
