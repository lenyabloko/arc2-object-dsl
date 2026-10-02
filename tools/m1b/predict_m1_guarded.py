"""Kaggle driver for the M1b lattice/RDR probe (occupancy2.py), with the round scheduler (Fable G27-G29 / v17 §4).

Every prediction comes from rules induced on the task's own training pairs over the frozen prior
vocabulary; unresolved slots get a 1x1 [[0]] placeholder. Deterministic (sorted iteration), so a
local run and the Kaggle run over the same file must produce the same submission digest.

Round scheduler (only when --deadline-at is given; the parity run never passes it, so its predictions and digest are
unchanged):
  - the sorted tasks are cut into --rounds equal rounds; each round's budget is (deadline - start) / rounds
  - per-round commit: the whole submission (finished tasks + placeholders for the rest) is written atomically after
    every task, so a valid file always exists
  - 25 % overrun skip: once a round has used more than --overrun x its budget, its remaining tasks get placeholders
    and the next round starts on time
  - hard stop: no task starts within --reserve seconds of the deadline; each task's alarm is capped by the time left
A guard report (tasks run / skipped, rounds overrun, seconds) goes to <out>.guard.json.
"""
import argparse, hashlib, json, math, os, signal, sys, time

PLACEHOLDER = [[0]]


class TaskTimeout(BaseException):
    pass


def write_atomic(path, obj):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f: f.write(json.dumps(obj))
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)      # dir containing image.py / ARCGraph.py
    ap.add_argument("--probe", required=True)          # dir containing occupancy2.py
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--challenges", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-seconds", type=int, default=120)
    ap.add_argument("--deadline-at", type=float, default=0.0)   # absolute epoch seconds; 0 = no scheduler
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--overrun", type=float, default=1.25)
    ap.add_argument("--reserve", type=float, default=120.0)
    args = ap.parse_args()
    os.environ["M1B_VOCAB"] = args.vocab
    sys.path[:0] = [args.probe, args.candidate]
    import occupancy2 as probe
    probe.Timeout = TaskTimeout
    ch = json.load(open(args.challenges))
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TaskTimeout()))
    keys = sorted(ch)
    sub = {k: [{"attempt_1": PLACEHOLDER, "attempt_2": PLACEHOLDER} for _ in ch[k]["test"]] for k in keys}
    sched = args.deadline_at > 0
    t0 = time.time()
    per = max(1, math.ceil(len(keys) / max(1, args.rounds)))
    budget = (args.deadline_at - t0) / max(1, args.rounds) if sched else 0.0
    rep = {"tasks": len(keys), "run": 0, "skipped_overrun": 0, "skipped_deadline": 0, "rounds_overrun": [], "scheduler": sched}
    round_start, cur = t0, -1
    for n, k in enumerate(keys):
        task = ch[k]
        if sched:
            r = n // per
            if r != cur:
                cur, round_start = r, time.time()
            now = time.time()
            if now + args.reserve > args.deadline_at:
                rep["skipped_deadline"] += 1; continue
            if now - round_start > args.overrun * budget:
                if not rep["rounds_overrun"] or rep["rounds_overrun"][-1] != r: rep["rounds_overrun"].append(r)
                rep["skipped_overrun"] += 1; continue
            secs = int(max(1, min(args.task_seconds, args.deadline_at - args.reserve - now)))
        else:
            secs = args.task_seconds
        slots = sub[k]
        try:
            signal.alarm(secs)
            attempts, _, _ = probe.solve(task)
            for rank, a in enumerate(attempts[:2]):
                for i, g in enumerate(a["preds"]):
                    if g and all(isinstance(r_, list) and r_ for r_ in g):
                        slots[i]["attempt_1" if rank == 0 else "attempt_2"] = g
        except TaskTimeout:
            pass
        except Exception:
            pass
        finally:
            signal.alarm(0)
        rep["run"] += 1
        if sched: write_atomic(args.out, sub)
    blob = json.dumps(sub, sort_keys=True).encode()
    open(args.out, "w").write(json.dumps(sub))
    rep["seconds"] = round(time.time() - t0, 1)
    if sched: json.dump(rep, open(args.out + ".guard.json", "w"), indent=1)
    print(json.dumps({"tasks": len(sub), "digest": hashlib.sha256(blob).hexdigest(), **({"guard": rep} if sched else {})}))


if __name__ == "__main__":
    main()
