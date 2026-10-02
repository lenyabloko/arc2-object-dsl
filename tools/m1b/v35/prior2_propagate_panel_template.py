"""Prior family propagate_panel_template (test-blind; anti-unified from the member one-offs and train pairs).

One generator: split the grid into panels (the cells between full separator lines, or the interiors of
framed boxes), pick the template panel inside each panel group by one selection rule, pick the target
panels by one target rule, and paint into every target a copy of the template passed through one
per-target transform (identity or a D4 element learned per offset from the template), one size fit
(clip or keep-margin-to-nearer-wall), one ink rule (own colours, the target's frame colour, or the key
colour of the target's panel row/column) and one paint mode (replace, overlay, under).  Non-target
panels are kept or cleared.  Everything outside the panels is never touched.

Shared steps (written once): panel parsing, backgrounds, groups, keys, template choice, target choice,
the render/paint loop, the D4-per-offset induction and the verify loop.

Members and the parameter values they need:
  1e32b0e9  lattice · src=fullest · tgt=all · ink=frame · paint=under
  42918530  boxes · group=frame · src=only · tgt=empty
  5a5a2103  lattice · keys=row · src=only · tgt=all · ink=key · paint=replace
  6d0160f0  lattice · src=marker c · tgt=index · rest=clear
  8e5a5113  lattice · src=only · tgt=all · xf=d4 per offset
  92e50de0  lattice · src=only · tgt=stride2
  9841fdad  lattice · bg=panel · src=only · tgt=empty · fit=margin · paint=overlay
Not covered: 15113be4 (template is a blown-up copy; targets are panels that cover its mask),
             4c7dc4dd (Raven matrix: output is the blank panel filled by a relation library).
"""
from collections import Counter

CARD = "prior_propagate_panel_template"
CONCEPT = "propagate_panel_template"
MEMBERS = ["15113be4", "1e32b0e9", "42918530", "4c7dc4dd", "5a5a2103", "6d0160f0", "8e5a5113",
           "92e50de0", "9841fdad"]
READING = {
    "generator": "Split the grid into panels (between full separator lines, or inside framed boxes); in each "
                 "panel group take the template panel (the only patterned one, the fullest one, or the one "
                 "holding the marker colour) and paint a copy of it into each target panel (all, the empty "
                 "ones, those an even number of panels away, or the one indexed by the marker's in-panel "
                 "position), transformed by a D4 element learned per offset, fitted to the target size, inked "
                 "with its own colours, the frame colour or the row/column key colour.",
    "stop": "One copy per target panel; non-target panels are kept or cleared; separator/frame cells and "
            "everything outside the panels never change.",
    "params": "panel ∈ {lattice, boxes} · bg ∈ {global, panel} · group ∈ {one, frame colour} · "
              "keys ∈ {none, row, col} · src ∈ {only, fullest, marker c (induced)} · "
              "tgt ∈ {all, empty, stride2, index} · rest ∈ {keep, clear} · xf ∈ {id, d4 per offset (induced)} · "
              "fit ∈ {clip, margin} · ink ∈ {own, frame, key} · paint ∈ {replace, overlay, under}",
    "participants": "lattice: separator colour = the non-majority colour with the most full rows+columns; "
                    "panels = products of the runs between them. boxes: 4-connected non-background components "
                    "whose bounding-box ring is one colour (not nested); panel = interior, frame = ring colour. "
                    "Background: the most common panel colour (global) or each panel's own majority (panel). "
                    "Keys: the first panel of each panel row (column), holding exactly one non-background colour; "
                    "keys are not template candidates. Marker: a colour that lies in exactly one panel of every "
                    "training input.",
    "preconditions": "Output size = input size; all cells outside the panels unchanged; at least two panels; "
                     "every changed panel is a target (or, under rest=clear, a non-target that became blank).",
}


# ------------------------------------------------------------------ panel parsing
def _maj(cnt):
    return max(cnt, key=lambda k: (cnt[k], -k))


def _runs(n, lines):
    s = set(lines)
    out, start = [], None
    for k in range(n + 1):
        if k == n or k in s:
            if start is not None:
                out.append((start, k))
            start = None
        elif start is None:
            start = k
    return out


def _lattice(g):
    H, W = len(g), len(g[0])
    cnt = Counter(v for r in g for v in r)
    maj = _maj(cnt)
    best = None
    for c in sorted(cnt):
        if c == maj:
            continue
        rows = [i for i in range(H) if all(v == c for v in g[i])]
        cols = [j for j in range(W) if all(g[i][j] == c for i in range(H))]
        n = len(rows) + len(cols)
        if n and (best is None or n > best[0]):
            best = (n, c, rows, cols)
    if best is None:
        return None
    _, c, rows, cols = best
    rr, cc = _runs(H, rows), _runs(W, cols)
    if len(rr) * len(cc) < 2:
        return None
    return [(a, b, x, y, i, j, c) for i, (a, b) in enumerate(rr) for j, (x, y) in enumerate(cc)]


def _boxes(g):
    H, W = len(g), len(g[0])
    bg = _maj(Counter(v for r in g for v in r))
    seen = [[False] * W for _ in range(H)]
    found = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            seen[i][j] = True
            st, r0, r1, c0, c1 = [(i, j)], i, i, j, j
            while st:
                a, b = st.pop()
                r0, r1, c0, c1 = min(r0, a), max(r1, a), min(c0, b), max(c1, b)
                for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            if r1 - r0 < 2 or c1 - c0 < 2:
                continue
            ring = set(g[r0][c0:c1 + 1]) | set(g[r1][c0:c1 + 1]) | {g[r][c0] for r in range(r0, r1 + 1)} \
                | {g[r][c1] for r in range(r0, r1 + 1)}
            if len(ring) == 1:
                found.append((r0, r1, c0, c1, ring.pop()))
    found = [f for f in found if not any(o is not f and o[0] < f[0] and f[1] < o[1] and o[2] < f[2]
                                         and f[3] < o[3] for o in found)]
    if len(found) < 2:
        return None
    rk = {v: k for k, v in enumerate(sorted({f[0] for f in found}))}
    ck = {v: k for k, v in enumerate(sorted({f[2] for f in found}))}
    return sorted((r0 + 1, r1, c0 + 1, c1, rk[r0], ck[c0], col) for r0, r1, c0, c1, col in found)


class _Ctx:
    __slots__ = ("g", "P", "cont", "gb", "bg", "nb", "at")

    def __init__(self, g, panel, bgmode):
        P = _lattice(g) if panel == "lattice" else _boxes(g)
        if not P:
            raise ValueError
        self.g, self.P = g, P
        self.cont = [[row[c0:c1] for row in g[r0:r1]] for (r0, r1, c0, c1, _, _, _) in P]
        self.gb = _maj(Counter(v for m in self.cont for row in m for v in row))
        if bgmode == "global":
            self.bg = [self.gb] * len(P)
        else:
            self.bg = [_maj(Counter(v for row in m for v in row)) for m in self.cont]
        self.nb = [sum(v != b for row in m for v in row) for m, b in zip(self.cont, self.bg)]
        self.at = {(p[4], p[5]): k for k, p in enumerate(P)}


# ------------------------------------------------------------------ the generator
def _d4(m, k):
    x = [list(r) for r in m]
    if k & 4:
        x = [list(r) for r in zip(*x)]
    if k & 1:
        x = [r[::-1] for r in x]
    if k & 2:
        x = x[::-1]
    return x


def _fit_row(row, w2, b):
    w, out, j = len(row), [b] * w2, 0
    while j < w:
        v = row[j]
        if v == b:
            j += 1
            continue
        e = j
        while e + 1 < w and row[e + 1] == v:
            e += 1
        L, R, n = j, w - 1 - e, e - j + 1
        if L == R:
            lo, hi = L, w2 - 1 - R
        elif L < R:
            lo, hi = L, L + n - 1
        else:
            lo, hi = w2 - R - n, w2 - 1 - R
        for x in range(max(lo, 0), min(hi, w2 - 1) + 1):
            out[x] = v
        j = e + 1
    return out


def _fit(pat, h, w, b, mode):
    H, W = len(pat), len(pat[0])
    if (H, W) == (h, w):
        return pat
    if mode == "clip":
        return [[pat[i][j] if i < H and j < W else b for j in range(w)] for i in range(h)]
    if W != w:
        pat = [_fit_row(r, w, b) for r in pat]
    if H != h:
        pat = [list(r) for r in zip(*[_fit_row(list(c), h, b) for c in zip(*pat)])]
    return pat


def _template(cx, idxs, src):
    if src == "only":
        ne = [i for i in idxs if cx.nb[i]]
        if not ne or len({tuple(map(tuple, cx.cont[i])) for i in ne}) != 1:
            return None
        return ne[0]
    if src == "fullest":
        if not idxs:
            return None
        m = max(cx.nb[i] for i in idxs)
        top = [i for i in idxs if cx.nb[i] == m]
        if not m or len({tuple(map(tuple, cx.cont[i])) for i in top}) != 1:
            return None
        return top[0]
    c = src[1]
    hit = [i for i in idxs if any(c in row for row in cx.cont[i])]
    return hit[0] if len(hit) == 1 else None


def _targets(cx, idxs, T, tgt, src):
    bi, bj = cx.P[T][4], cx.P[T][5]
    if tgt == "all":
        return list(idxs)
    if tgt == "empty":
        return [i for i in idxs if i != T and not cx.nb[i]]
    if tgt == "stride2":
        return [i for i in idxs if (cx.P[i][4] - bi) % 2 == 0 and (cx.P[i][5] - bj) % 2 == 0]
    if not isinstance(src, tuple):
        return None
    pos = [(i, j) for i, row in enumerate(cx.cont[T]) for j, v in enumerate(row) if v == src[1]]
    if len(pos) != 1 or pos[0] not in cx.at or cx.at[pos[0]] not in idxs:
        return None
    return [cx.at[pos[0]]]


def _plan(cx, S):
    """S = (group, keys, src, tgt) -> list of (template, target, key colour) or None."""
    group, keys, src, tgt = S
    n = len(cx.P)
    keyof = {}
    if keys:
        ax = 5 if keys == "row" else 4
        for k in range(n):
            if cx.P[k][ax] == 0:
                cols = {v for row in cx.cont[k] for v in row} - {cx.bg[k]}
                keyof[cx.P[k][9 - ax]] = cols.pop() if len(cols) == 1 else None
    groups = {}
    for k in range(n):
        groups.setdefault(cx.P[k][6] if group == "frame" else 0, []).append(k)
    plan = []
    for gk in sorted(groups):
        idxs = groups[gk]
        cand = [k for k in idxs if not keys or cx.P[k][5 if keys == "row" else 4] != 0]
        T = _template(cx, cand, src)
        if T is None:
            continue
        ts = _targets(cx, idxs, T, tgt, src)
        if ts is None:
            return None
        for t in ts:
            kc = None
            if keys:
                kc = keyof.get(cx.P[t][4 if keys == "row" else 5])
                if kc is None:
                    return None
            plan.append((T, t, kc))
    return plan or None


def _pattern(cx, T, t, k, fit):
    r0, r1, c0, c1 = cx.P[t][:4]
    return _fit(_d4(cx.cont[T], k) if k else cx.cont[T], r1 - r0, c1 - c0, cx.bg[T], fit)


def _render(cx, T, t, pat, ink, kc, paint, clear):
    b, tb, fr = cx.bg[T], cx.bg[t], cx.P[t][6]
    reg = [[tb] * len(pat[0]) for _ in pat] if clear else [row[:] for row in cx.cont[t]]
    for i, prow in enumerate(pat):
        rr = reg[i]
        for j, v in enumerate(prow):
            if v == b:
                if paint == "replace":
                    rr[j] = tb
            elif paint != "under" or rr[j] == tb:
                rr[j] = v if ink == "own" else (fr if ink == "frame" else kc)
    return reg


def _offset(cx, T, t):
    return (cx.P[t][4] - cx.P[T][4], cx.P[t][5] - cx.P[T][5])


def _apply(g, prm):
    panel, bgmode, S, rest, xf, D = prm
    try:
        cx = _Ctx(g, panel, bgmode)
    except ValueError:
        return None
    plan = _plan(cx, S)
    if plan is None:
        return None
    out = [row[:] for row in g]
    if rest == "clear":
        for k, (r0, r1, c0, c1, _, _, _) in enumerate(cx.P):
            for r in range(r0, r1):
                out[r][c0:c1] = [cx.bg[k]] * (c1 - c0)
    for T, t, kc in plan:
        k = 0
        if xf is not None:
            k = xf.get(_offset(cx, T, t))
            if k is None:
                continue
        reg = _render(cx, T, t, _pattern(cx, T, t, k, D[0]), D[1], kc, D[2], rest == "clear")
        r0, _, c0, c1, _, _, _ = cx.P[t]
        for i, row in enumerate(reg):
            out[r0 + i][c0:c1] = row
    return out


# ------------------------------------------------------------------ induction
_COST = {"lattice": 0, "boxes": 1, "global": 0, "panel": 1, "one": 0, "frame": 1, None: 0, "row": 1, "col": 1.2,
         "only": 0, "fullest": 1, "all": 0, "empty": 0.3, "stride2": 1, "index": 1, "keep": 0, "clear": 1,
         "clip": 0, "margin": 1, "own": 0, "key": 0.5, "replace": 0, "overlay": 0.3, "under": 1}


def _region(g, p):
    return [row[p[2]:p[3]] for row in g[p[0]:p[1]]]


def _draw_search(cxs, outs, plans, rest, keys, sizes_differ):
    """Yield (xf, D) drawing choices that reproduce every target region of every pair."""
    jobs = [(cx, T, t, kc, _region(o, cx.P[t]), _offset(cx, T, t))
            for cx, o, pl in zip(cxs, outs, plans) for T, t, kc in pl]
    clear = rest == "clear"
    pats = {}

    def pat(n, k, fit):
        key = (n, k, fit)
        if key not in pats:
            cx, T, t = jobs[n][:3]
            pats[key] = _pattern(cx, T, t, k, fit)
        return pats[key]

    for fit in (("clip", "margin") if sizes_differ else ("clip",)):
        for ink in (("key",) if keys else ("own", "frame")):
            for paint in ("replace", "overlay", "under"):
                D = (fit, ink, paint)
                if all(_render(cx, T, t, pat(n, 0, fit), ink, kc, paint, clear) == want
                       for n, (cx, T, t, kc, want, _) in enumerate(jobs)):
                    yield None, D
                    continue
                okk = {}
                for n, (cx, T, t, kc, want, key) in enumerate(jobs):
                    s = [k for k in okk.get(key, range(8))
                         if _render(cx, T, t, pat(n, k, fit), ink, kc, paint, clear) == want]
                    if not s:
                        break
                    okk[key] = s
                else:
                    if okk:
                        yield {key: s[0] for key, s in okk.items()}, D


def _fam(train):
    try:
        pairs = [(p["input"], p["output"]) for p in train]
        if not pairs or any(len(a) != len(b) or len(a[0]) != len(b[0]) for a, b in pairs):
            return
        if all(a == b for a, b in pairs):
            return
    except Exception:
        return
    found = []

    def bound():
        return sorted(f[0] for f in found)[2] if len(found) >= 3 else float("inf")

    for panel in ("lattice", "boxes"):
        for bgmode in ("global", "panel"):
            try:
                cxs = [_Ctx(a, panel, bgmode) for a, _ in pairs]
            except ValueError:
                break
            if bgmode == "panel" and all(b == cx.gb for cx in cxs for b in cx.bg):
                continue                                   # same as bg=global on every pair
            outs = [b for _, b in pairs]
            # cells outside the panels never change
            ok = True
            for cx, (a, b) in zip(cxs, pairs):
                inside = [[False] * len(a[0]) for _ in a]
                for r0, r1, c0, c1, _, _, _ in cx.P:
                    for r in range(r0, r1):
                        inside[r][c0:c1] = [True] * (c1 - c0)
                if any(a[r][c] != b[r][c] and not inside[r][c] for r in range(len(a)) for c in range(len(a[0]))):
                    ok = False
                    break
            if not ok:
                break
            changed = [{k for k, p in enumerate(cx.P) if _region(cx.g, p) != _region(o, p)}
                       for cx, o in zip(cxs, outs)]
            markers = []
            for c in range(10):
                if all(sum(any(c in row for row in m) for m in cx.cont) == 1 for cx in cxs) and \
                        all(c != b for cx in cxs for b in cx.bg):
                    markers.append(("marker", c))
            one_frame = all(len({p[6] for p in cx.P}) == 1 for cx in cxs)
            for group in (("one",) if one_frame else ("one", "frame")):
                for keys in (None, "row", "col"):
                    for src in ["only", "fullest"] + markers:
                        for tgt in ("all", "empty", "stride2", "index"):
                            if tgt == "index" and not isinstance(src, tuple):
                                continue
                            base = sum(_COST[x] for x in (panel, bgmode, group, keys, tgt)) + \
                                (_COST[src] if isinstance(src, str) else 1)
                            if base > bound():
                                continue
                            S = (group, keys, src, tgt)
                            plans = [_plan(cx, S) for cx in cxs]
                            if any(pl is None for pl in plans):
                                continue
                            for rest in ("keep", "clear"):
                                if base + _COST[rest] > bound():
                                    continue
                                good = True
                                for cx, o, pl, ch in zip(cxs, outs, plans, changed):
                                    tg = {t for _, t, _ in pl}
                                    if rest == "keep":
                                        good = ch <= tg
                                    else:
                                        good = all(all(v == cx.bg[k] for row in _region(o, cx.P[k]) for v in row)
                                                   for k in range(len(cx.P)) if k not in tg)
                                    if not good:
                                        break
                                if not good:
                                    continue
                                sd = any((cx.P[T][1] - cx.P[T][0], cx.P[T][3] - cx.P[T][2]) !=
                                         (cx.P[t][1] - cx.P[t][0], cx.P[t][3] - cx.P[t][2])
                                         for cx, pl in zip(cxs, plans) for T, t, _ in pl)
                                for xf, D in _draw_search(cxs, outs, plans, rest, keys, sd):
                                    cost = base + _COST[rest] + sum(_COST[x] for x in D) + (0 if xf is None else 2)
                                    if cost > bound():
                                        continue
                                    srcn = src if isinstance(src, str) else "marker%d" % src[1]
                                    name = "propagate_panel_template[%s]" % ",".join(
                                        [panel, "bg=" + bgmode, "group=" + group, "keys=%s" % keys, "src=" + srcn,
                                         "tgt=" + tgt, "rest=" + rest, "xf=" + ("id" if xf is None else "d4"),
                                         "fit=" + D[0], "ink=" + D[1], "paint=" + D[2]])
                                    found.append((cost, name, (panel, bgmode, S, rest, xf, D)))
    found.sort(key=lambda x: (x[0], x[1]))
    n = 0
    for cost, name, prm in found:
        if n == 3:
            break
        if all(_apply(a, prm) == b for a, b in pairs):     # final whole-grid check
            n += 1
            yield name, cost, _safe(prm)


def _safe(prm):
    def fn(g):
        try:
            return _apply(g, prm)
        except Exception:
            return None
    return fn


def fam(train):
    try:
        progs = list(_fam(train))
    except Exception:
        return
    for prog in progs:
        yield prog


FAMILIES = [fam]
