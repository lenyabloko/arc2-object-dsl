"""Family for ARC task 2ba387bc -- concept: GENUS SORT (topology).

Picture: the scene holds equal-sized blobs, some with a hole (genus 1, "rings") and some without
(genus 0, "discs").  The blobs are sorted by their topological genus into bins -- one column per
genus -- and inside each column they are stacked edge-to-edge in the order they are met when the
grid is scanned (top row first, then left column).  Shorter columns are padded with background tiles;
the output is just the stacked bins (a "type case" of shapes filed by genus).

Everything is induced from the training pairs:
  background = most common colour of the input
  objects    = 4-connected single-colour components; all must share one bounding-box size (the tile)
  genus      = number of enclosed background regions inside an object's bounding box
Declared finite parameter domains, chosen by fitting the training pairs:
  frame in the 8 dihedral maps  -- which way is "down the stack" / "across the bins" (the canonical
                                   frame stacks downward and files bins left-to-right)
  bins  in {"holes_first", "solid_first"} -- order of the genus columns
Only the first fitting (frame, bins) in declared order is yielded: a mirrored frame with the opposite bin
order fits the same data and differs only in tie-breaking, so it adds no independent hypothesis.
"""
from collections import Counter


def most_common_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


# ---- dihedral frames: (forward map, inverse map) -------------------------------------------------
def _rot(g):  # rotate 90 deg clockwise
    return [list(r) for r in zip(*g[::-1])]


def _tr(g):
    return [list(r) for r in zip(*g)]


def _compose(*fs):
    def h(g):
        for f in fs:
            g = f(g)
        return g
    return h


_id = lambda g: [list(r) for r in g]
FRAMES = {
    "id": (_id, _id),
    "rot90": (_rot, _compose(_rot, _rot, _rot)),
    "rot180": (_compose(_rot, _rot), _compose(_rot, _rot)),
    "rot270": (_compose(_rot, _rot, _rot), _rot),
    "transpose": (_tr, _tr),
    "flipud": (lambda g: [list(r) for r in g[::-1]], lambda g: [list(r) for r in g[::-1]]),
    "fliplr": (lambda g: [list(r[::-1]) for r in g], lambda g: [list(r[::-1]) for r in g]),
    "antitranspose": (_compose(_rot, _rot, _tr), _compose(_rot, _rot, _tr)),
}


# ---- topology ------------------------------------------------------------------------------------
def components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col, stack, cells = g[r][c], [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            out.append((col, cells))
    return out


def genus(cells):
    """Number of holes: background regions of the padded bounding box that do not touch its rim."""
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    y0, x0 = min(ys) - 1, min(xs) - 1
    h, w = max(ys) - y0 + 2, max(xs) - x0 + 2
    body = {(y - y0, x - x0) for y, x in cells}
    seen, regions = set(), 0
    for r in range(h):
        for c in range(w):
            if (r, c) in body or (r, c) in seen:
                continue
            regions += 1
            stack = [(r, c)]; seen.add((r, c))
            while stack:
                y, x = stack.pop()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and (ny, nx) not in body and (ny, nx) not in seen:
                        seen.add((ny, nx)); stack.append((ny, nx))
    return regions - 1  # minus the outside region


def genus_sort(g, bins):
    """Canonical frame: bins are columns left-to-right, each stacked top-to-bottom in scan order."""
    bg = most_common_colour(g)
    objs = []
    for col, cells in components(g, bg):
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        top, left = min(ys), min(xs)
        th, tw = max(ys) - top + 1, max(xs) - left + 1
        tile = [[bg] * tw for _ in range(th)]
        for y, x in cells:
            tile[y - top][x - left] = col
        objs.append(((top, left), genus(cells), tile))
    if not objs:
        return None
    th, tw = len(objs[0][2]), len(objs[0][2][0])
    if any(len(t) != th or len(t[0]) != tw for _, _, t in objs):
        return None  # tiles must be congruent to stack into a lattice
    classes = sorted({k for _, k, _ in objs}, reverse=(bins == "holes_first"))
    columns = [[t for _, k, t in sorted(objs, key=lambda o: o[0]) if k == cls] for cls in classes]
    n = max(len(c) for c in columns)
    blank = [[bg] * tw for _ in range(th)]
    out = []
    for i in range(n):
        for r in range(th):
            row = []
            for column in columns:
                row.extend((column[i] if i < len(column) else blank)[r])
            out.append(row)
    return out


def fam_genus_sort(train):
    for fname, (fwd, inv) in FRAMES.items():
        for bins in ("holes_first", "solid_first"):
            def fn(g, fwd=fwd, inv=inv, bins=bins):
                o = genus_sort(fwd(g), bins)
                return None if o is None else inv(o)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("topology:genus_sort[frame=%s,bins=%s]" % (fname, bins), 3, fn)
                return  # later frames that also fit are mirror-equivalent readings; keep the simplest


FAMILIES = (fam_genus_sort,)
