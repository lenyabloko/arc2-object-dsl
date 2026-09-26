"""Competition driver for the widened object-DSL search (search2.py).

attempt_1 / attempt_2 = test outputs of up to two distinct training-exact programs,
found across registered object abstractions and re-verified on every training pair with
the shadow (connector) interpreter. Unresolved slots receive a 1x1 [[0]] placeholder.
Per-task failures never abort the batch.
"""
from __future__ import annotations

import argparse, json, signal, sys, time
from pathlib import Path

PLACEHOLDER = [[0]]


class TaskTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise TaskTimeout()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--challenges", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--task-seconds", type=int, default=120)
    ap.add_argument("--total-seconds", type=int, default=9 * 3600)
    ap.add_argument("--evaluations", type=int, default=1500)
    ap.add_argument("--abstractions", default="nbccg,ccgbr,nbvcg,nbhcg,mcccg,ccgbr2,lrg")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    sys.path.insert(0, str(args.candidate))
    from experiments.object_dsl_recovery.search import Limits
    from experiments.object_dsl_recovery import search2

    challenges = json.loads(args.challenges.read_text(encoding="utf-8"))
    keys = sorted(challenges) if not args.only else [k for k in args.only.split(",") if k in challenges]
    submission, rows = {}, []
    started = time.monotonic()
    signal.signal(signal.SIGALRM, _alarm)
    limits = Limits(evaluations=args.evaluations, candidates_per_state=64, depth=3, beam=4)
    for key in keys:
        task = challenges[key]
        slots = [{"attempt_1": PLACEHOLDER, "attempt_2": PLACEHOLDER} for _ in task["test"]]
        submission[key] = slots
        row = {"task": key, "status": "unattempted", "programs": 0, "predicted": 0}
        rows.append(row)
        if time.monotonic() - started > args.total_seconds:
            row["status"] = "global_budget_exhausted"
            continue
        t0 = time.monotonic()
        verified = []
        try:
            signal.alarm(args.task_seconds)
            statuses = []
            for abstraction in args.abstractions.split(","):
                if len(verified) >= 2:
                    break
                try:
                    found = search2.infer(task["train"], abstraction, limits, want=2)
                except TaskTimeout:
                    raise
                except Exception as error:
                    found = {"status": f"error:{type(error).__name__}", "programs": []}
                statuses.append(f"{abstraction}:{found['status']}")
                for program in found.get("programs", []):
                    try:
                        if all(search2.execute(p["input"], program, abstraction) == p["output"] for p in task["train"]):
                            verified.append((abstraction, program))
                    except TaskTimeout:
                        raise
                    except Exception:
                        pass
                    if len(verified) >= 2:
                        break
            row["status"] = ";".join(statuses)
        except TaskTimeout:
            row["status"] = "task_timeout"
        except Exception as error:
            row["status"] = f"error:{type(error).__name__}:{error}"[:300]
        finally:
            signal.alarm(0)
        row["programs"] = len(verified)
        row["abstractions"] = [a for a, _ in verified]
        for rank, (abstraction, program) in enumerate(verified[:2]):
            for index, example in enumerate(task["test"]):
                try:
                    signal.alarm(20)
                    grid = search2.execute(example["input"], program, abstraction)
                    if grid and all(isinstance(r, list) and r for r in grid):
                        slots[index]["attempt_1" if rank == 0 else "attempt_2"] = grid
                        row["predicted"] += 1
                except Exception as error:
                    row.setdefault("test_errors", []).append(f"{rank}.{index}:{type(error).__name__}")
                finally:
                    signal.alarm(0)
        row["seconds"] = round(time.monotonic() - t0, 3)
    args.out.write_text(json.dumps(submission), encoding="utf-8")
    summary = {"tasks": len(keys), "slots": sum(len(v) for v in submission.values()),
               "tasks_with_program": sum(1 for r in rows if r["programs"]),
               "seconds": round(time.monotonic() - started, 3), "rows": rows}
    args.log.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}))


if __name__ == "__main__":
    main()
