"""translate_of(x, y): x and y are distinct objects whose coloured shapes coincide up to a translation (Euclidean
translation group acting on the grid lattice). Grounding: an object's coloured shape is the set of (dy, dx, colour)
triples of its cells, with (dy, dx) taken relative to the top-left corner of its bounding box and colour read from
the grid; x translate_of y iff the two normalised coloured shapes are equal. Both arguments range over objects
(background-cell individuals are skipped). The relation is symmetric and transitive on distinct objects.

It is the identity element of the D4 family: with r_T(x, y) iff norm(x) = T(norm(y)) and x != y
(reflection_of[axis], rotation_of[k]), every chain r_S o r_T is included in r_{S.T} or the diagonal, so
translate_of o r_T and r_T o translate_of are included in r_T (up to x = y)."""


def _key(grid, pix):
    y0 = min(y for y, _ in pix); x0 = min(x for _, x in pix)
    return tuple(sorted((y - y0, x - x0, grid[y][x]) for y, x in pix))


def translate_of(grid, inds, bg):
    groups = {}
    for i, ind in enumerate(inds):
        if ind["kind"] != "object" or not ind["pix"]: continue
        groups.setdefault(_key(grid, ind["pix"]), []).append(i)
    out = {}
    for k in sorted(groups):
        g = groups[k]
        if len(g) < 2: continue
        s = set(g)
        for i in g: out[i] = s - {i}
    return {i: out[i] for i in sorted(out)}


ITEM = {"name": "translate_of", "layer": 1, "iri": "qsr:translate_of", "kind": "role", "params": {}, "subsumes": [],
        "definition": "x and y are distinct objects with identical shape and cell colours up to a translation "
                      "(normalised coloured shapes are equal).",
        "chains": ["translate_of o translate_of -> translate_of (x != y)",
                   "translate_of o r_T -> r_T and r_T o translate_of -> r_T for r_T in reflection_of[axis], "
                   "rotation_of[k] (x != y)"],
        "fn": translate_of}
