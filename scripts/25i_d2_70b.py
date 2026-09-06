"""D-2: single-call polarity check on llama3.3:70b (no group runs).

Common claims (4 originals + 4 approved paraphrases) x k {0,4,8} x l levels
x 12 reps. Inbox messages come from the existing llama3.1:8b banks (only the
judging model is scaled — recorded in notes). Run with
S2_URL=http://127.0.0.1:11435/api/generate S2_MODEL=llama3.3:70b.
"""
import os
import sys

import numpy as np
import pandas as pd

assert os.environ.get("S2_MODEL") == "llama3.3:70b"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_lib import ROOT, run_batch
import importlib.util
_m = importlib.util.spec_from_file_location(
    "s26", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "26_s2b_single.py"))
s26 = importlib.util.module_from_spec(_m)
_m.loader.exec_module(s26)
# importing s26 overwrites stage1_lib.URL with the (dead) 11435 instance;
# restore the URL requested via the environment
import stage1_lib
stage1_lib.URL = os.environ.get("S2_URL",
                                "http://localhost:11434/api/generate")

RNG = np.random.default_rng(31)
K_LEVELS = {0: [0], 4: [0, 1, 2, 3, 4], 8: [0, 2, 4, 6, 8]}
N_REP = 12


def main():
    orig = pd.read_csv(os.path.join(ROOT, "results", "stage2_claims.csv"))
    orig["truth"] = orig.truth.map({True: "TRUE", False: "FALSE",
                                    "TRUE": "TRUE", "FALSE": "FALSE"})
    orig = orig[orig.selected][["claim_id", "claim", "truth"]]
    para = pd.read_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"))
    para["truth"] = para.truth.map({True: "TRUE", False: "FALSE",
                                    "TRUE": "TRUE", "FALSE": "FALSE"})
    para = para[para["set"] == "A2_paraphrase"][["claim_id", "claim",
                                                 "truth"]]
    claims = pd.concat([orig, para], ignore_index=True)

    b1 = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                      "message_bank.parquet"))
    b2 = pd.read_parquet(os.path.join(ROOT, "data", "stage2b",
                                      "message_bank.parquet"))
    bank = pd.concat([b1[b1.pure][["claim_id", "stance", "message"]],
                      b2[b2.pure][["claim_id", "stance", "message"]]],
                     ignore_index=True)
    pool = {k: v.reset_index(drop=True)
            for k, v in bank.groupby(["claim_id", "stance"])}

    calls = []
    for _, c in claims.iterrows():
        wrong = "FALSE" if c.truth == "TRUE" else "TRUE"
        for k, ls in K_LEVELS.items():
            for l in ls:
                for j in range(N_REP):
                    asg = "TF" if j < N_REP // 2 else "FT"
                    msgs = []
                    if l > 0:
                        p = pool[(c.claim_id, c.truth)]
                        msgs += [("C", p.iloc[i].message) for i in
                                 RNG.choice(len(p), l, replace=False)]
                    if k - l > 0:
                        p = pool[(c.claim_id, wrong)]
                        msgs += [("W", p.iloc[i].message) for i in
                                 RNG.choice(len(p), k - l, replace=False)]
                    RNG.shuffle(msgs)
                    inbox = ("(no messages)" if not msgs else
                             "\n".join(f"- {m[1]}" for m in msgs))
                    oa, ob = (("TRUE", "FALSE") if asg == "TF"
                              else ("FALSE", "TRUE"))
                    persona = s26.PERSONAS[int(RNG.integers(
                        len(s26.PERSONAS)))]
                    calls.append({
                        "prompt": s26.PROMPT_TMPL.format(
                            persona=persona, inbox=inbox, claim=c.claim,
                            option_A=oa, option_B=ob),
                        "seed": int(RNG.integers(96_000_000, 990_000_000)),
                        "condition": {"claim_id": int(c.claim_id),
                                      "truth": c.truth, "k": k, "l": l,
                                      "assign": asg}})
    print(f"D-2: {len(calls)} calls on llama3.3:70b")
    recs = run_batch(calls, "25i_70b_single", conc=8)
    rows = []
    for r in recs:
        if r.get("parsed") not in ("A", "B"):
            continue
        c = r["condition"]
        chosen = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                  else "FALSE")
        rows.append({"claim_id": c["claim_id"], "k": c["k"], "l": c["l"],
                     "y": int(chosen == c["truth"]),
                     "chose_true": int(chosen == "TRUE")})
    df = pd.DataFrame(rows)
    df.to_parquet(os.path.join(ROOT, "data", "stage2d",
                               "d2_70b_obs.parquet"), index=False)
    out = []
    for cid, sub in df.groupby("claim_id"):
        X = np.column_stack([np.ones(len(sub)), sub.l,
                             (sub.k - sub.l).astype(float)])
        b = s26.fit_logit(X, sub.y.to_numpy(float))
        out.append({"claim_id": cid, "c0": round(b[0], 3),
                    "bT": round(b[1], 3), "bF": round(b[2], 3),
                    "n": len(sub),
                    "p_true_k0": round(sub[sub.k == 0].chose_true.mean(), 3)})
    co = pd.DataFrame(out)
    co.to_csv(os.path.join(ROOT, "results", "stage2d_70b_coeffs.csv"),
              index=False)
    print(co.to_string(index=False))
    print("parse failures:", len(recs) - len(df))


if __name__ == "__main__":
    main()
