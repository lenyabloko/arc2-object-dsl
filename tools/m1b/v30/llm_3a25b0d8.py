"""Family for ARC task 3a25b0d8 -- concept: TEXTURE MAPPING (computer graphics).

Picture: the input holds two drawings of the same design in the same outline colour.  One is a bare
wire-frame (the *mesh*: outline only, its cells enclosed by the outline are background).  The other is
a coloured, somewhat distorted copy (the *texture*: its compartments are painted).  The output is the
mesh with the texture mapped onto it: both drawings are parametrised by normalised bounding-box
coordinates (u, v) in [0,1]^2, every enclosed compartment of the mesh is paired with the texture
compartment whose (u, v) centroid is closest, and it is filled with that compartment's colour.  The
result is the mesh's bounding box, everything outside the mesh left as background.

Everything is induced from the grid / training pairs:
  background     = most common colour of the input
  objects        = 8-connected components of non-background cells
  mesh           = the one object drawn in a single colour (that colour is the outline colour)
  texture        = the one object drawn in several colours
  mesh cells     = background cells inside the mesh's box not 4-reachable from the box border
  texture cells  = 4-connected same-colour patches of non-outline colours in the texture's box
                   (plus any enclosed background patch there, which maps to "leave empty")
Declared finite parameter domain, chosen by fitting the training pairs:
  pairing in {"bijective", "nearest"}  -- one-to-one greedy assignment by (u, v) distance / each mesh
                                          compartment independently takes the nearest texture patch
"""
from collections import Counter

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def modal_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def components(cells, nbrs):
    """Connected components of a set of (r, c) cells."""
    cells = set(cells)
    seen, out = set(), []
    for s in sorted(cells):
        if s in seen:
            continue
        seen.add(s)
        comp, stack = [], [s]
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for dr, dc in nbrs:
                q = (r + dr, c + dc)
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
        out.append(comp)
    return out


def bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), min(cs), max(rs), max(cs)


def enclosed(box, wall):
    """Cells of the box that are not walls and cannot be reached (4-connectivity) from the box border."""
    r0, c0, r1, c1 = box
    free = {(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if (r, c) not in wall}
    outside = set()
    stack = [p for p in free if p[0] in (r0, r1) or p[1] in (c0, c1)]
    outside.update(stack)
    while stack:
        r, c = stack.pop()
        for dr, dc in N4:
            q = (r + dr, c + dc)
            if q in free and q not in outside:
                outside.add(q)
                stack.append(q)
    return free - outside


def uv(cells, box):
    """Centroid of a patch in normalised (u, v) coordinates of a bounding box."""
    r0, c0, r1, c1 = box
    h, w = r1 - r0, c1 - c0
    mr = sum(r for r, _ in cells) / len(cells)
    mc = sum(c for _, c in cells) / len(cells)
    return ((mr - r0) / h if h else 0.5, (mc - c0) / w if w else 0.5)


def texture_map(g, pairing):
    bg = modal_colour(g)
    H, W = len(g), len(g[0])
    ink = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    objs = components(ink, N8)
    meshes = [o for o in objs if len({g[r][c] for r, c in o}) == 1]
    textures = [o for o in objs if len({g[r][c] for r, c in o}) > 1]
    if len(meshes) != 1 or len(textures) != 1:
        return None
    mesh, tex = meshes[0], textures[0]
    outline = g[mesh[0][0]][mesh[0][1]]
    if not any(g[r][c] == outline for r, c in tex):
        return None

    # mesh compartments: background enclosed by the wire-frame
    mbox = bbox(mesh)
    holes = components(enclosed(mbox, set(mesh)), N4)
    if not holes:
        return None

    # texture patches: same-colour 4-components of painted cells, plus enclosed empty pockets
    tbox = bbox(tex)
    tset = set(tex)
    walls = {p for p in tex if g[p[0]][p[1]] == outline}
    pockets = [p for p in enclosed(tbox, walls) if p not in tset]
    patches = []
    by_colour = {}
    for r, c in tex:
        if g[r][c] != outline:
            by_colour.setdefault(g[r][c], []).append((r, c))
    for col, cells in by_colour.items():
        for comp in components(cells, N4):
            patches.append((col, comp))
    for comp in components(pockets, N4):
        patches.append((bg, comp))
    if not patches:
        return None

    hu = [uv(h, mbox) for h in holes]
    pu = [uv(p, tbox) for _, p in patches]

    def d2(a, b):
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2

    assign = {}
    if pairing == "bijective":
        pairs = sorted((d2(hu[i], pu[j]), i, j) for i in range(len(holes)) for j in range(len(patches)))
        used = set()
        for _, i, j in pairs:
            if i not in assign and j not in used:
                assign[i] = j
                used.add(j)
    for i in range(len(holes)):  # "nearest", and any hole left over by the one-to-one pass
        if i not in assign:
            assign[i] = min(range(len(patches)), key=lambda j: (d2(hu[i], pu[j]), j))

    r0, c0, r1, c1 = mbox
    out = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for r, c in mesh:
        out[r - r0][c - c0] = outline
    for i, h in enumerate(holes):
        col = patches[assign[i]][0]
        for r, c in h:
            out[r - r0][c - c0] = col
    return out


def fam_texture_mapping(train):
    for pairing in ("bijective", "nearest"):
        fn = (lambda p: (lambda g: texture_map(g, p)))(pairing)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("graphics:texture_mapping[uv=bbox,pairing=%s]" % pairing, 3, fn)
            return


FAMILIES = (fam_texture_mapping,)
