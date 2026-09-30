"""reflection_of(x, y; axis): x is the mirror image of y (shape and cell colours) under the reflection named by axis,
at any placement. Reflections of the dihedral group D4 acting on (row, col) = (r, c), up to translation:
  H  horizontal mirror (across a horizontal line, rows reversed):   (r, c) -> (-r,  c)
  V  vertical mirror   (across a vertical line, columns reversed):  (r, c) -> ( r, -c)
  D  main diagonal (transpose):                                     (r, c) -> ( c,  r)
  A  anti-diagonal:                                                 (r, c) -> (-c, -r)
Grounding: norm(o) = set of (dr, dc, colour) relative to o's bounding-box corner, colour read from the grid;
x reflection_of[axis] y iff norm(x) == norm(T_axis(y)) and x != y (so a symmetric y is not related to itself, but is
related to its translates). Both arguments range over objects. Each reflection is an involution, so the relation is
symmetric.

Subsumption: none holds on every grid between items (default settings), so none is declared. Chains (RBox, verified
on the design grids with x != y): r_S o r_T -> r_{S.T}, where r_I = translate_of, r_{R_k} = rotation_of[k]; e.g.
reflection_of[H] o reflection_of[V] -> rotation_of[2] (H.V = rotation by 180), reflection_of[a] o reflection_of[a]
-> translate_of, reflection_of[V] o reflection_of[D] -> rotation_of[1], reflection_of[D] o reflection_of[A] ->
rotation_of[2]. rotation_of[2] is NOT the relational composition of reflection_of[H] and reflection_of[V] (that needs an
intermediate object z on the grid); it is the relation of the composed shape map H.V."""
T = {"H": lambda r, c: (-r, c), "V": lambda r, c: (r, -c), "D": lambda r, c: (c, r), "A": lambda r, c: (-c, -r)}


def _key(cells):
    r0 = min(r for r, _, _ in cells); c0 = min(c for _, c, _ in cells)
    return tuple(sorted((r - r0, c - c0, k) for r, c, k in cells))


def reflection_of(grid, inds, bg, axis):
    t = T[axis]
    objs = [i for i, ind in enumerate(inds) if ind["kind"] == "object" and ind["pix"]]
    cells = {i: [(r, c, grid[r][c]) for r, c in inds[i]["pix"]] for i in objs}
    groups = {}
    for i in objs: groups.setdefault(_key(cells[i]), []).append(i)
    out = {}
    for j in objs:
        for i in groups.get(_key([(*t(r, c), k) for r, c, k in cells[j]]), ()):
            if i != j: out.setdefault(i, set()).add(j)
    return {i: out[i] for i in sorted(out)}


ITEM = {"name": "reflection_of", "layer": 1, "iri": "qsr:reflection_of", "kind": "role",
        "params": {"axis": ["H", "V", "D", "A"]}, "subsumes": [],
        "definition": "x is the mirror image of y (shape and cell colours, any placement) under the reflection axis "
                      "(H rows reversed, V columns reversed, D transpose, A anti-transpose); x != y; objects only.",
        "chains": ["reflection_of[S] o reflection_of[T] -> rotation_of[k] with R_k = S.T, or translate_of if S = T "
                   "(x != y); e.g. H o V -> k=2, D o A -> k=2, V o D -> k=1, D o V -> k=3"],
        "fn": reflection_of}
