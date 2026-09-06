"""Stage 2 episode engine.

One episode = 32 llama3.1:8b agents, 8 rounds on an attention-generated
directed network, exogenous x0 assignment, El et al.-style round structure
(message phase -> spin phase), single-sample spins (5-sample for fidelity).

Uses the user ollama instance on port 11435 (OLLAMA_NUM_PARALLEL=16).
Prompts are verbatim Stage 1 wording (scripts/12 GEN_TMPL, scripts/13
PROMPT_TMPL) — no changes.
"""
import hashlib
import json
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EP_DIR = os.path.join(ROOT, "data", "stage2", "episodes")
URL = "http://127.0.0.1:11435/api/generate"
MODEL = os.environ.get("S2_MODEL", "llama3.1:8b")
TEMPERATURE = 0.7
N_AGENTS = 32
N_ROUNDS = 8
PHASE_CONC = 12

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

SPIN_TMPL = (
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


def parse_ab(response):
    text = response.strip().upper()
    if text in ("A", "B"):
        return text
    tokens = set(re.findall(r"\b([AB])\b", text))
    if tokens == {"A"}:
        return "A"
    if tokens == {"B"}:
        return "B"
    return None


def _call(prompt, seed, num_predict):
    payload = {
        "model": MODEL, "prompt": prompt, "stream": False,
        "options": {"temperature": TEMPERATURE, "num_predict": num_predict,
                    "seed": int(seed)},
    }
    if os.environ.get("S2_NOTHINK"):
        payload["think"] = False
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        URL, data=body, headers={"Content-Type": "application/json"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                return json.loads(r.read())["response"]
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2.0)
    raise RuntimeError(f"ollama call failed 3x: {last}")


def gen_network(alpha, rng):
    """Directed attention network: receiver j walks a uniform random order of
    the other 31, accepting the next candidate w.p. e^{-alpha*r} after r
    accepted. Returns accepted lists and candidate orders."""
    accepted, orders = [], []
    for j in range(N_AGENTS):
        cands = [i for i in range(N_AGENTS) if i != j]
        rng.shuffle(cands)
        acc = []
        for c in cands:
            if rng.random() < np.exp(-alpha * len(acc)):
                acc.append(c)
        accepted.append(acc)
        orders.append(cands)
    return accepted, orders


def rewire_indegree_preserving(accepted, rng):
    """rho = 1: keep each receiver's in-degree, resample senders uniformly."""
    out = []
    for j, acc in enumerate(accepted):
        pool = [i for i in range(N_AGENTS) if i != j]
        out.append([int(x) for x in
                    rng.choice(pool, size=len(acc), replace=False)])
    return out


def run_episode(spec, claims_df):
    """spec: dict(name, arm, alpha, x0_n, claim_id, rep, rho, spin_samples,
    seed). Writes EP_DIR/name.json (atomic). Returns wall seconds."""
    t_start = time.time()
    os.makedirs(EP_DIR, exist_ok=True)
    out_path = os.path.join(EP_DIR, spec["name"] + ".json")
    if os.path.exists(out_path):
        return 0.0
    rng = np.random.default_rng(spec["seed"])
    crow = claims_df[claims_df.claim_id == spec["claim_id"]].iloc[0]
    claim, truth = crow.claim, crow.truth      # truth: "TRUE"/"FALSE"
    wrong = "FALSE" if truth == "TRUE" else "TRUE"

    personas = [PERSONAS[int(rng.integers(len(PERSONAS)))]
                for _ in range(N_AGENTS)]
    accepted, orders = gen_network(spec["alpha"], rng)
    graph_note = "generated"
    if spec.get("rho"):
        accepted = rewire_indegree_preserving(accepted, rng)
        graph_note = "rewired_rho1"

    # exogenous x0: stance 1 = correct side, 0 = wrong side
    s = np.zeros(N_AGENTS, dtype=int)
    correct_idx = rng.choice(N_AGENTS, size=spec["x0_n"], replace=False)
    s[correct_idx] = 1
    stance_hist = [s.tolist()]
    msg_hist, spin_log = [], []
    n_parse_fail = 0

    for t in range(1, N_ROUNDS + 1):
        # ----- message phase -----
        has_out = set()
        for j in range(N_AGENTS):
            has_out.update(accepted[j])
        def gen_one(i):
            if i not in has_out:
                return None
            stance_word = truth if s[i] == 1 else wrong
            prompt = GEN_TMPL.format(persona=personas[i], claim=claim,
                                     stance=stance_word)
            resp = _call(prompt, msg_seeds[i], 120)
            return " ".join(resp.strip().split()).strip('"').strip()
        msg_seeds = rng.integers(1, 2**31, size=N_AGENTS)
        with ThreadPoolExecutor(PHASE_CONC) as ex:
            messages = list(ex.map(gen_one, range(N_AGENTS)))
        msg_hist.append(messages)

        # ----- spin phase -----
        spin_seeds = rng.integers(1, 2**31, size=(N_AGENTS, 5))
        inbox_orders, assigns = [], []
        for j in range(N_AGENTS):
            srcs = list(accepted[j])
            rng.shuffle(srcs)
            inbox_orders.append(srcs)
            assigns.append("TF" if rng.random() < 0.5 else "FT")

        def spin_one(j):
            srcs = inbox_orders[j]
            msgs = [messages[i] for i in srcs]
            inbox = ("(no messages)" if not msgs
                     else "\n".join(f"- {m}" for m in msgs))
            if spec["arm"] == "B":
                x_word = truth if s[j] == 1 else wrong
                selfline = ("# Your Current Answer\nYour current answer is "
                            f"that the claim is {x_word}.\n\n")
            else:
                selfline = ""
            asg = assigns[j]
            oa, ob = (("TRUE", "FALSE") if asg == "TF" else ("FALSE", "TRUE"))
            prompt = SPIN_TMPL.format(persona=personas[j], inbox=inbox,
                                      selfline=selfline, claim=claim,
                                      option_A=oa, option_B=ob)
            votes, raw = [], []
            for samp in range(spec["spin_samples"]):
                resp = _call(prompt, spin_seeds[j][samp], 3)
                p = parse_ab(resp)
                if p is None:   # one retry with shifted seed
                    resp = _call(prompt, spin_seeds[j][samp] + 10**6, 3)
                    p = parse_ab(resp)
                raw.append(resp)
                if p is not None:
                    chosen = "TRUE" if (p == "A") == (asg == "TF") else "FALSE"
                    votes.append(1 if chosen == truth else 0)
                else:
                    votes.append(None)
            ok = [v for v in votes if v is not None]
            if not ok:
                new = int(s[j])   # keep previous stance on total failure
                fail = True
            elif len(ok) == 1:
                new, fail = ok[0], False
            else:  # majority vote; tie broken by the first valid sample
                if 2 * sum(ok) > len(ok):
                    new = 1
                elif 2 * sum(ok) < len(ok):
                    new = 0
                else:
                    new = ok[0]
                fail = False
            return j, new, {
                "agent": j, "round": t, "sources": srcs, "assign": asg,
                "order_stances": "".join(
                    "C" if s[i] == 1 else "W" for i in srcs),
                "votes": votes, "raw": raw, "parse_fail": fail,
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "seeds": [int(x) for x in
                          spin_seeds[j][:spec["spin_samples"]]],
            }
        with ThreadPoolExecutor(PHASE_CONC) as ex:
            results = list(ex.map(spin_one, range(N_AGENTS)))
        new_s = s.copy()
        for j, new, logrec in results:
            new_s[j] = new
            n_parse_fail += int(logrec["parse_fail"])
            spin_log.append(logrec)
        s = new_s
        stance_hist.append(s.tolist())

    out = {
        "meta": {**{k: (v if not isinstance(v, np.integer) else int(v))
                    for k, v in spec.items()},
                 "claim": claim, "truth": truth,
                 "model": MODEL, "temperature": TEMPERATURE,
                 "n_agents": N_AGENTS, "n_rounds": N_ROUNDS,
                 "n_parse_fail": n_parse_fail,
                 "wall_s": round(time.time() - t_start, 1)},
        "personas": personas,
        "graph": {"accepted": accepted, "candidate_orders": orders,
                  "note": graph_note},
        "x0_assignment": sorted(int(i) for i in correct_idx),
        "stance_history": stance_hist,       # 9 x 32, 1 = correct side
        "messages": msg_hist,                # 8 x 32 (None if no out-edge)
        "spin_log": spin_log,
    }
    tmp = out_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(out, f, ensure_ascii=False)
    os.replace(tmp, out_path)
    return time.time() - t_start
