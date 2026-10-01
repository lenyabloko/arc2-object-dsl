"""Concept family "decorate" (test-blind; anti-unified from the member lines and their train pairs only).

One generator: (optionally) clean the scene of free objects, find the participants (objects or holes), take
each participant's accentuated locations of a few finite kinds (its own cells, its sides, its corners /
diagonals, its line ends / flanks, at distance d) and paint each kind with a colour drawn from a small
vocabulary {keep, own colour, host colour, alternate colour, a literal colour}, the value induced per
(key, kind) from the training pairs, key = constant, the participant's own colour or its host colour.
Members differ only in parameter values:
  0ca9ddb6  clean=none, who=objects, frame=bbox, d=1, key=own, side/corner -> literal, bg-only
  de809cff  clean=territory, who=holes, frame=bbox, d=1, key=const, self -> literal, side/corner -> alternate,
            overwrite
"""
from collections import Counter

CARD = "concept_decorate"
CONCEPT = "decorate"
MEMBERS = ["0ca9ddb6", "de809cff"]
READING = {
    "generator": "After optionally removing free objects (repainting them with the territory around them), "
                 "paint around each participant -- an object, or a background hole inside a region -- a mark of "
                 "the mapped colour on each of its accentuated locations (its own cells, the cells at distance d "
                 "off its sides, its corners or its line ends/flanks), the colour per location kind induced as "
                 "keep, the participant's own colour, its host colour, the alternate region colour or a fixed "
                 "colour, keyed by nothing, the own colour or the host colour.",
    "stop": "One stamp per participant: only cells of the chosen location kinds at distance d (or 1..d) are "
            "painted, off-grid cells are clipped, other participants are never painted over (their own 'self' "
            "marks go on top last), and kinds mapped to 'keep' stay as they are.",
    "params": "clean ∈ {none, territory} · bg ∈ {most frequent, most frequent on border} · who ∈ {objects, "
              "singletons, holes} · connectivity ∈ {4, 8} · frame ∈ {bbox: sides|corners, shape: edge|diagonal, "
              "line: ends|flanks|corners, bbox: 8 directions} (+ self) · d ∈ {1,2,3} · span ∈ {at, upto} · "
              "key ∈ {const, own colour, host colour} · value ∈ {keep, own, host, alternate, literal} · "
              "overwrite ∈ {background only, any non-participant cell}",
    "participants": "Objects: single-colour connected components of non-background cells (host = most common "
                    "colour around them). Holes: background cells with a same-colour neighbour horizontally and "
                    "vertically in some region (host = that region), grouped into components. Alternate colour = "
                    "the other region colour (with more than two regions: the one sharing the longest border). "
                    "Territory cleaning repaints non-background cells lacking that support, and blobs that fit "
                    "in a 2x2 box, with the surrounding territory.",
    "preconditions": "Input and output have the same size, some cell changes, after cleaning every changed cell "
                     "becomes a non-background colour, and a consistent induced colour map reproduces every "
                     "training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
DG = ((-1, -1), (-1, 1), (1, -1), (1, 1))
D8 = D4 + DG


def _bg(g, how):
    if how == "border":
        H, W = len(g), len(g[0])
        cnt = Counter(g[r][c] for r in range(H) for c in range(W) if r in (0, H - 1) or c in (0, W - 1))
    else:
        cnt = Counter(v for r in g for v in r)
    return max(sorted(cnt), key=lambda k: cnt[k])


# ---------------------------------------------------------------- territory (support test, cleaning, holes)
def _supported(M, r, c, col):
    H, W = len(M), len(M[0])
    if not ((c > 0 and M[r][c - 1] == col) or (c < W - 1 and M[r][c + 1] == col)):
        return False
    return (r > 0 and M[r - 1][c] == col) or (r < H - 1 and M[r + 1][c] == col)


def _n8count(M, r, c, col):
    H, W = len(M), len(M[0])
    return sum(1 for dr, dc in D8 if 0 <= r + dr < H and 0 <= c + dc < W and M[r + dr][c + dc] == col)


def _pick(M, r, c, cands):
    return max(cands, key=lambda v: (_n8count(M, r, c, v), -v))


def _wildcards(G, bg):
    """Background cells with >= 3 same-colour non-background 4-neighbours count as that colour."""
    H, W = len(G), len(G[0])
    M = [row[:] for row in G]
    for r in range(H):
        for c in range(W):
            if G[r][c] == bg:
                cnt = Counter(G[r + dr][c + dc] for dr, dc in D4
                              if 0 <= r + dr < H and 0 <= c + dc < W and G[r + dr][c + dc] != bg)
                best = [v for v in sorted(cnt) if cnt[v] >= 3]
                if best:
                    M[r][c] = best[0]
    return M


def _comps(H, W, inside, conn):
    """Connected components of cells with the same key inside(r, c) (None = not a cell of any component)."""
    nb = D4 if conn == 4 else D8
    seen, out = set(), []
    for y in range(H):
        for x in range(W):
            k = inside(y, x)
            if k is None or (y, x) in seen:
                continue
            st, pix = [(y, x)], []
            seen.add((y, x))
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and (p, q) not in seen and inside(p, q) == k:
                        seen.add((p, q))
                        st.append((p, q))
            out.append((k, frozenset(pix)))
    return out


def _clean(g, bg):
    """Remove free objects: unsupported cells are peeled from the solid side inwards, tiny blobs vanish."""
    H, W = len(g), len(g[0])
    colours = sorted({v for row in g for v in row if v != bg})
    G = [row[:] for row in g]
    for _ in range(H * W + 1):
        M = _wildcards(G, bg)
        U = [(r, c) for r in range(H) for c in range(W) if G[r][c] != bg and not _supported(M, r, c, G[r][c])]
        if not U:
            break
        Ms = [row[:] for row in M]
        for r, c in U:
            Ms[r][c] = None
        ch = {}
        for r, c in U:
            cands = [k for k in colours if _supported(Ms, r, c, k)]
            if cands:
                ch[(r, c)] = _pick(Ms, r, c, cands)
            elif not any(_supported(M, r, c, k) for k in colours):
                ch[(r, c)] = bg
        for (r, c), v in (ch or {p: bg for p in U}).items():
            G[r][c] = v
    for col, pix in _comps(H, W, lambda r, c: G[r][c] if G[r][c] != bg else None, 4):
        if max(p[0] for p in pix) - min(p[0] for p in pix) < 2 and max(p[1] for p in pix) - min(p[1] for p in pix) < 2:
            for a, b in pix:
                G[a][b] = bg
    return G


def _alt_map(G, bg):
    H, W = len(G), len(G[0])
    colours = sorted({v for row in G for v in row if v != bg})
    if len(colours) == 2:
        return {colours[0]: colours[1], colours[1]: colours[0]}
    adj = Counter()
    for r in range(H):
        for c in range(W):
            for rr, cc in ((r + 1, c), (r, c + 1)):
                if rr < H and cc < W and bg not in (G[r][c], G[rr][cc]) and G[r][c] != G[rr][cc]:
                    adj[(G[r][c], G[rr][cc])] += 1
                    adj[(G[rr][cc], G[r][c])] += 1
    alt = {}
    for a in colours:
        o = [(adj[(a, b)], -b) for b in colours if b != a and adj[(a, b)]]
        if o:
            alt[a] = -max(o)[1]
    return alt


# ---------------------------------------------------------------- participants and their accentuated locations
def _participants(G, bg, who, conn):
    """[(own colour, host colour, pixels)] sorted by position."""
    H, W = len(G), len(G[0])
    if who == "holes":
        colours = sorted({v for row in G for v in row if v != bg})
        M = _wildcards(G, bg)
        host = {}
        for r in range(H):
            for c in range(W):
                if G[r][c] == bg:
                    cands = [k for k in colours if _supported(M, r, c, k)]
                    if cands:
                        host[(r, c)] = _pick(M, r, c, cands)
        parts = [(bg, h, pix) for h, pix in _comps(H, W, lambda r, c: host.get((r, c)), conn)]
    else:
        parts = []
        for col, pix in _comps(H, W, lambda r, c: G[r][c] if G[r][c] != bg else None, conn):
            if who == "singletons" and len(pix) > 1:
                continue
            around = Counter(G[a + dy][b + dx] for a, b in pix for dy, dx in D4
                             if 0 <= a + dy < H and 0 <= b + dx < W and (a + dy, b + dx) not in pix)
            parts.append((col, max(sorted(around), key=lambda k: around[k]) if around else bg, pix))
    parts.sort(key=lambda o: (min(o[2]), o[0]))
    return parts


def _kinds(frame, pix, d, span):
    """{kind: [cells]} (cells may be off-grid); 'self' is always present."""
    ks = [d] if span == "at" else list(range(1, d + 1))
    r0, r1 = min(p[0] for p in pix), max(p[0] for p in pix)
    c0, c1 = min(p[1] for p in pix), max(p[1] for p in pix)
    out = {"self": sorted(pix)}
    if frame in ("bbox", "bbox8"):
        for k in ks:
            parts = {"N": [(r0 - k, c) for c in range(c0, c1 + 1)], "S": [(r1 + k, c) for c in range(c0, c1 + 1)],
                     "W": [(r, c0 - k) for r in range(r0, r1 + 1)], "E": [(r, c1 + k) for r in range(r0, r1 + 1)],
                     "NW": [(r0 - k, c0 - k)], "NE": [(r0 - k, c1 + k)],
                     "SW": [(r1 + k, c0 - k)], "SE": [(r1 + k, c1 + k)]}
            for n, cells in parts.items():
                out.setdefault(n if frame == "bbox8" else ("side" if len(n) == 1 else "corner"), []).extend(cells)
    elif frame == "shape":
        edge = {(a + k * dy, b + k * dx) for k in ks for a, b in pix for dy, dx in D4} - pix
        diag = {(a + k * dy, b + k * dx) for k in ks for a, b in pix for dy, dx in DG} - pix - edge
        out.update(edge=sorted(edge), diag=sorted(diag))
    elif frame == "line":
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if (h == 1) == (w == 1) or len(pix) != h * w:
            return out  # not a straight solid line
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


def _key(keym, col, host):
    return "*" if keym == "const" else (col if keym == "own" else host)


def _resolve(v, col, host, alt):
    if v == "own":
        return col
    if v == "host":
        return host
    if v == "alt":
        return alt
    return v if isinstance(v, int) else None  # "keep"


def _targets(G, bg, pset, kind, cells, ow):
    H, W = len(G), len(G[0])
    for a, b in cells:
        if 0 <= a < H and 0 <= b < W and (kind == "self" or ((a, b) not in pset and (ow or G[a][b] == bg))):
            yield a, b


def _prep(g, clean, bgm, who, conn, frame, d, span, base=None):
    bg, G = base if base else (_bg(g, bgm), None)
    if G is None:
        G = _clean(g, bg) if clean == "territory" else [r[:] for r in g]
    alt = _alt_map(G, bg)
    parts = [(col, host, alt.get(host), _kinds(frame, pix, d, span)) for col, host, pix in _participants(G, bg, who, conn)]
    return G, bg, parts, frozenset(p for _, _, _, k in parts for p in k["self"])


VALS = ("keep", "own", "host", "alt")  # preference order on ties; literal colours last


def _induce(train, preps, keym, both):
    """Colour maps (bg-only, overwrite) from one pass: bg-only targets are a subset of the overwrite targets."""
    vb, vo = {}, {}
    for pr, (G, bg, parts, pset) in zip(train, preps):
        go, H, W = pr["output"], len(G), len(G[0])
        for col, host, alt, kinds in parts:
            key = "*" if keym == "const" else (col if keym == "own" else host)
            for kind, cells in kinds.items():
                kk = (key, kind)
                co = vo.get(kk)
                if co is None:
                    co, cb = vo[kk], vb[kk] = {}, {}
                else:
                    cb = vb[kk]
                sf = kind == "self"
                for a, b in cells:
                    if a < 0 or b < 0 or a >= H or b >= W:
                        continue
                    if sf:
                        tb = True
                    elif (a, b) in pset:
                        continue
                    else:
                        tb = both and G[a][b] == bg
                    o = go[a][b]
                    ls = [o]
                    if o == G[a][b]:
                        ls.append("keep")
                    if o == col:
                        ls.append("own")
                    if o == host:
                        ls.append("host")
                    if o == alt:
                        ls.append("alt")
                    for l in ls:
                        co[l] = co.get(l, 0) + 1
                    if tb:
                        for l in ls:
                            cb[l] = cb.get(l, 0) + 1
    return (_choose(vb) if both else None), _choose(vo)


def _choose(votes):
    cmap = {}
    for kk, cnt in votes.items():
        if cnt:
            v = sorted(cnt.items(), key=lambda t: (-t[1], VALS.index(t[0]) if t[0] in VALS else 9, repr(t[0])))[0][0]
            if v != "keep":
                cmap[kk] = v
    return cmap or None


def _covers(G, bg, parts, pset, chg):
    """(bg-only, overwrite): can the targets of these participants reach every changed cell at all?"""
    K = set()
    for _, _, _, kinds in parts:
        for kind, cells in kinds.items():
            if kind != "self":
                K.update(cells)
    oko = all(x in pset or x in K for x in chg)
    return oko and all(x in pset or G[x[0]][x[1]] == bg for x in chg), oko


def _paint(G, bg, parts, pset, cmap, keym, ow):
    out = [r[:] for r in G]
    for last in (False, True):
        for col, host, alt, kinds in parts:
            key = _key(keym, col, host)
            for kind, cells in kinds.items():
                if (kind == "self") != last or (key, kind) not in cmap:
                    continue
                c = _resolve(cmap[(key, kind)], col, host, alt)
                if c is not None:
                    for a, b in _targets(G, bg, pset, kind, cells, ow):
                        out[a][b] = c
    return out


def _self_fits(train, bases, alts, ps, keym):
    """Participant cells are painted by their own 'self' mark only, and the self part of the colour map is voted
    by those cells alone (whatever the frame, d, span, overwrite): it must already reproduce them."""
    votes, P = {}, []
    for p, (bg, G), alt, pp in zip(train, bases, alts, ps):
        go = p["output"]
        for col, host, pix in pp:
            key = ("*" if keym == "const" else (col if keym == "own" else host), "self")
            cnt, al = votes.setdefault(key, {}), alt.get(host)
            P.append((go, G, col, host, al, key, pix))
            for a, b in pix:
                o = go[a][b]
                for l, hit in ((o, True), ("keep", o == G[a][b]), ("own", o == col), ("host", o == host),
                               ("alt", o == al)):
                    if hit:
                        cnt[l] = cnt.get(l, 0) + 1
    smap = _choose(votes) or {}
    for go, G, col, host, al, key, pix in P:
        c = _resolve(smap[key], col, host, al) if key in smap else None
        if any(go[a][b] != (G[a][b] if c is None else c) for a, b in pix):
            return False
    return True


def fam(train):
    if not train or any(len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0])
                        for p in train):
        return
    if all(p["input"] == p["output"] for p in train):
        return
    bgms = ["mode"] + (["border"] if any(_bg(p["input"], "mode") != _bg(p["input"], "border") for p in train) else [])
    found, kcache = [], {}  # kinds are read-only: shared between settings with the same participant
    for ci, clean in enumerate(("none", "territory")):
        for bi, bgm in enumerate(bgms):
            bases = []
            for p in train:
                bg = _bg(p["input"], bgm)
                G = _clean(p["input"], bg) if clean == "territory" else [r[:] for r in p["input"]]
                bases.append((bg, G))
            if clean == "territory" and all(G == p["input"] for (bg, G), p in zip(bases, train)):
                continue  # cleaning is a no-op on the training inputs: same as clean=none
            if any(o != x and o == bg for (bg, G), p in zip(bases, train)
                   for rg, ro in zip(G, p["output"]) for x, o in zip(rg, ro)):
                continue  # decoration only adds paint
            if all(G == p["output"] for (bg, G), p in zip(bases, train)):
                continue
            alts = [_alt_map(G, bg) for bg, G in bases]
            chg = [[(a, b) for a, (rg, ro) in enumerate(zip(G, p["output"])) for b, (x, o) in enumerate(zip(rg, ro)) if x != o]
                   for (bg, G), p in zip(bases, train)]
            seen_parts = []
            for wi, who in enumerate(("objects", "singletons", "holes")):
                for conn in (4, 8):
                    ps = [_participants(G, bg, who, conn) for bg, G in bases]
                    if not any(ps) or ps in seen_parts:
                        continue  # no participants, or the same participants as a cheaper setting
                    seen_parts.append(ps)
                    psets = [frozenset(q for _, _, pix in pp for q in pix) for pp in ps]
                    keyms = ["const"] + (["own"] if len({o[0] for pp in ps for o in pp}) > 1 else []) \
                        + (["host"] if len({o[1] for pp in ps for o in pp}) > 1 else [])
                    kms = [(ki, keym) for ki, keym in enumerate(keyms) if _self_fits(train, bases, alts, ps, keym)]
                    if not kms:
                        continue
                    for fi, frame in enumerate(("bbox", "shape", "line", "bbox8")):
                        for d, span in [(1, "at")] + [(d, s) for d in (2, 3) for s in ("at", "upto")]:
                            preps, okb = [], True
                            for j in range(len(train)):
                                bg, G = bases[j]
                                parts = []
                                for col, host, pix in ps[j]:
                                    kd = kcache.get((frame, d, span, pix))
                                    if kd is None:
                                        kd = kcache[(frame, d, span, pix)] = _kinds(frame, pix, d, span)
                                    parts.append((col, host, alts[j].get(host), kd))
                                b_, o_ = _covers(G, bg, parts, psets[j], chg[j])
                                if not o_:
                                    break  # some changed cell is no target of any kind: no colour map can fit
                                okb = okb and b_
                                preps.append((G, bg, parts, psets[j]))
                            if len(preps) < len(train):
                                continue
                            for ki, keym in kms:
                                cmaps = _induce(train, preps, keym, okb)
                                for ow in (False, True):
                                    cmap = cmaps[ow]
                                    if cmap is None or not all(_paint(G, bg, parts, pset, cmap, keym, ow) == p["output"]
                                                               for p, (G, bg, parts, pset) in zip(train, preps)):
                                        continue
                                    cost = (10 + 3 * ci + bi + wi + fi + 2 * (d - 1) + (span == "upto") + ki
                                            + len(cmap) + (conn == 8) + ow)
                                    name = "decorate[clean=%s,bg=%s,%s,c%d,%s,d=%d,%s,key=%s,%s]" % (
                                        clean, bgm, who, conn, frame, d, span, keym, "overwrite" if ow else "bg-only")
                                    found.append((cost, len(found), name,
                                                  (clean, bgm, who, conn, frame, d, span, dict(cmap), keym, ow)))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


def _make(clean, bgm, who, conn, frame, d, span, cmap, keym, ow):
    def fn(grid):
        G, bg, parts, pset = _prep(grid, clean, bgm, who, conn, frame, d, span)
        return _paint(G, bg, parts, pset, cmap, keym, ow)
    return fn


FAMILIES = [fam]
