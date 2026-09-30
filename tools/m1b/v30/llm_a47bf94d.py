"""Family for ARC task a47bf94d -- concept: CONNECTOR GENDER (electrical wiring).

Picture: a wiring diagram.  Coloured k x k terminals sit at the ends of thin cables.  A terminal is one of
the two parity halves of its k x k box -- the "male" half (cells with (dr+dc) of one parity) or the
"female" half (the complementary parity) -- and a solid box is a mated pair (male plugged into female).
Every cable must carry one gender at each end, in the same colour.  So:
  * a mated (solid) terminal is unplugged: it keeps its `stay` half and the other half travels along the
    cable to the far end;
  * a lone half whose far end is empty gets its complementary half drawn at the far end;
  * a cable already terminated male/female is left alone.
Cables are traced like a schematic: go straight whenever the way ahead is wire (so crossings and
hop-over marks are passed straight through), turn only at corners, and pass under occluders (thick
rectangular blobs) by amodal continuation -- straight through if the cable re-emerges on the far side,
otherwise along the unique perpendicular exit.

Roles (no colour numbers):
  background = most common colour
  terminal colours = colours whose every 8-connected component is a k x k solid box or parity half
  occluder cells = other non-background cells lying in a 2x2 block of one colour (thick blobs)
  wire cells = the remaining non-background cells
Declared finite parameter: stay in {0, 1} -- which parity half a mated terminal keeps (fitted on train).
"""
from collections import Counter

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, colour, conn8=True):
    H, W = len(g), len(g[0])
    seen, comps = set(), []
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)] if conn8 else list(DIRS)
    for r in range(H):
        for c in range(W):
            if g[r][c] != colour or (r, c) in seen:
                continue
            stack, comp = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                comp.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] == colour:
                        seen.add((yy, xx))
                        stack.append((yy, xx))
            comps.append(comp)
    return comps


def _classify(comp):
    """Return (top, left, k, kind) for a k x k terminal (kind 'solid', 0 or 1 = parity half) else None."""
    rs = [p[0] for p in comp]
    cs = [p[1] for p in comp]
    top, left = min(rs), min(cs)
    h, w = max(rs) - top + 1, max(cs) - left + 1
    if h != w or h < 3 or h % 2 == 0:
        return None
    k = h
    cells = {(r - top, c - left) for r, c in comp}
    if len(cells) == k * k:
        return top, left, k, "solid"
    for par in (0, 1):
        if cells == {(a, b) for a in range(k) for b in range(k) if (a + b) % 2 == par}:
            return top, left, k, par
    return None


def _analyse(g):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    colours = {v for row in g for v in row} - {bg}
    terminals = {}  # (top, left) -> (k, colour, kind)
    term_cols = set()
    for col in colours:
        comps = _components(g, col)
        cl = [_classify(cp) for cp in comps]
        if cl and all(x is not None for x in cl):
            term_cols.add(col)
            for top, left, k, kind in cl:
                terminals[(top, left)] = (k, col, kind)
    ks = {v[0] for v in terminals.values()}
    if len(ks) != 1:
        return None
    k = ks.pop()
    occ = set()
    for r in range(H - 1):
        for c in range(W - 1):
            v = g[r][c]
            if v != bg and v not in term_cols and g[r][c + 1] == v and g[r + 1][c] == v and g[r + 1][c + 1] == v:
                # flood the whole thick blob
                for comp in _components(g, v, conn8=False):
                    if (r, c) in comp:
                        occ.update(comp)
    wire = {(r, c) for r in range(H) for c in range(W)
            if g[r][c] != bg and g[r][c] not in term_cols and (r, c) not in occ}
    return bg, k, terminals, occ, wire


def _trace(start, d, occ, wire, limit):
    """Follow a cable from wire cell `start` heading `d`; return (end_cell, heading) or None."""
    trav = occ | wire
    pos = start
    seen = set()
    for _ in range(limit):
        if (pos, d) in seen:
            return None
        seen.add((pos, d))
        nxt = (pos[0] + d[0], pos[1] + d[1])
        if nxt in occ and pos not in occ:
            q, path = nxt, []
            while q in occ:
                path.append(q)
                q = (q[0] + d[0], q[1] + d[1])
            if q in wire:            # re-emerges straight ahead
                pos = q
                continue
            cands = []
            for cell in path:
                for p in ((d[1], d[0]), (-d[1], -d[0])):
                    r = cell
                    while r in occ:
                        r = (r[0] + p[0], r[1] + p[1])
                    if r not in wire or r == pos:
                        continue
                    back = (r[0] - p[0], r[1] - p[1])   # would this exit pair straight with another?
                    b = back
                    while b in occ:
                        b = (b[0] - p[0], b[1] - p[1])
                    if b in wire:
                        continue
                    cands.append((r, p))
            if len(set(cands)) != 1:
                return None
            pos, d = cands[0]
            continue
        if nxt in trav:
            pos = nxt
            continue
        opts = [p for p in ((d[1], d[0]), (-d[1], -d[0])) if (pos[0] + p[0], pos[1] + p[1]) in trav]
        if not opts:
            return pos, d
        if len(opts) > 1:
            return None
        d = opts[0]
    return None


def _cells(top, left, k, kind):
    return [(top + a, left + b) for a in range(k) for b in range(k)
            if kind == "solid" or (a + b) % 2 == kind]


def _solve(g, stay):
    A = _analyse(g)
    if A is None:
        return None
    bg, k, terminals, occ, wire = A
    H, W = len(g), len(g[0])
    h = k // 2
    out = [row[:] for row in g]
    limit = 4 * H * W + 10
    done = set()
    for (top, left), (_, col, kind) in sorted(terminals.items()):
        mids = {(-1, 0): (top, left + h), (1, 0): (top + k - 1, left + h),
                (0, -1): (top + h, left), (0, 1): (top + h, left + k - 1)}
        for d, m in mids.items():
            s = (m[0] + d[0], m[1] + d[1])
            if s not in wire and s not in occ:
                continue
            res = _trace(s, d, occ, wire, limit)
            if res is None:
                return None
            (er, ec), (dr, dc) = res
            # far terminal box: its near side-middle is just beyond the cable end
            cr, cc = er + dr * (h + 1), ec + dc * (h + 1)
            ftop, fleft = cr - h, cc - h
            if (ftop, fleft) == (top, left):
                continue
            key = frozenset([(top, left), (ftop, fleft)])
            if key in done:
                continue
            done.add(key)
            far = terminals.get((ftop, fleft))
            if far is None:
                if not (0 <= ftop and ftop + k <= H and 0 <= fleft and fleft + k <= W):
                    return None
                if any(g[y][x] != bg for y, x in _cells(ftop, fleft, k, "solid")):
                    return None
                if kind == "solid":
                    for y, x in _cells(top, left, k, "solid"):
                        out[y][x] = bg
                    for y, x in _cells(top, left, k, stay):
                        out[y][x] = col
                    for y, x in _cells(ftop, fleft, k, 1 - stay):
                        out[y][x] = col
                else:
                    for y, x in _cells(ftop, fleft, k, 1 - kind):
                        out[y][x] = col
            else:
                fk, fcol, fkind = far
                if fcol != col:
                    return None
                # already a male/female pair: nothing to do; a mated pair at both ends is undefined
                if kind == "solid" and fkind == "solid":
                    return None
                if kind == "solid" or fkind == "solid":
                    sp, (st, sl), ot = ((top, left), (top, left), fkind) if kind == "solid" else \
                        ((ftop, fleft), (ftop, fleft), kind)
                    for y, x in _cells(st, sl, k, "solid"):
                        out[y][x] = bg
                    for y, x in _cells(st, sl, k, 1 - ot):
                        out[y][x] = col
    return out


def fam_connector_gender(train):
    for stay in (0, 1):
        def fn(g, stay=stay):
            return _solve(g, stay)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("electrical:connector_gender[stay=parity%d,occluder=amodal,crossing=straight]" % stay, 3, fn)


FAMILIES = (fam_connector_gender,)
