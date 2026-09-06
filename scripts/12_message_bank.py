"""Stage 1 step 2: message bank generation + purity check.

For each selected claim: 24 messages per stance (claim-is-TRUE / claim-is-
FALSE), El et al. message_sampler style (2 sentences, single strongest
reason), diversified by a one-line expertise persona and per-call seeds.
Purity: each message judged twice (A/B label assignment counterbalanced);
discarded unless both judgments match the intended stance.

Output: data/stage1/message_bank.parquet
"""
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_lib import ROOT, run_batch, parse_ab

RNG = np.random.default_rng(7)
N_PER_STANCE = 24

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


def clean_message(text):
    t = " ".join(text.strip().split())
    t = t.strip('"').strip()
    return t


def main():
    claims = pd.read_csv(os.path.join(ROOT, "results", "stage1_claims.csv"))
    claims = claims[claims.selected].reset_index(drop=True)
    print(f"{len(claims)} selected claims")

    gen_calls = []
    meta = []
    for _, c in claims.iterrows():
        for stance in ("TRUE", "FALSE"):
            for j in range(N_PER_STANCE):
                persona = PERSONAS[int(RNG.integers(len(PERSONAS)))]
                gen_calls.append({
                    "prompt": GEN_TMPL.format(persona=persona, claim=c.claim,
                                              stance=stance),
                    "seed": int(30_000_000 + c.claim_id * 1000
                                + (0 if stance == "TRUE" else 500) + j),
                    "condition": {"phase": "gen", "claim_id": int(c.claim_id),
                                  "stance": stance, "j": j,
                                  "persona": persona},
                })
                meta.append((int(c.claim_id), c.claim, c.truth, stance,
                             persona))
    print(f"generating {len(gen_calls)} messages")
    recs = run_batch(gen_calls, "12_gen_messages", num_predict=150,
                     parse=None, retries=1)

    rows = []
    for (cid, claim, truth, stance, persona), r in zip(meta, recs):
        msg = clean_message(r["response"] or "")
        n_sent = len(re.findall(r"[.!?](?:\s|$)", msg))
        rows.append({"claim_id": cid, "claim": claim, "truth": truth,
                     "stance": stance, "persona": persona, "message": msg,
                     "n_sentences": n_sent, "gen_seed": r["seed"]})
    bank = pd.DataFrame(rows)
    empty = bank.message.str.len() < 20
    print("empty/short generations:", int(empty.sum()))
    bank = bank[~empty].reset_index(drop=True)

    # purity: 2 judgments per message, counterbalanced label assignment
    judge_calls = []
    for i, b in bank.iterrows():
        for asg in ("TF", "FT"):
            oa, ob = (("The claim is TRUE", "The claim is FALSE")
                      if asg == "TF" else
                      ("The claim is FALSE", "The claim is TRUE"))
            judge_calls.append({
                "prompt": JUDGE_TMPL.format(claim=b.claim, message=b.message,
                                            option_A=oa, option_B=ob),
                "seed": int(40_000_000 + i * 10 + (0 if asg == "TF" else 1)),
                "condition": {"phase": "purity", "bank_idx": int(i),
                              "assign": asg, "stance": b.stance},
            })
    print(f"purity: {len(judge_calls)} calls")
    jrecs = run_batch(judge_calls, "12_purity")

    verdicts = {}
    for r in jrecs:
        cond = r["condition"]
        if r.get("parsed") is None:
            v = None
        else:
            v = ("TRUE" if (r["parsed"] == "A") == (cond["assign"] == "TF")
                 else "FALSE")
        verdicts.setdefault(cond["bank_idx"], []).append(v)
    bank["purity_votes"] = [
        ";".join(str(v) for v in verdicts.get(i, [])) for i in bank.index]
    bank["pure"] = [
        all(v == bank.at[i, "stance"] for v in verdicts.get(i, []))
        and len(verdicts.get(i, [])) == 2 for i in bank.index]

    discard_rate = 1 - bank.pure.mean()
    print(f"discard rate: {discard_rate:.3f}")
    print(bank.groupby(["stance"]).pure.mean().round(3))
    per_cell = bank[bank.pure].groupby(["claim_id", "stance"]).size()
    print("kept per (claim, stance): min", int(per_cell.min()),
          "median", float(per_cell.median()))

    os.makedirs(os.path.join(ROOT, "data", "stage1"), exist_ok=True)
    bank.to_parquet(os.path.join(ROOT, "data", "stage1",
                                 "message_bank.parquet"), index=False)
    print("saved", len(bank), "messages (", int(bank.pure.sum()), "pure )")


if __name__ == "__main__":
    main()
