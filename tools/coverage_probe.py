"""Probe: fraction of tasks whose train pairs are all explained by ONE general grid op
(D4 symmetry, integer up/down-scale, tiling with D4 tiles, crop to bbox of one object selected by
size/color extremum). Uses train pairs only; reports per-dataset counts. Diagnostic, not a solver."""
import json, sys, collections
import numpy as np
from scipy.ndimage import label

def d4(g):
    out = {}
    for k in range(4):
        r = np.rot90(g, k); out[f"rot{k}"] = r; out[f"rot{k}_T"] = r.T
    return out

def ops(x):
    x = np.array(x)
    c = {}
    for n, v in d4(x).items(): c["d4:" + n] = v
    for k in (2, 3, 4, 5):
        c[f"up{k}"] = np.kron(x, np.ones((k, k), int))
        if x.shape[0] % k == 0 and x.shape[1] % k == 0:
            c[f"down{k}"] = x[::k, ::k]
    for a in (1, 2, 3, 4):
        for b in (1, 2, 3, 4):
            if a * b > 1: c[f"tile{a}x{b}"] = np.tile(x, (a, b))
    bg = 0
    objs = []
    for mode, st in (("c4", None), ("c8", np.ones((3, 3), int))):
        lab, n = label(x != bg, structure=st)
        for i in range(1, n + 1):
            ys, xs = np.nonzero(lab == i)
            objs.append((mode, len(ys), ys.min(), ys.max(), xs.min(), xs.max()))
    for mode in ("c4", "c8"):
        o = [t for t in objs if t[0] == mode]
        if not o: continue
        for name, pick in (("largest", max), ("smallest", min)):
            t = pick(o, key=lambda t: t[1])
            c[f"crop_{mode}_{name}"] = x[t[2]:t[3] + 1, t[4]:t[5] + 1]
    return c

def solved(task):
    names = None
    for p in task["train"]:
        y = np.array(p["output"]); c = ops(p["input"])
        ok = {n for n, v in c.items() if v.shape == y.shape and (v == y).all()}
        names = ok if names is None else names & ok
        if not names: return None
    return sorted(names)

for path in sys.argv[1:]:
    data = json.load(open(path))
    hits = {k: solved(t) for k, t in data.items()}
    s = {k: v for k, v in hits.items() if v}
    print(path.split("/")[-1], len(s), "of", len(data), collections.Counter(v[0].split("_")[0] for v in s.values()).most_common(8))
