"""Line family for card d2acf2cb (test-blind; written from the reviewer's line and train pairs only).

Reading: a colour-pair mapping f (here two pairs of colours, side A -> side B) is applied inside
regions; each region picks its own direction from what it contains. A region made of side-A colours
is mapped forward (A -> B); a region made of side-B colours is mapped by the inverse (B -> A). In
d2acf2cb the regions are the rows / columns that carry a marker colour at both grid borders; the first
training example holds lines already in the "B" colours, so it shows the inverse mapping.

The family is generic over the region kind (lines bounded by a marker at both borders, segments
between two markers on a line, 4-connected objects of mapped colours, the whole grid), and over the
direction rule (majority side per region, or a cellwise involution as the degenerate case).
"""

CARD = "d2acf2cb"
LINE = "the first example does inverse"
READING = {
    "generator": "Every line (row or column) that has the marker colour at both of its border ends gets its "
                 "interior recoloured by a colour-pair mapping induced from the changes (e.g. 0->8, 6->7). "
                 "The direction is chosen per line: a line made of the mapping's source colours is mapped "
                 "forward, a line already made of its target colours is mapped back by the inverse "
                 "(8->0, 7->6) -- which is what the first example shows.",
    "stop": "Each region is recoloured once, from the input; cells outside regions, marker cells and "
            "colours outside the mapping stay unchanged. A tie between the two sides leaves the region as is.",
    "params": "region in {span(marker at both borders), between(consecutive markers), component(4-conn. "
              "mapped colours), grid} · axes in {both, rows, cols} (line regions) · "
              "marker in {colours unchanged in every train pair} · "
              "dir in {majority(per region: forward on side A or inverse on side B), swap(cellwise involution)} · "
              "mapping = colour pairs induced from changed cells; sides from co-occurrence in a region",
    "participants": "Marker: an unchanged colour sitting at both ends of every changed line. Regions: the "
                    "interiors of those lines (or the chosen region kind). Mapping: the matching of colour "
                    "pairs {a,b} read off every changed cell (a->b or b->a both count as the same pair); "
                    "side A / side B split so colours changing together in one region share a side.",
    "preconditions": "Input and output have the same shape in every train pair; the changed cells form a "
                     "consistent colour matching (each colour has one partner, pairs disjoint); some region "
                     "kind covers every changed cell.",
}


# ---------------------------------------------------------------- mapping induction

def _changes(train):
    """Undirected colour matching {a: b, b: a} from all changed cells, or None if inconsistent."""
    part = {}
    any_change = False
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or any(len(a) != len(b) for a, b in zip(gi, go)):
            return None
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a == b:
                    continue
                any_change = True
                if part.get(a, b) != b or part.get(b, a) != a:
                    return None
                part[a] = b
                part[b] = a
    if not any_change:
        return None
    return part


# ---------------------------------------------------------------- regions

def _span_lines(g, marker, axes):
    H, W = len(g), len(g[0])
    regs = []
    if axes in ("both", "rows") and W >= 3:
        for r in range(H):
            if g[r][0] == marker and g[r][W - 1] == marker:
                regs.append([(r, c) for c in range(1, W - 1)])
    if axes in ("both", "cols") and H >= 3:
        for c in range(W):
            if g[0][c] == marker and g[H - 1][c] == marker:
                regs.append([(r, c) for r in range(1, H - 1)])
    return regs


def _between_lines(g, marker, axes):
    H, W = len(g), len(g[0])
    regs = []
    lines = []
    if axes in ("both", "rows"):
        lines += [[(r, c) for c in range(W)] for r in range(H)]
    if axes in ("both", "cols"):
        lines += [[(r, c) for r in range(H)] for c in range(W)]
    for line in lines:
        idx = [i for i, (r, c) in enumerate(line) if g[r][c] == marker]
        for i, j in zip(idx, idx[1:]):
            if j - i > 1:
                regs.append(line[i + 1:j])
    return regs


def _components(g, cols):
    H, W = len(g), len(g[0])
    seen = set()
    regs = []
    for r in range(H):
        for c in range(W):
            if (r, c) in seen or g[r][c] not in cols:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            comp = []
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] in cols:
                        seen.add((yy, xx))
                        stack.append((yy, xx))
            regs.append(sorted(comp))
    return regs


def _regions(g, kind, marker, axes, mapped):
    if kind == "span":
        return _span_lines(g, marker, axes)
    if kind == "between":
        return _between_lines(g, marker, axes)
    if kind == "component":
        return _components(g, mapped)
    H, W = len(g), len(g[0])
    return [[(r, c) for r in range(H) for c in range(W)]]


# ---------------------------------------------------------------- sides (A / B)

def _sides(train, part, kind, marker, axes):
    """Assign each mapped colour to side 0 or 1 (partners opposite; colours that change together
    inside one region on the same side). Returns {colour: side} or None on contradiction."""
    mapped = set(part)
    parent = {c: c for c in mapped}
    parity = {c: 0 for c in mapped}

    def find(c):
        if parent[c] == c:
            return c, 0
        root, p = find(parent[c])
        parent[c] = root
        parity[c] ^= p
        return root, parity[c]

    def union(a, b, rel):           # rel 0: same side, 1: opposite
        ra, pa = find(a)
        rb, pb = find(b)
        if ra == rb:
            return (pa ^ pb) == rel
        parent[rb] = ra
        parity[rb] = pa ^ pb ^ rel
        return True

    for a in sorted(mapped):
        if not union(a, part[a], 1):
            return None
    for p in train:
        gi, go = p["input"], p["output"]
        for reg in _regions(gi, kind, marker, axes, mapped):
            src = sorted({gi[r][c] for r, c in reg if gi[r][c] != go[r][c]})
            for a, b in zip(src, src[1:]):
                if not union(a, b, 0):
                    return None
    side = {}
    for c in sorted(mapped):
        side[c] = find(c)[1]
    # deterministic orientation: side 0 holds the smallest colour of each class (already by root order)
    return side


# ---------------------------------------------------------------- program

def _make(part, side, kind, marker, axes, rule):
    mapped = set(part)

    def fn(g):
        out = [list(row) for row in g]
        done = {}
        for reg in _regions(g, kind, marker, axes, mapped):
            n0 = sum(1 for r, c in reg if g[r][c] in mapped and side[g[r][c]] == 0)
            n1 = sum(1 for r, c in reg if g[r][c] in mapped and side[g[r][c]] == 1)
            if rule == "majority":
                if n0 == n1:
                    continue
                src = 0 if n0 > n1 else 1      # forward (A->B) or inverse (B->A)
                todo = [(r, c) for r, c in reg if g[r][c] in mapped and side[g[r][c]] == src]
            else:                               # swap: cellwise involution
                if n0 + n1 == 0:
                    continue
                todo = [(r, c) for r, c in reg if g[r][c] in mapped]
            for r, c in todo:
                if (r, c) in done:
                    continue                    # a crossing cell keeps the first region's colour
                done[(r, c)] = True
                out[r][c] = part[g[r][c]]
        return out
    return fn


def fam(train):
    part = _changes(train)
    if part is None:
        return
    # markers: colours present in every input and never changed
    common = None
    for p in train:
        cs = {v for row in p["input"] for v in row}
        common = cs if common is None else common & cs
    markers = sorted(c for c in (common or set()) if c not in part)

    specs = []
    for ai, axes in enumerate(("both", "rows", "cols")):
        for m in markers:
            specs.append(("span", m, axes, 1 + ai))
            specs.append(("between", m, axes, 4 + ai))
    specs.append(("component", None, None, 7))
    specs.append(("grid", None, None, 8))

    progs = []
    for kind, m, axes, base in specs:
        side = _sides(train, part, kind, m, axes)
        if side is None:
            continue
        for ri, rule in enumerate(("majority", "swap")):
            name = "pair_map_per_region[region=%s,axes=%s,marker=%s,dir=%s]" % (kind, axes, m, rule)
            progs.append((name, base + 10 * ri, _make(part, side, kind, m, axes, rule)))
    progs.sort(key=lambda t: t[1])
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = repr(outs)
        if sig in seen:
            continue
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
