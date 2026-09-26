"""Competition driver for the frozen object-DSL candidate (commit 9d446873).

Symbolic only: every prediction is produced by a program inferred from the
task's own training pairs by experiments/object_dsl_recovery/search.py.
Unresolved slots receive a 1x1 placeholder that cannot plausibly be correct,
so any non-zero score is attributable to the DSL. Per-task failures (fragment
gaps, query gaps, timeouts, unexpected errors) are recorded and never abort
the batch.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path

PLACEHOLDER = [[0]]


class TaskTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise TaskTimeout()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--challenges", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--task-seconds", type=int, default=90)
    parser.add_argument("--total-seconds", type=int, default=6 * 3600)
    args = parser.parse_args()

    sys.path.insert(0, str(args.candidate))
    from experiments.object_dsl_recovery.search import infer, execute, Limits

    challenges = json.loads(args.challenges.read_text(encoding="utf-8"))
    submission, log = {}, []
    started = time.monotonic()
    use_alarm = hasattr(signal, "SIGALRM")
    if use_alarm:
        signal.signal(signal.SIGALRM, _alarm)

    for key in sorted(challenges):
        task = challenges[key]
        slots = [{"attempt_1": PLACEHOLDER, "attempt_2": PLACEHOLDER} for _ in task["test"]]
        submission[key] = slots
        row = {"task": key, "status": "unattempted", "predicted": 0}
        if time.monotonic() - started > args.total_seconds:
            row["status"] = "global_budget_exhausted"
            log.append(row)
            continue
        t0 = time.monotonic()
        try:
            if use_alarm:
                signal.alarm(args.task_seconds)
            found = infer(task["train"], Limits(evaluations=256))
            program = found.get("program")
            row["status"] = found.get("status")
            if program is not None:
                for index, example in enumerate(task["test"]):
                    try:
                        grid = execute(example["input"], program)["grid"]
                        if grid and all(isinstance(r, list) and r for r in grid):
                            slots[index]["attempt_1"] = grid
                            row["predicted"] += 1
                    except TaskTimeout:
                        raise
                    except Exception as error:  # out-of-fragment test input
                        row.setdefault("test_errors", []).append(f"{index}:{type(error).__name__}:{error}")
        except TaskTimeout:
            row["status"] = "task_timeout"
        except Exception as error:
            row["status"] = f"error:{type(error).__name__}:{error}"[:300]
        finally:
            if use_alarm:
                signal.alarm(0)
        row["seconds"] = round(time.monotonic() - t0, 3)
        log.append(row)

    args.out.write_text(json.dumps(submission), encoding="utf-8")
    summary = {"tasks": len(challenges), "slots": sum(len(v) for v in submission.values()),
               "predicted_slots": sum(r["predicted"] for r in log),
               "seconds": round(time.monotonic() - started, 3), "rows": log}
    args.log.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}))


if __name__ == "__main__":
    main()
