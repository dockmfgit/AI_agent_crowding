"""Stage 2b preparation.

1. A-1 claims: 3 lowest-p_q SUPPORTS in [0.70, 0.95] (993, 1103, 1239).
2. A-2 paraphrases: minimal-negation polarity flips of the 4 Stage 2 claims
   (paraphrase truth = TRUE; correct side = claim-affirming side).
3. Model semantic-opposition check for each pair (20 calls, counterbalanced).
4. Bare-prompt calibration of the paraphrases (64 calls each).
5. Message banks (both stances x 24) + purity for all 7 new claims.

Outputs: data/stage2b/claims.csv, data/stage2b/message_bank.parquet,
results/stage2b_paraphrase_check.csv
All calls go to the port-11435 instance.
"""
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage1_lib
stage1_lib.URL = "http://127.0.0.1:11435/api/generate"
stage1_lib.CONCURRENCY = 16
from stage1_lib import ROOT, run_batch

RNG = np.random.default_rng(13)

SUPPORTS_IDS = [993, 1103, 1239]

PARAPHRASES = {
    90006: ("The polar bear population has not been growing.", 6),
    91569: ("Sea level rise is not decelerating.", 1569),
    90382: ("The amount of energy used to construct solar and wind "
            "facilities is not greater than they produce in their working "
            "lives.", 382),
    92070: ("When life is considered, ocean acidification is often found to "
            "be a problem, and not a benefit.", 2070),
}

CAL_TMPL = (
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

OPP_TMPL = (
    "# Statements\n"
    'Statement 1: "{orig}"\n'
    'Statement 2: "{para}"\n'
    "# Problem\n"
    "Does Statement 2 assert the opposite of Statement 1?\n"
    "Options:\n"
    "A) {option_A}\n"
    "B) {option_B}\n"
    "# Instruction\n"
    "Give your direct answer. Do NOT explain — just commit to a snap "
    "judgement.\n"
    "## Response Format\n"
    "Respond with a single character, A or B, and nothing else."
)

GEN_TMPL = (
    "# Your Expertise\n{persona}\n\n"
    "# Problem\n"
    "You are one member of an expert panel judging the following claim.\n"
    'Claim: "{claim}"\n\n'
    "# Instruction\n"
    "Your current answer is that the claim is {stance}. Write a brief message "
    "to a fellow panelist stating that you believe the claim is {stance} and "
    "giving the single strongest reason from your reasoning.\n"
    "## Response Format\n"
    "Respond only with a two-sentence message. Do not output anything else."
)

JUDGE_TMPL = (
    "# Message\n"
    "A panelist sent the following message about a claim.\n"
    'Claim: "{claim}"\n'
    'Message: "{message}"\n'
    "# Problem\n"
    "Which option does the message argue for?\n"
    "Options:\n"
    "A) {option_A}\n"
    "B) {option_B}\n"
    "# Instruction\n"
    "Give your direct answer on which option the message argues for. Do NOT "
    "explain — just commit to a snap judgement.\n"
    "## Response Format\n"
    "Respond with a single character, A or B, and nothing else."
)

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


def main():
    cal = pd.read_csv(os.path.join(ROOT, "results", "stage1_claims.csv"))
    sup = cal[cal.claim_id.isin(SUPPORTS_IDS)]
    rows = [{"claim_id": int(r.claim_id), "claim": r.claim, "truth": "TRUE",
             "set": "A1_supports", "p_q_bare": r.p_q, "orig_id": None}
            for _, r in sup.iterrows()]
    for pid, (text, oid) in PARAPHRASES.items():
        rows.append({"claim_id": pid, "claim": text, "truth": "TRUE",
                     "set": "A2_paraphrase", "p_q_bare": np.nan,
                     "orig_id": oid})
    claims = pd.DataFrame(rows)

    # --- 3. semantic opposition check (20 per pair, counterbalanced) ---
    calls = []
    for pid, (text, oid) in PARAPHRASES.items():
        orig = cal[cal.claim_id == oid].claim.iloc[0]
        for j in range(20):
            asg = "YN" if j < 10 else "NY"
            oa, ob = ("yes", "no") if asg == "YN" else ("no", "yes")
            calls.append({"prompt": OPP_TMPL.format(orig=orig, para=text,
                                                    option_A=oa, option_B=ob),
                          "seed": int(60_000_000 + pid * 100 + j),
                          "condition": {"phase": "opp", "pid": pid,
                                        "assign": asg, "j": j}})
    rec = run_batch(calls, "25_opposition")
    opp_rows = []
    for pid in PARAPHRASES:
        rs = [r for r in rec if r["condition"]["pid"] == pid
              and r.get("parsed")]
        yes = sum(1 for r in rs if
                  (r["parsed"] == "A") == (r["condition"]["assign"] == "YN"))
        opp_rows.append({"claim_id": pid, "n": len(rs), "opposite_rate":
                         yes / max(len(rs), 1)})
    opp = pd.DataFrame(opp_rows)
    print("opposition check:\n", opp.to_string(index=False))

    # --- 4. bare calibration of paraphrases (64 each, counterbalanced) ---
    calls = []
    for pid, (text, oid) in PARAPHRASES.items():
        for j in range(64):
            asg = "TF" if j < 32 else "FT"
            oa, ob = ("TRUE", "FALSE") if asg == "TF" else ("FALSE", "TRUE")
            calls.append({"prompt": CAL_TMPL.format(claim=text, option_A=oa,
                                                    option_B=ob),
                          "seed": int(61_000_000 + pid * 100 + j),
                          "condition": {"phase": "cal", "pid": pid,
                                        "assign": asg, "j": j}})
    rec = run_batch(calls, "25_para_calibration")
    for pid in PARAPHRASES:
        rs = [r for r in rec if r["condition"]["pid"] == pid
              and r.get("parsed")]
        k = sum(1 for r in rs if
                (r["parsed"] == "A") == (r["condition"]["assign"] == "TF"))
        p = k / max(len(rs), 1)   # P(answer TRUE) = correct side
        claims.loc[claims.claim_id == pid, "p_q_bare"] = p
    print("\nparaphrase bare p_q (TRUE = correct side):")
    print(claims[claims.set == "A2_paraphrase"][
        ["claim_id", "p_q_bare"]].to_string(index=False))

    # --- 5. message banks: 7 claims x 2 stances x 24 + purity x2 ---
    gen_calls, meta = [], []
    for _, c in claims.iterrows():
        for stance in ("TRUE", "FALSE"):
            for j in range(24):
                persona = PERSONAS[int(RNG.integers(len(PERSONAS)))]
                gen_calls.append({
                    "prompt": GEN_TMPL.format(persona=persona, claim=c.claim,
                                              stance=stance),
                    "seed": int(62_000_000 + c.claim_id * 100
                                + (0 if stance == "TRUE" else 50) + j),
                    "condition": {"phase": "gen", "claim_id": int(c.claim_id),
                                  "stance": stance, "j": j}})
                meta.append((int(c.claim_id), c.claim, stance, persona))
    print(f"\ngenerating {len(gen_calls)} messages")
    recs = run_batch(gen_calls, "25_gen_messages", num_predict=150,
                     parse=None, retries=1)
    bank_rows = []
    for (cid, claim, stance, persona), r in zip(meta, recs):
        msg = " ".join((r["response"] or "").strip().split()).strip('"').strip()
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
                "prompt": JUDGE_TMPL.format(claim=b.claim, message=b.message,
                                            option_A=oa, option_B=ob),
                "seed": int(63_000_000 + i * 10 + (asg == "FT")),
                "condition": {"phase": "purity", "bank_idx": int(i),
                              "assign": asg, "stance": b.stance}})
    jrecs = run_batch(judge_calls, "25_purity")
    verdicts = {}
    for r in jrecs:
        c = r["condition"]
        v = None
        if r.get("parsed"):
            v = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                 else "FALSE")
        verdicts.setdefault(c["bank_idx"], []).append(v)
    bank["pure"] = [
        len(verdicts.get(i, [])) == 2
        and all(v == bank.at[i, "stance"] for v in verdicts[i])
        for i in bank.index]
    print("purity discard rate:", round(1 - bank.pure.mean(), 3))
    print(bank[bank.pure].groupby(["claim_id", "stance"]).size().to_string())

    os.makedirs(os.path.join(ROOT, "data", "stage2b"), exist_ok=True)
    claims = claims.merge(opp, on="claim_id", how="left")
    claims.to_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"),
                  index=False)
    bank.to_parquet(os.path.join(ROOT, "data", "stage2b",
                                 "message_bank.parquet"), index=False)
    opp.merge(claims[["claim_id", "claim", "p_q_bare"]], on="claim_id") \
        .to_csv(os.path.join(ROOT, "results", "stage2b_paraphrase_check.csv"),
                index=False)
    print("saved claims.csv, message_bank.parquet")


if __name__ == "__main__":
    main()
