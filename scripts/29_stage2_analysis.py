"""Stage 2 step 7: analysis.

Reads data/stage2/episodes/*.json (trial_* excluded). Produces:
- results/stage2_committor.csv        (arm, alpha, x0, q, Wilson CI, n)
- results/stage2_alpha_star_emp.csv   (empirical alpha* from low-x0 wrong rate)
- results/stage2_rule_discrimination.csv  (arm B criteria)
- results/stage2_onestep_calibration.csv  (Brier / calibration by alpha)
- results/stage2_rho_control.csv
- fig/stage2_committor_family.png, fig/stage2_alpha_star.png

Uncertainty: claim-cluster pairs bootstrap (only 4 claims — coarse; episode
iid bootstrap reported alongside, labeled).
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP_DIR = os.path.join(ROOT, "data", "stage2", "episodes")
RNG = np.random.default_rng(5)
DELTA = 0.10
N_BOOT = 2000
N_ROLL = 200

# ---------- per-k rule from Stage 1 (variant A, claim FE) ----------

def stage1_perk_rule():
    """Fit per-k (beta_T, beta_F) + claim FE on Stage 1 variant A data.
    Returns (fe_by_claim, k_grid, bT, bF, interp fn)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "a14", os.path.join(ROOT, "scripts", "14_analysis.py"))
    a14 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a14)
    df = pd.read_parquet(os.path.join(ROOT, "data", "stage1",
                                      "main_obs.parquet"))
    claim_ids = sorted(df.claim_id.unique())
    sub = df[df.self_state == "none"]
    S_C, S_W = a14.counts_drives(sub)
    X = a14.design(sub, claim_ids, S_C, S_W, with_self=False)
    b = a14.fit_logit(X, sub.y.to_numpy(float))
    fe = dict(zip(claim_ids, b[:len(claim_ids)]))
    ks, bT, bF = [], [], []
    for k in [1, 2, 3, 5, 8, 12]:
        sk = sub[sub.k == k]
        Xk = a14.design(sk, claim_ids, *a14.counts_drives(sk), False)
        keep = Xk.sum(0) > 0
        bk = a14.fit_logit(Xk[:, keep], sk.y.to_numpy(float))
        ks.append(k); bT.append(bk[-2]); bF.append(bk[-1])
    ks = np.array(ks, float); bT = np.array(bT); bF = np.array(bF)

    def coef(k, extrap="power"):
        """log-log interpolation; power or flat extrapolation beyond k=12."""
        if k <= 0:
            return 0.0, 0.0
        lk = np.log(k)
        lks = np.log(ks)
        if k <= 12:
            t = np.interp(lk, lks, np.log(bT))
            f = np.interp(lk, lks, np.log(-bF))
            return float(np.exp(t)), -float(np.exp(f))
        if extrap == "flat":
            return float(bT[-1]), float(bF[-1])
        st = (np.log(bT[-1]) - np.log(bT[-2])) / (lks[-1] - lks[-2])
        sf = (np.log(-bF[-1]) - np.log(-bF[-2])) / (lks[-1] - lks[-2])
        return (float(np.exp(np.log(bT[-1]) + st * (lk - lks[-1]))),
                -float(np.exp(np.log(-bF[-1]) + sf * (lk - lks[-1]))))
    return fe, ks, bT, bF, coef


def sig(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


# ---------- load episodes ----------

def load_episodes():
    rows, graphs = [], {}
    for fp in sorted(glob.glob(os.path.join(EP_DIR, "*.json"))):
        name = os.path.basename(fp)[:-5]
        if name.startswith("trial"):
            continue
        d = json.load(open(fp))
        m = d["meta"]
        S = np.array(d["stance_history"], float)   # (9, 32)
        x = S.mean(axis=1)
        rows.append({
            "name": name, "block": m["block"], "arm": m["arm"],
            "alpha": m["alpha"], "x0_n": m["x0_n"], "x0": m["x0_n"] / 32,
            "claim_id": m["claim_id"], "rep": m["rep"], "rho": m.get("rho", 0),
            "spin_samples": m.get("spin_samples", 1),
            "x8": x[8], "n_parse_fail": m["n_parse_fail"],
            **{f"x{t}": x[t] for t in range(9)},
        })
        graphs[name] = d
    return pd.DataFrame(rows), graphs


def outcome(x8, delta=DELTA):
    if x8 >= 0.5 + delta:
        return "correct"
    if x8 <= 0.5 - delta:
        return "wrong"
    return "undecided"


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan, np.nan
    p = k / n
    den = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / den
    hw = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / den
    return p, c - hw, c + hw


def cluster_boot_q(sub, col="correct", n_boot=N_BOOT):
    """Pairs bootstrap over claims of mean(col). Returns (lo, hi)."""
    cids = sub.claim_id.unique()
    if len(cids) < 2:
        return np.nan, np.nan
    groups = [sub[sub.claim_id == c][col].to_numpy() for c in cids]
    est = []
    for _ in range(n_boot):
        idx = RNG.integers(0, len(groups), len(groups))
        v = np.concatenate([groups[i] for i in idx])
        if len(v):
            est.append(v.mean())
    return tuple(np.percentile(est, [2.5, 97.5]))


# ---------- surrogate rollout on the actual graphs ----------

def surrogate_rollout(d, fe, coef, extrap, n_roll=N_ROLL, rng=None):
    """Roll the Stage 1 per-k rule on this episode's actual graph and initial
    assignment. Returns fraction of rollouts ending correct (delta rule)."""
    rng = rng or np.random.default_rng(0)
    acc = d["graph"]["accepted"]
    n = len(acc)
    h = fe[d["meta"]["claim_id"]]
    ks = [len(a) for a in acc]
    coefs = {k: coef(k, extrap) for k in set(ks)}
    s0 = np.zeros(n)
    s0[d["x0_assignment"]] = 1.0
    S = np.tile(s0, (n_roll, 1))                     # (R, n)
    for t in range(8):
        P = np.empty_like(S)
        for j in range(n):
            k = ks[j]
            if k == 0:
                P[:, j] = sig(h)
                continue
            bT, bF = coefs[k]
            l = S[:, acc[j]].sum(axis=1)
            P[:, j] = sig(h + bT * l + bF * (k - l))
        S = (rng.random(S.shape) < P).astype(float)
    x8 = S.mean(axis=1)
    return {"q_roll": float((x8 >= 0.5 + DELTA).mean()),
            "wrong_roll": float((x8 <= 0.5 - DELTA).mean())}


# ---------- one-step calibration ----------

def one_step(d, fe, coef, extrap="power"):
    """Predicted P(next=correct) vs observed transition for every
    (agent, round) from the actual inbox stance composition."""
    S = np.array(d["stance_history"], int)
    h = fe[d["meta"]["claim_id"]]
    out = []
    for rec in d["spin_log"]:
        t, j = rec["round"], rec["agent"]
        k = len(rec["sources"])
        l = rec["order_stances"].count("C")
        if k == 0:
            p = sig(h)
        else:
            bT, bF = coef(k, extrap)
            p = sig(h + bT * l + bF * (k - l))
        out.append({"round": t, "agent": j, "k": k, "l": l,
                    "p_pred": float(p), "y_next": int(S[t][j])})
    return out


# ---------- main ----------

def main(min_reps=1):
    fe, ks, bT_k, bF_k, coef = stage1_perk_rule()
    print("per-k rule: k", ks.astype(int).tolist(),
          "bT", np.round(bT_k, 3).tolist(), "bF", np.round(bF_k, 3).tolist())
    df, graphs = load_episodes()
    if not len(df):
        print("no episodes yet"); return
    for delta, tag in [(0.05, "d05"), (0.10, "d1"), (0.20, "d2")]:
        df[f"outcome_{tag}"] = df.x8.apply(lambda v: outcome(v, delta))
    df["correct"] = (df.outcome_d1 == "correct").astype(float)
    df["wrong"] = (df.outcome_d1 == "wrong").astype(float)
    print(f"{len(df)} episodes loaded")
    print(df.groupby(["block", "arm", "alpha"]).size())

    # ----- committor family -----
    rows = []
    for (arm, alpha, rho, x0n), sub in df[df.spin_samples == 1].groupby(
            ["arm", "alpha", "rho", "x0_n"]):
        k = int(sub.correct.sum()); n = len(sub)
        q, lo, hi = wilson(k, n)
        blo, bhi = cluster_boot_q(sub)
        rows.append({"arm": arm, "alpha": alpha, "rho": rho, "x0_n": x0n,
                     "x0": x0n / 32, "n": n, "q": q,
                     "wilson_lo": lo, "wilson_hi": hi,
                     "claimboot_lo": blo, "claimboot_hi": bhi,
                     "undecided": float((sub.outcome_d1 == "undecided").mean()),
                     "q_d05": float((sub.outcome_d05 == "correct").mean()),
                     "q_d2": float((sub.outcome_d2 == "correct").mean()),
                     "q_excl_und": (sub.correct.sum()
                                    / max((sub.outcome_d1 != "undecided").sum(), 1))})
    com = pd.DataFrame(rows).sort_values(["arm", "rho", "alpha", "x0_n"])
    com.to_csv(os.path.join(ROOT, "results", "stage2_committor.csv"),
               index=False)

    # ----- empirical alpha* (arm A, rho=0): wrong rate at x0 <= 8/32 -----
    armA = df[(df.arm == "A") & (df.rho == 0) & (df.spin_samples == 1)]
    low = armA[armA.x0_n <= 8]
    ast_rows = []
    for alpha, sub in low.groupby("alpha"):
        w = sub.wrong.mean()
        blo, bhi = cluster_boot_q(sub, "wrong")
        ast_rows.append({"alpha": alpha, "n": len(sub), "wrong_rate": w,
                         "ci_lo": blo, "ci_hi": bhi})
    ast = pd.DataFrame(ast_rows).sort_values("alpha")
    # threshold crossing at 20% (linear interp between grid points)
    a_star_emp = np.nan
    aa, ww = ast.alpha.to_numpy(), ast.wrong_rate.to_numpy()
    for i in range(len(aa) - 1):
        if (ww[i] - 0.2) * (ww[i + 1] - 0.2) < 0:
            a_star_emp = aa[i] + (0.2 - ww[i]) * (aa[i + 1] - aa[i]) / (
                ww[i + 1] - ww[i])
            break
    # bootstrap the crossing over claims
    boots = []
    cids = low.claim_id.unique()
    groups = {a: [low[(low.alpha == a) & (low.claim_id == c)].wrong.to_numpy()
                  for c in cids] for a in aa}
    for _ in range(N_BOOT):
        idx = RNG.integers(0, len(cids), len(cids))
        wr = []
        for a in aa:
            v = np.concatenate([groups[a][i] for i in idx])
            wr.append(v.mean() if len(v) else np.nan)
        cross = np.nan
        for i in range(len(aa) - 1):
            if np.isfinite(wr[i]) and np.isfinite(wr[i + 1]) and \
                    (wr[i] - 0.2) * (wr[i + 1] - 0.2) < 0:
                cross = aa[i] + (0.2 - wr[i]) * (aa[i + 1] - aa[i]) / (
                    wr[i + 1] - wr[i])
                break
        boots.append(cross)
    boots = np.array([b for b in boots if np.isfinite(b)])
    ast["a_star_emp"] = a_star_emp
    ast["a_star_ci_lo"] = (np.percentile(boots, 2.5)
                           if len(boots) > 100 else np.nan)
    ast["a_star_ci_hi"] = (np.percentile(boots, 97.5)
                           if len(boots) > 100 else np.nan)
    ast["n_boot_crossing"] = len(boots)
    ast.to_csv(os.path.join(ROOT, "results", "stage2_alpha_star_emp.csv"),
               index=False)
    print(f"\nalpha*_emp = {a_star_emp} "
          f"(crossings in {len(boots)}/{N_BOOT} bootstraps)")
    print(ast[["alpha", "n", "wrong_rate", "ci_lo", "ci_hi"]].to_string(
        index=False))

    # ----- arm B discrimination -----
    armB = df[(df.arm == "B") & (df.spin_samples == 1)]
    rdb = []
    for alpha, sub in armB[armB.x0_n <= 10].groupby("alpha"):
        w = sub.wrong.mean()
        blo, bhi = cluster_boot_q(sub, "wrong")
        rdb.append({"alpha": alpha, "n": len(sub),
                    "wrong_rate_lowx0": w, "ci_lo": blo, "ci_hi": bhi,
                    "absorbing": w > 0.20})
    rdbdf = pd.DataFrame(rdb).sort_values("alpha") if rdb else pd.DataFrame()
    if len(rdbdf):
        pattern = tuple(rdbdf.absorbing)
        verdict = ("constant-rule (no absorption anywhere)"
                   if not any(pattern) else
                   "saturating-rule (absorption up to 0.9+)"
                   if len(pattern) >= 2 and pattern[0] and pattern[1] else
                   "intermediate (absorption only at 0.6)"
                   if pattern[0] else "unclassified")
        rdbdf["verdict"] = verdict
        rdbdf.to_csv(os.path.join(
            ROOT, "results", "stage2_rule_discrimination.csv"), index=False)
        print("\narm B:", verdict)
        print(rdbdf.to_string(index=False))

    # ----- rho control -----
    r0 = com[(com.arm == "A") & (com.alpha == 0.30) & (com.rho == 0)]
    r1 = com[(com.arm == "A") & (com.alpha == 0.30) & (com.rho == 1)]
    if len(r1):
        mg = r0.merge(r1, on="x0_n", suffixes=("_rho0", "_rho1"))
        mg["dq"] = mg.q_rho1 - mg.q_rho0
        mg[["x0_n", "n_rho0", "q_rho0", "n_rho1", "q_rho1", "dq"]].to_csv(
            os.path.join(ROOT, "results", "stage2_rho_control.csv"),
            index=False)
        print("\nrho control (alpha=0.30):")
        print(mg[["x0_n", "q_rho0", "q_rho1", "dq"]].to_string(index=False))

    # ----- surrogate rollout + one-step calibration -----
    roll_rows, cal_rows = [], []
    rng = np.random.default_rng(9)
    for name, d in graphs.items():
        m = d["meta"]
        if m.get("spin_samples", 1) != 1 or m["arm"] != "A":
            continue
        rr = surrogate_rollout(d, fe, coef, "power", rng=rng)
        roll_rows.append({"name": name, "alpha": m["alpha"],
                          "x0_n": m["x0_n"], "rho": m.get("rho", 0),
                          "claim_id": m["claim_id"], **rr})
        cal_rows += [{**r, "alpha": m["alpha"], "name": name}
                     for r in one_step(d, fe, coef)]
    roll = pd.DataFrame(roll_rows)
    roll.to_csv(os.path.join(ROOT, "results", "stage2_surrogate_roll.csv"),
                index=False)
    cal = pd.DataFrame(cal_rows)
    cal_out = []
    for alpha, sub in cal.groupby("alpha"):
        brier = float(((sub.p_pred - sub.y_next) ** 2).mean())
        base = sub.y_next.mean()
        brier_clim = float(base * (1 - base))
        bins = pd.cut(sub.p_pred, np.linspace(0, 1, 11))
        rel = sub.groupby(bins, observed=True).agg(
            p=("p_pred", "mean"), o=("y_next", "mean"), n=("y_next", "size"))
        ece = float((rel.n * (rel.p - rel.o).abs()).sum() / rel.n.sum())
        cal_out.append({"alpha": alpha, "n_transitions": len(sub),
                        "brier": brier, "brier_climatology": brier_clim,
                        "ece": ece})
    pd.DataFrame(cal_out).to_csv(
        os.path.join(ROOT, "results", "stage2_onestep_calibration.csv"),
        index=False)
    print("\none-step calibration:")
    print(pd.DataFrame(cal_out).round(4).to_string(index=False))

    # ----- figures -----
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    A = com[(com.arm == "A") & (com.rho == 0)]
    colors = plt.cm.viridis(np.linspace(0, 0.95, A.alpha.nunique()))
    for c, (alpha, sub) in zip(colors, A.groupby("alpha")):
        yerr = [np.clip(sub.q - sub.wilson_lo, 0, None),
                np.clip(sub.wilson_hi - sub.q, 0, None)]
        axes[0].errorbar(sub.x0, sub.q, yerr=yerr, fmt="o-", color=c,
                         capsize=3, label=f"α={alpha}")
        if len(roll):
            rsub = roll[(roll.alpha == alpha) & (roll.rho == 0)].groupby(
                "x0_n").q_roll.mean()
            axes[0].plot(rsub.index / 32, rsub.values, "--", color=c,
                         alpha=0.6)
    axes[0].axhline(0.5, color="gray", ls=":", lw=1)
    axes[0].set_xlabel("x0"); axes[0].set_ylabel("q (correct, δ=0.1)")
    axes[0].set_title("arm A committor family (solid=obs, dashed=surrogate)")
    axes[0].legend(fontsize=8)
    axes[1].errorbar(ast.alpha, ast.wrong_rate,
                     yerr=[np.clip(ast.wrong_rate - ast.ci_lo, 0, None),
                           np.clip(ast.ci_hi - ast.wrong_rate, 0, None)],
                     fmt="o-", color="k", capsize=3)
    axes[1].axhline(0.2, color="crimson", ls="--", lw=1,
                    label="threshold 20%")
    if np.isfinite(a_star_emp):
        axes[1].axvline(a_star_emp, color="crimson", lw=1)
    axes[1].axvspan(0.40, 0.46, color="steelblue", alpha=0.15,
                    label="predicted α* 0.43±0.03")
    axes[1].set_xlabel("α"); axes[1].set_ylabel("wrong-consensus rate, x0≤8/32")
    axes[1].set_title("empirical α*")
    axes[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(ROOT, "fig", "stage2_committor_family.png"),
                dpi=150)
    plt.close(fig)

    fig2, ax = plt.subplots(figsize=(6, 5))
    ax.errorbar(ast.alpha, ast.wrong_rate,
                yerr=[np.clip(ast.wrong_rate - ast.ci_lo, 0, None),
                      np.clip(ast.ci_hi - ast.wrong_rate, 0, None)],
                fmt="o-", color="k", capsize=3, label="observed")
    if len(roll):
        rlow = roll[(roll.x0_n <= 8) & (roll.rho == 0)].groupby(
            "alpha").wrong_roll.mean()
        ax.plot(rlow.index, rlow.values, "s--", color="tab:blue",
                label="surrogate rollout")
    ax.axhline(0.2, color="crimson", ls="--", lw=1)
    ax.axvspan(0.40, 0.46, color="steelblue", alpha=0.15)
    ax.set_xlabel("α"); ax.set_ylabel("wrong-consensus rate (x0 ≤ 8/32)")
    ax.legend(); fig2.tight_layout()
    fig2.savefig(os.path.join(ROOT, "fig", "stage2_alpha_star.png"), dpi=150)
    plt.close(fig2)
    print("\nfigures written")


if __name__ == "__main__":
    main()
