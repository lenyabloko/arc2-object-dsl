"""g10 "frame or box spanned by markers"  ->  prepress: CROP MARKS (trim box).

Concept (printing / prepress): crop marks are small marks placed OUTSIDE the area to be
trimmed; the trim box is the rectangle lying just inside the marks.  The trim box is then
either STROKED (a one-cell frame along its edge) or FILLED (solid box).  When a page carries
no crop marks at all, the page edge itself is the trim -- the frame is drawn on the grid border.

Mechanism, applied per input grid:
  1. marker cells = cells of the marker colour (a colour common to all training inputs, or the
     colour whose cells are all isolated pixels; None = no marks, the grid edge is the span).
  2. marker cells are partitioned into "spanning groups": a group is exactly the set of markers
     inside its own bounding box, every member lies on that box's boundary, every side of the
     box carries a mark (a single mark, or corner marks).  The partition with the fewest groups
     (then smallest total area) is used.
  3. each group's span, shrunk by `inset` (1 = strictly inside the marks, 0 = through them), is
     the trim box; it is stroked or filled on background cells, in the paint colour.
  4. paint colour: a constant, the marker colour, or the colour of the content already inside
     the trim box (induced from training).

Finite parameter domains:
  marker : {const colour common to all inputs} U {isolated-pixel colour} U {None}
  inset  : {1, 0}
  style  : {stroke, fill}
  colour : {const k, marker, content}
"""
import time
from collections import Counter

_TIME_BUDGET = 0.25  # seconds per grid for the partition search (a guard, not a size limit)


class _Timeout(Exception):
    pass


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _isolated_colour(g, bg):
    """The unique non-background colour all of whose cells are isolated pixels (no same-colour
    8-neighbour); None if there is not exactly one such colour."""
    H, W = len(g), len(g[0])
    cols = {}
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v == bg:
                continue
            iso = True
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < H and 0 <= cc < W and g[rr][cc] == v:
                        iso = False
            cols[v] = cols.get(v, True) and iso
    ks = [k for k, ok in cols.items() if ok]
    return ks[0] if len(ks) == 1 else None


def _marker_colour(g, bg, spec):
    if spec is None:
        return None
    kind, val = spec
    if kind == 'const':
        return val
    if kind == 'isolated':
        return _isolated_colour(g, bg)
    return None


def _partition(marks, minspan, deadline):
    """Partition marker cells into spanning groups; return list of spans (r1, r2, c1, c2) or None."""
    marks = sorted(marks)
    n = len(marks)
    rows = sorted({r for r, _ in marks})
    cols = sorted({c for _, c in marks})
    covered = [False] * n
    best = [None]  # (count, area, spans)

    def valid(r1, r2, c1, c2):
        top, bot, left, right, members = [], [], [], [], []
        for i, (r, c) in enumerate(marks):
            if r1 <= r <= r2 and c1 <= c <= c2:
                if covered[i]:
                    return None
                onb = False
                if r == r1:
                    top.append(c); onb = True
                if r == r2:
                    bot.append(c); onb = True
                if c == c1:
                    left.append(r); onb = True
                if c == c2:
                    right.append(r); onb = True
                if not onb:
                    return None
                members.append(i)
        for side, lo, hi in ((top, c1, c2), (bot, c1, c2), (left, r1, r2), (right, r1, r2)):
            if not side:
                return None
            noncorner = [x for x in side if x != lo and x != hi]
            # a side carries a single mark, or only corner marks
            if len(noncorner) > 1 or (noncorner and len(side) > 1):
                return None
        return members

    def dfs(groups, area):
        if time.time() > deadline:
            raise _Timeout
        if best[0] is not None and len(groups) >= best[0][0] and (len(groups) > best[0][0] or area >= best[0][1]):
            return
        i = next((k for k in range(n) if not covered[k]), None)
        if i is None:
            if best[0] is None or (len(groups), area) < (best[0][0], best[0][1]):
                best[0] = (len(groups), area, list(groups))
            return
        r, c = marks[i]
        cands = []
        for r2 in rows:
            if r2 < r + minspan:
                continue
            for c1 in cols:
                if c1 > c:
                    break
                for c2 in cols:
                    if c2 < c or c2 < c1 + minspan:
                        continue
                    mem = valid(r, r2, c1, c2)
                    if mem is not None:
                        cands.append((-len(mem), (r2 - r + 1) * (c2 - c1 + 1), r2, c1, c2, mem))
        cands.sort()
        for _, a, r2, c1, c2, mem in cands:
            for k in mem:
                covered[k] = True
            groups.append((r, r2, c1, c2))
            dfs(groups, area + a)
            groups.pop()
            for k in mem:
                covered[k] = False

    dfs([], 0)
    return best[0][2] if best[0] is not None else None


def _boxes(g, bg, mspec, inset, deadline=None):
    """Trim boxes (r1, r2, c1, c2), inclusive, clipped to the grid; None if the grid does not fit."""
    H, W = len(g), len(g[0])
    if deadline is None:
        deadline = time.time() + _TIME_BUDGET
    m = _marker_colour(g, bg, mspec)
    if mspec is not None and m is None:
        return None
    if m is None:
        spans = [(-1, H, -1, W)]
    else:
        marks = [(r, c) for r in range(H) for c in range(W) if g[r][c] == m]
        if not marks:
            return None
        try:
            spans = _partition(marks, 2 * inset if inset else 1, deadline)
        except _Timeout:
            return None
        if spans is None:
            return None
    out = []
    for r1, r2, c1, c2 in spans:
        r1, r2, c1, c2 = r1 + inset, r2 - inset, c1 + inset, c2 - inset
        r1, c1 = max(r1, 0), max(c1, 0)
        r2, c2 = min(r2, H - 1), min(c2, W - 1)
        if r1 > r2 or c1 > c2:
            return None
        out.append((r1, r2, c1, c2))
    return out, m


def _cells(box, style):
    r1, r2, c1, c2 = box
    if style == 'fill':
        return [(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)]
    return [(r, c) for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)
            if r in (r1, r2) or c in (c1, c2)]


def _content(g, bg, m, box):
    r1, r2, c1, c2 = box
    ks = {g[r][c] for r in range(r1, r2 + 1) for c in range(c1, c2 + 1)} - {bg, m}
    return next(iter(ks)) if len(ks) == 1 else None


def _paint_colour(g, bg, m, box, crule):
    kind, val = crule
    if kind == 'const':
        return val
    if kind == 'marker':
        return m
    if kind == 'content':
        return _content(g, bg, m, box)
    return None


def _apply(g, mspec, inset, style, crule):
    bg = _bg(g)
    res = _boxes(g, bg, mspec, inset)
    if res is None:
        return None
    boxes, m = res
    out = [row[:] for row in g]
    for box in boxes:
        k = _paint_colour(g, bg, m, box, crule)
        if k is None:
            return None
        for r, c in _cells(box, style):
            if g[r][c] == bg:
                out[r][c] = k
    return out


def fam_crop_marks(train):
    if not train:
        return
    # marker-colour candidates: constants common to every input, the isolated-pixel role, none
    common = None
    for p in train:
        g = p['input']
        bg = _bg(g)
        ks = {v for row in g for v in row} - {bg}
        common = ks if common is None else common & ks
    mspecs = [('const', k) for k in sorted(common)] + [('isolated', None), None]
    deadline = time.time() + 0.4  # one budget for the whole induction: reject quickly
    for mspec in mspecs:
        for inset in (1, 0):
            per_pair = []
            ok = True
            for p in train:
                g, o = p['input'], p['output']
                if len(o) != len(g) or len(o[0]) != len(g[0]):
                    return
                bg = _bg(g)
                res = _boxes(g, bg, mspec, inset, deadline)
                if res is None:
                    ok = False
                    break
                per_pair.append((g, o, bg) + res)
            if not ok:
                continue
            for style in ('stroke', 'fill'):
                # collect the painted colour of every box, and check nothing else changes
                obs = []  # (g, bg, m, box, colour)
                ok = True
                for g, o, bg, boxes, m in per_pair:
                    painted = set()
                    for box in boxes:
                        cs = [(r, c) for r, c in _cells(box, style) if g[r][c] == bg]
                        ks = {o[r][c] for r, c in cs}
                        if len(ks) > 1 or (ks and bg in ks):
                            ok = False
                            break
                        painted.update(cs)
                        if ks:
                            obs.append((g, bg, m, box, next(iter(ks))))
                    if not ok:
                        break
                    H, W = len(g), len(g[0])
                    if any(o[r][c] != g[r][c] for r in range(H) for c in range(W) if (r, c) not in painted):
                        ok = False
                        break
                if not ok or not obs:
                    continue
                crules = []
                ks = {k for *_, k in obs}
                if len(ks) == 1:
                    crules.append(('const', next(iter(ks))))
                if all(m is not None and k == m for _, _, m, _, k in obs):
                    crules.append(('marker', None))
                if all(_content(g, bg, m, box) == k for g, bg, m, box, k in obs):
                    crules.append(('content', None))
                for crule in crules:
                    def fn(g, mspec=mspec, inset=inset, style=style, crule=crule):
                        return _apply(g, mspec, inset, style, crule)
                    if all(fn(p['input']) == p['output'] for p in train):
                        mname = 'none' if mspec is None else (str(mspec[1]) if mspec[0] == 'const' else 'isolated')
                        cname = str(crule[1]) if crule[0] == 'const' else crule[0]
                        yield (f"prepress:crop_marks[marker={mname},inset={inset},style={style},colour={cname}]", 3, fn)
                        return


FAMILIES = (fam_crop_marks,)
