"""Stage 2b block D-1 (qwen3:8b): calibration, banks, mini singles,
blind predictions. Run with:
  S2_URL=http://127.0.0.1:11435/api/generate S2_MODEL=qwen3:8b S2_NOTHINK=1 \
  python3 scripts/25h_d1_qwen.py

Steps:
1. Re-calibrate the 120 Stage-1 candidate claims x 24 (A/B counterbalanced).
   REPORT: number of SUPPORTS with |h_q| < 0.4 (>= 6 -> balanced set).
2. Common claims (4 originals + 4 paraphrases + 3 SUPPORTS) + balanced set
   (if available): qwen message banks (2 stances x 24, purity x2).
3. Mini singles k in {2,5,8}, Stage-1 l levels, 24 reps.
4. Per-claim coefficients + blind fixed-point predictions (alpha 0.30/0.55/1.0).

Outputs under data/stage2d/ and results/stage2d_*.csv
"""
import os
import sys

import numpy as np
import pandas as pd

assert os.environ.get("S2_MODEL") == "qwen3:8b", "run with S2_MODEL=qwen3:8b"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_lib import ROOT, run_batch  # noqa: E402  (env already applied)
import importlib.util
_p = importlib.util.spec_from_file_location(
    "pred", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "27_s2b_predict.py"))
pred = importlib.util.module_from_spec(_p)
_p.loader.exec_module(pred)

RNG = np.random.default_rng(29)
D_DIR = os.path.join(ROOT, "data", "stage2d")
K_LEVELS = {2: [0, 1, 2], 5: [0, 1, 2, 3, 4, 5], 8: [0, 2, 4, 6, 8]}

CAL_TMPL = (
    "# Problem\n"
    "You are one member of an expert panel judging the following claim.\n"
    'Claim: "{claim}"\n'
    "Options:\nA) {option_A}\nB) {option_B}\n"
    "# Instruction\n"
    "Give your direct answer on which option is correct. Do NOT work through\n"
    "the problem, show any steps, compute, or explain — just commit to a snap\n"
    "judgement.\n"
    "## Response Format\n"
    "Respond with a single character, A or B, and nothing else."
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_m = importlib.util.spec_from_file_location(
    "s26", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "26_s2b_single.py"))
s26 = importlib.util.module_from_spec(_m)
_m.loader.exec_module(s26)
GEN_TMPL = __import__("importlib.util", fromlist=["x"])  # placeholder


def get_prepare_templates():
    _q = importlib.util.spec_from_file_location(
        "s25", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "25_s2b_prepare.py"))
    s25 = importlib.util.module_from_spec(_q)
    _q.loader.exec_module(s25)
    return s25


def main():
    s25 = get_prepare_templates()
    os.makedirs(D_DIR, exist_ok=True)

    # ---- 1. calibration of 120 candidates on qwen ----
    cand = pd.read_csv(os.path.join(ROOT, "results", "stage1_claims.csv"))
    cand["truth"] = cand.truth.map({True: "TRUE", False: "FALSE",
                                    "TRUE": "TRUE", "FALSE": "FALSE"})
    calls = []
    for _, c in cand.iterrows():
        for j in range(24):
            asg = "TF" if j < 12 else "FT"
            oa, ob = ("TRUE", "FALSE") if asg == "TF" else ("FALSE", "TRUE")
            calls.append({"prompt": CAL_TMPL.format(claim=c.claim,
                                                    option_A=oa, option_B=ob),
                          "seed": int(90_000_000 + c.claim_id * 100 + j),
                          "condition": {"phase": "cal",
                                        "claim_id": int(c.claim_id),
                                        "truth": c.truth, "assign": asg}})
    print(f"calibration: {len(calls)} calls")
    rec = run_batch(calls, "25h_qwen_cal")
    rows = []
    for cid, sub in pd.DataFrame(
            [{"cid": r["condition"]["claim_id"],
              "truth": r["condition"]["truth"],
              "correct": (("TRUE" if (r["parsed"] == "A")
                           == (r["condition"]["assign"] == "TF")
                           else "FALSE") == r["condition"]["truth"])}
             for r in rec if r.get("parsed")]).groupby("cid"):
        p = sub.correct.mean()
        p_adj = (sub.correct.sum() + 0.5) / (len(sub) + 1)
        rows.append({"claim_id": cid, "n": len(sub), "p_q": p,
                     "h_q": np.log(p_adj / (1 - p_adj))})
    qcal = pd.DataFrame(rows).merge(
        cand[["claim_id", "claim", "label", "truth"]], on="claim_id")
    qcal.to_csv(os.path.join(ROOT, "results", "stage2d_qwen_claims.csv"),
                index=False)
    sup_ok = qcal[(qcal.label == "SUPPORTS") & (qcal.h_q.abs() < 0.4)]
    ref_ok = qcal[(qcal.label == "REFUTES") & (qcal.h_q.abs() < 0.4)]
    print(f"\n*** qwen SUPPORTS with |h_q|<0.4: {len(sup_ok)} "
          f"(REFUTES: {len(ref_ok)}) ***")
    balanced = None
    if len(sup_ok) >= 6 and len(ref_ok) >= 6:
        balanced = pd.concat([
            sup_ok.reindex(sup_ok.h_q.abs().sort_values().index).head(6),
            ref_ok.reindex(ref_ok.h_q.abs().sort_values().index).head(6)])
        print("balanced set:", list(balanced.claim_id))

    # ---- claim sets ----
    s2 = pd.read_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"))
    s2["truth"] = s2.truth.map({True: "TRUE", False: "FALSE",
                                "TRUE": "TRUE", "FALSE": "FALSE"})
    orig = pd.read_csv(os.path.join(ROOT, "results", "stage2_claims.csv"))
    orig["truth"] = orig.truth.map({True: "TRUE", False: "FALSE",
                                    "TRUE": "TRUE", "FALSE": "FALSE"})
    orig = orig[orig.selected][["claim_id", "claim", "truth"]]
    orig["set"] = "orig"
    common = pd.concat([orig,
                        s2[["claim_id", "claim", "truth", "set"]]],
                       ignore_index=True)
    if balanced is not None:
        extra = balanced[~balanced.claim_id.isin(common.claim_id)][
            ["claim_id", "claim", "truth"]].copy()
        extra["set"] = "balanced"
        common = pd.concat([common, extra], ignore_index=True)
    common.to_csv(os.path.join(D_DIR, "claims.csv"), index=False)
    print(f"claim set for qwen singles: {len(common)}")

    # ---- 2. banks ----
    gen_calls, meta = [], []
    for _, c in common.iterrows():
        for stance in ("TRUE", "FALSE"):
            for j in range(24):
                persona = s25.PERSONAS[int(RNG.integers(len(s25.PERSONAS)))]
                gen_calls.append({
                    "prompt": s25.GEN_TMPL.format(persona=persona,
                                                  claim=c.claim,
                                                  stance=stance),
                    "seed": int(93_000_000 + c.claim_id * 100
                                + (stance == "FALSE") * 50 + j),
                    "condition": {"phase": "gen",
                                  "claim_id": int(c.claim_id),
                                  "stance": stance}})
                meta.append((int(c.claim_id), c.claim, stance, persona))
    print(f"bank generation: {len(gen_calls)}")
    recs = run_batch(gen_calls, "25h_qwen_gen", num_predict=150, parse=None,
                     retries=1)
    bank_rows = []
    for (cid, claim, stance, persona), r in zip(meta, recs):
        msg = " ".join((r["response"] or "").strip().split()).strip('"')
        bank_rows.append({"claim_id": cid, "claim": claim, "stance": stance,
                          "persona": persona, "message": msg})
    bank = pd.DataFrame(bank_rows)
    bank = bank[bank.message.str.len() >= 20].reset_index(drop=True)
    judge_calls = []
    for i, b in bank.iterrows():
        for asg in ("TF", "FT"):
            oa, ob = (("The claim is TRUE", "The claim is FALSE")
                      if asg == "TF" else
                      ("The claim is FALSE", "The claim is TRUE"))
            judge_calls.append({
                "prompt": s25.JUDGE_TMPL.format(claim=b.claim,
                                                message=b.message,
                                                option_A=oa, option_B=ob),
                "seed": int(94_000_000 + i * 10 + (asg == "FT")),
                "condition": {"bank_idx": int(i), "assign": asg,
                              "stance": b.stance}})
    jrecs = run_batch(judge_calls, "25h_qwen_purity")
    verdicts = {}
    for r in jrecs:
        c = r["condition"]
        v = None
        if r.get("parsed"):
            v = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                 else "FALSE")
        verdicts.setdefault(c["bank_idx"], []).append(v)
    bank["pure"] = [len(verdicts.get(i, [])) == 2 and
                    all(v == bank.at[i, "stance"] for v in verdicts[i])
                    for i in bank.index]
    print("purity discard:", round(1 - bank.pure.mean(), 3),
          " min cell:", bank[bank.pure].groupby(
              ["claim_id", "stance"]).size().min())
    bank.to_parquet(os.path.join(D_DIR, "message_bank.parquet"), index=False)

    # ---- 3. mini singles ----
    pool = {k: v.reset_index(drop=True)
            for k, v in bank[bank.pure].groupby(["claim_id", "stance"])}
    calls = []
    for _, c in common.iterrows():
        wrong = "FALSE" if c.truth == "TRUE" else "TRUE"
        for k, ls in K_LEVELS.items():
            for l in ls:
                if (l > 0 and (c.claim_id, c.truth) not in pool) or \
                   (k - l > 0 and (c.claim_id, wrong) not in pool):
                    continue
                for j in range(24):
                    asg = "TF" if j < 12 else "FT"
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
                    oa, ob = (("TRUE", "FALSE") if asg == "TF"
                              else ("FALSE", "TRUE"))
                    persona = s25.PERSONAS[int(RNG.integers(
                        len(s25.PERSONAS)))]
                    calls.append({
                        "prompt": s26.PROMPT_TMPL.format(
                            persona=persona,
                            inbox="\n".join(f"- {m[1]}" for m in msgs),
                            claim=c.claim, option_A=oa, option_B=ob),
                        "seed": int(RNG.integers(95_000_000, 990_000_000)),
                        "condition": {"claim_id": int(c.claim_id),
                                      "truth": c.truth, "k": k, "l": l,
                                      "assign": asg,
                                      "order": "".join(m[0] for m in msgs)}})
    print(f"mini singles: {len(calls)} calls")
    recs = run_batch(calls, "25h_qwen_single")
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
    df.to_parquet(os.path.join(D_DIR, "single_obs.parquet"), index=False)

    out = []
    for cid, sub in df.groupby("claim_id"):
        X0 = np.column_stack([np.ones(len(sub)), sub.l,
                              (sub.k - sub.l).astype(float)])
        b = s26.fit_logit(X0, sub.y.to_numpy(float))
        out.append({"claim_id": cid, "k": "pooled", "c0": b[0], "bT": b[1],
                    "bF": b[2], "n": len(sub)})
        for k, sk in sub.groupby("k"):
            Xk = np.column_stack([np.ones(len(sk)), sk.l,
                                  (sk.k - sk.l).astype(float)])
            bk = s26.fit_logit(Xk, sk.y.to_numpy(float))
            out.append({"claim_id": cid, "k": k, "c0": bk[0], "bT": bk[1],
                        "bF": bk[2], "n": len(sk)})
    co = pd.DataFrame(out)
    co.to_csv(os.path.join(ROOT, "results", "stage2d_single_coeffs.csv"),
              index=False)

    # ---- 4. blind predictions ----
    prows = []
    for cid, sub in co.groupby("claim_id"):
        c0 = float(sub[sub.k == "pooled"].c0.iloc[0])
        coef = pred.make_coef(sub[sub.k != "pooled"].astype({"k": str}))
        for a in (0.30, 0.55, 1.00):
            fps = pred.fixed_points(a, c0, coef)
            prows.append({"claim_id": cid, "alpha": a,
                          "c0": round(c0, 3),
                          "fixed_points": "; ".join(
                              f"{r}({s})" for r, s in fps)})
    pp = pd.DataFrame(prows)
    pp.to_csv(os.path.join(ROOT, "results",
                           "stage2d_blind_predictions.csv"), index=False)
    print(pp.to_string(index=False))


if __name__ == "__main__":
    main()
