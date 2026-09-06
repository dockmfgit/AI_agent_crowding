"""Stage 2c Part A (D-3): origin of the polarity channel.

Variants (judging model only; inboxes from the existing llama3.1:8b bank):
  instruct = llama3.1:8b (positive control, re-measured in the same batch)
  base     = llama3.1:8b-text-q4_K_M
  ablit    = (pluggable; blocked at pull time -> run later if provided)

A-4 parse-gate pilot (200 calls/variant) -> A-2 polarity regression
(6,000 calls/variant, k in {1,2,3,5,8}) -> A-3 bare affirmation index
(8 claims x 64 calls/variant).

Outputs: results/stage2c_d3_polarity.csv, results/stage2c_d3_bare_pairs.csv,
raw JSONL in data/stage1/raw/42_*.jsonl
"""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage1_lib
stage1_lib.URL = "http://127.0.0.1:11435/api/generate"
stage1_lib.CONCURRENCY = 16
from stage1_lib import ROOT, run_batch, parse_ab

RNG = np.random.default_rng(43)
VARIANTS = {"instruct": "llama3.1:8b",
            "base": "llama3.1:8b-text-q4_K_M"}
if os.environ.get("D3_ABLIT_TAG"):
    VARIANTS["ablit"] = os.environ["D3_ABLIT_TAG"]
if os.environ.get("D3_ONLY"):
    keep = os.environ["D3_ONLY"].split(",")
    VARIANTS = {k: v for k, v in VARIANTS.items() if k in keep}

KS = [1, 2, 3, 5, 8]
N_A2 = 6000
N_A3_PER_CLAIM = 64
PAIRS = {6: 90006, 382: 90382, 1569: 91569, 2070: 92070}

PERSONAS = [
    "You are a climate scientist.", "You are an atmospheric physicist.",
    "You are an oceanographer.", "You are a glaciologist.",
    "You are a statistician specializing in environmental data.",
    "You are a meteorologist.", "You are an ecologist.",
    "You are a geophysicist.", "You are an environmental economist.",
    "You are a science journalist with a physics background.",
    "You are a paleoclimatologist.", "You are an energy systems engineer.",
]

SCAFFOLD_TMPL = (
    "# Your Expertise\n{persona}\n\n"
    "# Messages\n"
    "You received the following messages from fellow panelists:\n"
    "{inbox}\n\n"
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

BARE_TMPL = (
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

FEWSHOT = (
    "Here are three examples of the required response format:\n"
    "Example 1 answer: A\n"
    "Example 2 answer: B\n"
    "Example 3 answer: A\n\n"
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


def build_a2_calls(claims, bank, prefix, seed0):
    """Polarity regression design: TRUE/FALSE message counts randomized."""
    pool = {k: v.reset_index(drop=True)
            for k, v in bank.groupby(["claim_id", "stance"])}
    calls = []
    per_claim = N_A2 // len(claims)
    for _, c in claims.iterrows():
        for j in range(per_claim):
            k = KS[int(RNG.integers(len(KS)))]
            n_true = int(RNG.integers(0, k + 1))
            msgs = []
            if n_true:
                p = pool[(c.claim_id, "TRUE")]
                msgs += [("T", p.iloc[i].message) for i in
                         RNG.choice(len(p), n_true, replace=False)]
            if k - n_true:
                p = pool[(c.claim_id, "FALSE")]
                msgs += [("F", p.iloc[i].message) for i in
                         RNG.choice(len(p), k - n_true, replace=False)]
            RNG.shuffle(msgs)
            asg = "TF" if j % 2 == 0 else "FT"
            oa, ob = ("TRUE", "FALSE") if asg == "TF" else ("FALSE", "TRUE")
            persona = PERSONAS[int(RNG.integers(len(PERSONAS)))]
            calls.append({
                "prompt": prefix + SCAFFOLD_TMPL.format(
                    persona=persona,
                    inbox="\n".join(f"- {m[1]}" for m in msgs),
                    claim=c.claim, option_A=oa, option_B=ob),
                "seed": int(seed0 + c.claim_id * 1000 + j),
                "condition": {"claim_id": int(c.claim_id), "k": k,
                              "n_true": n_true, "assign": asg,
                              "order": "".join(m[0] for m in msgs)}})
    return calls


def analyze_a2(recs, tag, n_boot=1000):
    rows = []
    for r in recs:
        if r.get("parsed") not in ("A", "B"):
            continue
        c = r["condition"]
        rows.append({"claim_id": c["claim_id"], "n_true": c["n_true"],
                     "n_false": c["k"] - c["n_true"],
                     "chose_true": int((r["parsed"] == "A")
                                       == (c["assign"] == "TF"))})
    df = pd.DataFrame(rows)
    cids = sorted(df.claim_id.unique())
    cidx = {c: i for i, c in enumerate(cids)}

    def fit(d):
        X = np.zeros((len(d), len(cids) + 2))
        X[np.arange(len(d)), d.claim_id.map(cidx)] = 1
        X[:, -2] = d.n_true
        X[:, -1] = d.n_false
        b = fit_logit(X, d.chose_true.to_numpy(float))
        return b[-2], b[-1]

    bT, bF = fit(df)
    ratio = abs(bT) / abs(bF) if bF != 0 else np.nan
    boots = []
    groups = {c: df[df.claim_id == c] for c in cids}
    for _ in range(n_boot):
        pick = RNG.choice(cids, len(cids), replace=True)
        parts = []
        for slot, c in enumerate(pick):
            g = groups[c].copy()
            g["claim_id"] = slot          # duplicates get their own FE
            parts.append(g)
        rb = pd.concat(parts, ignore_index=True)
        rcids = sorted(rb.claim_id.unique())
        ridx = {c: i for i, c in enumerate(rcids)}
        X = np.zeros((len(rb), len(rcids) + 2))
        X[np.arange(len(rb)), rb.claim_id.map(ridx)] = 1
        X[:, -2] = rb.n_true
        X[:, -1] = rb.n_false
        bb = fit_logit(X, rb.chose_true.to_numpy(float))
        if bb[-1] != 0:
            boots.append(abs(bb[-2]) / abs(bb[-1]))
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"variant": tag, "n_parsed": len(df), "b_true": bT, "b_false": bF,
            "polarity_ratio": ratio, "ci_lo": lo, "ci_hi": hi}


def main():
    cal = pd.read_csv(os.path.join(ROOT, "results", "stage1_claims.csv"))
    cal["truth"] = cal.truth.map({True: "TRUE", False: "FALSE",
                                  "TRUE": "TRUE", "FALSE": "FALSE"})
    claims17 = cal[cal.selected].reset_index(drop=True)
    bank = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                        "message_bank.parquet"))
    bank = bank[bank.pure]
    s2b = pd.read_csv(os.path.join(ROOT, "data", "stage2b", "claims.csv"))
    s2b["truth"] = s2b.truth.map({True: "TRUE", False: "FALSE",
                                  "TRUE": "TRUE", "FALSE": "FALSE"})
    texts = dict(zip(cal.claim_id, cal.claim)) | dict(
        zip(s2b.claim_id, s2b.claim))

    # ---- A-4 parse-gate pilot: 200 calls per variant, plain format ----
    pilot_rates = {}
    for tag, model in VARIANTS.items():
        stage1_lib.MODEL = model
        calls = build_a2_calls(claims17, bank, "", 200_000_000)[:200]
        recs = run_batch(calls, f"42_pilot_{tag}", retries=0)
        ok = sum(1 for r in recs if r.get("parsed") in ("A", "B"))
        pilot_rates[tag] = ok / len(recs)
        print(f"pilot {tag}: parse rate {pilot_rates[tag]:.3f}")
    use_fewshot = (bool(os.environ.get("D3_FORCE_FEWSHOT"))
                   or any(v < 0.95 for v in pilot_rates.values()))
    prefix = FEWSHOT if use_fewshot else ""
    print("fallback few-shot prefix:", use_fewshot)

    # ---- A-2 main polarity regression ----
    out = []
    for tag, model in VARIANTS.items():
        stage1_lib.MODEL = model
        calls = build_a2_calls(claims17, bank, prefix,
                               210_000_000 + hash(tag) % 10**7)
        print(f"A-2 {tag}: {len(calls)} calls")
        recs = run_batch(calls, f"42_a2_{tag}")
        res = analyze_a2(recs, tag)
        res["pilot_parse_rate"] = pilot_rates[tag]
        res["fewshot_prefix"] = use_fewshot
        res["model"] = model
        out.append(res)
        print(res)
    ppath = os.path.join(ROOT, "results", "stage2c_d3_polarity.csv")
    newdf = pd.DataFrame(out)
    if os.environ.get("D3_ONLY") and os.path.exists(ppath):
        newdf = pd.concat([pd.read_csv(ppath), newdf], ignore_index=True)
    newdf.to_csv(ppath, index=False)

    # ---- A-3 bare affirmation index ----
    rows = []
    for tag, model in VARIANTS.items():
        stage1_lib.MODEL = model
        calls = []
        for cid in list(PAIRS) + list(PAIRS.values()):
            for j in range(N_A3_PER_CLAIM):
                asg = "TF" if j < N_A3_PER_CLAIM // 2 else "FT"
                oa, ob = (("TRUE", "FALSE") if asg == "TF"
                          else ("FALSE", "TRUE"))
                calls.append({
                    "prompt": prefix + BARE_TMPL.format(
                        claim=texts[cid], option_A=oa, option_B=ob),
                    "seed": int(230_000_000 + cid * 100 + j),
                    "condition": {"claim_id": int(cid), "assign": asg}})
        print(f"A-3 {tag}: {len(calls)} calls")
        recs = run_batch(calls, f"42_a3_{tag}")
        aff = {}
        for cid in list(PAIRS) + list(PAIRS.values()):
            rs = [r for r in recs if r["condition"]["claim_id"] == cid
                  and r.get("parsed") in ("A", "B")]
            aff[cid] = (np.mean([
                (r["parsed"] == "A") == (r["condition"]["assign"] == "TF")
                for r in rs]) if rs else np.nan, len(rs))
        for orig, para in PAIRS.items():
            rows.append({"variant": tag, "orig_id": orig, "para_id": para,
                         "p_affirm_orig": aff[orig][0],
                         "n_orig": aff[orig][1],
                         "p_affirm_para": aff[para][0],
                         "n_para": aff[para][1],
                         "S": aff[orig][0] + aff[para][0]})
    bp = pd.DataFrame(rows)
    bpath = os.path.join(ROOT, "results", "stage2c_d3_bare_pairs.csv")
    if os.environ.get("D3_ONLY") and os.path.exists(bpath):
        bp = pd.concat([pd.read_csv(bpath), bp], ignore_index=True)
    bp.to_csv(bpath, index=False)
    print(bp.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
