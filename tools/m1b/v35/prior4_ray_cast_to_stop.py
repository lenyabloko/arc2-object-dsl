"""Prior family "ray_cast_to_stop", third pass (Fable v11 T68 / D38 / G68 changed): every colour parameter is a declared
colour role (colour_roles: background, rank_colour(k), novel_colour) or a role-bound value; no literal colour numbers.

G68 BINDINGS (priors4) -- per fitted member, the role each former literal became (training pairs only):
  member    | former literal slot used by the first fitting program      | role now
  1ae2feb7  | none (colour <- emitter.colour, period <- run length)       | -
  6d58a25d  | none (colour <- first foreign cell met)                     | -
  981add89  | none (colour <- emitter.colour)                             | -
  9def23fe  | emitter colour 2 (priors2 literal, priors3 "major")         | major (most frequent ink colour)
  9f8de559  | ray colour 7 (priors2 literal, priors3 "bg")                | background
  d07ae81c  | none (colour <- medium's marker)                            | -
  Literal slots removed (3): emitter "colour c" (c in every training input) -> emitter "rank k" (cells of
  rank_colour(k) of each input); ray colour "literal c" (a colour new in some output) -> novel_colour(train) or
  rank_colour(k) of the input; emitter-after "literal c" -> background | novel_colour(train) | rank_colour(k).
  Members lost for lack of a role: none (no fitted member used a literal colour).  Background = CR.background.

Earlier pass (priors3):

BINDINGS (every induced value of the members priors2 already fits, with the role that explains it):
  member    | emitter                         | dirs                         | ray colour                 | pattern | stop   | extras
  6d58a25d  | body cells (multi-cell object)  | literal {S} (no role found)  | <- first foreign cell met  | solid   | edge   | -
  981add89  | border markers                  | <- inward normal of border   | <- emitter.colour          | solid   | toggle | -
  9def23fe  | colour 2 <- MAJOR colour (most  | orthogonal 4 (learned)       | <- emitter.colour          | solid   | cancel | -
            |   frequent non-bg colour)       |                              |                            |         |        |
  9f8de559  | port (odd cell of an object)    | <- away from object centre   | 7 <- BACKGROUND colour     | solid   | block  | hit cell <- ray colour
Role-bound replacements made (literal -> role, both kept in the menu, role preferred by cost):
  emitter colour c  -> "major" (most frequent non-bg colour of each input)          [9def23fe]
  ray colour literal -> "bg" (the background colour: the ray punches a hole)        [9f8de559]
Role-bound widenings (each is a role or a shared step, never a member branch):
  pattern period k  -> k <- emitter.run_length (length of the same-colour run the ray continues), with the new
                       shared stop "past" (paint only beyond the last obstacle on the ray, phase anchored there,
                       nearer emitters on top) and dirs = own-outward ∩ learned subset              [1ae2feb7]
  ray colour        -> "medium": colour <- the emitter colour of the marker that sits in the same medium as the
                       crossed cell (medium = majority colour around a lone marker)                  [d07ae81c]
  emitter "lone"    -> a cell with no same-colour 8-neighbour (a marker inside any region, not only on bg)
  emitter "run"     -> each end of a maximal horizontal / vertical same-colour run, outward, carrying its length

One generator, DRAW_LINE: every emitter cell steps repeatedly along each of its directions and paints the cells
it passes in the ray colour (solid, every k-th cell at a learned phase, or every run_length-th cell), until the
stop rule ends the ray; optionally the cell that stopped it is recoloured and the emitter takes a learned colour.
"""
from collections import Counter

import colour_roles as CR

CARD = "prior4_ray_cast_to_stop"
CONCEPT = "ray_cast_to_stop"
MEMBERS = ["05a7bcf2", "13f06aa5", "140c817e", "1ae2feb7", "212895b5", "252143c9", "256b0a75", "264363fd",
           "2f767503", "3f23242b", "4a21e3da", "4e469f39", "58e15b12", "673ef223", "696d4842", "6d58a25d",
           "73c3b0d8", "758abdf0", "85fa5666", "90f3ed37", "981add89", "9def23fe", "9f8de559", "ac3e2b04",
           "ac605cbb", "b527c5c6", "b7249182", "c1990cce", "d07ae81c", "e4075551", "ecdecbb3", "f15e1fac",
           "f1cefba8", "f8be4b64", "fcc82909"]
READING = {
    "generator": "Every emitter cell (an isolated marker pixel, a lone cell with no same-colour neighbour, every "
                 "cell of a multi-cell body, of the major colour or of a chosen colour, an odd-coloured port cell, "
                 "a line end, the end of a same-colour run, or a marker on the grid border) steps repeatedly along "
                 "each of its directions (a learned subset of the 8 compass directions, shared or per emitter "
                 "colour, or its own outward direction, optionally narrowed by a learned subset) and paints the "
                 "cells it passes in the emitter colour, the colour of the first foreign cell it meets, the "
                 "background colour, the colour of the marker living in the crossed cell's medium, or a learned "
                 "colour role (novel colour, a rank colour); solid, every k-th cell, or every run-length-th cell; the cell that stops the ray may be "
                 "recoloured and the emitters may take a learned colour.",
    "stop": "edge: to the grid edge painting background only (passing behind objects); block: before the first "
            "non-background cell; reach: like block but only rays that meet a cell are drawn; cancel: a ray that "
            "would meet a non-background cell is not drawn; over: to the edge overwriting everything; toggle: to "
            "the edge, cells of the ray colour become background and all others take the ray colour; past: only "
            "the stretch beyond the last obstacle on the ray (none if no obstacle), phase anchored at its first "
            "cell, rays from nearer emitters on top.",
    "params": "emitter ∈ {pixel, lone, body, port, end, run, border, major, rank k} · dirs ∈ {learned subset of "
              "8 (shared | per emitter colour), own outward, own ∩ learned} · colour ∈ {own, first-met, bg, "
              "medium, novel, rank k} · pattern ∈ {solid, every k-th at phase p (k ∈ {2,3}), every run_length-th} · "
              "stop ∈ {block, edge, reach, cancel, over, toggle, past} · hit ∈ {none, recolour} · "
              "emitter-after ∈ {keep, bg, novel, rank k}",
    "bindings": "6d58a25d colour <- first foreign cell met; 981add89 dirs <- inward border normal, colour <- own; "
                "9def23fe emitter colour <- major colour; 9f8de559 dirs <- away from object centre, colour <- "
                "background, hit <- ray colour; widened: period <- run length, colour <- medium's marker.",
    "participants": "bg = most frequent colour. pixel = non-background cell without non-background 8-neighbours; "
                    "lone = non-background cell without same-colour 8-neighbours; body = non-background cell with a "
                    "non-background 8-neighbour; port = in a multi-colour 8-connected object of >= 3 cells, a cell "
                    "whose colour occurs once there (direction: away from the object centre); end = cell with "
                    "exactly one same-colour 8-neighbour (direction: away from it); run = end cell of a maximal "
                    "horizontal/vertical same-colour run (direction: outward along the run, carrying its length); "
                    "border = border cell not in a same-colour run along the border (direction: inward); major = "
                    "every cell of the most frequent non-background colour; rank k = every cell of rank_colour(k) of "
                    "the grid; novel = novel_colour(train); medium of a marker = most frequent colour of its 8-neighbours.",
    "preconditions": "Same input/output size, some cell changes, every pair has emitters, the rays of all 8 "
                     "directions reach every changed cell (fast rejection), each chosen direction paints only "
                     "cells the outputs agree with (strict) or, for stop past whose "
                     "nearer rays overwrite farther ones, wrong only on changed cells (lenient) and at least one changed cell, and the whole program reproduces every "
                     "training pair.",
}

D8 = ((-1, 0), (0, 1), (1, 0), (0, -1), (-1, 1), (1, 1), (1, -1), (-1, -1))
D4 = D8[:4]
STOPS = ("block", "edge", "reach", "cancel", "over", "toggle", "past")
PATTERNS = ((1, 0), (2, 1), (2, 0), (3, 1), (3, 2), (3, 0))   # (k, phase): step i painted iff i % k == phase % k
RUNPAT = (0, 1)                                               # k <- emitter run length, first cell painted


def _bg(g):
    return CR.background(g)


def _role(spec, g, bg):
    """A declared colour role -> colour on grid g: ("novel", v) is fixed by the training pairs (v =
    CR.novel_colour(train)); ("rank", k) is CR.rank_colour(g, k, bg); "bg" is the background."""
    if spec == "bg":
        return bg
    if spec[0] == "novel":
        return spec[1]
    key = (id(g), spec[1], bg)
    hit = _RMEMO.get(key)
    if hit is None or hit[0] is not g:          # identity-checked memo (the grid is held, so ids are not reused)
        if len(_RMEMO) > 4096:
            _RMEMO.clear()
        hit = _RMEMO[key] = (g, CR.rank_colour(g, spec[1], bg))
    return hit[1]


_RMEMO = {}


def _rname(spec):
    return spec if isinstance(spec, str) else ("novel" if spec[0] == "novel" else "rank%d" % spec[1])


def _sgn(x):
    return (x > 0) - (x < 0)


def _major(g, bg):
    cnt = Counter(v for row in g for v in row if v != bg)
    if not cnt:
        return None
    best = max(cnt.values())
    top = [v for v in cnt if cnt[v] == best]
    return top[0] if len(top) == 1 else None


# ------------------------------------------------------------------ emitters: list of (r, c, colour, dirs|None, L)
def _emitters(g, bg, kind, arg):
    H, W = len(g), len(g[0])
    if kind == "major":
        kind, arg = "colour", _major(g, bg)
        if arg is None:
            return []
    elif kind == "rank":
        kind, arg = "colour", CR.rank_colour(g, arg, bg)
        if arg is None:
            return []
    if kind == "colour":
        return [(r, c, arg, None, None) for r in range(H) for c in range(W) if g[r][c] == arg]
    if kind == "run":
        out = []
        for r in range(H):
            for c in range(W):
                v = g[r][c]
                if v == bg:
                    continue
                for (dr, dc) in D4:
                    x, y = r + dr, c + dc
                    if 0 <= x < H and 0 <= y < W and g[x][y] == v:
                        continue                  # not the end of the run in this direction
                    n, x, y = 1, r - dr, c - dc
                    while 0 <= x < H and 0 <= y < W and g[x][y] == v:
                        n += 1
                        x -= dr
                        y -= dc
                    out.append((r, c, v, ((dr, dc),), n))
        return out
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
                    out.append((r, c, g[r][c], tuple(ds), None))
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
                    out.append((r, c, v, ((-nb[0][0], -nb[0][1]),), None))
        return out
    if kind in ("pixel", "body", "lone"):
        out = []
        for r in range(H):
            for c in range(W):
                v = g[r][c]
                if v == bg:
                    continue
                if kind == "lone":
                    if all(not (0 <= r + dr < H and 0 <= c + dc < W) or g[r + dr][c + dc] != v for dr, dc in D8):
                        out.append((r, c, v, None, None))
                    continue
                lone = all(not (0 <= r + dr < H and 0 <= c + dc < W) or g[r + dr][c + dc] == bg for dr, dc in D8)
                if lone == (kind == "pixel"):
                    out.append((r, c, v, None, None))
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
                        out.append((a, b, g[a][b], (d,), None))
    return out


def _medium_map(g, ems):
    """medium colour -> emitter colour: the colour of the marker living in that medium (ambiguous media dropped)."""
    H, W = len(g), len(g[0])
    m, bad = {}, set()
    for r, c, ec, _, _ in ems:
        cnt = Counter(g[r + dr][c + dc] for dr, dc in D8 if 0 <= r + dr < H and 0 <= c + dc < W)
        cnt.pop(ec, None)
        if not cnt:
            continue
        best = max(cnt.values())
        top = sorted(v for v in cnt if cnt[v] == best)
        if len(top) != 1:
            continue
        md = top[0]
        if md in m and m[md] != ec:
            bad.add(md)
        m[md] = ec
    for md in bad:
        del m[md]
    return m


# ------------------------------------------------------------------ the march (one ray), stop rule written once
def _march(g, bg, r, c, d, stop, ec):
    """Returns (cells, hit, fc, pre): cells = [(step, r, c)] the ray covers, hit = the cell that stopped it, fc = the
    colour of the first non-background cell of another colour than the emitter met on the way (or None), pre = the
    steps skipped before the painted stretch (stop "past").  cells is None when the stop rule cancels the ray."""
    H, W = len(g), len(g[0])
    dr, dc = d
    cells, i, fc = [], 0, None
    x, y = r + dr, c + dc
    last = 0
    while 0 <= x < H and 0 <= y < W:
        i += 1
        v = g[x][y]
        if v != bg:
            last = i
            if fc is None and v != ec:
                fc = v
            if stop == "cancel":
                return None, None, None, 0
            if stop in ("block", "reach"):
                return cells, (x, y), fc, 0
        cells.append((i, x, y))
        x += dr
        y += dc
    if stop == "reach":
        return None, None, None, 0
    if stop == "past":
        if not last or last == i:
            return None, None, None, 0
        return [(j - last, a, b) for j, a, b in cells if j > last], None, fc, last
    return cells, None, fc, 0


def _colour(colour, ec, fc, bg):
    """colour is None (own), "hit", "bg", "medium" (resolved per cell) or a role already resolved on the grid."""
    if colour is None:
        return ec
    if colour == "hit":
        return fc
    if colour == "bg":
        return bg
    return colour


def _on_grid(colour, g, bg):
    """Resolve a declared role (tuple) on grid g; relational colours pass through."""
    return _role(colour, g, bg) if isinstance(colour, tuple) else colour


def _paint(g, bg, ems, dirsel, colour, pat, stop, hit, after, out):
    """Paint all rays into out (a copy of g). dirsel maps emitter colour (or None) -> dirs; for emitters with own
    dirs a non-empty dirsel narrows them (own ∩ learned)."""
    k0, ph = pat
    mm = _medium_map(g, ems) if colour == "medium" else None
    if isinstance(colour, tuple):
        colour = _role(colour, g, bg)
        if colour is None:                       # the role names no colour on this grid: no rays
            return out
    if after is not None:
        after = _role(after, g, bg)
    rays = []
    for r, c, ec, own, L in ems:
        if own is not None:
            sel = dirsel.get(ec, dirsel.get(None)) if dirsel else None
            dirs = own if sel is None else tuple(d for d in own if d in sel)
        else:
            dirs = dirsel.get(ec, dirsel.get(None, ()))
        k = k0 or L
        if not k:
            continue
        for d in dirs:
            cells, h, fc, pre = _march(g, bg, r, c, d, stop, ec)
            col = _colour(colour, ec, fc, bg)
            if cells is None or col is None:
                continue
            rays.append((-pre, len(rays), cells, h, col, k))
    if stop == "past":
        rays.sort()
    for _, _, cells, h, col, k in rays:
        for i, x, y in cells:
            if i % k != ph % k:
                continue
            v = g[x][y]
            cc = col
            if mm is not None:
                cc = mm.get(v)
                if cc is None:
                    continue
            elif stop in ("edge", "past"):
                if v != bg:
                    continue
            elif stop == "toggle":
                cc = bg if v == col else col
            out[x][y] = cc
        if h is not None and hit and mm is None:
            out[h[0]][h[1]] = col
    if after is not None:
        for r, c, _, _, _ in ems:
            out[r][c] = after
    return out


def _make(kind, arg, dirsel, colour, pat, stop, hit, after):
    def fn(g):
        bg = _bg(g)
        ems = _emitters(g, bg, kind, arg)
        out = [row[:] for row in g]
        return _paint(g, bg, ems, dirsel, colour, pat, stop, hit, after, out)
    return fn


def _ok_dir(pairs, bgs, emss, mms, marches, d, key, colour, pat, stop, hit, lenient):
    """Does direction d (for the emitters of colour key, or all if key is None) paint only cells the outputs
    agree with (lenient: wrong only on cells the outputs change, which another ray may overwrite), and at least
    one changed cell?  Returns (valid, useful).  marches[p][e][d] caches the march."""
    k0, ph = pat
    useful = False
    role = colour
    for (I, O), bg, ems, mm, mp in zip(pairs, bgs, emss, mms, marches):
        colour = _on_grid(role, I, bg)
        if isinstance(role, tuple) and colour is None:
            continue
        for e, (r, c, ec, own, L) in enumerate(ems):
            if key is not None and ec != key:
                continue
            if d not in mp[e]:
                continue
            k = k0 or L
            if not k:
                continue
            cells, h, fc, _ = mp[e][d]
            col = _colour(colour, ec, fc, bg)
            if cells is None or col is None:
                continue
            for i, x, y in cells:
                if i % k != ph % k:
                    continue
                v = I[x][y]
                if mm is not None:
                    want = mm.get(v)
                    if want is None:
                        continue
                elif stop in ("edge", "past"):
                    if v != bg:
                        continue
                    want = col
                elif stop == "toggle":
                    want = bg if v == col else col
                else:
                    want = col
                if O[x][y] != want:
                    if not lenient or O[x][y] == v:
                        return False, False
                elif v != want:
                    useful = True
            if h is not None and hit and mm is None:
                if O[h[0]][h[1]] != col:
                    if not lenient or O[h[0]][h[1]] == I[h[0]][h[1]]:
                        return False, False
                elif I[h[0]][h[1]] != col:
                    useful = True
    return True, useful


def _cover(pairs, bgs, emss, changed, stop, add_em):
    """March every emitter once per direction; (marches, ok) with ok iff the rays reach every changed cell."""
    marches = []
    for (I, O), bg, ems, ch in zip(pairs, bgs, emss, changed):
        mp, reach = [], set()
        for r, c, ec, own, L in ems:
            md = {}
            for d in (own if own is not None else D8):
                m = _march(I, bg, r, c, d, stop, ec)
                md[d] = m
                if m[0] is not None:
                    reach.update((x, y) for _, x, y in m[0])
                    if m[1] is not None:
                        reach.add(m[1])
            if add_em:
                reach.add((r, c))
            mp.append(md)
        if not ch <= reach:
            return None, False
        marches.append(mp)
    return marches, True


def _name(kind, arg, dsel, colour, pat, stop, hit, after, has_own):
    ds = ";".join("%s:%s" % ("all" if kk is None else kk, ",".join("%d%d" % dd for dd in v))
                  for kk, v in sorted(dsel.items(), key=lambda t: str(t[0])))
    dn = ("own&" + ds if ds else "own") if has_own else ds
    pn = "run/1" if pat == RUNPAT else "%d/%d" % (pat[0], pat[1] % pat[0])
    return "ray[emit=%s%s|dirs=%s|col=%s|pat=%s|stop=%s|hit=%s|after=%s]" % (
        kind, "" if arg is None else "=%d" % arg, dn, "own" if colour is None else _rname(colour),
        pn, stop, "recolour" if hit else "none", "keep" if after is None else _rname(after))


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
    changed = []
    for I, O in pairs:
        ch = set()
        for r, (ri, ro) in enumerate(zip(I, O)):
            for c, (a, b) in enumerate(zip(ri, ro)):
                if a != b:
                    ch.add((r, c))
        changed.append(ch)
    nov = CR.novel_colour(train)
    roles = ([("novel", nov)] if nov is not None else []) + [("rank", k) for k in CR.RANKS]
    kinds = [("pixel", None), ("body", None), ("port", None), ("border", None), ("end", None), ("major", None),
             ("lone", None), ("run", None)] + [("rank", k) for k in CR.RANKS]
    found = []
    seen_ems = set()
    for kind, arg in kinds:
        emss = [_emitters(I, bg, kind, arg) for (I, _), bg in zip(pairs, bgs)]
        if not all(emss) or sum(len(e) for e in emss) > 600:
            continue
        if kind == "rank":                       # same emitters as a cheaper earlier kind: same programs, dearer
            sig = repr(emss)
            if sig in seen_ems:
                continue
            seen_ems.add(sig)
        elif kind in ("major", "lone", "body", "pixel"):
            seen_ems.add(repr(emss))
        colours_e = sorted({e[2] for ems in emss for e in ems})
        has_own = any(e[3] is not None for ems in emss for e in ems)
        # emitter-after colour: one colour per pair, named by a role (bg, novel, rank k) resolved on each input
        after_opts = [None]
        per = [{O[r][c] for r, c, _, _, _ in ems} for (I, O), ems in zip(pairs, emss)]
        if all(len(s) == 1 for s in per) and any(I[r][c] != O[r][c] for (I, O), ems in zip(pairs, emss)
                                                   for r, c, _, _, _ in ems):
            for spec in ["bg"] + roles:
                if all(_role(spec, I, bg) == next(iter(s)) for (I, _), bg, s in zip(pairs, bgs, per)):
                    after_opts = [spec]
                    break
        mmaps = [_medium_map(I, ems) for (I, _), ems in zip(pairs, emss)]
        # colours the outputs give the changed non-emitter cells, per pair (fast colour rejection)
        chouts = []
        for (I, O), ems, ch in zip(pairs, emss, changed):
            ecs = {(r, c) for r, c, _, _, _ in ems}
            chouts.append({O[x][y] for x, y in ch if (x, y) not in ecs})
        pats = (RUNPAT,) + PATTERNS if kind == "run" else PATTERNS
        # every stop's ray is a part of the full ray to the edge: if full rays miss a change, nothing reaches it
        group_cache = {"full": _cover(pairs, bgs, emss, changed, "over", after_opts[0] is not None)}
        if not group_cache["full"][1]:
            continue
        for stop in STOPS:
            # march every emitter once per direction (cached; edge/over/toggle march alike), then reject fast
            # unless rays reach every change
            grp = "full" if stop in ("edge", "over", "toggle") else stop
            if grp in group_cache:
                marches, cover_ok = group_cache[grp]
                if not cover_ok:
                    continue
            else:
                marches, cover_ok = _cover(pairs, bgs, emss, changed, stop, after_opts[0] is not None)
                group_cache[grp] = (marches, cover_ok)
            if not cover_ok:
                continue
            colours = [None, "hit", "bg"] + (["medium"] if all(mmaps) and stop in ("edge", "over") else []) + \
                roles
            for colour in colours:
                if colour != "hit":
                    ok = True
                    for (I, _), bg, ems, co in zip(pairs, bgs, emss, chouts):
                        allowed = {e[2] for e in ems} if colour in (None, "medium") else \
                            {bg} if colour == "bg" else {_role(colour, I, bg)}
                        if stop == "toggle":
                            allowed = allowed | {bg}
                        if not co <= allowed:
                            ok = False
                            break
                    if not ok:
                        continue
                mms = mmaps if colour == "medium" else [None] * len(pairs)
                for hit in ((False, True) if stop in ("block", "reach") and colour != "medium" else (False,)):
                    for pat in pats:
                        dsel_opts = [{}] if has_own else []
                        for lenient in ((False, True) if stop == "past" else (False,)):   # z-order only in past
                            D = tuple(d for d in D8
                                      if _ok_dir(pairs, bgs, emss, mms, marches, d, None, colour, pat, stop, hit,
                                                 lenient) == (True, True))
                            if D and {None: D} not in dsel_opts and (not has_own or len(D) < len(D8)):
                                dsel_opts.append({None: D})
                            if not lenient and len(colours_e) > 1 and not has_own:
                                ds = {ec: tuple(d for d in D8
                                                if _ok_dir(pairs, bgs, emss, mms, marches, d, ec, colour, pat,
                                                           stop, hit, False) == (True, True)) for ec in colours_e}
                                if any(ds.values()) and any(v != D for v in ds.values()):
                                    dsel_opts.append(ds)
                        for dsel in dsel_opts:
                            for after in after_opts:
                                fn = _make(kind, arg, dsel, colour, pat, stop, hit, after)
                                if all(fn(I) == O for I, O in pairs):
                                    role_col = colour in (None, "hit", "bg", "medium")
                                    cost = 1 + (len(dsel) > 1) + (colour is not None) + 0.2 * (not role_col) + \
                                        (pat[0] > 1) + 0.5 * (pat == RUNPAT) + hit + (after is not None) + \
                                        0.5 * (kind == "rank") + 0.3 * (kind in ("major", "lone", "run")) + \
                                        0.3 * (has_own and bool(dsel)) + 0.1 * STOPS.index(stop)
                                    found.append((cost, len(found), _name(kind, arg, dsel, colour, pat, stop,
                                                                          hit, after, has_own), fn))
                        if len(found) >= 8:
                            break
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, fn in found[:3]:
        yield name, cost, fn


FAMILIES = [fam]
