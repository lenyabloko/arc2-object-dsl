"""per-family time of fit+predict on a task list (FAM_MODULE=prior_lines for the V31 line stratum); cap 20 s to catch hangs."""
import json, os, sys, time
probe = sys.argv[1]; keys_file = sys.argv[2]; out = sys.argv[3]
sys.path[:0] = [probe]
import importlib; L = importlib.import_module(os.environ.get("FAM_MODULE", "prior_llm"))
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
ch = {}
for s in ('training', 'evaluation'): ch.update(json.load(open(B + f'arc-agi_{s}_challenges.json')))
keys = [k for k in open(keys_file).read().split() if k]
done = set()
if os.path.exists(out): done = {json.loads(l)["task"] for l in open(out)}
fams = L.families()
with open(out, 'a') as f:
    for k in keys:
        if k in done: continue
        row = {"task": k, "t": {}, "fire": []}
        for src, fam in fams:
            t0 = time.time()
            try:
                progs = L._capped(20.0, L._fit_and_predict, fam, ch[k])
                if progs: row["fire"].append(src)
            except L._Cap: row.setdefault("capped", []).append(src)
            except Exception: pass
            dt = time.time() - t0
            if dt > 0.05: row["t"][src] = round(dt, 2)
        row["total"] = round(sum(row["t"].values()), 2)
        f.write(json.dumps(row) + "\n"); f.flush()
