"""Surrogate rollouts and one-step replay of the BLIND pooled rule (run on GX10).

The pre-registered prediction used the pooled Stage 1 coefficients (constant
weights, identified): variant A  c0 = 0.725, bT = 0.419, bF = -0.568 (arm A);
variant B  c0 = -0.758, theta = 1.909, bT = 0.291, bF = -0.326 (arm B).
This script rolls that rule on the realized graphs/seedings of every Stage 2
episode (finite N, eight rounds) so that Fig. 4a can show the finite-horizon
blind prediction band, and appends the results to results/r34_*.csv under
rule = "blind_pooled".

Usage: python scripts/53_blind_pooled_surrogate.py [PROJECT_ROOT]
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hmf_lib as H  # noqa: E402

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(HERE)
RES = os.path.join(ROOT, "results")
spec = importlib.util.spec_from_file_location("s52", os.path.join(HERE, "52_replay_surrogate_identified.py"))
s52 = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], ROOT]
spec.loader.exec_module(s52)


def blind_rule(arm):
    co = pd.read_csv(os.path.join(RES, "stage1_coeffs.csv"))
    c = co[co.variant == arm].set_index("coef").estimate
    th = float(c.theta) if arm == "B" else 0.0

    def rule(claim_id, k, l, s):
        return H.sig(c.c0 + th * s + c.beta_T * l + c.beta_F * (k - l))
    return rule


def main():
    rules = {"blind_pooled": {"A": blind_rule("A"), "B": blind_rule("B")}}
    df, eps = s52.load_episodes()
    df["correct"] = (df.x8 >= 0.5 + s52.DELTA).astype(float)
    df["wrong"] = (df.x8 <= 0.5 - s52.DELTA).astype(float)
    cal_rows, cell_rows = [], []
    for rname, byarm in rules.items():
        cal, roll = [], []
        for name, d in eps.items():
            arm = d["meta"]["arm"]
            rule = byarm[arm]
            cal += [{**r, "alpha": d["meta"]["alpha"], "arm": arm, "name": name} for r in s52.one_step(d, rule)]
            roll.append({"name": name, **s52.surrogate(d, rule)})
        cal = pd.DataFrame(cal)
        for (arm, a), sub in cal.groupby(["arm", "alpha"]):
            p, y = sub.p_pred.to_numpy(), sub.y_next.to_numpy(float)
            contested = sub[(sub.k > 0) & (sub.l / sub.k >= 0.4) & (sub.l / sub.k <= 0.6)]
            cal_rows.append({"rule": rname, "arm": arm, "alpha": a, "n_transitions": len(sub),
                             "brier": float(((p - y) ** 2).mean()),
                             "brier_climatology": float(y.mean() * (1 - y.mean())),
                             "ece": s52.ece(p, y), "mean_resid": float((y - p).mean()),
                             "mean_resid_contested": float((contested.y_next - contested.p_pred).mean()) if len(contested) else np.nan,
                             "n_contested": len(contested)})
        m = df.merge(pd.DataFrame(roll), on="name")
        for (arm, a, rho, x0n), sub in m.groupby(["arm", "alpha", "rho", "x0_n"]):
            cell_rows.append({"rule": rname, "arm": arm, "alpha": a, "rho": rho, "x0_n": x0n, "x0": x0n / 32,
                              "n": len(sub), "obs_q": sub.correct.mean(), "obs_wrong": sub.wrong.mean(),
                              "obs_mean_x8": sub.x8.mean(), "pred_q": sub.q_roll.mean(),
                              "pred_wrong": sub.wrong_roll.mean(), "pred_mean_x8": sub.mean_x8_roll.mean()})
    for fname, new in [("r34_onestep_calibration.csv", pd.DataFrame(cal_rows)),
                       ("r34_surrogate_cells.csv", pd.DataFrame(cell_rows))]:
        p = os.path.join(RES, fname)
        old = pd.read_csv(p)
        old = old[old.rule != "blind_pooled"]
        pd.concat([old, new], ignore_index=True).to_csv(p, index=False)
        print("updated", fname, "with", len(new), "blind_pooled rows")
    cells = pd.DataFrame(cell_rows)
    a0 = cells[(cells.arm == "A") & (cells.rho == 0) & (cells.x0_n <= 8)].groupby("alpha").agg(
        obs_wrong=("obs_wrong", "mean"), pred_wrong=("pred_wrong", "mean"))
    print("blind pooled rule, arm A low x0 wrong rate (obs vs surrogate):\n", a0.round(3))
    print("finite-horizon alpha* (20% rule) of the blind rule:",
          s52.alpha_star_20pct(cells[(cells.arm == "A") & (cells.rho == 0)], "pred_wrong"))


if __name__ == "__main__":
    main()
