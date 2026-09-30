"""Fable v2 E1/E3: compare two jobs' private N2-gate records and emit ONLY (b, c, n_changed); append the release to
the looks ledger.  b = gate tasks exact in the baseline but not in the candidate (lost); c = the reverse (gained);
n_changed = gate tasks whose prediction hash differs.  No task id (hashed or not) is printed.
usage: python3 compare_gate.py <baseline_result_dir> <candidate_result_dir> [ledger_path]"""
import json, os, sys, time
a_dir, b_dir = sys.argv[1], sys.argv[2]
ledger = sys.argv[3] if len(sys.argv) > 3 else os.path.expanduser("~/arc/arc2-object-dsl/results/looks_ledger.txt")
rd = lambda d: {r["hid"]: r for r in map(json.loads, open(os.path.join(d, "n2_gate_private.jsonl.txt")))}
A, B = rd(a_dir), rd(b_dir)
assert set(A) == set(B), "gate sets differ (different salt or task list)"
# G21 (Fable guidance v3 §3): a task that timed out in either run is excluded from both sides of the comparison
K = [k for k in A if not (A[k].get("to") or B[k].get("to"))]
b = sum(1 for k in K if A[k]["exact"] and not B[k]["exact"])
c = sum(1 for k in K if B[k]["exact"] and not A[k]["exact"])
n = sum(1 for k in K if A[k]["ph"] != B[k]["ph"])
rec = {"time": time.strftime("%Y-%m-%dT%H:%M"), "split": "N2-gate", "salt": "arc2-c21-2026-09-29", "cycle": os.environ.get("CYCLE", ""), "baseline": os.path.basename(a_dir.rstrip("/")),
       "candidate": os.path.basename(b_dir.rstrip("/")), "b": b, "c": c, "n_changed": n, "n_gate": len(A), "n_compared": len(K)}
os.makedirs(os.path.dirname(ledger), exist_ok=True)
open(ledger, "a").write(json.dumps(rec) + "\n")
print(json.dumps({"b": b, "c": c, "n_changed": n}))
