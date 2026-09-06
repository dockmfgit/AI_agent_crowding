"""R3/R4 (episode part, run on GX10): one-step replay, surrogate rollouts and
finite-horizon predictions for the Stage 2 collective experiment (llama3.1:8b,
arms A and B, rho = 0 and 1) with IDENTIFIED response rules.

Usage: python scripts/52_replay_surrogate_identified.py [PROJECT_ROOT] [--selftest]

Rules compared (all from scripts/50 outputs; nothing fitted to episodes):
  perk17     : identified joint per-k rule (Stage 1, 17 claims, claim FE of the
               episode's claim), variant A for arm A, variant B (+theta*own
               state) for arm B. This is the corrected version of the blind
               pooled rule (coefficients from ALL 17 calibrated claims).
  claim_const: per-claim reduced model, constant weights (4 Stage 2 claims).
  claim_div  : per-claim reduced model, divisive weights, gamma = 0.9.
  legacy     : the rule used in scripts/29 (pooled FE + legacy per-k slopes),
               reproduced for the record only.

Per rule:
  one-step replay of every realized inbox -> Brier, climatology Brier, ECE,
     mean residual (y - p) overall and at contested compositions (0.4<=l/k<=0.6);
  surrogate rollout (n_roll per episode) on the actual graph and seeding ->
     per-(arm, alpha, rho, x0) predicted P(correct outcome), P(wrong outcome),
     mean x8, against the observed values; the pre-registered 20% rule applied
     to the surrogate (finite-horizon alpha*_emp,pred) as well as to the data.
Observed per-claim low-x0 mean x8 for arms A and B (for comparison with the
fixed points in results/r23_stage2_armAB_fixed_points.csv).

Outputs: results/r34_onestep_calibration.csv, results/r34_surrogate_cells.csv,
         results/r34_perclaim_lowx0.csv, results/r34_alpha_star_finite.csv,
         results/r34_summary.txt
"""
import glob
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hmf_lib as H  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.dirname(HERE)
SELFTEST = "--selftest" in sys.argv
RES = os.path.join(ROOT, "results")
EP_DIR = os.path.join(ROOT, "data", "stage2", "episodes")
DELTA = 0.1
N_ROLL = 200
RNG = np.random.default_rng(11)


# ------------------------------------------------------------------ rules
def load_rules():
    perk = pd.read_csv(os.path.join(RES, "r1_stage1_identified_perk.csv"))
    fe = pd.read_csv(os.path.join(RES, "r1_stage1_identified_FE.csv"))
    cm = pd.read_csv(os.path.join(RES, "r1_claim_models.csv"))
    rules = {}

    def perk17(arm):
        pk = perk[perk.variant == arm]
        ws = arm == "B"
        theta = float(pk.theta.iloc[0]) if ws else 0.0
        fe_map = fe[fe.variant == arm].set_index("claim_id").FE.to_dict()
        base = H.response_perk(0.0, pk.k, pk.bT, pk.bF, "power", theta=theta)

        def rule(claim_id, k, l, s):
            c0 = fe_map[claim_id]
            t, f = base.coef(k)
            return H.sig(c0 + theta * s + t * l + f * (k - l))
        return rule
    rules["perk17"] = {"A": perk17("A"), "B": perk17("B")}

    def claim_rule(gname, arm):
        ws = arm == "B"
        ds = f"stage2_{arm}"
        sub = cm[(cm.dataset == ds) & (cm.model == gname)].set_index("claim_id")

        def rule(claim_id, k, l, s):
            m = sub.loc[claim_id]
            g = 1.0 / (1.0 + m.gamma * k) if gname == "divisive" else 1.0
            th = m.theta if ws else 0.0
            return H.sig(m.c0 + th * s + g * (m.delta * k + m.beta_bar * (2 * l - k)))
        return rule
    rules["claim_const"] = {a: claim_rule("constant", a) for a in "AB"}
    rules["claim_div"] = {a: claim_rule("divisive", a) for a in "AB"}

    # legacy rule (scripts/29): pooled FE + legacy per-k slopes, variant A only
    try:
        spec = importlib.util.spec_from_file_location("s29", os.path.join(HERE, "29_stage2_analysis.py"))
        s29 = importlib.util.module_from_spec(spec); spec.loader.exec_module(s29)
        fe_l, ks_l, bT_l, bF_l, coef_l = s29.stage1_perk_rule()

        def legacy(claim_id, k, l, s):
            if k == 0:
                return H.sig(fe_l[claim_id])
            bT, bF = coef_l(k, "power")
            return H.sig(fe_l[claim_id] + bT * l + bF * (k - l))
        rules["legacy"] = {"A": legacy, "B": legacy}
    except Exception as e:  # noqa: BLE001
        print("legacy rule unavailable:", e)
    return rules


# --------------------------------------------------------------- episodes
def load_episodes():
    rows, eps = [], {}
    for fp in sorted(glob.glob(os.path.join(EP_DIR, "*.json"))):
        name = os.path.basename(fp)[:-5]
        if name.startswith("trial"):
            continue
        d = json.load(open(fp))
        m = d["meta"]
        if m.get("spin_samples", 1) != 1 or m["arm"] not in ("A", "B"):
            continue
        # Stage 2 main experiment only (llama3.1:8b): blocks B1-B4 first
        # pass, B6 second pass. Excludes stage 2b (S2b_*), 2c (B3c),
        # 2d (D1) episodes, whose claims are outside the llama rule maps.
        if m.get("block", "") not in ("B1", "B2", "B3", "B4", "B6"):
            continue
        S = np.array(d["stance_history"], float)
        x = S.mean(axis=1)
        rows.append({"name": name, "arm": m["arm"], "alpha": m["alpha"], "rho": m.get("rho", 0),
                     "x0_n": m["x0_n"], "x0": m["x0_n"] / 32, "claim_id": m["claim_id"],
                     "x8": x[8], "block": m.get("block", "")})
        eps[name] = d
    return pd.DataFrame(rows), eps


def one_step(d, rule):
    S = np.array(d["stance_history"], int)
    cid = d["meta"]["claim_id"]
    out = []
    for rec in d["spin_log"]:
        t, j = rec["round"], rec["agent"]
        k = len(rec["sources"])
        l = rec["order_stances"].count("C")
        s = int(S[t - 1][j])
        p = float(rule(cid, k, l, s))
        out.append({"round": t, "agent": j, "k": k, "l": l, "s": s, "p_pred": p, "y_next": int(S[t][j])})
    return out


def surrogate(d, rule, n_roll=N_ROLL):
    acc = d["graph"]["accepted"]
    n = len(acc)
    cid = d["meta"]["claim_id"]
    ks = np.array([len(a) for a in acc])
    s0 = np.zeros(n)
    s0[d["x0_assignment"]] = 1.0
    S = np.tile(s0, (n_roll, 1))
    for _ in range(8):
        P = np.empty_like(S)
        for j in range(n):
            k = ks[j]
            l = S[:, acc[j]].sum(axis=1) if k else np.zeros(n_roll)
            # vectorized over rollouts: rule is scalar in l, s -> evaluate on unique pairs
            for s in (0, 1):
                m = S[:, j] == s
                if m.any():
                    ls = l[m]
                    P[m, j] = np.array([rule(cid, int(k), int(li), s) for li in ls])
        S = (RNG.random(S.shape) < P).astype(float)
    x8 = S.mean(axis=1)
    return {"q_roll": float((x8 >= 0.5 + DELTA).mean()), "wrong_roll": float((x8 <= 0.5 - DELTA).mean()),
            "mean_x8_roll": float(x8.mean())}


def ece(p, y, bins=10):
    idx = np.clip((p * bins).astype(int), 0, bins - 1)
    tot = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            tot += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(tot)


def alpha_star_20pct(cells, col):
    """First alpha at which the low-x0 (<= 8/32) wrong rate falls through 20%."""
    low = cells[cells.x0_n <= 8].groupby("alpha")[col].mean().sort_index()
    a, w = low.index.to_numpy(), low.to_numpy()
    for i in range(len(a) - 1):
        if (w[i] - 0.2) * (w[i + 1] - 0.2) < 0:
            return float(a[i] + (0.2 - w[i]) * (a[i + 1] - a[i]) / (w[i + 1] - w[i]))
    return np.nan


def make_selftest_episode(rng, arm="A", alpha=0.3, x0_n=8, cid=6):
    n = 32
    acc = []
    for j in range(n):
        order = rng.permutation([i for i in range(n) if i != j])
        a, r = [], 0
        for i in order:
            if rng.random() < np.exp(-alpha * r):
                a.append(int(i)); r += 1
        acc.append(a)
    corr = sorted(rng.choice(n, x0_n, replace=False).tolist())
    s = np.zeros(n, int); s[corr] = 1
    hist = [s.tolist()]; log = []
    for t in range(1, 9):
        new = s.copy()
        for j in range(n):
            l = int(s[acc[j]].sum()); k = len(acc[j])
            p = 1 / (1 + np.exp(-(0.5 + 0.4 * l - 0.5 * (k - l))))
            new[j] = int(rng.random() < p)
            log.append({"round": t, "agent": j, "sources": acc[j],
                        "order_stances": "".join("C" if s[i] else "W" for i in acc[j])})
        s = new; hist.append(s.tolist())
    return {"meta": {"arm": arm, "alpha": alpha, "x0_n": x0_n, "claim_id": cid, "rho": 0, "spin_samples": 1},
            "graph": {"accepted": acc}, "x0_assignment": corr, "stance_history": hist, "spin_log": log}


def main():
    rules = load_rules()
    if SELFTEST:
        rng = np.random.default_rng(0)
        eps = {f"self_{i}": make_selftest_episode(rng, alpha=a, x0_n=x, cid=c)
               for i, (a, x, c) in enumerate([(0.3, 8, 6), (0.3, 24, 382), (1.0, 8, 1569)])}
        df = pd.DataFrame([{"name": k, "arm": "A", "alpha": d["meta"]["alpha"], "rho": 0, "x0_n": d["meta"]["x0_n"],
                            "x0": d["meta"]["x0_n"] / 32, "claim_id": d["meta"]["claim_id"],
                            "x8": np.mean(d["stance_history"][8]), "block": "self"} for k, d in eps.items()])
        print("selftest episodes:", len(df))
    else:
        df, eps = load_episodes()
        print(f"{len(df)} episodes loaded (arms A/B, single-sample)")
    df["correct"] = (df.x8 >= 0.5 + DELTA).astype(float)
    df["wrong"] = (df.x8 <= 0.5 - DELTA).astype(float)

    cal_rows, cell_rows, lines = [], [], []
    for rname, byarm in rules.items():
        cal = []
        roll = []
        for name, d in eps.items():
            arm = d["meta"]["arm"]
            rule = byarm[arm]
            cal += [{**r, "alpha": d["meta"]["alpha"], "arm": arm, "name": name} for r in one_step(d, rule)]
            rr = surrogate(d, rule)
            roll.append({"name": name, **rr})
        cal = pd.DataFrame(cal)
        for (arm, a), sub in cal.groupby(["arm", "alpha"]):
            p, y = sub.p_pred.to_numpy(), sub.y_next.to_numpy(float)
            contested = sub[(sub.k > 0) & (sub.l / sub.k >= 0.4) & (sub.l / sub.k <= 0.6)]
            cal_rows.append({"rule": rname, "arm": arm, "alpha": a, "n_transitions": len(sub),
                             "brier": float(((p - y) ** 2).mean()),
                             "brier_climatology": float(y.mean() * (1 - y.mean())),
                             "ece": ece(p, y), "mean_resid": float((y - p).mean()),
                             "mean_resid_contested": float((contested.y_next - contested.p_pred).mean()) if len(contested) else np.nan,
                             "n_contested": len(contested)})
        roll = pd.DataFrame(roll)
        m = df.merge(roll, on="name")
        for (arm, a, rho, x0n), sub in m.groupby(["arm", "alpha", "rho", "x0_n"]):
            cell_rows.append({"rule": rname, "arm": arm, "alpha": a, "rho": rho, "x0_n": x0n, "x0": x0n / 32,
                              "n": len(sub), "obs_q": sub.correct.mean(), "obs_wrong": sub.wrong.mean(),
                              "obs_mean_x8": sub.x8.mean(), "pred_q": sub.q_roll.mean(),
                              "pred_wrong": sub.wrong_roll.mean(), "pred_mean_x8": sub.mean_x8_roll.mean()})
    cal_df = pd.DataFrame(cal_rows)
    cells = pd.DataFrame(cell_rows)
    cal_df.to_csv(os.path.join(RES, "r34_onestep_calibration.csv"), index=False)
    cells.to_csv(os.path.join(RES, "r34_surrogate_cells.csv"), index=False)

    # observed per-claim low-x0 mean x8 (for comparison with fixed points)
    low = df[df.x0_n <= 8].groupby(["arm", "alpha", "rho", "claim_id"]).agg(
        n=("x8", "size"), mean_x8=("x8", "mean"), wrong_rate=("wrong", "mean")).reset_index()
    low.to_csv(os.path.join(RES, "r34_perclaim_lowx0.csv"), index=False)

    # finite-horizon alpha* by the pre-registered 20% rule: data vs each surrogate
    ast = [{"source": "observed", "alpha_star_20pct": alpha_star_20pct(
        cells[(cells.rule == list(rules)[0]) & (cells.arm == "A") & (cells.rho == 0)], "obs_wrong")}]
    for rname in rules:
        ast.append({"source": f"surrogate:{rname}", "alpha_star_20pct": alpha_star_20pct(
            cells[(cells.rule == rname) & (cells.arm == "A") & (cells.rho == 0)], "pred_wrong")})
    ast = pd.DataFrame(ast)
    ast.to_csv(os.path.join(RES, "r34_alpha_star_finite.csv"), index=False)

    lines.append("== one-step calibration by rule")
    lines.append(cal_df.round(4).to_string(index=False))
    lines.append("== surrogate vs observed, arm A rho=0, low x0 (<= 8/32): wrong rate")
    a0 = cells[(cells.arm == "A") & (cells.rho == 0) & (cells.x0_n <= 8)]
    lines.append(a0.groupby(["rule", "alpha"]).agg(obs_wrong=("obs_wrong", "mean"), pred_wrong=("pred_wrong", "mean"),
                                                   obs_x8=("obs_mean_x8", "mean"), pred_x8=("pred_mean_x8", "mean")).round(3).to_string())
    lines.append("== surrogate vs observed, arm B, low x0 (<= 10/32)")
    b0 = cells[(cells.arm == "B") & (cells.x0_n <= 10)]
    lines.append(b0.groupby(["rule", "alpha"]).agg(obs_wrong=("obs_wrong", "mean"), pred_wrong=("pred_wrong", "mean"),
                                                   obs_x8=("obs_mean_x8", "mean"), pred_x8=("pred_mean_x8", "mean")).round(3).to_string())
    lines.append("== finite-horizon alpha* (20% rule)")
    lines.append(ast.to_string(index=False))
    lines.append("== observed per-claim low-x0 mean x8")
    lines.append(low.round(3).to_string(index=False))
    txt = "\n".join(lines)
    open(os.path.join(RES, "r34_summary.txt"), "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
