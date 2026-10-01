"""Line family for card 0ca9ddb6 (test-blind; induced only from train pairs).

Reading: every marker/object is a single-colour connected component.  Around it lie
"accentuated locations" of a few finite kinds (its sides, its corners/diagonals, its line
ends/flanks, at a distance d).  A decoration colour is induced per (object colour, location
kind) from the training pairs ("mapped colour"); objects whose colour maps to nothing stay bare.
"""
from collections import Counter

CARD = "0ca9ddb6"
LINE = "decorate marker/object with mapped color marker/object in accentuated locations"
READING = {
    "generator": "Around each marker/object, paint the colour mapped from that object's colour onto its "
                 "accentuated locations: the cells at distance d off its sides, off its corners (diagonals) or "
                 "off its line ends/flanks, with the kind of location and the colour induced per object colour.",
    "stop": "One stamp per object: only cells at distance d (or 1..d) of the chosen location kinds are painted; "
            "off-grid cells are clipped, by default only background cells are painted, and colours with no "
            "induced decoration get none.",
    "params": "frame ∈ {bbox: sides|corners, bbox: 8 directions, shape: edge|diagonal, line: ends|flanks|corners} · "
              "d ∈ {1,2,3} · span ∈ {at, upto} · colour map ∈ {same as object, constant, per-colour table} · "
              "who ∈ {any, singleton} · connectivity ∈ {4,8} · overwrite ∈ {no, yes}",
    "participants": "Single-colour connected components of non-background cells in the input (background = most "
                    "frequent colour); the object's colour keys the map; its bbox / pixels / axis give the locations.",
    "preconditions": "Input and output have the same size, some cell changes, every changed cell becomes a "
                     "non-background colour (decoration only adds paint), and a consistent induced map reproduces "
                     "every training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
DG = ((-1, -1), (-1, 1), (1, -1), (1, 1))
D8 = D4 + DG


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _objects(g, bg, conn):
    H, W = len(g), len(g[0])
    nb = D4 if conn == 4 else D8
    seen = [[False] * W for _ in range(H)]
    objs = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] == bg:
                continue
            c = g[y][x]
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] == c:
                        seen[p][q] = True
                        st.append((p, q))
            objs.append((c, frozenset(pix)))
    objs.sort(key=lambda o: (min(o[1]), o[0]))
    return objs


def _kinds(frame, pix, d, span):
    """Accentuated locations of one object: {kind: [cells]} (cells may be off-grid)."""
    ks = [d] if span == "at" else list(range(1, d + 1))
    ys = [p[0] for p in pix]; xs = [p[1] for p in pix]
    r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
    out = {}
    if frame in ("bbox", "bbox8"):
        for k in ks:
            parts = {
                "N": [(r0 - k, c) for c in range(c0, c1 + 1)],
                "S": [(r1 + k, c) for c in range(c0, c1 + 1)],
                "W": [(r, c0 - k) for r in range(r0, r1 + 1)],
                "E": [(r, c1 + k) for r in range(r0, r1 + 1)],
                "NW": [(r0 - k, c0 - k)], "NE": [(r0 - k, c1 + k)],
                "SW": [(r1 + k, c0 - k)], "SE": [(r1 + k, c1 + k)],
            }
            for n, cells in parts.items():
                key = n if frame == "bbox8" else ("side" if len(n) == 1 else "corner")
                out.setdefault(key, []).extend(cells)
    elif frame == "shape":
        edge = set()
        for k in ks:
            edge |= {(a + k * dy, b + k * dx) for a, b in pix for dy, dx in D4}
        edge -= pix
        diag = set()
        for k in ks:
            diag |= {(a + k * dy, b + k * dx) for a, b in pix for dy, dx in DG}
        diag -= pix | edge
        out = {"edge": sorted(edge), "diag": sorted(diag)}
    elif frame == "line":
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if (h == 1) == (w == 1) or len(pix) != h * w:
            return {}  # not a straight solid line (pixels have no axis)
        for k in ks:
            corner = [(r0 - k, c0 - k), (r0 - k, c1 + k), (r1 + k, c0 - k), (r1 + k, c1 + k)]
            if h == 1:
                end = [(r0, c0 - k), (r0, c1 + k)]
                flank = [(r0 - k, c) for c in range(c0, c1 + 1)] + [(r1 + k, c) for c in range(c0, c1 + 1)]
            else:
                end = [(r0 - k, c0), (r1 + k, c0)]
                flank = [(r, c0 - k) for r in range(r0, r1 + 1)] + [(r, c1 + k) for r in range(r0, r1 + 1)]
            for n, cells in (("end", end), ("flank", flank), ("corner", corner)):
                out.setdefault(n, []).extend(cells)
    return out


def _paint(g, bg, objs_k, cmap, mode, overwrite):
    H, W = len(g), len(g[0])
    out = [r[:] for r in g]
    for c, kinds in objs_k:
        key = c if mode == "table" else "*"
        for kind, cells in kinds.items():
            v = cmap.get((key, kind))
            if v is None:
                continue
            col = c if v == "same" else v
            for a, b in cells:
                if 0 <= a < H and 0 <= b < W and (overwrite or g[a][b] == bg):
                    out[a][b] = col
    return out


def _prep(g, conn, who, frame, d, span):
    bg = _bg(g)
    objs = _objects(g, bg, conn)
    if who == "singleton":
        objs = [o for o in objs if len(o[1]) == 1]
    return bg, [(c, _kinds(frame, pix, d, span)) for c, pix in objs]


def _induce(train, preps, mode):
    votes = {}
    for pr, (bg, objs_k) in zip(train, preps):
        gi, go = pr["input"], pr["output"]
        H, W = len(gi), len(gi[0])
        for c, kinds in objs_k:
            key = c if mode == "table" else "*"
            for kind, cells in kinds.items():
                for a, b in cells:
                    if 0 <= a < H and 0 <= b < W and gi[a][b] == bg:
                        v = go[a][b]
                        if mode == "same":
                            v = "same" if v == c else (None if v == bg else ("x", v))
                        elif v == bg:
                            v = None
                        votes.setdefault((key, kind), Counter())[v] += 1
    cmap = {}
    for kk, cnt in votes.items():
        v = sorted(cnt.items(), key=lambda t: (-t[1], repr(t[0])))[0][0]
        if isinstance(v, tuple):
            return None  # 'same' contradicted by a foreign colour
        if v is not None:
            cmap[kk] = v
    return cmap if cmap else None


def fam(train):
    if not train:
        return
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    changed = False
    for pr in train:
        gi, go = pr["input"], pr["output"]
        bg = _bg(gi)
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    changed = True
                    if b == bg:
                        return  # decoration never erases
    if not changed:
        return
    # structural pruning: skip settings that are identical to cheaper ones on the training inputs
    obj_sets = {cn: [_objects(p["input"], _bg(p["input"]), cn) for p in train] for cn in (4, 8)}
    conns = [4] if obj_sets[4] == obj_sets[8] else [4, 8]
    all_single = all(len(o[1]) == 1 for cn in conns for os_ in obj_sets[cn] for o in os_)
    whos = ["any"] if all_single else ["any", "singleton"]
    frames = [("bbox", 0), ("shape", 1), ("line", 2), ("bbox8", 3)]
    dspans = [(1, "at")] + [(d, s) for d in (2, 3) for s in ("at", "upto")]
    modes = [("same", 0), ("const", 1), ("table", 2)]
    found = []
    for frame, fc in frames:
        for d, span in dspans:
            for conn in conns:
                for who in whos:
                    preps = [_prep(p["input"], conn, who, frame, d, span) for p in train]
                    if not any(k for _, ok in preps for _, k in ok):
                        continue
                    for mode, mc in modes:
                        cmap = _induce(train, preps, mode)
                        if cmap is None:
                            continue
                        for ow in (False, True):
                            ok = all(_paint(p["input"], bg, ok_, cmap, mode, ow) == p["output"]
                                     for p, (bg, ok_) in zip(train, preps))
                            if not ok:
                                continue
                            cost = (10 + fc + 2 * (d - 1) + (span == "upto") + mc + len(cmap)
                                    + (who != "any") + (conn == 8) + ow)
                            name = "decorate[%s,d=%d,%s,%s,%s,c%d,%s]" % (
                                frame, d, span, mode, who, conn, "overwrite" if ow else "bg-only")
                            found.append((cost, len(found), name, (conn, who, frame, d, span, dict(cmap), mode, ow)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


def _make(conn, who, frame, d, span, cmap, mode, ow):
    def fn(grid):
        bg, objs_k = _prep(grid, conn, who, frame, d, span)
        return _paint(grid, bg, objs_k, cmap, mode, ow)
    return fn


FAMILIES = [fam]
