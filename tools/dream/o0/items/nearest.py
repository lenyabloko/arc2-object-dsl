"""nearest(x, y): y is an object at minimum Chebyshev distance from x.

Distance between cell sets = min over cell pairs of max(|dr|, |dc|) (king-move distance; the grid border plays no
role). x ranges over all individuals (background cells and objects); y over objects, y != x. Ties: every tied object
is related. A grid with no object other than x relates nothing to x.
Grounding: per object y a distance map D_y over all grid positions (numpy, O(H*W*|y|)); dist(x, y) = min of D_y over
x's cells. Integer arithmetic only, so ties are exact.
"""
import numpy as np


def nearest(grid, inds, bg):
    H, W = len(grid), len(grid[0])
    objs = [j for j, x in enumerate(inds) if x["kind"] == "object"]
    if not objs or not inds: return {}
    ry = np.repeat(np.arange(H), W)[:, None]; rx = np.tile(np.arange(W), H)[:, None]
    D = np.empty((len(objs), H * W), dtype=np.int32)
    for k, j in enumerate(objs):
        P = np.array(sorted(inds[j]["pix"]), dtype=np.int32)
        D[k] = np.maximum(np.abs(ry - P[None, :, 0]), np.abs(rx - P[None, :, 1])).min(1)
    pos, start = [], []
    for x in inds:                                    # pixels grouped by individual
        start.append(len(pos)); pos.extend(r * W + c for r, c in x["pix"])
    M = np.minimum.reduceat(D[:, np.array(pos)], np.array(start), axis=1)   # (objects, individuals)
    big = H + W + 1
    M[np.arange(len(objs)), np.array(objs)] = big     # exclude x itself
    m = M.min(0)
    ks, iis = np.nonzero((M == m[None, :]) & (m[None, :] < big))
    out = {}
    for k, i in zip(ks.tolist(), iis.tolist()):
        out.setdefault(i, set()).add(objs[k])
    return out


ITEM = {"name": "nearest", "layer": 1, "iri": "qsr:nearest", "kind": "role", "params": {},
        "subsumes": [],
        "definition": "y is an object at minimum Chebyshev (king-move) distance from x, distance between cell sets "
                      "being the minimum over cell pairs; x is any individual, y ranges over objects other than x; "
                      "all tied objects are related.",
        "grounding": "cell sets; Chebyshev set distance; ties kept; no border effect",
        "expected_phi": "high (every individual has a nearest object once the grid has >= 2 objects)",
        "fn": nearest}
