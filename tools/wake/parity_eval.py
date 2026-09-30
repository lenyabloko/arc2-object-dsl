"""Parity + timing run of the full probe (lattice + G-DSL) on the 120 public-eval tasks, exactly as the Kaggle notebook does.
Called by wake_eval.py for jobs with "mode": "parity". Writes summary.json (digest, design slot count, split counts, timing)
and halfA_times.json. Sealed tasks (the 21 never attempted; OQ7) are reported as counts and anonymous timings only; half B is design."""
import hashlib, json, os, re, signal, sys, time
def run(job, out, REPO, DATA):
    probe = os.path.join(REPO, job["probe"]); cand = os.path.join(REPO, job.get("candidate", "candidate"))
    vocab = open(os.path.join(REPO, job.get("vocab_file", "tools/m1b/V7.txt"))).read().strip()
    os.environ["M1B_VOCAB"] = vocab; sys.path[:0] = [probe, cand]
    import occupancy2 as probe_mod
    class TaskTimeout(BaseException): pass
    probe_mod.Timeout = TaskTimeout
    chf = os.path.join(DATA, "arc-agi_evaluation_challenges.json"); solf = os.path.join(DATA, "arc-agi_evaluation_solutions.json")
    eval_sha = hashlib.sha256(open(chf, "rb").read()).hexdigest()
    ch = json.load(open(chf)); sol = json.load(open(solf)) if os.path.exists(solf) else None
    rd = lambda f: set(x for x in re.split(r"[,\s]+", open(os.path.join(REPO, "tools/m1b", f)).read()) if x)
    A, B = rd("deval_a.txt"), rd("deval_b.txt")
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TaskTimeout()))
    secs = int(job.get("task_seconds", 300)); sub = {}; times = {}
    keys = sorted(ch)[: int(job['limit'])] if job.get('limit') else sorted(ch)
    for k in keys:
        task = ch[k]; slots = [{"attempt_1": [[0]], "attempt_2": [[0]]} for _ in task["test"]]; t0 = time.time(); to = False
        try:
            signal.alarm(secs); attempts, _, _ = probe_mod.solve(task)
            for rank, a in enumerate(attempts[:2]):
                for i, g in enumerate(a["preds"]):
                    if g and all(isinstance(r, list) and r for r in g): slots[i]["attempt_1" if rank == 0 else "attempt_2"] = g
        except TaskTimeout: to = True
        except Exception: pass
        finally: signal.alarm(0)
        sub[k] = slots; times[k] = (round(time.time() - t0, 2), to)
    digest = hashlib.sha256(json.dumps(sub, sort_keys=True).encode()).hexdigest()
    S = {"job_id": job["job_id"], "mode": "parity", "eval_sha256": eval_sha, "digest": digest, "expected_digest": job.get("expected_digest"),
         "digest_match": (digest == job.get("expected_digest")) if job.get("expected_digest") else None,
         "total_s": round(sum(t for t, _ in times.values())), "max_s": max(t for t, _ in times.values()),
         "n_over_120s": sum(1 for t, _ in times.values() if t > 120), "n_over_200s": sum(1 for t, _ in times.values() if t > 200),
         "timeouts": sum(1 for _, x in times.values() if x), "sealed_times_sorted_desc": sorted((t for k, (t, _) in times.items() if k not in A and k not in B), reverse=True)[:15]}
    if sol:
        full = lambda k: k in sub and all(any(sub[k][i][a] == t for a in ("attempt_1", "attempt_2")) for i, t in enumerate(sol[k]))
        slot_ok = lambda k: sum(any(sub[k][i][a] == t for a in ("attempt_1", "attempt_2")) for i, t in enumerate(sol[k])) if k in sub else 0
        # G18 fix (cycle 22): the all-120 slot count (sealed included) moves into decide_sealed.json; the summary reports
        # design slots only, so no design count can be subtracted from it.  The notebook's parity gate compares the digest.
        S["correct_design_slots"] = sum(slot_ok(k) for k in sol if k in A or k in B)
        S["halfA_tasks"] = sum(full(k) for k in sol if k in A)
        # decision OQ7 (Len, 2026-09-30): half B is design; only the 21 never-attempted tasks stay sealed (Nov 1)
        S["halfB_tasks"] = sum(full(k) for k in sol if k in B)
        json.dump({"sealed_tasks_count": sum(full(k) for k in sol if k not in A and k not in B),
                   "correct_of_172": sum(slot_ok(k) for k in sol)},
                  open(os.path.join(out, "decide_sealed.json"), "w"), indent=1)
        S["decision_set"] = "sealed: decide_sealed.json (the 21 never-attempted tasks; Nov 1 look, OQ7)"
    json.dump({k: v for k, v in times.items() if k in A}, open(os.path.join(out, "halfA_times.json"), "w"), indent=0)
    json.dump({k: v for k, v in times.items() if k in B}, open(os.path.join(out, "halfB_times.json"), "w"), indent=0)
    json.dump(S, open(os.path.join(out, "summary.json"), "w"), indent=1); print(S)
