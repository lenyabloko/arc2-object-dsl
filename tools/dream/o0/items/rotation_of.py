"""rotation_of(x, y; k): x is y (shape and cell colours) rotated by k quarter turns clockwise, at any placement.
Rotations of the dihedral group D4 acting on (row, col) = (r, c), up to translation:
  k=1 (90 cw) (r, c) -> (c, -r);  k=2 (180) (r, c) -> (-r, -c);  k=3 (270 cw = 90 ccw) (r, c) -> (-c, r).
Grounding: norm(o) = set of (dr, dc, colour) relative to o's bounding-box corner, colour read from the grid;
x rotation_of[k] y iff norm(x) == norm(R_k(y)) and x != y (a rotationally symmetric y is not related to itself, but is
related to its translates). Both arguments range over objects. rotation_of[1] is the inverse of rotation_of[3];
rotation_of[2] is symmetric.

Subsumption: none holds on every grid between items (default settings), so none is declared. rotation_of[2] is the
relation of the composed shape map H.V (rows and columns reversed), not the relational composition
reflection_of[H] o reflection_of[V]; that composition (through an intermediate object z) is included in rotation_of[2]
(chain, verified on design grids). Chains: rotation_of[j] o rotation_of[k] -> rotation_of[(j+k) mod 4], or translate_of
when j + k = 4 (x != y)."""
R = {1: lambda r, c: (c, -r), 2: lambda r, c: (-r, -c), 3: lambda r, c: (-c, r)}


def _key(cells):
    r0 = min(r for r, _, _ in cells); c0 = min(c for _, c, _ in cells)
    return tuple(sorted((r - r0, c - c0, v) for r, c, v in cells))


def rotation_of(grid, inds, bg, k):
    t = R[k]
    objs = [i for i, ind in enumerate(inds) if ind["kind"] == "object" and ind["pix"]]
    cells = {i: [(r, c, grid[r][c]) for r, c in inds[i]["pix"]] for i in objs}
    groups = {}
    for i in objs: groups.setdefault(_key(cells[i]), []).append(i)
    out = {}
    for j in objs:
        for i in groups.get(_key([(*t(r, c), v) for r, c, v in cells[j]]), ()):
            if i != j: out.setdefault(i, set()).add(j)
    return {i: out[i] for i in sorted(out)}


ITEM = {"name": "rotation_of", "layer": 1, "iri": "qsr:rotation_of", "kind": "role", "params": {"k": [1, 2, 3]},
        "subsumes": [],
        "definition": "x is y (shape and cell colours, any placement) rotated by k quarter turns clockwise; x != y; "
                      "objects only.",
        "chains": ["rotation_of[j] o rotation_of[k] -> rotation_of[(j+k) mod 4], translate_of if j+k = 4 (x != y)",
                   "reflection_of[H] o reflection_of[V] -> rotation_of[2]; reflection_of[V] o reflection_of[D] -> "
                   "rotation_of[1]; reflection_of[D] o reflection_of[V] -> rotation_of[3] (x != y)"],
        "fn": rotation_of}
