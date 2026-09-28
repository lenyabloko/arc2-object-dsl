"""Deterministic WAKE runner (run by WSL). One job = one frozen probe directory + a task set.
usage: python3 wake_eval.py <job.json> <out_dir>
job.json: {"job_id": "...", "probe": "tools/m1b/v13",            # dir holding gdsl.py and fam_*.py
           "families": null | ["fam_x", ...],                     # null = full gdsl; list = only these family modules
           "sets": ["train", "halfA"], "halfB_count": true, "timeout": 25}
Writes out_dir/results.jsonl (train + half A rows only) and out_dir/summary.json.
Half B is COUNTS ONLY: no half-B task id is ever written anywhere."""
import json, sys, os, re, signal, time, importlib, importlib.util
from multiprocessing import Pool
DATA = os.environ.get("ARC_DATA", "/kaggle/input/arc-prize-2026-arc-agi-2")
REPO = os.environ.get("ARC_REPO", os.path.expanduser("~/arc/arc2-object-dsl"))
job = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
probe = os.path.join(REPO, job["probe"]); sys.path.insert(0, probe)
import gdsl
if job.get("families"):
    fams = []
    for m in job["families"]:
        fams += list(importlib.import_module(m).FAMILIES)
    gdsl.FAMILIES = tuple(fams)
tr = json.load(open(f"{DATA}/arc-agi_training_challenges.json")); trs = json.load(open(f"{DATA}/arc-agi_training_solutions.json"))
ev = json.load(open(f"{DATA}/arc-agi_evaluation_challenges.json")); evs = json.load(open(f"{DATA}/arc-agi_evaluation_solutions.json"))
rd = lambda f: [x for x in re.split(r"[,\s]+", open(os.path.join(REPO, "tools/m1b", f)).read()) if x]
A, B = rd("deval_a.txt"), rd("deval_b.txt")
TO_S = int(job.get("timeout", 25))
class TO(Exception): pass
def one(k):
    ch, so = (tr, trs) if k in tr else (ev, evs)
    def h(*a): raise TO()
    signal.signal(signal.SIGALRM, h); signal.alarm(TO_S); t0 = time.time()
    try:
        res = gdsl.search(ch[k])
        ok = bool(res) and all(any(r["preds"][i] == so[k][i] for r in res[:2]) for i in range(len(so[k])))
        return {"task": k, "occupied": bool(res), "exact": ok, "progs": [r["program"] for r in res[:3]], "s": round(time.time() - t0, 2)}
    except TO: return {"task": k, "occupied": False, "exact": False, "progs": [], "timeout": True, "s": TO_S}
    except BaseException as e: return {"task": k, "occupied": False, "exact": False, "progs": [], "err": repr(e)[:80]}
    finally: signal.alarm(0)
if __name__ == "__main__":
    keys = (sorted(tr) if "train" in job["sets"] else []) + (A if "halfA" in job["sets"] else [])
    n = int(os.environ.get("WAKE_WORKERS", os.cpu_count() or 2))
    t0 = time.time()
    with Pool(n, maxtasksperchild=50) as p:
        R = p.map(one, keys, chunksize=4)
        RB = p.map(one, B, chunksize=4) if job.get("halfB_count") else []
    with open(os.path.join(out, "results.jsonl"), "w") as f:
        for r in R: f.write(json.dumps(r) + "\n")
    S = {"job_id": job["job_id"], "workers": n, "seconds": round(time.time() - t0),
         "train_exact": sum(r["exact"] for r in R if r["task"] in tr), "halfA_exact": sum(r["exact"] for r in R if r["task"] in A),
         "wrong_first": sum(r["occupied"] and not r["exact"] for r in R), "timeouts": sum(1 for r in R if r.get("timeout")),
         "halfB_exact_count": (sum(r["exact"] for r in RB) if RB else None), "halfB_n": len(B) if RB else None,
         "codex_ops_loaded": bool(__import__("codex_ops").load())}
    json.dump(S, open(os.path.join(out, "summary.json"), "w"), indent=1); print(S)
