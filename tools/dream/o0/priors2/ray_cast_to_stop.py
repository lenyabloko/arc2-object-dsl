"""Prior family "ray_cast_to_stop" (test-blind; anti-unified from the member one-offs and their train pairs only).

One generator, DRAW_LINE: every emitter cell steps repeatedly along each of its directions and paints the cells
it passes in the ray colour (solid, or every k-th cell at a learned phase), until the stop rule ends the ray;
optionally the cell that stopped it is recoloured (hit effect) and the emitter itself takes a learned colour.
Shared steps written once: background, emitter selection, the march loop with its stop rule, and the induction
of directions / colours / pattern from the training diffs.  Members differ only in parameter values:
  6d58a25d  emit=body, dirs={S}, colour=first-met, stop=edge
  981add89  emit=border (inward), colour=own, stop=toggle
  9def23fe  emit=colour c, dirs=orthogonal 4, colour=own, stop=cancel
  9f8de559  emit=port (outward), colour=literal, stop=block, hit=recolour
The other members need more than a straight ray (stamps, staircases, shifts, z-order, region-keyed colours,
object moves or erasure) and are left uncovered rather than given member-specific branches.
"""
from collections import Counter

CARD = "prior_ray_cast_to_stop"
CONCEPT = "ray_cast_to_stop"
MEMBERS = ["05a7bcf2", "13f06aa5", "140c817e", "1ae2feb7", "212895b5", "252143c9", "256b0a75", "264363fd",
           "2f767503", "3f23242b", "4a21e3da", "4e469f39", "58e15b12", "673ef223", "696d4842", "6d58a25d",
           "73c3b0d8", "758abdf0", "85fa5666", "90f3ed37", "981add89", "9def23fe", "9f8de559", "ac3e2b04",
           "ac605cbb", "b527c5c6", "b7249182", "c1990cce", "d07ae81c", "e4075551", "ecdecbb3", "f15e1fac",
           "f1cefba8", "f8be4b64", "fcc82909"]
READING = {
    "generator": "Every emitter cell (an isolated marker pixel, every cell of a multi-cell body or of a chosen "
                 "colour -- whose rays then leave the object's faces --, an odd-coloured port cell, a line end, or "
                 "a marker on the grid border) steps repeatedly along each of its directions (a learned subset of "
                 "the 8 compass directions, shared or per emitter colour, or the emitter's own outward direction) "
                 "and paints the cells it passes in the emitter colour, the colour of the first foreign cell it "
                 "meets, or a learned colour, solid or every k-th cell; the cell that stops the ray may be "
                 "recoloured and the emitters may take a learned colour.",
    "stop": "edge: to the grid edge painting background only (passing behind objects); block: before the first "
            "non-background cell; reach: like block but only rays that meet a cell are drawn; cancel: a ray that "
            "would meet a non-background cell is not drawn; over: to the edge overwriting everything; toggle: to "
            "the edge, cells of the ray colour become background and all others take the ray colour.",
    "params": "emitter ∈ {pixel, body, port, end, border, colour c} · dirs ∈ {learned subset of 8 (shared | per "
              "emitter colour), own outward} · colour ∈ {own, first-met, literal c} · pattern ∈ {solid, every "
              "k-th at phase p, k ∈ {2,3}} · stop ∈ {block, edge, reach, cancel, over, toggle} · hit ∈ {none, "
              "recolour} · emitter-after ∈ {keep, literal c}",
    "participants": "bg = most frequent colour. pixel = non-background cell without non-background 8-neighbours; "
                    "body = non-background cell with one; port = in a multi-colour 8-connected object of >= 3 "
                    "cells, a cell whose colour occurs once there (direction: away from the object centre); end = "
                    "cell with exactly one same-colour 8-neighbour (direction: away from it); border = border cell "
                    "not in a same-colour run along the border (direction: inward); colour c = every cell of a "
                    "colour present in every input.",
    "preconditions": "Same input/output size, some cell changes, every pair has emitters, the rays of all 8 "
                     "directions reach every changed cell (fast rejection), each chosen direction paints only "
                     "cells the outputs agree with and at least one changed cell, and the whole program "
                     "reproduces every training pair.",
}

D8 = ((-1, 0), (0, 1), (1, 0), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1))
STOPS = ("block", "edge", "reach", "cancel", "over", "toggle")
PATTERNS = ((1, 0), (2, 1), (2, 0), (3, 1), (3, 2), (3, 0))   # (k, phase): step i painted iff i % k == phase % k


def _bg(g):
    cnt = Counter(v for row in g for v in row)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _sgn(x):
    return (x > 0) - (x < 0)


# ------------------------------------------------------------------ emitters: list of (r, c, colour, dirs|None)
def _emitters(g, bg, kind, arg):
    H, W = len(g), len(g[0])
    if kind == "colour":
        return [(r, c, arg, None) for r in range(H) for c in range(W) if g[r][c] == arg]
    if kind == "border":
        out = []
        for r in range(H):
            for c in range(W):
                if g[r][c] == bg:
                    continue
                ds = [d for d, ok in (((1, 0), r == 0), ((-1, 0), r == H - 1), ((0, 1), c == 0),
                                       ((0, -1), c == W - 1)) if ok]
                if ds and ds[0][0]:
                    side = [g[r][c + e] for e in (-1, 1) if 0 <= c + e < W]
                else:
                    side = [g[r + e][c] for e in (-1, 1) if 0 <= r + e < H]
                if len(ds) == 1 and H > 1 and W > 1 and g[r][c] not in side:
                    out.append((r, c, g[r][c], tuple(ds)))
        return out
    if kind == "end":
        out = []
        for r in range(H):
            for c in range(W):
                v = g[r][c]
                if v == bg:
                    continue
                nb = [(dr, dc) for dr, dc in D8 if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == v]
                if len(nb) == 1:
                    out.append((r, c, v, ((-nb[0][0], -nb[0][1]),)))
        return out
    if kind in ("pixel", "body"):
        out = []
        for r in range(H):
            for c in range(W):
                if g[r][c] == bg:
                    continue
                lone = all(not (0 <= r + dr < H and 0 <= c + dc < W) or g[r + dr][c + dc] == bg for dr, dc in D8)
                if lone == (kind == "pixel"):
                    out.append((r, c, g[r][c], None))
        return out
    # port: odd-coloured cell of a multi-colour 8-connected object, direction away from the object centre
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            seen[r][c] = True
            st, cells = [(r, c)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for dr, dc in D8:
                    x, y = a + dr, b + dc
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            cnt = Counter(g[a][b] for a, b in cells)
            if len(cnt) < 2 or len(cells) < 3:
                continue
            n = len(cells)
            cr2 = sum(a for a, _ in cells) * 2
            cc2 = sum(b for _, b in cells) * 2
            for a, b in sorted(cells):
                if cnt[g[a][b]] == 1 and cnt[g[a][b]] < n - 1:
                    d = (_sgn(a * 2 * n - cr2), _sgn(b * 2 * n - cc2))
                    if d != (0, 0):
                        out.append((a, b, g[a][b], (d,)))
    return out


# ------------------------------------------------------------------ the march (one ray), stop rule written once
def _march(g, bg, r, c, d, stop, ec):
    """Returns (cells, hit, fc): cells = [(step, r, c)] the ray covers, hit = the cell that stopped it, fc = the
    colour of the first non-background cell of another colour than the emitter met on the way (or None).
    cells is None when the stop rule cancels the ray."""
    H, W = len(g), len(g[0])
    dr, dc = d
    cells, i, fc = [], 0, None
    x, y = r + dr, c + dc
    while 0 <= x < H and 0 <= y < W:
        i += 1
        v = g[x][y]
        if v != bg:
            if fc is None and v != ec:
                fc = v
            if stop == "cancel":
                return None, None, None
            if stop in ("block", "reach"):
                return cells, (x, y), fc
        cells.append((i, x, y))
        x += dr
        y += dc
    if stop == "reach":
        return None, None, None
    return cells, None, fc


def _paint(g, bg, ems, dirsel, colour, pat, stop, hit, after, out):
    """Paint all rays into out (a copy of g). dirsel(colour) -> dirs for emitters without own dirs."""
    k, ph = pat
    for r, c, ec, own in ems:
        dirs = own if own is not None else dirsel.get(ec, dirsel.get(None, ()))
        for d in dirs:
            cells, h, fc = _march(g, bg, r, c, d, stop, ec)
            col = ec if colour is None else fc if colour == "hit" else colour
            if cells is None or col is None:
                continue
            for i, x, y in cells:
                if i % k != ph % k:
                    continue
                v = g[x][y]
                if stop == "edge":
                    if v == bg:
                        out[x][y] = col
                elif stop == "toggle":
                    out[x][y] = bg if v == col else col
                else:
                    out[x][y] = col
            if h is not None and hit:
                out[h[0]][h[1]] = col
    if after is not None:
        for r, c, _, _ in ems:
            out[r][c] = after
    return out


def _make(kind, arg, dirsel, colour, pat, stop, hit, after):
    def fn(g):
        bg = _bg(g)
        ems = _emitters(g, bg, kind, arg)
        out = [row[:] for row in g]
        return _paint(g, bg, ems, dirsel, colour, pat, stop, hit, after, out)
    return fn


def _ok_dir(pairs, bgs, emss, marches, d, key, colour, pat, stop, hit):
    """Does direction d (for the emitters of colour key, or all if key is None) paint only cells the outputs
    agree with, and at least one changed cell?  Returns (valid, useful).  marches[p][e][d] caches the march."""
    k, ph = pat
    useful = False
    for (I, O), bg, ems, mp in zip(pairs, bgs, emss, marches):
        for e, (r, c, ec, own) in enumerate(ems):
            if own is not None or (key is not None and ec != key):
                continue
            cells, h, fc = mp[e][d]
            col = ec if colour is None else fc if colour == "hit" else colour
            if cells is None or col is None:
                continue
            for i, x, y in cells:
                if i % k != ph % k:
                    continue
                v = I[x][y]
                if stop == "edge":
                    if v != bg:
                        continue
                    want = col
                elif stop == "toggle":
                    want = bg if v == col else col
                else:
                    want = col
                if O[x][y] != want:
                    return False, False
                if v != want:
                    useful = True
            if h is not None and hit:
                if O[h[0]][h[1]] != col:
                    return False, False
                if I[h[0]][h[1]] != col:
                    useful = True
    return True, useful


def _name(kind, arg, dsel, colour, pat, stop, hit, after):
    ds = ";".join("%s:%s" % ("all" if kk is None else kk, ",".join("%d%d" % dd for dd in v))
                  for kk, v in sorted(dsel.items(), key=lambda t: str(t[0])))
    return "ray[emit=%s%s|dirs=%s|col=%s|pat=%d/%d|stop=%s|hit=%s|after=%s]" % (
        kind, "" if arg is None else "=%d" % arg, ds or "own", "own" if colour is None else colour,
        pat[0], pat[1] % pat[0], stop, "recolour" if hit else "none", "keep" if after is None else after)


def fam(train):
    pairs = [(p["input"], p["output"]) for p in train]
    if not pairs:
        return
    for I, O in pairs:
        if len(I) != len(O) or len(I[0]) != len(O[0]):
            return
    if all(I == O for I, O in pairs):
        return
    bgs = [_bg(I) for I, _ in pairs]
    common = None
    for (I, _), bg in zip(pairs, bgs):
        s = {v for row in I for v in row if v != bg}
        common = s if common is None else common & s
    newcols, changed = set(), []
    for I, O in pairs:
        ch = set()
        for r, (ri, ro) in enumerate(zip(I, O)):
            for c, (a, b) in enumerate(zip(ri, ro)):
                if a != b:
                    newcols.add(b)
                    ch.add((r, c))
        changed.append(ch)
    kinds = [("pixel", None), ("body", None), ("port", None), ("border", None), ("end", None)] + \
        [("colour", c) for c in sorted(common or ())]
    found = []
    for kind, arg in kinds:
        emss = [_emitters(I, bg, kind, arg) for (I, _), bg in zip(pairs, bgs)]
        if not all(emss) or sum(len(e) for e in emss) > 600:
            continue
        colours_e = sorted({e[2] for ems in emss for e in ems})
        has_own = any(e[3] is not None for ems in emss for e in ems)
        afters = {O[r][c] for (I, O), ems in zip(pairs, emss) for r, c, _, _ in ems}
        after_opts = [None]
        if len(afters) == 1:
            a = next(iter(afters))
            if any(I[r][c] != a for (I, O), ems in zip(pairs, emss) for r, c, _, _ in ems):
                after_opts = [a]
        for stop in STOPS:
            # march every emitter once per direction (cached), then reject fast unless rays reach every change
            marches, cover_ok = [], True
            for (I, O), bg, ems, ch in zip(pairs, bgs, emss, changed):
                mp, reach = [], set()
                for r, c, ec, own in ems:
                    md = {}
                    for d in (own if own is not None else D8):
                        m = _march(I, bg, r, c, d, stop, ec)
                        md[d] = m
                        if m[0] is not None:
                            reach.update((x, y) for _, x, y in m[0])
                            if m[1] is not None:
                                reach.add(m[1])
                    if after_opts[0] is not None:
                        reach.add((r, c))
                    mp.append(md)
                if not ch <= reach:
                    cover_ok = False
                    break
                marches.append(mp)
            if not cover_ok:
                continue
            for colour in [None, "hit"] + sorted(newcols):
                for hit in ((False, True) if stop in ("block", "reach") else (False,)):
                    for pat in PATTERNS:
                        if has_own:
                            dsel_opts = [{}]
                        else:
                            dsel_opts = []
                            D = tuple(d for d in D8
                                      if _ok_dir(pairs, bgs, emss, marches, d, None, colour, pat, stop, hit)
                                      == (True, True))
                            if D:
                                dsel_opts.append({None: D})
                            if len(colours_e) > 1:
                                ds = {ec: tuple(d for d in D8
                                                if _ok_dir(pairs, bgs, emss, marches, d, ec, colour, pat, stop,
                                                           hit) == (True, True)) for ec in colours_e}
                                if any(ds.values()) and any(v != D for v in ds.values()):
                                    dsel_opts.append(ds)
                        for dsel in dsel_opts:
                            for after in after_opts:
                                fn = _make(kind, arg, dsel, colour, pat, stop, hit, after)
                                if all(fn(I) == O for I, O in pairs):
                                    cost = 1 + (len(dsel) > 1) + (colour is not None) + (pat[0] > 1) + hit + \
                                        (after is not None) + 0.5 * (kind == "colour") + 0.1 * STOPS.index(stop)
                                    found.append((cost, len(found), _name(kind, arg, dsel, colour, pat, stop,
                                                                          hit, after), fn))
                        if len(found) >= 8:
                            break
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, fn in found[:3]:
        yield name, cost, fn


FAMILIES = [fam]
