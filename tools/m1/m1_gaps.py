"""Gap report: for not_occupied tasks, show label classes and prior-indistinguishable conflicts."""
import json, sys, collections
from occupancy import *
ch = json.load(open(sys.argv[1])); rows = [json.loads(l) for l in open(sys.argv[2])]
out = ["# M1 gap report: " + sys.argv[3], ""]
kinds = collections.Counter()
for r in rows:
    st = r.get("statuses", {})
    if r.get("occupied") or "not_occupied" not in st.values(): continue
    ab = next(a for a, s in st.items() if s == "not_occupied")
    cases = []
    for pi, p in enumerate(ch[r["task"]]["train"]):
        nodes, bg, at, src, others = prepare(p["input"], ab)
        for n, a, s, o in zip(nodes, at, src, others):
            labs = candidate_labels(n, s, p["input"], p["output"], bg, o)
            r0, c0, r1, c1 = bbox(n["pix"])
            cases.append((frozenset(a), labs, f"pair{pi}@({r0},{c0}) color={n['color']} size={len(n['pix'])}"))
    labcount = collections.Counter(min(l, key=len) for _, l, _ in cases)
    conflicts = [(x, y) for i, x in enumerate(cases) for y in cases[i + 1:] if x[0] == y[0] and not (x[1] & y[1])]
    kind = "indistinguishable_under_priors" if conflicts else "needs_>2_attribute_or_>5_rule_concept"
    kinds[kind] += 1
    out.append(f"## {r['task']} ({ab}) — {kind}")
    out.append(f"- label classes: {dict(labcount)}; cases: {len(cases)}")
    for x, y in conflicts[:2]:
        out.append(f"- same prior intent, different change: {x[2]} -> {sorted(x[1])[:2]}  vs  {y[2]} -> {sorted(y[1])[:2]}")
    out.append("")
out.insert(1, f"Summary: {dict(kinds)}")
print("\n".join(out))
