"""Prior concept family continue_progression (test-blind; anti-unified from the member one-offs and their train pairs).

One generator:  EXTRAPOLATE a 1-D progression of unit terms along an axis.
The grid is viewed (rows / columns / long axis, forward / backward) so the progression runs along increasing index.
Unit terms are either whole slices of the grid (scope=grid: the non-background rows of the view) or the cells / runs
of every line separately (scope=line).  Term positions must follow  p_{j+1} = p_j + g0 + j*delta  (constant period
for delta=0, gap growing by delta otherwise; g0 read from the first two terms); term contents cycle through the
observed terms (colour cycle).  The sequence is continued until the grid edge.  Two further step models share the
same view / line / painting loop: run-period (each run before a wall repeats its colour every |run| cells beyond the
wall, nearer runs on top) and repair (each line's interior is rewritten to its majority period, overwriting the
cells that disagree).

Shared steps written once: background, views (orientation in / out), term extraction, the position law, the
content cycle, the paint-until-edge loop and the verify loop.
"""
from collections import Counter

CARD = "prior_continue_progression"
CONCEPT = "continue_progression"
MEMBERS = ["0a938d79", "12422b43", "135a2760", "1ae2feb7", "20a9e565", "221dfab4", "2ccd9fef", "34cfa167",
           "351d6448", "522fdd07", "5d588b4d", "695367ec", "72207abc", "762cd429", "8403a5d5", "bbc9ae5d",
           "bd4472b8", "c1990cce", "d304284e", "e78887d1", "e7b06bea", "f8c80d96", "fd4b2b02"]
READING = {
    "generator": "View the grid so the progression runs along increasing index, take the unit terms (non-background "
                 "slices of the grid, or the cells / runs of each line), infer the step (period g0 with gap growing "
                 "by delta, colour cycling through the observed terms; or each run's own length beyond a wall; or "
                 "the line's majority period) and paint the continued terms until the grid edge, in repair mode "
                 "overwriting cells that disagree with the period.",
    "stop": "Grid edge (the next term position falls outside the view); repair rewrites each line's interior once.",
    "params": "step ∈ {gap(delta ∈ {0,1,2}), run-period beyond wall, repair(majority period)} · "
              "scope ∈ {grid slices, line} (gap) · view ∈ {rows, cols, long axis} × {forward, backward} (gap), "
              "line direction ∈ {rows, cols, long} with the wall side chosen per grid (run-period), "
              "∈ {rows, cols, auto = more periodic orientation} (repair) · fill ∈ {copy term, uniform term colour} "
              "(grid scope)",
    "participants": "Background: most frequent colour. Grid terms: rows of the view holding any non-background cell "
                    "(uniform fill needs one colour per term). Line terms: non-background cells of the line. Wall: "
                    "a full non-background uniform slice across the lines; runs: maximal one-colour runs before it. "
                    "Repair segment: the line minus a symmetric frame of t cells, t and the period chosen by fewest "
                    "disagreements (each phase sampled at least 3 times).",
    "preconditions": "Gap step: >= 2 terms whose positions obey the law exactly; grid fill uniform needs single-colour "
                     "terms; run-period needs exactly one wall; repair needs a period with disagreements on at most "
                     "a quarter of the segment; the program reproduces every training pair.",
}


# ---------------------------------------------------------------- shared participants
def _bg(g):
    cnt = Counter(v for r in g for v in r)
    return max(cnt, key=lambda k: (cnt[k], -k))


def _T(g):
    return [list(r) for r in zip(*g)]


def _view(g, axis, back):
    """Return (view grid, inverse fn): progression along increasing row index of the view's slices,
    i.e. lines are the view's columns for scope=grid, and rows for scope=line (see callers)."""
    H, W = len(g), len(g[0])
    if axis == "long":
        axis = "rows" if H >= W else "cols"
    v = [list(r) for r in g] if axis == "rows" else _T(g)
    if back:
        v = v[::-1]

    def inv(o):
        if back:
            o = o[::-1]
        return [list(r) for r in o] if axis == "rows" else _T(o)
    return v, inv


def _positions(n, P, delta, limit):
    """Continue positions P (>=2, obeying p_{j+1} = p_j + g0 + j*delta) up to limit; None if P breaks the law."""
    if len(P) < 2:
        return None
    g0 = P[1] - P[0]
    if g0 <= 0:
        return None
    q = [P[0]]
    for j in range(1, n):
        q.append(q[-1] + g0 + (j - 1) * delta)
    if q != P:
        return None
    out = list(P)
    j = n
    while True:
        nxt = out[-1] + g0 + (j - 1) * delta
        if nxt >= limit or nxt <= out[-1]:
            break
        out.append(nxt)
        j += 1
    return out


# ---------------------------------------------------------------- step models (all paint in the view)
def _grid_gap(v, bg, delta, fill):
    """Terms = non-background rows of the view; continue with the gap law, contents cycling."""
    H, W = len(v), len(v[0])
    P = [i for i in range(H) if any(x != bg for x in v[i])]
    if len(P) < 2:
        return None
    terms = []
    for i in P:
        if fill == "uniform":
            cs = set(v[i]) - {bg}
            if len(cs) != 1:
                return None
            terms.append([cs.pop()] * W)
        else:
            terms.append(list(v[i]))
    pos = _positions(len(P), P, delta, H)
    if pos is None:
        return None
    out = [list(r) for r in v]
    for j, i in enumerate(pos):
        t = terms[j % len(terms)]
        for c in range(W):
            if t[c] != bg:
                out[i][c] = t[c]
    return out


def _line_gap(v, bg, delta):
    """Terms = non-background cells of every line (view row); continue each line with the gap law."""
    out = [list(r) for r in v]
    W = len(v[0])
    hit = False
    for i, row in enumerate(v):
        P = [j for j in range(W) if row[j] != bg]
        if not P:
            continue
        if len(P) < 2:
            return None
        pos = _positions(len(P), P, delta, W)
        if pos is None:
            return None
        cols = [row[j] for j in P]
        for k, j in enumerate(pos):
            out[i][j] = cols[k % len(cols)]
        hit = True
    return out if hit else None


def _line_runs(v, bg):
    """Wall = a view column of one non-background colour crossing every non-empty line, with one side empty;
    each run on the other side repeats its colour every |run| cells beyond the wall (nearer runs on top)."""
    H, W = len(v), len(v[0])
    live = [i for i in range(H) if any(x != bg for x in v[i])]
    cands = []
    for j in range(W):
        col = v[live[0]][j] if live else bg
        if col == bg or any(v[i][j] != col for i in live) or len(live) < 2:
            continue
        if any(v[i][j] not in (bg, col) for i in range(H)):
            continue
        right_empty = all(v[i][k] == bg for i in range(H) for k in range(j + 1, W))
        left_empty = all(v[i][k] == bg for i in range(H) for k in range(j))
        if right_empty != left_empty:
            cands.append((j, right_empty))
    if len(cands) != 1:
        return None
    j0, right = cands[0]
    lines = [list(r) for r in v] if right else [r[::-1] for r in v]
    w = j0 if right else W - 1 - j0
    if w + 1 >= W:
        return None
    out = [list(r) for r in lines]
    for i in range(H):
        seg = lines[i][:w]
        runs = []
        j = 0
        while j < w:
            if seg[j] == bg:
                j += 1
                continue
            k = j
            while k < w and seg[k] == seg[j]:
                k += 1
            runs.append((seg[j], k - j))
            j = k
        for col, L in runs:                       # outer to inner: the run nearest the wall ends on top
            for p in range(w + 1, W, L):
                out[i][p] = col
    return out if right else [r[::-1] for r in out]


def _repair_line(row, a, b):
    seg = row[a:b]
    n = len(seg)
    best = None
    for p in range(1, n // 3 + 1):
        pat, m = [], 0
        for ph in range(p):
            cnt = Counter(seg[ph::p])
            top = max(cnt, key=lambda k: (cnt[k], -k))
            pat.append(top)
            m += len(seg[ph::p]) - cnt[top]
        if 4 * m > n:
            continue
        if best is None or m < best[0]:
            best = (m, pat)
        if m == 0:
            break
    if best is None:
        return list(row), n
    m, pat = best
    out = list(row)
    for j in range(a, b):
        out[j] = pat[(j - a) % len(pat)]
    return out, m


def _line_repair(v, bg):
    """Frame = leading / trailing view columns constant over all non-uniform lines; each line's interior is
    rewritten to its majority period."""
    W = len(v[0])
    content = [r for r in v if len(set(r)) > 1]
    if not content:
        return None
    a = 0
    while a < W and len(set(r[a] for r in content)) == 1:
        a += 1
    b = W
    while b > a and len(set(r[b - 1] for r in content)) == 1:
        b -= 1
    if b - a < 3:
        return None
    res = [_repair_line(r, a, b) for r in v]
    out = [r for r, _ in res]
    return (out, sum(m for _, m in res)) if out != v else None


# ---------------------------------------------------------------- the generator
def _make(axis, back, step, delta, fill):
    def fn(g):
        bg = _bg(g)
        if step == "line_repair" and axis == "auto":
            # line direction chosen per grid: the orientation whose lines are the more periodic
            best = None
            for ax in ("rows", "cols"):
                v, inv = _view(g, ax, False)
                r = _line_repair(v, bg)
                if r is not None and (best is None or r[1] < best[0]):
                    best = (r[1], inv(r[0]))
            return None if best is None else best[1]
        if step == "grid_gap":
            # slices of the view = rows; build view so slices are rows
            v, inv = _view(g, axis, back)
            o = _grid_gap(v, bg, delta, fill)
        else:
            # lines run along the progression: view rows are the lines (axis names the line direction)
            lines_rows = axis == "rows" or (axis == "long" and len(g[0]) >= len(g))
            v, inv = _view(g, "rows" if lines_rows else "cols", False)
            if back:
                v = [r[::-1] for r in v]
                inv0 = inv
                inv = lambda o, inv0=inv0: inv0([r[::-1] for r in o])
            if step == "line_gap":
                o = _line_gap(v, bg, delta)
            elif step == "line_runs":
                o = _line_runs(v, bg)
            else:
                o = _line_repair(v, bg)
                o = None if o is None else o[0]
        return None if o is None else inv(o)
    return fn


def _programs():
    progs = []
    for step, base in (("grid_gap", 1), ("line_gap", 1), ("line_runs", 2), ("line_repair", 3)):
        deltas = (0, 1, 2) if step in ("grid_gap", "line_gap") else (0,)
        fills = ("copy", "uniform") if step == "grid_gap" else ("copy",)
        backs = (False, True) if step in ("grid_gap", "line_gap") else (False,)
        axes = ("auto", "rows", "cols") if step == "line_repair" else ("long", "rows", "cols")
        for axis in axes:
            for back in backs:
                for delta in deltas:
                    for fill in fills:
                        cost = base + delta * 0.5 + (fill == "uniform") * 0.25 + (axis not in ("long", "auto")) * 0.1 + back * 0.1
                        name = "%s_%s%s_d%d_%s" % (step, axis, "_back" if back else "", delta, fill)
                        progs.append((cost, name, _make(axis, back, step, delta, fill)))
    progs.sort(key=lambda t: t[0])
    return progs


_PROGS = _programs()


def fam(train):
    pairs = [(p["input"], p["output"]) for p in train]
    if not pairs or any(len(a) != len(b) or len(a[0]) != len(b[0]) for a, b in pairs):
        return
    if all(a == b for a, b in pairs):
        return
    n = 0
    for cost, name, fn in _PROGS:
        ok = True
        for a, b in pairs:
            try:
                if fn(a) != b:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield (name, cost, fn)
            n += 1
            if n >= 3:
                return


FAMILIES = [fam]
