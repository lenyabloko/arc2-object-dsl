"""mirror_cell(x, y; axis): x lies in the mirror image of object y across the grid's central axis (global mirror
symmetry of the frame, the relation used by symmetric completion). With grid height Hg and width Wg:
  H  across the middle row line:    (r, c) -> (Hg - 1 - r, c)
  V  across the middle column line: (r, c) -> (r, Wg - 1 - c)
Grounding: x is any individual (object or background cell), y an object, x != y; x mirror_cell y iff every cell of x
maps onto a cell of y (for a background cell: its mirror cell belongs to y). Positions only, colours are not
compared. A cell on the axis itself (odd Hg / Wg) is its own mirror and so never relates to an object other than one
containing it. Fires on almost every grid (any object not symmetric about the frame axis has mirror cells), so it
is meant as a filler inside a conjunction (e.g. kind=cell and exists mirror_cell.object), not as a selector alone.

Subsumption: none declared (no other item's extension contains it on every grid)."""


def mirror_cell(grid, inds, bg, axis):
    Hg, Wg = len(grid), len(grid[0])
    m = (lambda r, c: (Hg - 1 - r, c)) if axis == "H" else (lambda r, c: (r, Wg - 1 - c))
    owner = {}
    for j, ind in enumerate(inds):
        if ind["kind"] != "object": continue
        for p in ind["pix"]: owner.setdefault(p, []).append(j)
    out = {}
    for i, ind in enumerate(inds):
        pix = ind["pix"]
        if not pix: continue
        it = iter(pix)
        cand = [j for j in owner.get(m(*next(it)), ()) if j != i]
        if not cand: continue
        if len(pix) > 1:
            mp = [m(r, c) for r, c in pix]
            cand = [j for j in cand if all(q in inds[j]["pix"] for q in mp)]
        if cand: out[i] = set(cand)
    return out


ITEM = {"name": "mirror_cell", "layer": 1, "iri": "qsr:mirror_cell", "kind": "role", "params": {"axis": ["H", "V"]},
        "subsumes": [],
        "definition": "x (any individual, typically a background cell) is the mirror image of cells of object y "
                      "across the grid's central axis (H: middle row line, V: middle column line); every cell of x "
                      "mirrors into y; x != y.",
        "fn": mirror_cell}
