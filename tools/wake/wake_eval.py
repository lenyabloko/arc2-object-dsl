"""Deterministic WAKE runner (run by WSL). One job = one frozen probe directory + a task set.
usage: python3 wake_eval.py <job.json> <out_dir>
job.json: {"job_id": "...", "probe": "tools/m1b/v13",            # dir holding gdsl.py and fam_*.py
           "families": null | ["fam_x", ...],                     # null = full gdsl; list = only these family modules
           "sets": ["train", "halfA"], "halfB_count": false, "timeout": 25}
Writes out_dir/results.jsonl (train + half A rows only) and out_dir/summary.json.
Half B is COUNTS ONLY: no half-B task id is ever written anywhere."""
import json, sys, os, re, signal, time, importlib, importlib.util
from multiprocessing import Pool
DATA = os.environ.get("ARC_DATA", "/kaggle/input/arc-prize-2026-arc-agi-2")
REPO = os.environ.get("ARC_REPO", os.path.expanduser("~/arc/arc2-object-dsl"))
job = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
if job.get("mode") == "parity":           # full-probe parity + timing on the public eval (as the Kaggle notebook)
    if os.environ.get("PYTHONHASHSEED") != "0":   # same hash seed as the Kaggle notebook, or set order (and the digest) changes
        os.execvpe(sys.executable, [sys.executable] + sys.argv, dict(os.environ, PYTHONHASHSEED="0", OMP_NUM_THREADS="1"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import parity_eval; parity_eval.run(job, out, REPO, DATA); sys.exit(0)
if job.get("mode") == "full":             # cycle 21: full probe (lattice + G, Kaggle attempt ordering) on train + half A
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.execvpe(sys.executable, [sys.executable] + sys.argv, dict(os.environ, PYTHONHASHSEED="0", OMP_NUM_THREADS="1"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import full_eval; full_eval.run(job, out, REPO, DATA); sys.exit(0)
probe = os.path.join(REPO, job["probe"]); sys.path.insert(0, probe)
import gdsl, hashlib
ENGINE = None
if job.get("engine"):          # composition engine module (defines SEARCH(task)) instead of the plain library search
    spec = importlib.util.spec_from_file_location("engine_mod", os.path.join(REPO, job["engine"]))
    ENGINE = importlib.util.module_from_spec(spec); spec.loader.exec_module(ENGINE)
if job.get("families"):
    fams = []
    for m in job["families"]:
        fams += list(importlib.import_module(m).FAMILIES)
    gdsl.FAMILIES = tuple(fams)
tr = json.load(open(f"{DATA}/arc-agi_training_challenges.json")); trs = json.load(open(f"{DATA}/arc-agi_training_solutions.json"))
ev = json.load(open(f"{DATA}/arc-agi_evaluation_challenges.json")); evs = json.load(open(f"{DATA}/arc-agi_evaluation_solutions.json"))
rd = lambda f: [x for x in re.split(r"[,\s]+", open(os.path.join(REPO, "tools/m1b", f)).read()) if x]
A, B = rd("deval_a.txt"), rd("deval_b.txt")
N2 = set(rd("novel_N2.txt")) if os.path.exists(os.path.join(REPO, "tools/m1b", "novel_N2.txt")) else set()
TO_S = int(job.get("timeout", 25))
class TO(Exception): pass
def one(k):
    ch, so = (tr, trs) if k in tr else (ev, evs)
    def h(*a): raise TO()
    signal.signal(signal.SIGALRM, h); signal.alarm(TO_S); t0 = time.time()
    try:
        res = ENGINE.SEARCH(ch[k]) if ENGINE else gdsl.search(ch[k])
        ok = bool(res) and all(any(r["preds"][i] == so[k][i] for r in res[:2]) for i in range(len(so[k])))
        return {"task": k, "occupied": bool(res), "exact": ok, "progs": [r["program"] for r in res[:3]], "s": round(time.time() - t0, 2),
                "ph": hashlib.sha256(json.dumps([r["preds"] for r in res[:2]], sort_keys=True).encode()).hexdigest()[:16]}
    except TO: return {"task": k, "occupied": False, "exact": False, "progs": [], "timeout": True, "s": TO_S}
    except BaseException as e: return {"task": k, "occupied": False, "exact": False, "progs": [], "err": repr(e)[:80]}
    finally: signal.alarm(0)
if __name__ == "__main__":
    keys = (sorted(tr) if "train" in job["sets"] else []) + (A if "halfA" in job["sets"] else [])
    if job.get("limit"): keys = keys[:int(job["limit"])]
    n = int(os.environ.get("WAKE_WORKERS", os.cpu_count() or 2))
    t0 = time.time()
    with Pool(n, maxtasksperchild=50) as p:
        R = p.map(one, keys, chunksize=4)
        # decision OQ7 (Len, 2026-09-30): half B is DESIGN (the 99 Codex-fitted public tasks = half A + half B)
        RB = p.map(one, B, chunksize=4) if ("halfB" in job["sets"] or job.get("halfB_count")) else []
    with open(os.path.join(out, "results.jsonl"), "w") as f:
        for r in R + RB:
            if r["task"] not in N2: f.write(json.dumps(r) + "\n")   # N2 validation split: counts only
    import hashlib as _h
    SALT = "arc2-c21-2026-09-29"            # Fable guidance v1, B.4: N2 gate / decide split; decision set sealed
    gate = {k for k in N2 if int(_h.sha256((SALT + k).encode()).hexdigest()[:2], 16) % 2 == 0}
    S = {"job_id": job["job_id"], "workers": n, "seconds": round(time.time() - t0),
         "train_exact": sum(r["exact"] for r in R if r["task"] in tr and r["task"] not in N2),
         "N2_gate_n": len(gate), "N2_salt": SALT, "halfA_exact": sum(r["exact"] for r in R if r["task"] in A),
         "wrong_first": sum(r["occupied"] and not r["exact"] for r in R if r["task"] not in N2), "timeouts": sum(1 for r in R if r.get("timeout")),
         "halfB_exact": (sum(r["exact"] for r in RB) if RB else None), "halfB_fit": (sum(r["occupied"] for r in RB) if RB else None),
         "halfB_n": (len(B) if RB else None),
         "decision_set": "sealed: decide_sealed.json (N2-decide; Nov 1 look, OQ7)", "codex_ops_loaded": bool(__import__("codex_ops").load())}
    json.dump({"N2_decide_exact_count": sum(r["exact"] for r in R if r["task"] in N2 and r["task"] not in gate), "N2_decide_n": len(N2 - gate)},
              open(os.path.join(out, "decide_sealed.json"), "w"), indent=1)
    HID_SALT = os.environ.get("N2_HID_SALT") or (open(os.path.expanduser("~/arc/.hid_salt")).read().strip() if os.path.exists(os.path.expanduser("~/arc/.hid_salt")) else "")
    # Fable v3 A.2: no record without the secret salt (create ~/arc/.hid_salt once, see tools/wake/WAKE.md)
    with open(os.path.join(out, "n2_gate_private.jsonl.txt" if HID_SALT else "n2_gate_private_SKIPPED_no_salt.txt"), "w") as f:
        for r in sorted(R, key=lambda r: _h.sha256((HID_SALT + r["task"]).encode()).hexdigest()):
            if HID_SALT and r["task"] in gate:
                f.write(json.dumps({"hid": _h.sha256((HID_SALT + r["task"]).encode()).hexdigest()[:16], "exact": r["exact"], "ph": r.get("ph")}) + "\n")
    json.dump(S, open(os.path.join(out, "summary.json"), "w"), indent=1); print(S)
