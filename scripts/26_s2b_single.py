"""Stage 2b mini single-call measurement (variant A scaffold).

7 claims (3 SUPPORTS + 4 paraphrases) x k in {2,5,8} x Stage-1 l levels
x 24 reps (A/B counterbalanced), messages drawn from the purity-checked
Stage 2b bank, presentation order randomized.

Output: data/stage2b/single_obs.parquet, results/stage2b_single_coeffs.csv
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage1_lib
stage1_lib.URL = "http://127.0.0.1:11435/api/generate"
stage1_lib.CONCURRENCY = 16
from stage1_lib import ROOT, run_batch

RNG = np.random.default_rng(17)
K_LEVELS = {2: [0, 1, 2], 5: [0, 1, 2, 3, 4, 5], 8: [0, 2, 4, 6, 8]}
N_REP = 24

PERSONAS = [
    "You are a climate scientist.",
    "You are an atmospheric physicist.",
    "You are an oceanographer.",
    "You are a glaciologist.",
    "You are a statistician specializing in environmental data.",
    "You are a meteorologist.",
    "You are an ecologist.",
    "You are a geophysicist.",
    "You are an environmental economist.",
    "You are a science journalist with a physics background.",
    "You are a paleoclimatologist.",
    "You are an energy systems engineer.",
]

PROMPT_TMPL = (
    "# Your Expertise\n{persona}\n\n"
    "# Messages\n"
    "You received the following messages from fellow panelists:\n"
    "{inbox}\n\n"
    "# Problem\n"
    "You are one member of an expert panel judging the following claim.\n"
    'Claim: "{claim}"\n'
    "Options:\n"
    "A) {option_A}\n"
    "B) {option_B}\n"
    "# Instruction\n"
    "Give your direct answer on which option is correct. Do NOT work through\n"
    "the problem, show any steps, compute, or explain — just commit to a snap\n"
    "judgement.\n"
    "## Response Format\n"
    "Respond with a single character, A or B, and nothing else."
)


def fit_logit(X, y):
    b = np.zeros(X.shape[1])
    for _ in range(60):
        z = np.clip(X @ b, -30, 30)
        mu = 1 / (1 + np.exp(-z))
        g = X.T @ (mu - y)
        H = (X * (mu * (1 - mu) + 1e-9)[:, None]).T @ X
        try:
            step = np.linalg.solve(H + 1e-6 * np.eye(X.shape[1]), g)
        except np.linalg.LinAlgError:
            break
        b -= step
        if np.max(np.abs(step)) < 1e-9:
            break
    return b


def main():
    claims = pd.read_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"))
    claims["truth"] = claims.truth.map({True: "TRUE", False: "FALSE",
                                        "TRUE": "TRUE", "FALSE": "FALSE"})
    bank = pd.read_parquet(os.path.join(ROOT, "data", "stage2b",
                                        "message_bank.parquet"))
    bank = bank[bank.pure]
    pool = {k: v.reset_index(drop=True)
            for k, v in bank.groupby(["claim_id", "stance"])}

    calls = []
    for _, c in claims.iterrows():
        wrong = "FALSE" if c.truth == "TRUE" else "TRUE"
        for k, ls in K_LEVELS.items():
            for l in ls:
                assigns = ["TF"] * (N_REP // 2) + ["FT"] * (N_REP // 2)
                RNG.shuffle(assigns)
                for j, asg in enumerate(assigns):
                    msgs = []
                    if l > 0:
                        p = pool[(c.claim_id, c.truth)]
                        idx = RNG.choice(len(p), l, replace=False)
                        msgs += [("C", p.iloc[i].message) for i in idx]
                    if k - l > 0:
                        p = pool[(c.claim_id, wrong)]
                        idx = RNG.choice(len(p), k - l, replace=False)
                        msgs += [("W", p.iloc[i].message) for i in idx]
                    RNG.shuffle(msgs)
                    inbox = "\n".join(f"- {m[1]}" for m in msgs)
                    oa, ob = (("TRUE", "FALSE") if asg == "TF"
                              else ("FALSE", "TRUE"))
                    persona = PERSONAS[int(RNG.integers(len(PERSONAS)))]
                    calls.append({
                        "prompt": PROMPT_TMPL.format(
                            persona=persona, inbox=inbox, claim=c.claim,
                            option_A=oa, option_B=ob),
                        "seed": int(RNG.integers(70_000_000, 900_000_000)),
                        "condition": {"claim_id": int(c.claim_id),
                                      "truth": c.truth, "k": k, "l": l,
                                      "assign": asg, "j": j,
                                      "order": "".join(m[0] for m in msgs)}})
    print(f"{len(calls)} single calls")
    recs = run_batch(calls, "26_single")

    rows = []
    for r in recs:
        if r.get("parsed") not in ("A", "B"):
            continue
        c = r["condition"]
        chosen = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                  else "FALSE")
        rows.append({"claim_id": c["claim_id"], "k": c["k"], "l": c["l"],
                     "y": int(chosen == c["truth"])})
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(ROOT, "data", "stage2b",
                               "single_obs.parquet"), index=False)

    # per-claim coefficients: intercept c0_q + per-k (bT, bF)
    out = []
    for cid, sub in df.groupby("claim_id"):
        X0 = np.column_stack([np.ones(len(sub)), sub.l.to_numpy(float),
                              (sub.k - sub.l).to_numpy(float)])
        b = fit_logit(X0, sub.y.to_numpy(float))
        out.append({"claim_id": cid, "k": "pooled", "c0": b[0],
                    "bT": b[1], "bF": b[2], "n": len(sub)})
        for k, sk in sub.groupby("k"):
            Xk = np.column_stack([np.ones(len(sk)), sk.l.to_numpy(float),
                                  (sk.k - sk.l).to_numpy(float)])
            bk = fit_logit(Xk, sk.y.to_numpy(float))
            out.append({"claim_id": cid, "k": k, "c0": bk[0],
                        "bT": bk[1], "bF": bk[2], "n": len(sk)})
    co = pd.DataFrame(out)
    co.to_csv(os.path.join(ROOT, "results", "stage2b_single_coeffs.csv"),
              index=False)
    print(co.round(3).to_string(index=False))
    print("\nparse failures:", len(recs) - len(df))


if __name__ == "__main__":
    main()
