"""Prior family "count_bar_chart" (test-blind; anti-unified from the member one-offs and their train pairs only).
priors4 (Fable v11, D38 / G68): every colour parameter is a declared role of colour_roles.py (background,
rank_colour(k), novel_colour) or a role-bound value; no literal colour numbers.  Non-colour parameters, steps and
the enumeration order are those of priors3 (literal-colour options dropped or re-bound to roles).

One generator, TALLY -> CHART: tally a category in the input (cells per colour, same-colour objects per colour,
objects per shape, loose counters per colour, optionally one tally minus another), select which tallies are shown,
and render every shown tally as a run of marker cells (a bar, a solid square of that area, or a bead run with a
pitch) standing on a baseline of a chart canvas.  The canvas is a new grid sized by the largest tally, an induced
fixed-size template, the blank side of a separator line, the next slot of an existing bar series, or the rod of the
hollow frame owning that colour.  Shared steps written once: background by role, component extraction, the tally,
the run-drawing loop and the orientation normalisation.
Colour roles used: background = CR.background(g, train) (ties by frequency over the training inputs, as before);
  novel = CR.novel_colour(train); ink rank k = CR.rank_colour(g, k, bg); participant colours: the tallied colour,
  the separator / frame / bar colours read from the grid.  Role-keyed tables: fixed slot order (ink rank -> slot),
  template keys (ink rank, or the normalised shape with each colour replaced by its ink rank), template colours and
  canvas background (novel | background | ink rank).

BINDINGS (G68) -- per member, the literal colour value priors3 induced and the role it became
("LOST: needs literal c" = no declared role explains it; the member no longer fits).
  2685904e  bar colour <- the tallied colour (participant) ; separator read from the grid                 FITS
  27a77e38  marker colour <- the most frequent data colour (participant)                                  FITS
  37ce87bb  bar colour 5 <- novel (was a literal) ; plus/minus <- rank1 / rank2 ; edge <- bar feet         FITS
  8abad3cf  fill 7 <- background                                                                          FITS
  8f215267  bead colour <- the frame's own colour (participant)                                           FITS
  9af7a82c  fill 0 <- novel                                                                               FITS
  aaecdb9a  slot table 5,2,8,9,6  LOST: needs literal 5, 2, 8, 9, 6 (no ink rank names a slot's colour in every
            pair; fill 7 <- background would still hold)
  d5c634a2  canvas background 0 <- background ; shape keys: colour 2 <- rank1 ; template colours 3, 1  LOST: needs
            literal 3, 1 (two colours new in the outputs, so novel_colour is undefined)
  Unfitted in priors3 and still unfitted: a1aa0c1e, b1986d4b.
Literal colours removed: fill fallback 0, series plus/minus literal colours (-> every declared ink rank), series
bar colour (-> novel), fixed slot table keys, template background / colours / colour keys (-> roles).
"""
from collections import Counter

import colour_roles as CR

CARD = "prior4_count_bar_chart"
CONCEPT = "count_bar_chart"
MEMBERS = ["2685904e", "27a77e38", "37ce87bb", "8abad3cf", "8f215267", "9af7a82c", "a1aa0c1e", "aaecdb9a",
           "b1986d4b", "d5c634a2"]
READING = {
    "generator": "Tally a category of the input (cells or same-colour objects per colour, objects per shape, loose "
                 "counters per colour, or one colour's count minus another's), keep the selected tallies and draw "
                 "each as a run of its colour whose length (or square area) equals the tally, standing on the "
                 "baseline of a chart canvas: a new grid as long as the largest tally with bars ordered by count or "
                 "in a fixed induced colour order, an induced fixed slot template, the blank side of a separator, "
                 "the next slot of an existing bar series, or the rod of the frame of the same colour.",
    "stop": "A run stops after exactly `count` marker cells (one cell for unit length); it is rejected if it would "
            "leave its canvas or hit ink; the chart ends when every selected tally is drawn.",
    "params": "canvas ∈ {grid, slots, panel, series, frame} · unit ∈ {cell, obj4, obj8, shape4, shape8} · "
              "fill ∈ {background, novel} · order ∈ {desc, asc, fixed (ink rank -> slot)} · glyph ∈ {bar, square} · "
              "edge ∈ {feet (edge carrying the bars), top, bottom, left, right} · gap ∈ {0, 1} · "
              "sel ∈ {all, key, max, min} · base ∈ {sep, far} · pos ∈ {occ, mid} · len ∈ {count, unit} · "
              "plus/minus ∈ {ink rank 1/2 (feet edge), any declared ink rank (fixed edge), none} · bar colour = novel · "
              "side ∈ {near, far, lo, hi} · "
              "pitch/offset ∈ {1+gap/gap, literal pitch 1..3 / offset 0..2}",
    "participants": "bg = most frequent colour of the grid (ties by frequency over the training inputs); tallied "
                    "items = non-background cells / 4- or 8-connected same-colour objects / multicolour objects "
                    "keyed by normalised shape; separator = the unique full line of one colour; series bars = "
                    "baseline-anchored columns of ink; frames = 1-thick hollow rectangles, counters = the "
                    "components outside them.",
    "preconditions": "grid/slots: output colours are tallied colours plus the fill, output size follows the tallies "
                     "(or is constant for slots); panel/series/frame: same size, only background cells (or loose "
                     "counters) change; every parameter is chosen by exact fit on all training pairs.",
}

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIRS8 = DIRS4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))
EDGES = ('top', 'bottom', 'left', 'right')


# ----------------------------------------------------------------------------------------------- shared steps
def _copy(g):
    return [list(r) for r in g]


def _T(g):
    return [list(r) for r in zip(*g)]


def _to_top(g, edge):
    """Normalise a grid so that `edge` becomes the top edge."""
    if edge == 'top':
        return _copy(g)
    if edge == 'bottom':
        return [list(r) for r in g[::-1]]
    if edge == 'left':
        return _T(g)
    return _T([r[::-1] for r in g])           # right


def _from_top(g, edge):
    if edge == 'top':
        return _copy(g)
    if edge == 'bottom':
        return [list(r) for r in g[::-1]]
    if edge == 'left':
        return _T(g)
    return [r[::-1] for r in _T(g)]           # right


def _bg_fn(train):
    """role background (ties -> the colour more frequent over the training inputs, then the lower number)."""
    def bg(g):
        return CR.background(g, train)
    return bg


# ------------------------------------------------------------------------------------------ colour roles (G68)
RANKS = CR.RANKS


def _target_role(train, bgf, idx, t, N):
    """the role naming colour t in every training input of idx: novel | background | ink rank k (None if none)."""
    if not idx:
        return None
    if N is not None and t == N:
        return ('novel',)
    if all(bgf(train[i]['input']) == t for i in idx):
        return ('bg',)
    for k in RANKS:
        if all(CR.rank_colour(train[i]['input'], k, bgf(train[i]['input'])) == t for i in idx):
            return ('rank', k)
    return None


def _resolve(role, g, bg, N):
    if role[0] == 'novel':
        return N
    if role[0] == 'bg':
        return bg
    return CR.rank_colour(g, role[1], bg)


def _components(g, bg, conn, same):
    """Components of non-bg cells; same=True keeps one colour per component."""
    H, W = len(g), len(g[0])
    nb = DIRS8 if conn == 8 else DIRS4
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            c = g[i][j]
            seen[i][j] = True
            st, cells = [(i, j)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg \
                            and (not same or g[x][y] == c):
                        seen[x][y] = True
                        st.append((x, y))
            out.append((c, cells))
    return out


def _tally(g, bg, unit):
    """Counter category -> count.  Categories are colours, except for shape units (normalised shapes)."""
    if unit == 'cell':
        return Counter(v for r in g for v in r if v != bg)
    if unit in ('obj4', 'obj8'):
        return Counter(c for c, _ in _components(g, bg, 4 if unit == 'obj4' else 8, True))
    conn = 4 if unit == 'shape4' else 8
    cnt = Counter()
    for _, cells in _components(g, bg, conn, False):
        r0 = min(a for a, _ in cells)
        c0 = min(b for _, b in cells)
        cnt[tuple(sorted((a - r0, b - c0, g[a][b]) for a, b in cells))] += 1
    return cnt


def _run(out, r, c, dr, dc, n, pitch, col, bg=None, lim=None):
    """THE drawing loop: paint n marker cells from (r, c) stepping (dr, dc)*pitch.  Fails (False) when a cell would
    leave the canvas (grid or `lim` = (r0, c0, r1, c1)) or, if bg is given, land on a cell that is not bg."""
    H, W = len(out), len(out[0])
    r0, c0, r1, c1 = lim if lim else (0, 0, H - 1, W - 1)
    for k in range(n):
        y, x = r + dr * pitch * k, c + dc * pitch * k
        if not (r0 <= y <= r1 and c0 <= x <= c1):
            return False
        if bg is not None and out[y][x] != bg and out[y][x] != col:
            return False
        out[y][x] = col
    return True


def _isqrt_exact(n):
    s = int(round(n ** 0.5))
    return s if s * s == n else None


# ------------------------------------------------------------------------------- canvas: a new grid (chart)
def _chart_grid(tal, fill, order, glyph, edge, gap, slots):
    """slots (order=fixed): (number of slots, {colour: slot}) already resolved on the grid from the role-keyed table."""
    items = [(n, col) for col, n in tal.items() if n > 0 and isinstance(col, int)]
    if order == 'fixed':
        nslots, pos = slots
        items = [(n, col) for n, col in items if col in pos]
    if not items:
        return None
    glyphs = []                                   # (colour, thickness, length, x)
    if order == 'fixed':
        for n, col in sorted(items, key=lambda t: pos[t[1]]):
            glyphs.append((col, 1, n, pos[col]))
        width = nslots
    else:
        items.sort(key=lambda t: (-t[0] if order == 'desc' else t[0], t[1]))
        x = 0
        for n, col in items:
            if glyph == 'square':
                s = _isqrt_exact(n)
                if s is None:
                    return None
                glyphs.append((col, s, s, x))
                x += s + gap
            else:
                glyphs.append((col, 1, n, x))
                x += 1 + gap
        width = x - gap
    length = max(l for _, _, l, _ in glyphs)
    if length > 30 or width > 30 or width < 1:
        return None
    out = [[fill] * width for _ in range(length)]
    for col, t, l, x in glyphs:
        for k in range(t):
            _run(out, 0, x + k, 1, 0, l, 1, col)
    return _from_top(out, edge)


def _induce_slots(train, fillf, edge):
    """Fixed colour order: the bar slot of each colour, read from the training outputs (normalised to top)."""
    pos, nslots = {}, None
    for p in train:
        fill = fillf(p['input'])
        o = _to_top(p['output'], edge)
        if nslots is None:
            nslots = len(o[0])
        elif nslots != len(o[0]):
            return None
        for row in o:
            for x, v in enumerate(row):
                if v != fill:
                    if pos.get(v, x) != x:
                        return None
                    pos[v] = x
    return (nslots, pos) if pos else None


def _role_slots(train, bgf, slots):
    """literal {colour: slot} read from the outputs -> ((ink rank k, slot), ...): each colour is replaced by the ink
    rank naming it in every training input whose output shows it.  None when some colour has no rank role."""
    if slots is None:
        return None
    nslots, pos = slots
    out = []
    for c in sorted(pos):
        idx = [i for i, p in enumerate(train) if any(v == c for r in p['output'] for v in r)]
        k = next((k for k in RANKS
                  if idx and all(CR.rank_colour(train[i]['input'], k, bgf(train[i]['input'])) == c for i in idx)), None)
        if k is None or any(k == kk for kk, _ in out):
            return None
        out.append((k, pos[c]))
    return nslots, tuple(out)


def _resolve_slots(g, bg, rslots):
    nslots, rt = rslots
    pos = {}
    for k, x in rt:
        c = CR.rank_colour(g, k, bg)
        if c is not None and c not in pos:
            pos[c] = x
    return nslots, pos


# ------------------------------------------------------------------------ canvas: an induced fixed template
def _tally_roles(g, bg, unit):
    """the tally with role keys: colour units -> ink rank k of the tallied colour; shape units -> the normalised shape
    with every colour replaced by its ink rank.  Categories whose colour has no rank role are dropped."""
    tal = _tally(g, bg, unit)
    role = {}
    for k in reversed(RANKS):                    # colour -> first ink rank naming it (computed once per grid)
        c = CR.rank_colour(g, k, bg)
        if c is not None:
            role[c] = k
    out = Counter()
    for key, n in tal.items():
        if isinstance(key, int):
            k = role.get(key)
            if k is not None:
                out[k] += n
        else:
            ks = tuple((a, b, role.get(c)) for a, b, c in key)
            if all(t[2] is not None for t in ks):
                out[ks] += n
    return out


def _induce_template(train, tals, order, bgf, N):
    """tals: role-keyed tallies.  Output background and every template colour are re-bound to roles."""
    shapes = {(len(p['output']), len(p['output'][0])) for p in train}
    if len(shapes) != 1:
        return None
    H, W = shapes.pop()
    tot = Counter(v for p in train for r in p['output'] for v in r)
    obg = max(tot, key=lambda k: (tot[k], -k))
    allp = list(range(len(train)))
    obg_role = _target_role(train, bgf, allp, obg, N)
    if obg_role is None:
        return None
    keys = set()
    for t in tals:
        keys |= set(t)
    rules, used = [], set()
    for col in sorted(c for c in tot if c != obg):
        ncol = [sum(1 for r in p['output'] for v in r if v == col) for p in train]
        cand = sorted((k for k in keys if k not in used and all(t.get(k, 0) == n for t, n in zip(tals, ncol))),
                      key=repr)
        if len(cand) != 1:
            return None
        used.add(cand[0])
        cells = {(i, j) for p in train for i in range(H) for j in range(W) if p['output'][i][j] == col}
        seq = sorted(cells) if order == 'row' else sorted(cells, key=lambda t: (t[1], t[0]))
        for p, n in zip(train, ncol):
            if {(i, j) for i in range(H) for j in range(W) if p['output'][i][j] == col} != set(seq[:n]):
                return None
        crole = _target_role(train, bgf, [i for i, n in enumerate(ncol) if n > 0], col, N)
        if crole is None:
            return None                      # template colour without a role (would need a literal)
        rules.append((cand[0], crole, seq))
    return (H, W, obg_role, rules) if rules else None


def _chart_template(tal, H, W, obg_role, rules, g, bg, N):
    obg = _resolve(obg_role, g, bg, N)
    if obg is None:
        return None
    out = [[obg] * W for _ in range(H)]
    for key, crole, seq in rules:
        col = _resolve(crole, g, bg, N)
        if col is None:
            return None
        for i, j in seq[:min(tal.get(key, 0), len(seq))]:
            out[i][j] = col
    return out


# --------------------------------------------------------------- canvas: blank side of a separator (panel)
def _separator(g, bg):
    H, W = len(g), len(g[0])
    c = [('r', r) for r in range(H) if g[r][0] != bg and len(set(g[r])) == 1]
    c += [('c', x) for x in range(W) if g[0][x] != bg and len({g[r][x] for r in range(H)}) == 1]
    return c[0] if len(c) == 1 else None


def _chart_panel(g, bg, sel, base, pos, length):
    sep = _separator(g, bg)
    if sep is None:
        return None
    axis, s = sep
    work = _T(g) if axis == 'c' else _copy(g)
    H, W = len(work), len(work[0])
    top, bot = list(range(0, s)), list(range(s + 1, H))
    ink = lambda rows: sum(1 for r in rows for v in work[r] if v != bg)
    if not top or not bot or ink(top) == ink(bot):
        return None
    data, chart = (top, bot) if ink(top) > ink(bot) else (bot, top)
    rows = sorted(chart, key=lambda r: abs(r - s))
    if base == 'far':
        rows = rows[::-1]
    step = 1 if rows[-1] > rows[0] or len(rows) == 1 else -1
    tal = _tally([work[r] for r in data], bg, 'cell')
    if not tal:
        return None
    key = sum(1 for r in chart for v in work[r] if v != bg)
    if sel == 'key':
        chosen = [c for c, n in tal.items() if n == key]
    else:
        m = (max if sel == 'max' else min)(tal.values())
        chosen = [c for c, n in tal.items() if n == m]
    out = [row[:] for row in work]
    lim = (min(chart), 0, max(chart), W - 1)
    for col in sorted(chosen):
        n = tal[col] if length == 'count' else 1
        if pos == 'occ':
            xs = sorted({x for r in data for x in range(W) if work[r][x] == col})
        else:
            if W % 2 == 0 or len(chosen) != 1:
                return None
            xs = [W // 2]
        for x in xs:
            if not _run(out, rows[0], x, step, 0, n, 1, col, bg, lim):
                return None
    return _T(out) if axis == 'c' else out


# ------------------------------------------------------------ canvas: next slot of an existing bar series
def _feet(g, bg, edge):
    """Number of ink cells on the grid edge `edge` (bar feet when bars stand on that edge)."""
    return sum(1 for v in _to_top(g, edge)[0] if v != bg)


def _feet_edge(g, bg):
    """Role-bound baseline: the unique grid edge carrying >= 2 bar feet."""
    c = [e for e in EDGES if _feet(g, bg, e) >= 2]
    return c[0] if len(c) == 1 else None


def _colour(g, bg, ref):
    """ref = ('rank', k) -- role CR.rank_colour -- or None."""
    if ref is None:
        return None
    return CR.rank_colour(g, ref[1], bg)


def _chart_series(g, bg, edge, plus, minus, new, absval):
    if edge == 'feet':
        edge = _feet_edge(g, bg)
        if edge is None:
            return None
    w = _to_top(g, edge)
    H, W = len(w), len(w[0])
    cols = [x for x in range(W) if w[0][x] != bg]          # bars standing on the baseline (top after normalising)
    if len(cols) < 2:
        return None
    nxt = cols[-1] + (cols[-1] - cols[-2])
    if not 0 <= nxt < W:
        return None
    tal = Counter(v for r in g for v in r)
    plus, minus = _colour(g, bg, plus), _colour(g, bg, minus)
    if plus is None:
        return None
    n = tal.get(plus, 0) - (tal.get(minus, 0) if minus is not None else 0)
    if absval:
        n = abs(n)
    if n < 1:
        return None
    if not _run(w, 0, nxt, 1, 0, n, 1, new, bg):
        return None
    return _from_top(w, edge)


# ------------------------------------------------------------------ canvas: rod of each hollow frame (abacus)
def _frames(g, bg):
    res = []
    for c, cells in _components(g, bg, 4, True):
        ys = [y for y, _ in cells]; xs = [x for _, x in cells]
        r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
        if r1 - r0 < 2 or c1 - c0 < 2 or len(cells) != 2 * (r1 - r0 + c1 - c0):
            continue
        if any(not (y in (r0, r1) or x in (c0, c1)) for y, x in cells):
            continue
        if any(g[y][x] != bg for y in range(r0 + 1, r1) for x in range(c0 + 1, c1)):
            continue
        res.append((c, (r0, c0, r1, c1)))
    return res


def _chart_frame(g, bg, unit, side, offset, pitch):
    H, W = len(g), len(g[0])
    frames = _frames(g, bg)
    if not frames:
        return None
    infr = {(y, x) for _, (r0, c0, r1, c1) in frames for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)}
    g2 = [[bg if (y, x) in infr else g[y][x] for x in range(W)] for y in range(H)]
    tal = _tally(g2, bg, unit)
    lc = [(y, x) for y in range(H) for x in range(W) if g2[y][x] != bg]
    out = [[bg] * W for _ in range(H)]
    for c, (r0, c0, r1, c1) in frames:
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                if y in (r0, r1) or x in (c0, c1):
                    out[y][x] = c
    for c, (r0, c0, r1, c1) in frames:
        horiz = (c1 - c0) >= (r1 - r0)
        k = 1 if horiz else 0                      # axis along the rod
        lo, hi = (c0 + 1, c1 - 1) if horiz else (r0 + 1, r1 - 1)
        mid = (lo + hi) / 2.0
        ncen = sum(p[k] for p in lc) / len(lc) if lc else mid
        from_hi = {'lo': False, 'hi': True, 'near': ncen >= mid, 'far': ncen < mid}[side]
        n = tal.get(c, 0)
        start = hi - offset if from_hi else lo + offset
        d = -1 if from_hi else 1
        n = min(n, max(0, (hi - lo - offset) // pitch + 1))
        if horiz:
            _run(out, (r0 + r1) // 2, start, 0, d, n, pitch, c, None, (r0, c0 + 1, r1, c1 - 1))
        else:
            _run(out, start, (c0 + c1) // 2, d, 0, n, pitch, c, None, (r0 + 1, c0, r1 - 1, c1))
    return out


# --------------------------------------------------------------------------------------------- the generator
def _fits(fn, train):
    try:
        return all(fn(p['input']) == p['output'] for p in train)
    except Exception:
        return False


def _cands(train):
    bgf = _bg_fn(train)
    same = all(len(p['input']) == len(p['output']) and len(p['input'][0]) == len(p['output'][0]) for p in train)
    ins = [p['input'] for p in train]
    N = CR.novel_colour(train)                             # role novel_colour, fixed by the training pairs

    # ---- canvas = new grid sized by the tallies
    # fill: background (role) | the novel colour (role); no literal fallback
    fill_modes = [('bg', None)] + ([('new', N)] if N is not None else [])
    for fill_mode, fconst in fill_modes:
        fillf = (bgf if fill_mode == 'bg' else (lambda g, c=fconst: c))
        fills = [fillf(g) for g in ins]
        if any(not (set(v for r in p['output'] for v in r) <= set(v for r in p['input'] for v in r) | {f})
               for p, f in zip(train, fills)):
            continue
        for unit in ('cell', 'obj8', 'obj4'):
            tals = [_tally(g, f, unit) for g, f in zip(ins, fills)]
            for order in ('desc', 'asc', 'fixed'):
                for glyph in (('bar',) if order == 'fixed' else ('bar', 'square')):
                    for edge in EDGES:
                        rslots = (_role_slots(train, bgf, _induce_slots(train, fillf, edge))
                                  if order == 'fixed' else None)
                        if order == 'fixed' and rslots is None:
                            continue
                        for gap in ((0,) if order == 'fixed' else (0, 1)):
                            if not all(_chart_grid(t, f, order, glyph, edge, gap,
                                                   _resolve_slots(p['input'], bgf(p['input']), rslots)
                                                   if rslots else None) == p['output']
                                       for t, f, p in zip(tals, fills, train)):
                                continue
                            fn = (lambda g, a=(unit, order, glyph, edge, gap), rs=rslots, ff=fillf:
                                  _chart_grid(_tally(g, ff(g), a[0]), ff(g), *a[1:],
                                              _resolve_slots(g, bgf(g), rs) if rs else None))
                            yield ('chart:grid[unit=%s,fill=%s,order=%s,glyph=%s,edge=%s,gap=%d]'
                                   % (unit, fill_mode, order, glyph, edge, gap),
                                   1 + (unit != 'cell') + (order == 'fixed') + gap, fn)

    # ---- canvas = induced fixed template (constant output size)
    if len({(len(p['output']), len(p['output'][0])) for p in train}) == 1:
        for unit in ('cell', 'obj4', 'obj8', 'shape4', 'shape8'):
            tals = [_tally_roles(g, bgf(g), unit) for g in ins]
            for order in ('row', 'col'):
                m = _induce_template(train, tals, order, bgf, N)
                if m is None:
                    continue
                fn = (lambda g, u=unit, m=m: _chart_template(_tally_roles(g, bgf(g), u), *m, g, bgf(g), N))
                if _fits(fn, train):
                    yield ('chart:slots[unit=%s,order=%s]' % (unit, order), 3, fn)
                    break

    if not same:
        return

    # ---- canvas = blank side of a separator line
    if all(_separator(g, bgf(g)) is not None for g in ins):
        for sel in ('key', 'max', 'min'):
            for base in ('sep', 'far'):
                for pos in ('occ', 'mid'):
                    for length in ('count', 'unit'):
                        fn = (lambda g, a=(sel, base, pos, length): _chart_panel(g, bgf(g), *a))
                        if _fits(fn, train):
                            yield ('chart:panel[sel=%s,base=%s,pos=%s,len=%s]' % (sel, base, pos, length), 2, fn)

    # ---- canvas = next slot of an existing bar series (bar colour <- novel colour, tally may be a difference)
    if N is not None:
        new = N
        # role-bound first: edge <- the edge carrying the bar feet; plus/minus <- ink colours of count rank 1/2
        if all(_feet_edge(g, bgf(g)) is not None for g in ins):
            ranks = [('rank', 1), ('rank', 2)]
            for absval in (False, True):
                for plus in ranks:
                    for minus in [None] + ranks:
                        if minus == plus:
                            continue
                        fn = (lambda g, a=('feet', plus, minus, new, absval): _chart_series(g, bgf(g), *a))
                        if _fits(fn, train):
                            yield ('chart:series[edge=feet,plus=rank%d,minus=%s,abs=%d]'
                                   % (plus[1], 'rank%d' % minus[1] if minus else None, absval),
                                   1 + absval + (minus is not None), fn)
        # fixed-edge fallback (the edge is not a colour); plus/minus over every declared ink rank (no literal colours)
        ranks = [('rank', k) for k in RANKS]
        for edge in EDGES:
            if not all(_feet(g, bgf(g), edge) >= 2 for g in ins):
                continue
            for absval in (False, True):
                for plus in ranks:
                    for minus in [None] + ranks:
                        if minus == plus:
                            continue
                        fn = (lambda g, a=(edge, plus, minus, new, absval): _chart_series(g, bgf(g), *a))
                        if _fits(fn, train):
                            yield ('chart:series[edge=%s,plus=rank%d,minus=%s,abs=%d]'
                                   % (edge, plus[1], 'rank%d' % minus[1] if minus else None, absval),
                                   2 + absval + (minus is not None), fn)

    # ---- canvas = rod of each hollow frame; counters = loose components outside the frames
    if all(_frames(g, bgf(g)) for g in ins):
        # role-bound spacing first: bead + gap (pitch = 1 + gap), first bead one gap from the wall (offset = gap)
        spacings = [(gap, 1 + gap, 'gap=%d' % gap) for gap in (0, 1)]
        spacings += [(o, p, 'offset=%d,pitch=%d' % (o, p)) for o in (0, 1, 2) for p in (1, 2, 3)
                     if (o, p) not in ((0, 1), (1, 2))]     # literal fallback (role-bound pairs are above)
        for unit in ('obj4', 'obj8', 'cell'):
            for side in ('near', 'far', 'lo', 'hi'):
                for offset, pitch, tag in spacings:
                    fn = (lambda g, a=(unit, side, offset, pitch): _chart_frame(g, bgf(g), *a))
                    if _fits(fn, train):
                        yield ('chart:frame[unit=%s,side=%s,%s]' % (unit, side, tag),
                               2 + (side in ('lo', 'hi')) + (not tag.startswith('gap')), fn)


def fam(train):
    if not train or any(not p['input'] or not p['input'][0] or not p['output'] or not p['output'][0] for p in train):
        return
    found = []
    for name, cost, fn in _cands(train):
        found.append((cost, len(found), name, fn))
        if len(found) >= 6:
            break
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, fn in found[:3]:
        yield (name, cost, fn)


FAMILIES = [fam]
