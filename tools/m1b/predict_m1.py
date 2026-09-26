"""Kaggle driver for the M1b lattice/RDR probe (occupancy2.py).

Every prediction comes from rules induced on the task's own training pairs over the frozen prior
vocabulary; unresolved slots get a 1x1 [[0]] placeholder. Deterministic (sorted iteration), so a
local run and the Kaggle run over the same file must produce the same submission digest.
"""
import argparse, hashlib, json, os, signal, sys, time

PLACEHOLDER = [[0]]


class TaskTimeout(BaseException):
    pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)      # dir containing image.py / ARCGraph.py
    ap.add_argument("--probe", required=True)          # dir containing occupancy2.py
    ap.add_argument("--vocab", required=True)
    ap.add_argument("--challenges", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--task-seconds", type=int, default=120)
    args = ap.parse_args()
    os.environ["M1B_VOCAB"] = args.vocab
    sys.path[:0] = [args.probe, args.candidate]
    import occupancy2 as probe
    probe.Timeout = TaskTimeout
    ch = json.load(open(args.challenges))
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TaskTimeout()))
    sub, solved_slots = {}, 0
    for k in sorted(ch):
        task = ch[k]
        slots = [{"attempt_1": PLACEHOLDER, "attempt_2": PLACEHOLDER} for _ in task["test"]]
        try:
            signal.alarm(args.task_seconds)
            attempts, _, _ = probe.solve(task)
            for rank, a in enumerate(attempts[:2]):
                for i, g in enumerate(a["preds"]):
                    if g and all(isinstance(r, list) and r for r in g):
                        slots[i]["attempt_1" if rank == 0 else "attempt_2"] = g
        except TaskTimeout:
            pass
        except Exception:
            pass
        finally:
            signal.alarm(0)
        sub[k] = slots
    blob = json.dumps(sub, sort_keys=True).encode()
    open(args.out, "w").write(json.dumps(sub))
    print(json.dumps({"tasks": len(sub), "digest": hashlib.sha256(blob).hexdigest()}))


if __name__ == "__main__":
    main()
