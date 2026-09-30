"""Full-probe evaluation (lattice + G-DSL, the Kaggle attempt ordering) on training + half A, with N2 and half B
as counts only. Called by wake_eval.py for jobs with "mode": "full". Parallel over tasks (WAKE_WORKERS), per-task
alarm job["timeout"] seconds (default 300, as the notebook). Writes results.jsonl (training + half A rows without
N2 tasks: task, exact, attempt kinds, rule counts, seconds, prediction hash) and summary.json.
Added in cycle 21 so that changes to the attempt ordering (occupancy2.solve) are measured on held-out counts."""
import hashlib, json, os, re, signal, time
from multiprocessing import Pool

_S = {}


def _init(job, REPO, DATA):
    probe = os.path.join(REPO, job["probe"]); cand = os.path.join(REPO, job.get("candidate", "candidate"))
    os.environ["M1B_VOCAB"] = open(os.path.join(REPO, job.get("vocab_file", "tools/m1b/V7.txt"))).read().strip()
    import sys
    sys.path[:0] = [probe, cand]
    import occupancy2 as P

    class TaskTimeout(BaseException):
        pass
    P.Timeout = TaskTimeout
    _S.update(P=P, TO=TaskTimeout, secs=int(job.get("timeout", 300)),
              tr=json.load(open(f"{DATA}/arc-agi_training_challenges.json")),
              trs=json.load(open(f"{DATA}/arc-agi_training_solutions.json")),
              ev=json.load(open(f"{DATA}/arc-agi_evaluation_challenges.json")),
              evs=json.load(open(f"{DATA}/arc-agi_evaluation_solutions.json")))


def _one(k):
    P, TO = _S["P"], _S["TO"]
    ch, so = (_S["tr"], _S["trs"]) if k in _S["tr"] else (_S["ev"], _S["evs"])
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
    t0 = time.time(); row = {"task": k}
    try:
        signal.alarm(_S["secs"]); att, _, _ = P.solve(ch[k])
        sol = so[k]
        row["exact"] = bool(att) and all(any(a["preds"][i] == sol[i] for a in att[:2]) for i in range(len(sol)))
        row["occupied"] = bool(att)
        row["kinds"] = [a.get("abstraction") for a in att[:2]]
        row["nrules"] = [P.nrules(a["rules"]) if a.get("abstraction") != "gdsl" else 0 for a in att[:2]]
        row["ph"] = hashlib.sha256(json.dumps([a["preds"] for a in att[:2]], sort_keys=True).encode()).hexdigest()[:16]
    except TO:
        row.update(exact=False, occupied=False, timeout=True)
    except BaseException as e:
        row.update(exact=False, occupied=False, err=repr(e)[:80])
    finally:
        signal.alarm(0)
    row["s"] = round(time.time() - t0, 2)
    return row


def run(job, out, REPO, DATA):
    rd = lambda f: [x for x in re.split(r"[,\s]+", open(os.path.join(REPO, "tools/m1b", f)).read()) if x]
    A, B = rd("deval_a.txt"), rd("deval_b.txt")
    N2 = set(rd("novel_N2.txt")) if os.path.exists(os.path.join(REPO, "tools/m1b", "novel_N2.txt")) else set()
    tr = json.load(open(f"{DATA}/arc-agi_training_challenges.json"))
    keys = (sorted(tr) if "train" in job["sets"] else []) + (A if "halfA" in job["sets"] else [])
    if job.get("exclude_n2"): keys = [k for k in keys if k not in N2]     # design-only run (no held-out look)
    if job.get("limit"): keys = keys[: int(job["limit"])]
    n = int(os.environ.get("WAKE_WORKERS", os.cpu_count() or 2)); t0 = time.time()
    with Pool(n, initializer=_init, initargs=(job, REPO, DATA), maxtasksperchild=50) as p:
        R = p.map(_one, keys, chunksize=2)
        RB = p.map(_one, B, chunksize=2) if job.get("halfB_count") else []
    with open(os.path.join(out, "results.jsonl"), "w") as f:
        for r in R:
            if r["task"] not in N2: f.write(json.dumps(r) + "\n")        # N2: counts only
    S = {"job_id": job["job_id"], "mode": "full", "workers": n, "seconds": round(time.time() - t0),
         "train_exact": sum(r["exact"] for r in R if r["task"] in tr and r["task"] not in N2),
         "halfA_exact": sum(r["exact"] for r in R if r["task"] in A),
         "N2_exact_count": sum(r["exact"] for r in R if r["task"] in N2), "N2_n": len(N2),
         "halfB_exact_count": (sum(r["exact"] for r in RB) if RB else None), "halfB_n": len(B) if RB else None,
         "timeouts": sum(1 for r in R + RB if r.get("timeout")), "max_s": max((r["s"] for r in R + RB), default=0)}
    json.dump(S, open(os.path.join(out, "summary.json"), "w"), indent=1); print(S)
