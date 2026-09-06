"""Stage 2c Part B-1/B-2: qwen3:8b systematic threshold calibration.

1. 20 fresh CLIMATE-FEVER candidates (10 SUPPORTS / 10 REFUTES, none among
   the 120 Stage-1 candidates), two-stage calibration under the FULL scaffold
   (empty inbox), 24 -> 64 calls for p in [0.35, 0.65].
2. qwen message banks (2 stances x 24 + purity x2) per candidate.
3. Mini singles (D-1 design: k in {2,5,8}, Stage-1 l levels, 24 reps).
4. Per-claim fits -> fixed points at alpha in {0.30, 0.55}.
5. Selection of 8 by the frozen wording: >=4 with interior unstable FP in
   [0.10, 0.90], >=2 correct-monostable, >=2 wrong-dominant (as close as the
   pool allows; if fewer than 4 bistable, add 10 candidates and recalibrate).
6. Freeze predictions to results/stage2c_blind_predictions.csv (sha256+mtime
   recorded by the caller).

Run with S2_URL=http://127.0.0.1:11435/api/generate S2_MODEL=qwen3:8b
S2_NOTHINK=1.
"""
import hashlib
import os
import sys

import numpy as np
import pandas as pd
from datasets import load_dataset

assert os.environ.get("S2_MODEL") == "qwen3:8b"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage1_lib
stage1_lib.CONCURRENCY = 16
from stage1_lib import ROOT, run_batch
import importlib.util
_p = importlib.util.spec_from_file_location(
    "pred", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "27_s2b_predict.py"))
pred = importlib.util.module_from_spec(_p)
_p.loader.exec_module(pred)
_q = importlib.util.spec_from_file_location(
    "s25", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "25_s2b_prepare.py"))
s25 = importlib.util.module_from_spec(_q)
_q.loader.exec_module(s25)
_m = importlib.util.spec_from_file_location(
    "s26", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "26_s2b_single.py"))
s26 = importlib.util.module_from_spec(_m)
_m.loader.exec_module(s26)
# imports above rewrite stage1_lib.URL; restore the env-requested URL
stage1_lib.URL = os.environ.get("S2_URL",
                                "http://127.0.0.1:11435/api/generate")

RNG = np.random.default_rng(47)
K_LEVELS = {2: [0, 1, 2], 5: [0, 1, 2, 3, 4, 5], 8: [0, 2, 4, 6, 8]}
C_DIR = os.path.join(ROOT, "data", "stage2c")

SCAFFOLD = (
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


def candidates(n_extra=0):
    ds = load_dataset("tdiggelm/climate_fever", split="test")
    df = pd.DataFrame({"claim_id": [int(c) for c in ds["claim_id"]],
                       "claim": ds["claim"], "label": ds["claim_label"]})
    df = df[df.label.isin([0, 1])].drop_duplicates(subset="claim")
    used = set(pd.read_csv(os.path.join(
        ROOT, "results", "stage1_claims.csv")).claim_id)
    df = df[~df.claim_id.isin(used)]
    df["label"] = df.label.map({0: "SUPPORTS", 1: "REFUTES"})
    df["truth"] = df.label.map({"SUPPORTS": "TRUE", "REFUTES": "FALSE"})
    n_each = 10 + n_extra // 2
    sup = df[df.label == "SUPPORTS"].sample(n_each,
                                            random_state=int(RNG.integers(2**31)))
    ref = df[df.label == "REFUTES"].sample(n_each,
                                           random_state=int(RNG.integers(2**31)))
    return pd.concat([sup, ref]).reset_index(drop=True)


def scaffold_calls(claims, n_per, seed0, phase, persona_pool=s25.PERSONAS):
    calls = []
    for _, c in claims.iterrows():
        for j in range(n_per):
            asg = "TF" if j < n_per // 2 else "FT"
            oa, ob = ("TRUE", "FALSE") if asg == "TF" else ("FALSE", "TRUE")
            persona = persona_pool[int(RNG.integers(len(persona_pool)))]
            calls.append({
                "prompt": SCAFFOLD.format(persona=persona,
                                          inbox="(no messages)",
                                          claim=c.claim, option_A=oa,
                                          option_B=ob),
                "seed": int(seed0 + c.claim_id * 200 + j),
                "condition": {"phase": phase, "claim_id": int(c.claim_id),
                              "truth": c.truth, "assign": asg}})
    return calls


def tally_correct(recs):
    out = {}
    for r in recs:
        if r.get("parsed") not in ("A", "B"):
            continue
        c = r["condition"]
        chosen = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                  else "FALSE")
        out.setdefault(c["claim_id"], []).append(int(chosen == c["truth"]))
    return {k: (float(np.mean(v)), len(v)) for k, v in out.items()}


def main():
    os.makedirs(C_DIR, exist_ok=True)
    cand = candidates()
    print(f"{len(cand)} fresh candidates")

    # ---- calibration under full scaffold, two-stage ----
    recs = run_batch(scaffold_calls(cand, 24, 300_000_000, "cal24"),
                     "43_cal24")
    p1 = tally_correct(recs)
    band = [cid for cid, (p, n) in p1.items() if 0.35 <= p <= 0.65]
    print(f"boundary band [0.35,0.65]: {len(band)} claims")
    if band:
        sub = cand[cand.claim_id.isin(band)]
        recs2 = run_batch(scaffold_calls(sub, 40, 310_000_000, "cal40"),
                          "43_cal40")
        p2 = tally_correct(recs2)
        for cid, (p, n) in p2.items():
            p0, n0 = p1[cid]
            p1[cid] = ((p0 * n0 + p * n) / (n0 + n), n0 + n)
    cand["p_q_scaffold"] = cand.claim_id.map(lambda c: p1.get(c, (np.nan, 0))[0])
    cand["n_cal"] = cand.claim_id.map(lambda c: p1.get(c, (np.nan, 0))[1])

    # ---- banks ----
    gen_calls, meta = [], []
    for _, c in cand.iterrows():
        for stance in ("TRUE", "FALSE"):
            for j in range(24):
                persona = s25.PERSONAS[int(RNG.integers(len(s25.PERSONAS)))]
                gen_calls.append({
                    "prompt": s25.GEN_TMPL.format(persona=persona,
                                                  claim=c.claim,
                                                  stance=stance),
                    "seed": int(320_000_000 + c.claim_id * 100
                                + (stance == "FALSE") * 50 + j),
                    "condition": {"phase": "gen",
                                  "claim_id": int(c.claim_id),
                                  "stance": stance}})
                meta.append((int(c.claim_id), c.claim, stance, persona))
    print(f"bank generation: {len(gen_calls)}")
    grecs = run_batch(gen_calls, "43_gen", num_predict=150, parse=None,
                      retries=1)
    rows = []
    for (cid, claim, stance, persona), r in zip(meta, grecs):
        msg = " ".join((r["response"] or "").strip().split()).strip('"')
        rows.append({"claim_id": cid, "claim": claim, "stance": stance,
                     "persona": persona, "message": msg})
    bank = pd.DataFrame(rows)
    bank = bank[bank.message.str.len() >= 20].reset_index(drop=True)
    jcalls = []
    for i, b in bank.iterrows():
        for asg in ("TF", "FT"):
            oa, ob = (("The claim is TRUE", "The claim is FALSE")
                      if asg == "TF" else
                      ("The claim is FALSE", "The claim is TRUE"))
            jcalls.append({"prompt": s25.JUDGE_TMPL.format(
                claim=b.claim, message=b.message, option_A=oa, option_B=ob),
                "seed": int(330_000_000 + i * 10 + (asg == "FT")),
                "condition": {"bank_idx": int(i), "assign": asg,
                              "stance": b.stance}})
    jrecs = run_batch(jcalls, "43_purity")
    verd = {}
    for r in jrecs:
        c = r["condition"]
        v = None
        if r.get("parsed"):
            v = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                 else "FALSE")
        verd.setdefault(c["bank_idx"], []).append(v)
    bank["pure"] = [len(verd.get(i, [])) == 2 and
                    all(v == bank.at[i, "stance"] for v in verd[i])
                    for i in bank.index]
    print("purity discard:", round(1 - bank.pure.mean(), 3))
    bank.to_parquet(os.path.join(C_DIR, "message_bank.parquet"), index=False)
    pool = {k: v.reset_index(drop=True)
            for k, v in bank[bank.pure].groupby(["claim_id", "stance"])}

    # ---- mini singles ----
    calls = []
    for _, c in cand.iterrows():
        wrong = "FALSE" if c.truth == "TRUE" else "TRUE"
        for k, ls in K_LEVELS.items():
            for l in ls:
                if (l and (c.claim_id, c.truth) not in pool) or \
                   (k - l and (c.claim_id, wrong) not in pool):
                    continue
                for j in range(24):
                    asg = "TF" if j < 12 else "FT"
                    msgs = []
                    if l:
                        p = pool[(c.claim_id, c.truth)]
                        msgs += [("C", p.iloc[i].message) for i in
                                 RNG.choice(len(p), l, replace=False)]
                    if k - l:
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
                        "seed": int(RNG.integers(340_000_000, 990_000_000)),
                        "condition": {"claim_id": int(c.claim_id),
                                      "truth": c.truth, "k": k, "l": l,
                                      "assign": asg}})
    print(f"mini singles: {len(calls)}")
    srecs = run_batch(calls, "43_single")
    rows = []
    for r in srecs:
        if r.get("parsed") not in ("A", "B"):
            continue
        c = r["condition"]
        chosen = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                  else "FALSE")
        rows.append({"claim_id": c["claim_id"], "k": c["k"], "l": c["l"],
                     "y": int(chosen == c["truth"])})
    obs = pd.DataFrame(rows)
    obs.to_parquet(os.path.join(C_DIR, "single_obs.parquet"), index=False)

    # ---- per-claim fits + fixed points ----
    co, prow = [], []
    for cid, sub in obs.groupby("claim_id"):
        X0 = np.column_stack([np.ones(len(sub)), sub.l,
                              (sub.k - sub.l).astype(float)])
        b = s26.fit_logit(X0, sub.y.to_numpy(float))
        co.append({"claim_id": cid, "k": "pooled", "c0": b[0], "bT": b[1],
                   "bF": b[2], "n": len(sub)})
        for k, sk in sub.groupby("k"):
            Xk = np.column_stack([np.ones(len(sk)), sk.l,
                                  (sk.k - sk.l).astype(float)])
            bk = s26.fit_logit(Xk, sk.y.to_numpy(float))
            co.append({"claim_id": cid, "k": k, "c0": bk[0], "bT": bk[1],
                       "bF": bk[2], "n": len(sk)})
    codf = pd.DataFrame(co)
    codf.to_csv(os.path.join(ROOT, "results", "stage2c_single_coeffs.csv"),
                index=False)
    for cid, sub in codf.groupby("claim_id"):
        c0 = float(sub[sub.k == "pooled"].c0.iloc[0])
        coef = pred.make_coef(sub[sub.k != "pooled"].astype({"k": str}))
        for a in (0.30, 0.55):
            fps = pred.fixed_points(a, c0, coef)
            unstable = [r for r, s in fps if s == "unstable"
                        and 0.10 <= r <= 0.90]
            stable = [r for r, s in fps if s == "stable"]
            if unstable:
                cls = f"bistable(x_c={unstable[0]:.3f})"
            elif stable and stable[0] >= 0.5:
                cls = "mono_correct"
            elif stable:
                cls = "mono_wrong"
            else:
                # no interior crossing: boundary attractor by map direction
                F0 = pred.fixed_points  # noqa: F841  (documented in notes)
                cls = "mono_correct" if c0 > 0 else "mono_wrong"
            prow.append({"claim_id": cid, "alpha": a, "c0": round(c0, 3),
                         "fixed_points": "; ".join(
                             f"{r}({s})" for r, s in fps),
                         "class": cls})
    pp = pd.DataFrame(prow).merge(
        cand[["claim_id", "claim", "label", "truth", "p_q_scaffold",
              "n_cal"]], on="claim_id")
    pp.to_csv(os.path.join(C_DIR, "all_candidate_predictions.csv"),
              index=False)
    print(pp[["claim_id", "label", "alpha", "c0", "class"]].to_string(
        index=False))

    # ---- selection (frozen wording) ----
    per_claim = pp.groupby("claim_id").agg(
        n_bis=("class", lambda s: sum(c.startswith("bistable") for c in s)),
        n_mc=("class", lambda s: sum(c == "mono_correct" for c in s)),
        n_mw=("class", lambda s: sum(c == "mono_wrong" for c in s)))
    bis = per_claim[per_claim.n_bis > 0].index.tolist()
    mc = per_claim[(per_claim.n_bis == 0) &
                   (per_claim.n_mc > 0)].index.tolist()
    mw = per_claim[(per_claim.n_bis == 0) & (per_claim.n_mc == 0)
                   ].index.tolist()
    print(f"pools: bistable {len(bis)}, mono_correct {len(mc)}, "
          f"mono_wrong {len(mw)}")
    sel = bis[:4] + mc[:2] + mw[:2]
    for pool_ in (bis[4:], mc[2:], mw[2:]):
        for cid in pool_:
            if len(sel) >= 8:
                break
            sel.append(cid)
    sel = sel[:8]
    print("selected:", sel, f"(bistable among them: "
          f"{sum(1 for c in sel if c in bis)})")
    if sum(1 for c in sel if c in bis) < 4:
        print("*** fewer than 4 bistable claims — per the frozen rule, add "
              "10 candidates and recalibrate (NOT done automatically; "
              "rerun with extension) ***")
    sel_df = cand[cand.claim_id.isin(sel)][
        ["claim_id", "claim", "label", "truth", "p_q_scaffold"]]
    sel_df.to_csv(os.path.join(C_DIR, "claims.csv"), index=False)
    frozen = pp[pp.claim_id.isin(sel)]
    fpath = os.path.join(ROOT, "results", "stage2c_blind_predictions.csv")
    frozen.to_csv(fpath, index=False)
    sha = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
    print("FROZEN", fpath)
    print("sha256:", sha)
    print("mtime:", os.path.getmtime(fpath))


if __name__ == "__main__":
    main()
