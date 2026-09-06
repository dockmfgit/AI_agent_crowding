"""Stage 1 step 3: main measurement — randomized-inbox single calls.

Factors:
- k in {0,1,2,3,5,8,12} messages in the inbox
- l = number of correct-side messages; levels nearest to l/k in
  {0, 1/4, 1/2, 3/4, 1} (all levels for k<=3; for k=5 the midpoint 2.5 is
  equidistant so both 2 and 3 are included)
- self-state: variant A (no self line) / variant B correct / variant B wrong
- A/B label assignment counterbalanced 12/12 within each cell
- message presentation order randomized, per-position stance recorded
- claims: all selected from step 1; 24 reps per cell

One call = one observation. Raw log: data/stage1/raw/13_main.jsonl
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_lib import ROOT, run_batch

RNG = np.random.default_rng(11)
N_REP = 24
K_LEVELS = {0: [0], 1: [0, 1], 2: [0, 1, 2], 3: [0, 1, 2, 3],
            5: [0, 1, 2, 3, 4, 5], 8: [0, 2, 4, 6, 8], 12: [0, 3, 6, 9, 12]}
SELF_STATES = ["none", "self_correct", "self_wrong"]

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
    "{selfline}"
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


def main():
    claims = pd.read_csv(os.path.join(ROOT, "results", "stage1_claims.csv"))
    claims = claims[claims.selected].reset_index(drop=True)
    # read_csv turns the TRUE/FALSE strings into booleans; undo that
    claims["truth"] = claims.truth.map(
        {True: "TRUE", False: "FALSE", "TRUE": "TRUE", "FALSE": "FALSE"})
    bank = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                        "message_bank.parquet"))
    bank = bank[bank.pure]
    pool = {}
    for (cid, stance), sub in bank.groupby(["claim_id", "stance"]):
        pool[(cid, stance)] = sub.reset_index()[["index", "message"]]
    min_pool = min(len(v) for v in pool.values())
    print(f"pure pool per (claim, stance): min={min_pool}")
    kmax_ok = min_pool  # a call never needs more than 12 of one stance

    calls = []
    n_skipped = 0
    for _, c in claims.iterrows():
        cid = int(c.claim_id)
        correct_stance = c.truth               # TRUE or FALSE
        wrong_stance = "FALSE" if c.truth == "TRUE" else "TRUE"
        for k, l_levels in K_LEVELS.items():
            for l in l_levels:
                if l > kmax_ok or (k - l) > kmax_ok:
                    n_skipped += 1
                    continue
                for ss in SELF_STATES:
                    assigns = ["TF"] * (N_REP // 2) + ["FT"] * (N_REP // 2)
                    RNG.shuffle(assigns)
                    for j, asg in enumerate(assigns):
                        # sample messages without replacement within the call
                        msgs = []
                        if l > 0:
                            p = pool[(cid, correct_stance)]
                            idx = RNG.choice(len(p), l, replace=False)
                            msgs += [(p.iloc[i]["index"], "C",
                                      p.iloc[i].message) for i in idx]
                        if k - l > 0:
                            p = pool[(cid, wrong_stance)]
                            idx = RNG.choice(len(p), k - l, replace=False)
                            msgs += [(p.iloc[i]["index"], "W",
                                      p.iloc[i].message) for i in idx]
                        RNG.shuffle(msgs)
                        inbox = ("(no messages)" if not msgs else
                                 "\n".join(f"- {m[2]}" for m in msgs))
                        if ss == "none":
                            selfline = ""
                            self_x = None
                        else:
                            self_x = (correct_stance if ss == "self_correct"
                                      else wrong_stance)
                            selfline = (f"# Your Current Answer\n"
                                        f"Your current answer is that the "
                                        f"claim is {self_x}.\n\n")
                        oa, ob = (("TRUE", "FALSE") if asg == "TF"
                                  else ("FALSE", "TRUE"))
                        persona = PERSONAS[int(RNG.integers(len(PERSONAS)))]
                        calls.append({
                            "prompt": PROMPT_TMPL.format(
                                persona=persona, inbox=inbox,
                                selfline=selfline, claim=c.claim,
                                option_A=oa, option_B=ob),
                            "seed": int(RNG.integers(50_000_000, 900_000_000)),
                            "condition": {
                                "phase": "main", "claim_id": cid,
                                "truth": c.truth, "k": k, "l": l,
                                "self_state": ss, "self_x": self_x,
                                "assign": asg, "j": j,
                                "persona": persona,
                                "order": "".join(m[1] for m in msgs),
                                "msg_ids": [int(m[0]) for m in msgs],
                            },
                        })
    print(f"total calls: {len(calls)} (skipped cells: {n_skipped})")
    est = len(calls) / 17.0 / 60
    print(f"estimated {est:.0f} min at 17 calls/s")
    run_batch(calls, "13_main")
    print("done")


if __name__ == "__main__":
    main()
