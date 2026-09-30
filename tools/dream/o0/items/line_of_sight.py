"""line_of_sight(x, y; axis): x sees object y along a row (axis=row) or a column (axis=col).

x and y (x != y) share a row (column) and, for some cell a of x and b of y on it, every cell strictly between a and b
is background. Adjacent cells (nothing strictly between) see each other.
Grounding (cell sets, individuals are disjoint as built by the harness):
- background = pixel of a background-cell individual (kind == "cell"); every other position blocks sight, including
  non-background pixels that belong to no object (they are never y).
- per line: a background cell sees the object owning the nearest non-background position on each side (if any);
  two objects see each other iff they own consecutive non-background positions on the line.
Relation to on_ray: for a background-cell x, line_of_sight[row] = on_ray[E,obstacle] ∪ on_ray[W,obstacle]
(col: N, S). Cost: one scan per line, O(H * W).
"""


def line_of_sight(grid, inds, bg, axis):
    H, W = len(grid), len(grid[0])
    owner, free = {}, set()
    for i, x in enumerate(inds):
        cell = x["kind"] == "cell"
        for p in x["pix"]:
            owner[p] = i
            if cell: free.add(p)
    isobj = [x["kind"] == "object" for x in inds]
    lines = ([[(r, c) for c in range(W)] for r in range(H)] if axis == "row"
             else [[(r, c) for r in range(H)] for c in range(W)])
    out = {}

    def add(i, j):
        out.setdefault(i, set()).add(j)

    for line in lines:
        nf = []
        for t, p in enumerate(line):
            if p in free: continue
            i = owner.get(p)
            nf.append((t, i if i is not None and isobj[i] else -1))
        if not nf: continue
        bounds = [(-1, -1)] + nf + [(len(line), -1)]   # virtual blockers at the border
        for (t1, a), (t2, b) in zip(bounds, bounds[1:]):
            if a >= 0 and b >= 0 and a != b:          # two objects facing each other
                add(a, b); add(b, a)
            if a >= 0 or b >= 0:
                for t in range(t1 + 1, t2):           # background cells in the gap see both flanking objects
                    i = owner[line[t]]
                    if a >= 0: add(i, a)
                    if b >= 0: add(i, b)
    return out


ITEM = {"name": "line_of_sight", "layer": 1, "iri": "qsr:line_of_sight", "kind": "role",
        "params": {"axis": ["row", "col"]},
        "subsumes": ["aligned"],
        "subsumes_settings": [[{"axis": "row"}, "aligned", {"axis": "row"}],
                              [{"axis": "col"}, "aligned", {"axis": "col"}]],
        "definition": "x sees object y (x != y) along the axis: x and y share a row (axis=row) or a column (axis=col) "
                      "and every cell strictly between some cell of x and some cell of y on it is background (adjacent "
                      "cells see each other). For a background-cell x, line_of_sight[row] = on_ray[E,obstacle] ∪ "
                      "on_ray[W,obstacle] and line_of_sight[col] = on_ray[N,obstacle] ∪ on_ray[S,obstacle]. "
                      "Subsumption per matched axis: line_of_sight[row] ⊑ aligned[row], line_of_sight[col] ⊑ aligned[col].",
        "grounding": "cell sets; background = pixels of background-cell individuals; anything else blocks; the "
                     "border ends sight",
        "expected_phi": "high (any object with background on its row/column)",
        "fn": line_of_sight}
