"""Stage 1 step 1: calibrate claim fields h_q on CLIMATE-FEVER claims.

- 120 candidate claims (60 SUPPORTS / 60 REFUTES), 24 single calls each with
  the A/B <-> TRUE/FALSE assignment counterbalanced 12/12.
- refine claims with p_q in [0.35, 0.65] to 64 calls.
- output results/stage1_claims.csv; selection criterion |h_q| < 0.4, need >=12.
"""
import os
import sys

import numpy as np
import pandas as pd
from datasets import load_dataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage1_lib import ROOT, run_batch

RNG = np.random.default_rng(42)
N_CAND = 120
N_COARSE = 24          # per claim, 12 per label assignment
N_REFINE_TOTAL = 64    # total calls per refined claim

PROMPT_TMPL = (
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


def candidate_claims(n=N_CAND, rng=RNG):
    ds = load_dataset("tdiggelm/climate_fever", split="test")
    df = pd.DataFrame({"claim_id": [int(c) for c in ds["claim_id"]],
                       "claim": ds["claim"],
                       "label": ds["claim_label"]})
    df = df[df.label.isin([0, 1])].drop_duplicates(subset="claim")
    df["label"] = df.label.map({0: "SUPPORTS", 1: "REFUTES"})
    # y_true: the claim statement itself is TRUE (SUPPORTS) or FALSE (REFUTES)
    df["truth"] = df.label.map({"SUPPORTS": "TRUE", "REFUTES": "FALSE"})
    sup = df[df.label == "SUPPORTS"].sample(n // 2, random_state=rng.integers(2**31))
    ref = df[df.label == "REFUTES"].sample(n // 2, random_state=rng.integers(2**31))
    return pd.concat([sup, ref]).reset_index(drop=True)


def build_calls(claims, n_calls, seed_base, phase):
    """Counterbalanced A/B assignment: half TRUE-as-A, half FALSE-as-A."""
    calls = []
    for _, c in claims.iterrows():
        assigns = ["TF"] * (n_calls // 2) + ["FT"] * (n_calls // 2)
        RNG.shuffle(assigns)
        for j, asg in enumerate(assigns):
            opt_a, opt_b = ("TRUE", "FALSE") if asg == "TF" else ("FALSE", "TRUE")
            calls.append({
                "prompt": PROMPT_TMPL.format(claim=c.claim, option_A=opt_a,
                                             option_B=opt_b),
                "seed": int(seed_base + c.claim_id * 1000 + j),
                "condition": {"phase": phase, "claim_id": int(c.claim_id),
                              "assign": asg, "truth": c.truth, "j": j},
            })
    return calls


def tally(records, claims):
    rows = []
    by_claim = {}
    for r in records:
        if r.get("parsed") is None:
            continue
        cond = r["condition"]
        cid = cond["claim_id"]
        chosen = ("TRUE" if (r["parsed"] == "A") == (cond["assign"] == "TF")
                  else "FALSE")
        correct = chosen == cond["truth"]
        chose_a = r["parsed"] == "A"
        by_claim.setdefault(cid, []).append((correct, chose_a))
    for _, c in claims.iterrows():
        obs = by_claim.get(int(c.claim_id), [])
        n = len(obs)
        k = sum(o[0] for o in obs)
        n_a = sum(o[1] for o in obs)
        rows.append({"claim_id": int(c.claim_id), "n": n, "k_correct": k,
                     "n_chose_A": n_a})
    return pd.DataFrame(rows)


def main():
    claims = candidate_claims()
    print(f"{len(claims)} candidate claims "
          f"({(claims.label == 'SUPPORTS').sum()} SUPPORTS / "
          f"{(claims.label == 'REFUTES').sum()} REFUTES)")

    calls = build_calls(claims, N_COARSE, seed_base=10_000_000, phase="coarse")
    print(f"coarse: {len(calls)} calls")
    rec = run_batch(calls, "11_calibrate_coarse")
    coarse = tally(rec, claims)

    m = claims.merge(coarse, on="claim_id")
    m["p_q"] = m.k_correct / m.n.replace(0, np.nan)
    refine = m[(m.p_q >= 0.35) & (m.p_q <= 0.65)]
    print(f"refine band [0.35,0.65]: {len(refine)} claims")

    extra = N_REFINE_TOTAL - N_COARSE
    if len(refine) and extra > 0:
        calls2 = build_calls(claims[claims.claim_id.isin(refine.claim_id)],
                             extra, seed_base=20_000_000, phase="refine")
        print(f"refine: {len(calls2)} calls")
        rec2 = run_batch(calls2, "11_calibrate_refine")
        fine = tally(rec2, claims[claims.claim_id.isin(refine.claim_id)])
        m = m.set_index("claim_id")
        for _, r in fine.iterrows():
            m.loc[r.claim_id, "n"] += r.n
            m.loc[r.claim_id, "k_correct"] += r.k_correct
            m.loc[r.claim_id, "n_chose_A"] += r.n_chose_A
        m = m.reset_index()

    m["p_q"] = m.k_correct / m.n.replace(0, np.nan)
    # logit with Haldane-Anscombe correction only for display of 0/1 claims
    p_adj = (m.k_correct + 0.5) / (m.n + 1.0)
    m["h_q"] = np.where((m.p_q > 0) & (m.p_q < 1),
                        np.log(m.p_q / (1 - m.p_q)),
                        np.log(p_adj / (1 - p_adj)))
    m["h_q_se"] = 1.0 / np.sqrt(m.n * p_adj * (1 - p_adj))
    m["p_A"] = m.n_chose_A / m.n.replace(0, np.nan)
    m["selected"] = (m.h_q.abs() < 0.4) & (m.n >= N_REFINE_TOTAL - 4)

    out = m[["claim_id", "claim", "label", "truth", "n", "k_correct", "p_q",
             "h_q", "h_q_se", "p_A", "selected"]].sort_values("h_q")
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    out.to_csv(os.path.join(ROOT, "results", "stage1_claims.csv"), index=False)

    n_sel = int(out.selected.sum())
    print(f"\nselected (|h_q|<0.4, refined): {n_sel}")
    print("label balance among selected:",
          out[out.selected].label.value_counts().to_dict())
    print("\np_q distribution:", np.round(np.percentile(
        m.p_q.dropna(), [0, 10, 25, 50, 75, 90, 100]), 3))
    print("overall A-rate (label-bias check):",
          round(m.n_chose_A.sum() / m.n.sum(), 4))
    parse_fail = sum(1 for r in rec if r.get("parsed") is None)
    print("coarse parse failures:", parse_fail, "/", len(rec))
    if n_sel < 12:
        print("\n*** FEWER THAN 12 SELECTED — need to widen candidates to 240 "
              "(rerun with N_CAND=240) ***")


if __name__ == "__main__":
    main()
