"""on_ray(x, y; d, stop): x lies on a ray cast from object y in direction d.

Grounding (cell sets, individuals are disjoint as built by the harness):
- free cell = the pixel of a background-cell individual (kind == "cell"); every other in-grid position (a pixel of
  some object, or a non-background pixel that no individual covers) is non-background.
- start cells: for EVERY direction d (cardinal and diagonal) the cells of y whose next position in direction d is not
  a cell of y (the face of y that looks in direction d; for a convex y the cardinal faces are its extreme row/column).
- a ray advances one cell per step from a start cell. Cells of y are transparent (never stop the ray, never marked).
  stop=border: runs to the grid border and marks every non-y cell it passes (objects included).
  stop=obstacle: stops before the first non-background cell that is not part of y, so it marks free cells only.
- x (x != y) is on the ray if any of x's cells is marked. The ray never wraps; the border simply ends it.
Cost: each (y, d) marks each grid position at most once (a ray that reaches an already visited position has the same
continuation, so it stops there): O(#objects * H * W) worst case, one dict lookup per step.
"""
DIRS = {"N": (-1, 0), "S": (1, 0), "E": (0, 1), "W": (0, -1),
        "NE": (-1, 1), "NW": (-1, -1), "SE": (1, 1), "SW": (1, -1)}


def on_ray(grid, inds, bg, d, stop):
    H, W = len(grid), len(grid[0])
    dy, dx = DIRS[d]
    obstacle = stop == "obstacle"
    owner, free = {}, set()
    for i, x in enumerate(inds):
        cell = x["kind"] == "cell"
        for p in x["pix"]:
            owner[p] = i
            if cell: free.add(p)
    out = {}
    for j, y in enumerate(inds):
        if y["kind"] != "object": continue
        Y = y["pix"]; seen = set(); hit = set()
        for (r, c) in Y:
            if (r + dy, c + dx) in Y: continue
            r += dy; c += dx
            while 0 <= r < H and 0 <= c < W:
                p = (r, c)
                if p in seen: break
                seen.add(p)
                if p not in Y:
                    if obstacle and p not in free: break
                    i = owner.get(p)
                    if i is not None: hit.add(i)
                r += dy; c += dx
        for i in hit:
            out.setdefault(i, set()).add(j)
    return out


# Setting-level subsumptions (the harness `subsumes` list only compares default settings of two items, so these are
# declared here and verified separately): obstacle ray is a prefix of the border ray from the same start cell; an
# obstacle ray along a row/column only crosses free cells, so the x it reaches sees y along that row/column.
SUBSUMES_SETTINGS = (
    [[{"d": d, "stop": "obstacle"}, "on_ray", {"d": d, "stop": "border"}] for d in DIRS]
    + [[{"d": d, "stop": "obstacle"}, "line_of_sight", {"axis": "row"}] for d in ("E", "W")]
    + [[{"d": d, "stop": "obstacle"}, "line_of_sight", {"axis": "col"}] for d in ("N", "S")])

ITEM = {"name": "on_ray", "layer": 1, "iri": "qsr:on_ray", "kind": "role",
        "params": {"d": ["N", "S", "E", "W", "NE", "NW", "SE", "SW"], "stop": ["border", "obstacle"]},
        "subsumes": [],
        "subsumes_settings": SUBSUMES_SETTINGS,
        "definition": "x is on the ray cast from object y in direction d: the ray starts at every cell of y whose next "
                      "position in direction d is not in y, advances one cell per step with y's own cells transparent, "
                      "and ends at the grid border (stop=border) or just before the first non-background cell not in y "
                      "(stop=obstacle); x (a cell or an object, x != y) is on it if any cell of x is. "
                      "Setting-level subsumptions (not expressible in `subsumes`): on_ray[d,obstacle] ⊑ on_ray[d,border] "
                      "for every d; on_ray[E|W,obstacle] ⊑ line_of_sight[row]; on_ray[N|S,obstacle] ⊑ line_of_sight[col]; "
                      "for background-cell x, line_of_sight[row] = on_ray[E,obstacle] ∪ on_ray[W,obstacle] (col: N, S).",
        "grounding": "cell sets; background = pixels of background-cell individuals; start cells by the local face rule "
                     "for all 8 directions; y transparent; border ends the ray",
        "expected_phi": "high (any grid with an object and a free cell in direction d)",
        "fn": on_ray}
