"""between(x, y; axis): binary form of the ternary between(x, y, z) with z existentially quantified.

x lies strictly between object y and some object z != y on one straight line along `axis` (row: a grid row; col: a
grid column; diag: a line of either diagonal direction), and every cell strictly between the y cell and the z cell on
that line is background or a cell of x.
Grounding (cell sets, individuals are disjoint as built by the harness):
- background = pixel of a background-cell individual (kind == "cell"). Any other position is non-background; a
  non-background pixel that belongs to no object is a blocker (it can be neither y, z nor x).
- per line, list the non-background positions in order and merge consecutive ones with the same owner into runs.
  A background cell x is between y and z iff the nearest non-background positions on both sides of it on the line
  belong to two different objects y, z. An object x is between y and z iff one of its runs has an object run y
  immediately before it and an object run z != y immediately after it (the segment then holds only background and x).
- x != y, x != z, y != z; the relation is symmetric in (y, z), so x is related to both y and z. The border ends a line
  (an object touching nothing on one side gives no z there).
Cost: one scan per line, O(H * W) per axis.
"""


def _lines(H, W, axis):
    if axis == "row":
        for r in range(H): yield [(r, c) for c in range(W)]
    elif axis == "col":
        for c in range(W): yield [(r, c) for r in range(H)]
    else:  # both diagonal directions
        for s in range(-(W - 1), H):          # r - c = s
            yield [(r, r - s) for r in range(max(0, s), min(H, W + s))]
        for s in range(H + W - 1):            # r + c = s
            yield [(r, s - r) for r in range(max(0, s - W + 1), min(H, s + 1))]


def between(grid, inds, bg, axis):
    H, W = len(grid), len(grid[0])
    owner, free = {}, set()
    for i, x in enumerate(inds):
        cell = x["kind"] == "cell"
        for p in x["pix"]:
            owner[p] = i
            if cell: free.add(p)
    isobj = [x["kind"] == "object" for x in inds]
    out = {}

    def add(i, j):
        out.setdefault(i, set()).add(j)

    for line in _lines(H, W, axis):
        nf = []                                   # (position on line, owner object or -1 for a blocker)
        for t, p in enumerate(line):
            if p in free: continue
            i = owner.get(p)
            nf.append((t, i if i is not None and isobj[i] else -1))
        for (t1, a), (t2, b) in zip(nf, nf[1:]):  # background cells strictly between two different objects
            if a >= 0 and b >= 0 and a != b and t2 - t1 > 1:
                for t in range(t1 + 1, t2):
                    i = owner[line[t]]; add(i, a); add(i, b)
        runs = []
        for _, lab in nf:
            if not runs or runs[-1] != lab: runs.append(lab)
        for a, x, b in zip(runs, runs[1:], runs[2:]):  # an object run flanked by two different object runs
            if x >= 0 and a >= 0 and b >= 0 and a != b:
                add(x, a); add(x, b)
    return out


ITEM = {"name": "between", "layer": 1, "iri": "qsr:between", "kind": "role",
        "params": {"axis": ["row", "col", "diag"]},
        "subsumes": ["line_of_sight"],
        "subsumes_settings": [[{"axis": "row"}, "line_of_sight", {"axis": "row"}],
                              [{"axis": "col"}, "line_of_sight", {"axis": "col"}]],
        "definition": "Binary form of between(x, y, z) with z existentially quantified: x lies strictly between object y "
                      "and some other object z (z != y, both != x) on one straight line along the axis (row, column, or "
                      "either diagonal for diag), and every cell strictly between the y cell and the z cell on that line "
                      "is background or a cell of x. Subsumption holds per matched axis only: between[row] ⊑ "
                      "line_of_sight[row], between[col] ⊑ line_of_sight[col]; between[diag] has no line_of_sight "
                      "counterpart (the harness checks `subsumes` at the default setting axis=row).",
        "grounding": "cell sets; background = pixels of background-cell individuals; non-object non-background pixels "
                     "block; lines end at the border",
        "expected_phi": "high (two objects sharing a row/column/diagonal with a background gap)",
        "fn": between}
