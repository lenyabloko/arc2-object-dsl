"""Concept family: recolour_by_mapping (test-blind; anti-unified from member lines 103eff5b, 20fb2937, d2acf2cb).

One generator. A colour mapping M is read from a source; the target zone is cut into units; every unit is
repainted through M by one painting rule; the answer is the repainted grid (optionally with the legend erased)
or a crop of it.
  source  examples  M = colour -> colour function read off the changed cells of the training pairs
          legend    one separator band splits the grid; on the legend side every key object (its colour occurs on
                    the other side) takes its nearest value object; M = key colour -> value patch
          palette   M = dominant non-background colour -> the small multicoloured patch formed by all other colours
  unit    object (8-conn one-colour objects of a key colour) | colour (all cells of one key colour) |
          zone (the whole target zone) | line (interior of rows/columns with a marker colour at both border ends)
  paint   map   cellwise colour lookup; dir forward, or majority: per unit, the side of the mapping (source or
                target colours) holding more cells is mapped (forward, or back through the inverse)
          stamp erase the unit and draw the value patch centred on it, clipped to the target zone
          fit   turn the patch by the square symmetry the training prefers, scale it to the unit's box and
                repaint each unit cell with the patch cell under it
Members: 103eff5b = palette/object/fit; 20fb2937 = legend/object/stamp, cropped to the target side;
d2acf2cb = examples/line/map (involutive mapping: forward swaps, majority picks the direction per line).
"""
from functools import lru_cache

CARD = "concept_recolour_by_mapping"
CONCEPT = "recolour_by_mapping"
MEMBERS = ["103eff5b", "20fb2937", "d2acf2cb"]
READING = {
    "generator": "Read a colour mapping (from the training changes, from a legend beyond a separator, or from a "
                 "small palette patch), cut the target zone into units, and repaint every unit through the "
                 "mapping: cellwise colour lookup (forward, or per unit in the direction its majority side asks), "
                 "a value patch stamped centred on it, or the patch turned and scaled to fit it.",
    "stop": "Each unit is repainted once, from the input, in reading order (later stamps overwrite earlier ones; a "
            "cell shared by two units keeps the first one's colour under map); cells outside units, colours "
            "outside the mapping and the background stay; a majority tie leaves the unit as it is.",
    "params": "source ∈ {examples, legend, palette} · side ∈ {smaller, larger} (legend side, legend only) · "
              "unit ∈ {object, colour, zone, line(marker ∈ colours present and unchanged in every train input)} · "
              "paint ∈ {map, stamp, fit} · dir ∈ {forward, majority(partition of the mapped pairs into two sides: "
              "keys|values for a legend, one of ≤8 induced partitions for examples)} (map) · "
              "sym = first D4 element in train-preference order whose scaled silhouette matches (fit) · "
              "mask ∈ {strict, loose} (fit) · out ∈ {full, erase legend} if shapes are kept, else {zone, units} "
              "(crop to the target zone / to the painted units) · bg = most frequent colour",
    "participants": "Background: most frequent colour. Legend zone and target zone: the two sides of the single "
                    "uniform separator band (legend), the bounding box of all non-dominant colours vs the rest "
                    "(palette), nothing vs the whole grid (examples). Entries: key colour -> value patch. Units: "
                    "key-coloured objects or colour classes in the target zone, the whole zone, or marker-bounded "
                    "line interiors.",
    "preconditions": "examples: same shapes and the changed cells define a colour function (majority also needs "
                     "it to complete to an involution of ≤4 pairs); legend: exactly one separator band, every key "
                     "has a unique nearest value, no key maps to two values; palette: ≥2 non-background colours; "
                     "fit: the unit box is an integer multiple of the turned patch (strict: silhouettes agree); "
                     "at least one unit is painted.",
}

D4 = [
    ("id", lambda g: [list(r) for r in g]),
    ("rot90cw", lambda g: [list(r) for r in zip(*g[::-1])]),
    ("rot180", lambda g: [list(r)[::-1] for r in g[::-1]]),
    ("rot90ccw", lambda g: [list(r) for r in zip(*g)][::-1]),
    ("flip_lr", lambda g: [list(r)[::-1] for r in g]),
    ("flip_ud", lambda g: [list(r) for r in g[::-1]]),
    ("transpose", lambda g: [list(r) for r in zip(*g)]),
    ("antitranspose", lambda g: [list(r)[::-1] for r in zip(*g)][::-1]),
]


# ---------------------------------------------------------------- participants

def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return min(cnt, key=lambda c: (-cnt[c], c))


def _box(cells):
    ys = [p[0] for p in cells]
    xs = [p[1] for p in cells]
    return min(ys), min(xs), max(ys), max(xs)


def _objects(g, cells):
    """8-connected one-colour components of the cell set, each sorted, in reading order."""
    seen, out = set(), []
    for s in sorted(cells):
        if s in seen:
            continue
        col, stack, comp = g[s[0]][s[1]], [s], []
        seen.add(s)
        while stack:
            y, x = stack.pop()
            comp.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in cells and q not in seen and g[q[0]][q[1]] == col:
                        seen.add(q)
                        stack.append(q)
        out.append(sorted(comp))
    return out


def _band(g, bg):
    """The single band of full uniform non-background rows, (lo, hi), strictly inside the grid; or None.
    Several bands: keep those whose colour occurs nowhere else."""
    H, bands, r = len(g), [], 0
    uni = [row[0] if row[0] != bg and all(v == row[0] for v in row) else None for row in g]
    while r < H:
        if uni[r] is None:
            r += 1
            continue
        s = r
        while r + 1 < H and uni[r + 1] == uni[s]:
            r += 1
        bands.append((s, r, uni[s]))
        r += 1
    if len(bands) > 1:
        bands = [b for b in bands if not any(v == b[2] for y in range(H) if not b[0] <= y <= b[1] for v in g[y])]
    if len(bands) != 1 or bands[0][0] == 0 or bands[0][1] == H - 1:
        return None
    return bands[0][:2]


def _patch(g, cells, transparent):
    """Bounding-box crop of the cells; with `transparent`, crop cells outside the set are None."""
    r0, c0, r1, c1 = _box(cells)
    keep = set(cells)
    return [[g[y][x] if not transparent or (y, x) in keep else None for x in range(c0, c1 + 1)]
            for y in range(r0, r1 + 1)]


@lru_cache(maxsize=2048)
def _parse(g, source, side):
    """(bg, legend cells, target cells, target box, M = {key colour: patch}) or None."""
    H, W = len(g), len(g[0])
    bg = _bg(g)
    cells = [(y, x) for y in range(H) for x in range(W)]
    if source == "examples":
        return bg, (), frozenset(cells), (0, 0, H - 1, W - 1), {}
    if source == "palette":
        cnt = {}
        for y, x in cells:
            if g[y][x] != bg:
                cnt[g[y][x]] = cnt.get(g[y][x], 0) + 1
        if len(cnt) < 2:
            return None
        c = min(cnt, key=lambda k: (-cnt[k], k))
        r0, c0, r1, c1 = _box([p for p in cells if g[p[0]][p[1]] not in (bg, c)])
        leg = [(y, x) for y, x in cells if r0 <= y <= r1 and c0 <= x <= c1]
        tgt = frozenset(cells) - set(leg)
        if not tgt:
            return None
        return bg, tuple(leg), tgt, _box(tgt), {c: _patch(g, leg, False)}
    found = []
    for axis, gg in ((0, g), (1, tuple(zip(*g)))):
        b = _band(gg, bg)
        if b:
            found.append((axis, b, len(gg), len(gg[0])))
    if len(found) != 1:
        return None
    axis, (lo, hi), n, m = found[0]
    before, after = list(range(lo)), list(range(hi + 1, n))
    L, T = (before, after) if (len(before) <= len(after)) == (side == "smaller") else (after, before)
    at = (lambda i, j: (i, j)) if axis == 0 else (lambda i, j: (j, i))
    leg = [at(i, j) for i in L for j in range(m)]
    tgt = frozenset(at(i, j) for i in T for j in range(m))
    tcols = {g[y][x] for y, x in tgt} - {bg}
    objs = _objects(g, {p for p in leg if g[p[0]][p[1]] != bg})
    keys = [o for o in objs if g[o[0][0]][o[0][1]] in tcols]
    vals = [o for o in objs if g[o[0][0]][o[0][1]] not in tcols]
    if not keys or not vals:
        return None
    M, used = {}, set()
    for k in keys:
        ds = sorted((min(abs(a - c) + abs(b - d) for a, b in k for c, d in v), i) for i, v in enumerate(vals))
        if (len(ds) > 1 and ds[0][0] == ds[1][0]) or ds[0][1] in used:
            return None
        used.add(ds[0][1])
        kc, p = g[k[0][0]][k[0][1]], _patch(g, vals[ds[0][1]], True)
        if M.setdefault(kc, p) != p:
            return None
    return bg, tuple(leg), tgt, _box(tgt), M


# ---------------------------------------------------------------- mapping helpers

def _complete(T):
    """Involutive completion of a colour function (a->b adds b->a), or None if it is not a matching."""
    full = dict(T)
    for a, b in T.items():
        if full.setdefault(b, a) != a:
            return None
    return full if all(full[full[a]] == a for a in full) else None


def _partitions(full):
    """All splits of the matched pairs into two sides (first pair fixed), as {colour: 0/1}; ≤4 pairs."""
    pairs = sorted({tuple(sorted((a, b))) for a, b in full.items() if a != b})
    if not pairs or len(pairs) > 4:
        return []
    out = []
    for bits in range(2 ** (len(pairs) - 1)):
        side = {}
        for i, (a, b) in enumerate(pairs):
            s = (bits >> (i - 1)) & 1 if i else 0
            side[a], side[b] = s, 1 - s
        out.append(side)
    return out


def _single(p):
    cols = {v for row in p for v in row if v is not None}
    return cols.pop() if len(cols) == 1 else None


# ---------------------------------------------------------------- units and painting

def _units(g, tgt, unit, keys, marker):
    H, W = len(g), len(g[0])
    if unit == "zone":
        return [sorted(tgt)]
    if unit == "line":
        regs = [[(r, x) for x in range(1, W - 1) if (r, x) in tgt]
                for r in range(H) if W >= 3 and g[r][0] == marker == g[r][W - 1]]
        regs += [[(y, x) for y in range(1, H - 1) if (y, x) in tgt]
                 for x in range(W) if H >= 3 and g[0][x] == marker == g[H - 1][x]]
        return [u for u in regs if u]
    cells = {p for p in tgt if g[p[0]][p[1]] in keys}
    if unit == "object":
        return _objects(g, cells)
    by = {}
    for p in sorted(cells):
        by.setdefault(g[p[0]][p[1]], []).append(p)
    return sorted(by.values())


def _paint(g, res, u, how, bg, tgt, M, T, side, pref, mask, done):
    """Repaint unit u into res; False when the unit cannot be painted."""
    if how == "map":
        todo = [p for p in u if g[p[0]][p[1]] in T]
        if side is not None:                       # majority: map the side holding more of the unit's cells
            n = [0, 0]
            for y, x in todo:
                n[side[g[y][x]]] += 1
            if n[0] == n[1]:
                return True
            todo = [(y, x) for y, x in todo if side[g[y][x]] == (0 if n[0] > n[1] else 1)]
        for y, x in todo:
            if (y, x) not in done:
                done.add((y, x))
                res[y][x] = T[g[y][x]]
        return True
    patch = M.get(g[u[0][0]][u[0][1]])
    if patch is None:
        return False
    r0, c0, r1, c1 = _box(u)
    if how == "stamp":
        for y, x in u:
            res[y][x] = bg
        h, w = len(patch), len(patch[0])
        top, left = r0 + (r1 - r0 + 1 - h) // 2, c0 + (c1 - c0 + 1 - w) // 2
        for i in range(h):
            for j in range(w):
                if patch[i][j] is not None and (top + i, left + j) in tgt:
                    res[top + i][left + j] = patch[i][j]
        return True
    on = set(u)
    for s in pref:                                 # fit: first preferred symmetry that fits the unit's box
        Q = D4[s][1](patch)
        h, w = len(Q), len(Q[0])
        if (r1 - r0 + 1) % h or (c1 - c0 + 1) % w:
            continue
        sy, sx = (r1 - r0 + 1) // h, (c1 - c0 + 1) // w
        val = [[Q[(y - r0) // sy][(x - c0) // sx] for x in range(c0, c1 + 1)] for y in range(r0, r1 + 1)]
        if mask == "strict" and any(((y, x) in on) != (val[y - r0][x - c0] not in (None, bg))
                                    for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)):
            continue
        for y, x in u:
            v = val[y - r0][x - c0]
            res[y][x] = bg if v is None else v
        return True
    return False


def _make(spec, T0=None, side0=None, pref=None):
    source, lside, unit, marker, how, dirn, mask, out = spec

    def fn(g):
        P = _parse(tuple(map(tuple, g)), source, lside)
        if P is None:
            return None
        bg, leg, tgt, box, M = P
        T, side = T0, side0
        if source != "examples":
            T = {k: _single(p) for k, p in M.items() if _single(p) is not None}
            if how == "map" and dirn == "majority":
                T = _complete(T)
                if T is None or set(M) & {T[k] for k in M}:
                    return None
                side = {c: int(c not in M) for c in T}
        keys = set(T) if how == "map" else set(M)
        units = _units(g, tgt, unit, keys, marker)
        if not units:
            return None
        res, done = [list(r) for r in g], set()
        for u in units:
            if not _paint(g, res, u, how, bg, tgt, M, T, side, pref, mask, done):
                return None
        if res == [list(r) for r in g]:
            return None
        if out == "erase":
            for y, x in leg:
                res[y][x] = bg
        if out in ("zone", "units"):
            r0, c0, r1, c1 = box if out == "zone" else _box([p for u in units for p in u])
            res = [row[c0:c1 + 1] for row in res[r0:r1 + 1]]
        return res
    return fn


def _fits(fn, train):
    try:
        return all(fn(p["input"]) == p["output"] for p in train)
    except Exception:
        return False


# ---------------------------------------------------------------- family

def fam(train):
    if not train or any(not p["input"] or not p["input"][0] for p in train):
        return
    same = all(len(p["input"]) == len(p["output"]) and len(p["input"][0]) == len(p["output"][0]) for p in train)
    outs = ("full", "erase") if same else ("zone", "units")
    T = {} if same else None
    for p in (train if same else ()):
        for ri, ro in zip(p["input"], p["output"]):
            for a, b in zip(ri, ro):
                if a != b and T is not None and T.setdefault(a, b) != b:
                    T = None
    common = None
    for p in train:
        cs = {v for row in p["input"] for v in row}
        common = cs if common is None else common & cs
    moved = set(T or ()) | set((T or {}).values())
    lines = [("line", m, 2 + i) for i, m in enumerate(sorted(common - moved))]
    units = [("object", None, 0), ("colour", None, 1), ("zone", None, 1)] + lines

    specs = []                                     # (cost, spec, T, side)
    if T:
        full = _complete(T)
        dirs = [("forward", T, None, 0)] + [("majority", full, s, 1 + i)
                                           for i, s in enumerate(_partitions(full) if full else [])]
        for unit, m, ui in units:
            for dirn, TT, side, di in dirs:
                specs.append((1 + ui + di, ("examples", None, unit, m, "map", dirn, None, "full"), TT, side))
    for src, lside, si in (("legend", "smaller", 1), ("legend", "larger", 2), ("palette", None, 1)):
        if any(_parse(tuple(map(tuple, p["input"])), src, lside) is None for p in train):
            continue
        for unit, m, ui in units:
            for how, opts in (("map", (("forward", None, 0), ("majority", None, 1))),
                              ("stamp", ((None, None, 1),)),
                              ("fit", ((None, "strict", 1), (None, "loose", 2)))):
                if how != "map" and unit not in ("object", "colour"):
                    continue
                for dirn, mask, hi in opts:
                    for oi, out in enumerate(outs):
                        specs.append((si + ui + hi + oi, (src, lside, unit, m, how, dirn, mask, out), None, None))
    progs = []
    for cost, spec, TT, side in specs:
        pref = None
        if spec[4] == "fit":                       # symmetry preference: D4 elements ranked by train pairs fitted
            score = [sum(_fits(_make(spec, pref=[s]), [p]) for p in train) for s in range(len(D4))]
            if not any(score):
                continue
            pref = sorted(range(len(D4)), key=lambda s: (-score[s], s))
        name = "recolour_by_mapping[source=%s,side=%s,unit=%s,marker=%s,paint=%s,dir=%s,mask=%s,out=%s%s]" % (
            spec[:8] + (",A=" + "".join(str(c) for c in sorted(side) if side[c] == 0) if side else "",))
        if pref:
            name = name[:-1] + ",sym=auto(%s)]" % D4[pref[0]][0]
        progs.append((cost, name, _make(spec, TT, side, pref)))
    progs.sort(key=lambda t: (t[0], t[1]))
    seen = set()
    for cost, name, fn in progs:
        if not _fits(fn, train):
            continue
        cls = name.split(",marker")[0] + name.split(",paint")[1].split(",out")[0]
        if cls in seen:
            continue                               # same reading class as a cheaper fitted program
        seen.add(cls)
        yield name, cost, fn


FAMILIES = [fam]
