"""Stage 2b block E: residual and consistency analyses.

E-1a  message length/hedging by side (Stage 2 logs)
E-1b  recorded-message persuasiveness probes (k=4 per side, episode vs bank)
E-2   repeated-exposure: one-step regression with round interaction and
      persistent-source split
E-3   finite-time check on high-x0 episodes (slope x8 - x7)
E-4   A/B assignment balance vs outcome
E-5   paper-3 previews: refractory coefficient, branching ratio sigma(alpha),
      El et al. async cascade size distribution

Outputs: results/stage2b_E_*.csv, printed summary for notes/13.
"""
import glob
import json
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage1_lib
stage1_lib.URL = "http://127.0.0.1:11435/api/generate"
stage1_lib.CONCURRENCY = 8   # group driver is running; stay modest
from stage1_lib import ROOT, run_batch

RNG = np.random.default_rng(23)
EP_GLOB = os.path.join(ROOT, "data", "stage2", "episodes", "B[146]_*.json")
HEDGES = ["may", "might", "could", "some", "uncertain", "possibly", "perhaps",
          "suggest", "unclear", "not necessarily", "debate", "complex"]

PROBE_TMPL = (
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
PERSONA = "You are a climate scientist."


def sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


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


def cluster_se(X, y, b, cl):
    """CR0 sandwich by cluster labels cl."""
    z = np.clip(X @ b, -30, 30)
    mu = 1 / (1 + np.exp(-z))
    W = mu * (1 - mu) + 1e-9
    H = (X * W[:, None]).T @ X
    Hinv = np.linalg.inv(H + 1e-8 * np.eye(X.shape[1]))
    S = np.zeros((X.shape[1], X.shape[1]))
    resid = y - mu
    for c in np.unique(cl):
        m = cl == c
        g = X[m].T @ resid[m]
        S += np.outer(g, g)
    V = Hinv @ S @ Hinv
    return np.sqrt(np.diag(V))


def load_stage2():
    eps = []
    for fp in sorted(glob.glob(EP_GLOB)):
        d = json.load(open(fp))
        if d["meta"].get("rho", 0) or d["meta"].get("spin_samples", 1) != 1:
            continue
        eps.append(d)
    return eps


def e1a_messages(eps):
    rows = []
    for d in eps:
        y_correct_stance = 1
        S = d["stance_history"]
        for t, msgs in enumerate(d["messages"]):
            for i, m in enumerate(msgs):
                if not m:
                    continue
                side = "correct" if S[t][i] == y_correct_stance else "wrong"
                text = m.lower()
                rows.append({
                    "claim_id": d["meta"]["claim_id"], "side": side,
                    "n_chars": len(m), "n_words": len(m.split()),
                    "hedges": sum(len(re.findall(r"\b" + re.escape(h) + r"\b",
                                                 text)) for h in HEDGES)})
    df = pd.DataFrame(rows)
    out = df.groupby(["claim_id", "side"]).agg(
        n=("n_words", "size"), words=("n_words", "mean"),
        hedges_per_msg=("hedges", "mean")).round(3)
    out.to_csv(os.path.join(ROOT, "results", "stage2b_E_messages.csv"))
    print("E-1a message stats by side:\n", out.to_string())
    return df


def e1b_probes(eps):
    """k=4 one-sided probes: episode-recorded vs Stage-1-bank messages."""
    bank = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                        "message_bank.parquet"))
    bank = bank[bank.pure]
    claims = pd.read_csv(os.path.join(ROOT, "results", "stage2_claims.csv"))
    claims["truth"] = claims.truth.map({True: "TRUE", False: "FALSE",
                                        "TRUE": "TRUE", "FALSE": "FALSE"})
    claims = claims[claims.selected]
    ep_msgs = {}
    for d in eps:
        cid = d["meta"]["claim_id"]
        S = d["stance_history"]
        for t, msgs in enumerate(d["messages"]):
            for i, m in enumerate(msgs):
                if m:
                    side = "correct" if S[t][i] == 1 else "wrong"
                    ep_msgs.setdefault((cid, side), []).append(m)
    calls = []
    N_REP = 60
    for _, c in claims.iterrows():
        wrong_stance = "TRUE" if c.truth == "FALSE" else "FALSE"
        for side in ("correct", "wrong"):
            stance = c.truth if side == "correct" else wrong_stance
            for source in ("episode", "bank"):
                msgs_pool = (ep_msgs.get((c.claim_id, side), [])
                             if source == "episode" else
                             bank[(bank.claim_id == c.claim_id)
                                  & (bank.stance == stance)].message.tolist())
                if len(msgs_pool) < 4:
                    continue
                for j in range(N_REP):
                    pick = [msgs_pool[i] for i in
                            RNG.choice(len(msgs_pool), 4, replace=False)]
                    asg = "TF" if j % 2 == 0 else "FT"
                    oa, ob = (("TRUE", "FALSE") if asg == "TF"
                              else ("FALSE", "TRUE"))
                    calls.append({
                        "prompt": PROBE_TMPL.format(
                            persona=PERSONA,
                            inbox="\n".join(f"- {m}" for m in pick),
                            claim=c.claim, option_A=oa, option_B=ob),
                        "seed": int(RNG.integers(80_000_000, 900_000_000)),
                        "condition": {"claim_id": int(c.claim_id),
                                      "truth": c.truth, "side": side,
                                      "source": source, "assign": asg}})
    print(f"E-1b: {len(calls)} probe calls")
    recs = run_batch(calls, "25e_probes")
    rows = []
    for r in recs:
        if r.get("parsed") not in ("A", "B"):
            continue
        c = r["condition"]
        chosen = ("TRUE" if (r["parsed"] == "A") == (c["assign"] == "TF")
                  else "FALSE")
        rows.append({"claim_id": c["claim_id"], "side": c["side"],
                     "source": c["source"],
                     "y": int(chosen == c["truth"])})
    df = pd.DataFrame(rows)
    out = df.groupby(["claim_id", "side", "source"]).y.agg(
        ["mean", "size"]).round(3)
    out.to_csv(os.path.join(ROOT, "results", "stage2b_E_probes.csv"))
    print("E-1b probe P(correct) by side x source:\n", out.to_string())


def e2_repeat_and_e5_refractory(eps):
    rows = []
    for d in eps:
        S = np.array(d["stance_history"], int)
        cid = d["meta"]["claim_id"]
        alpha = d["meta"]["alpha"]
        prev_flip = np.zeros(32, dtype=bool)
        by_round = {}
        for rec in d["spin_log"]:
            by_round.setdefault(rec["round"], {})[rec["agent"]] = rec
        for t in range(1, 9):
            for j in range(32):
                rec = by_round[t][j]
                k = len(rec["sources"])
                l = rec["order_stances"].count("C")
                flip_prev = bool(prev_flip[j])
                rows.append({"claim_id": cid, "alpha": alpha, "round": t,
                             "k": k, "l": l, "s_prev": int(S[t - 1][j]),
                             "y": int(S[t][j]),
                             "flip_prev": int(flip_prev)})
            prev_flip = S[t] != S[t - 1]
    df = pd.DataFrame(rows)

    # E-2: drive x round interaction (does the same static inbox lose force?)
    X = np.column_stack([
        np.ones(len(df)), df.l, df.k - df.l,
        df.l * (df["round"] - 1), (df.k - df.l) * (df["round"] - 1)])
    b = fit_logit(X, df.y.to_numpy(float))
    se = cluster_se(X, df.y.to_numpy(float), b, df.claim_id.to_numpy())
    print("E-2 one-step with round interaction "
          "[c0, bT, bF, bT x (t-1), bF x (t-1)]:")
    print("  coef:", np.round(b, 4).tolist())
    print("  claim-cluster SE:", np.round(se, 4).tolist())

    # E-5a refractory: does flipping at t-1 suppress flipping at t?
    df["flip"] = (df.y != df.s_prev).astype(float)
    X2 = np.column_stack([np.ones(len(df)), df.l, df.k - df.l, df.s_prev,
                          df.flip_prev])
    b2 = fit_logit(X2, df.flip.to_numpy(float))
    se2 = cluster_se(X2, df.flip.to_numpy(float), b2,
                     df.claim_id.to_numpy())
    print("E-5a refractory logit P(flip) [c0, l, k-l, s_prev, flip_prev]:")
    print("  coef:", np.round(b2, 4).tolist(),
          "\n  claim-cluster SE:", np.round(se2, 4).tolist())

    # E-5b branching ratio sigma(alpha): flips among downstream receivers
    sig_rows = []
    for d in eps:
        S = np.array(d["stance_history"], int)
        alpha = d["meta"]["alpha"]
        acc = d["graph"]["accepted"]
        downstream = {i: [j for j in range(32) if i in acc[j]]
                      for i in range(32)}
        for t in range(1, 8):
            flippers = np.where(S[t] != S[t - 1])[0]
            for i in flippers:
                ds = downstream[i]
                n_flip_next = int(sum(S[t + 1][j] != S[t][j] for j in ds))
                sig_rows.append({"alpha": alpha, "out_deg": len(ds),
                                 "n_flip_next": n_flip_next})
    sg = pd.DataFrame(sig_rows)
    out = sg.groupby("alpha").agg(n_flip_events=("n_flip_next", "size"),
                                  sigma=("n_flip_next", "mean")).round(3)
    out.to_csv(os.path.join(ROOT, "results", "stage2b_E_branching.csv"))
    print("E-5b branching ratio sigma(alpha) "
          "(mean downstream flips per flip):\n", out.to_string())
    return df


def e3_finite_time(eps):
    rows = []
    for d in eps:
        if d["meta"]["x0_n"] < 20:
            continue
        x = [float(np.mean(s)) for s in d["stance_history"]]
        rows.append({"alpha": d["meta"]["alpha"], "x0_n": d["meta"]["x0_n"],
                     "x7": x[7], "x8": x[8], "slope": x[8] - x[7],
                     "interior": 0.1 < x[8] < 0.9})
    df = pd.DataFrame(rows)
    out = df.groupby(["alpha", "x0_n"]).agg(
        n=("slope", "size"), mean_slope=("slope", "mean"),
        frac_interior=("interior", "mean"),
        frac_still_moving=("slope", lambda s: (np.abs(s) > 1 / 32).mean())
    ).round(3)
    out.to_csv(os.path.join(ROOT, "results", "stage2b_E_finitetime.csv"))
    print("E-3 finite-time (high-x0 episodes):\n", out.to_string())


def e4_label(eps):
    rows = []
    for d in eps:
        assigns = [r["assign"] for r in d["spin_log"]]
        a_share = np.mean([a == "TF" for a in assigns])
        x8 = float(np.mean(d["stance_history"][8]))
        rows.append({"a_share": a_share, "x8": x8})
    df = pd.DataFrame(rows)
    r = np.corrcoef(df.a_share, df.x8)[0, 1]
    print(f"E-4 corr(episode TF-assignment share, x8) = {r:.4f} "
          f"(n={len(df)})")


def e5c_async_cascades():
    files = glob.glob(os.path.join(
        ROOT, "external", "physics-of-agents", "data", "async",
        "gpt-4o-mini", "objective_energy_seq", "*.json"))
    sizes = []
    for fp in files:
        if fp.endswith("manifest.json"):
            continue
        d = json.load(open(fp))
        J = np.array(d["J"], dtype=int)
        spins = np.array(d["spins_history"][0], dtype=int)
        # replay events; cascade = chain of flips where the flipper is a
        # graph neighbor of some member of the active cascade and fires
        # within 3 events of the cascade's last flip
        cur, last_ev, ev_idx = set(), -10, 0
        cur_size = 0
        for step, (sched, evs) in enumerate(zip(d["firing_schedule"],
                                                d["event_spins_history"])):
            for (cell, agent), new in zip(sched, evs):
                if new == 0:
                    ev_idx += 1
                    continue
                flipped = new != spins[agent]
                spins[agent] = new
                if flipped:
                    linked = (cur and ev_idx - last_ev <= 3
                              and any(J[agent, m] != 0 for m in cur))
                    if linked:
                        cur.add(agent)
                        cur_size += 1
                    else:
                        if cur_size:
                            sizes.append(cur_size)
                        cur, cur_size = {agent}, 1
                    last_ev = ev_idx
                ev_idx += 1
        if cur_size:
            sizes.append(cur_size)
    s = pd.Series(sizes)
    dist = s.value_counts().sort_index()
    dist.to_csv(os.path.join(ROOT, "results",
                             "stage2b_E_async_cascades.csv"))
    print(f"E-5c async cascades (gpt-4o-mini, {len(files) - 1} runs): "
          f"n={len(s)}, mean={s.mean():.2f}, max={s.max()}")
    print("  size dist:", dict(dist.head(10)))


def main():
    eps = load_stage2()
    print(f"{len(eps)} Stage 2 arm-A episodes (rho=0, 1-sample)")
    e1a_messages(eps)
    e2_repeat_and_e5_refractory(eps)
    e3_finite_time(eps)
    e4_label(eps)
    e5c_async_cascades()
    e1b_probes(eps)


if __name__ == "__main__":
    main()
