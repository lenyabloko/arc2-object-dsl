"""within(x, y; k, metric): x is a background cell in the halo of width k around object y.

x is a background individual (kind == "cell") whose distance to object y is between 1 and k, distance between cell
sets being the minimum over cell pairs of max(|dr|, |dc|) (metric=cheb) or |dr| + |dc| (metric=manhattan). Objects
are never x. The halo is clipped by the grid border and passes over other objects (distance, not path length).
Grounding: per object y a distance map over all grid positions (numpy, O(H*W*|y|)); integer arithmetic.
"""
import numpy as np


def within(grid, inds, bg, k, metric):
    H, W = len(grid), len(grid[0])
    objs = [j for j, x in enumerate(inds) if x["kind"] == "object"]
    cells = [i for i, x in enumerate(inds) if x["kind"] == "cell"]
    if not objs or not cells: return {}
    ry = np.repeat(np.arange(H), W)[:, None]; rx = np.tile(np.arange(W), H)[:, None]
    D = np.empty((len(objs), H * W), dtype=np.int32)
    for n, j in enumerate(objs):
        P = np.array(sorted(inds[j]["pix"]), dtype=np.int32)
        a, b = np.abs(ry - P[None, :, 0]), np.abs(rx - P[None, :, 1])
        D[n] = (np.maximum(a, b) if metric == "cheb" else a + b).min(1)
    pos, start = [], []
    for i in cells:
        start.append(len(pos)); pos.extend(r * W + c for r, c in inds[i]["pix"])
    M = np.minimum.reduceat(D[:, np.array(pos)], np.array(start), axis=1)   # (objects, cells)
    ns, cs = np.nonzero((M >= 1) & (M <= k))
    out = {}
    for n, c in zip(ns.tolist(), cs.tolist()):
        out.setdefault(cells[c], set()).add(objs[n])
    return out


ITEM = {"name": "within", "layer": 1, "iri": "qsr:within", "kind": "role",
        "params": {"k": [1, 2, 3], "metric": ["cheb", "manhattan"]},
        "subsumes": ["nearest"],
        "subsumes_settings": ([[{"k": k, "metric": "manhattan"}, "within", {"k": k, "metric": "cheb"}] for k in (1, 2, 3)]
                              + [[{"k": k, "metric": m}, "within", {"k": k + 1, "metric": m}]
                                 for k in (1, 2) for m in ("cheb", "manhattan")]
                              + [[{"k": 1, "metric": m}, "nearest", {}] for m in ("cheb", "manhattan")]),
        "definition": "Halo / buffer (CENTER-PERIPHERY): x is a background-cell individual whose distance to object y "
                      "is between 1 and k (Chebyshev or Manhattan set distance). Setting-level subsumptions: "
                      "within[k,manhattan] ⊑ within[k,cheb]; within[k,m] ⊑ within[k+1,m]; within[1,m] ⊑ nearest "
                      "(a background cell at distance 1 has no object closer); for k >= 2 within is NOT ⊑ nearest "
                      "(the harness checks `subsumes` at the default setting k=1, metric=cheb).",
        "grounding": "cell sets; x background cells only; set distance ignores obstacles; border clips the halo",
        "expected_phi": "high (any grid with an object and a background cell within k)",
        "fn": within}
