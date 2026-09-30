"""fill.bg_windows: paint square patches made only of a target colour r with a paint colour p.

Reviewer rule for mechanism group M050 (Len, 2026-09-29): "cover the largest square background patch with colour".
Topology / geometry prior: a maximal empty square is the largest disc of the L-infinity metric inside a region.

Everything is induced from the training pairs:
  r         the single input colour of the changed cells: a literal colour when constant across pairs,
            else the per-grid role 'bg' (most frequent colour)
  p         the single output colour of the changed cells (constant across pairs)
  selector  which squares are painted (m = minimum side, induced from the smallest painted square):
    win k       every k x k window made only of r (union of placements)
    maxwin>=m   the windows of the LARGEST side K for which an all-r K x K window exists in this grid, if K >= m
    compsq>=m   4-connected components of r that are solid squares with side >= m
    comprect>=m 4-connected components of r that are solid rectangles with both sides >= m
    greedy>=m   repeatedly the largest all-r square not overlapping earlier picks (ties: reading order of the
                top-left corner), while its side is >= m
    maxrect/s   the unique largest-AREA all-r axis rectangle (s = 1: its interior, border ring left unpainted)
    maxrect2/s  the same among rectangles with both sides >= 2 (a patch, not a line)
    maxsq/s     the unique largest all-r square (s = 1: interior)
    maxdiag     the unique longest diagonal run of r cells (either diagonal direction)
Mechanism group M067 "fill.largest empty" is the same concept (reviewer's parent concept "patch").
A program is kept only if it reproduces every training output exactly.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _sq(g, r, blocked=None):
    """S[y][x] = side of the largest all-r square whose bottom-right corner is (y, x)."""
    h, w = H(g), W(g)
    S = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if g[y][x] != r or (blocked and (y, x) in blocked):
                continue
            S[y][x] = 1 if y == 0 or x == 0 else 1 + min(S[y - 1][x], S[y][x - 1], S[y - 1][x - 1])
    return S


def _windows(g, r, k):
    S = _sq(g, r)
    cells = set()
    for y in range(H(g)):
        for x in range(W(g)):
            if S[y][x] >= k:
                for dy in range(k):
                    for dx in range(k):
                        cells.add((y - dy, x - dx))
    return cells


def _maxwin(g, r, m):
    S = _sq(g, r)
    K = max((v for row in S for v in row), default=0)
    return _windows(g, r, K) if K >= m else set()


def _components(g, r):
    h, w = H(g), W(g)
    seen = set()
    for y in range(h):
        for x in range(w):
            if g[y][x] != r or (y, x) in seen:
                continue
            st, comp = [(y, x)], {(y, x)}
            seen.add((y, x))
            while st:
                a, b = st.pop()
                for dy, dx in N4:
                    n = (a + dy, b + dx)
                    if 0 <= n[0] < h and 0 <= n[1] < w and n not in seen and g[n[0]][n[1]] == r:
                        seen.add(n); comp.add(n); st.append(n)
            yield comp


def _comp_rect(g, r, m, square):
    cells = set()
    for c in _components(g, r):
        ys = [a for a, _ in c]; xs = [b for _, b in c]
        hh, ww = max(ys) - min(ys) + 1, max(xs) - min(xs) + 1
        if len(c) != hh * ww or min(hh, ww) < m or (square and hh != ww):
            continue
        cells |= c
    return cells


def _greedy(g, r, m):
    taken = set()
    for _ in range(H(g) * W(g)):
        S = _sq(g, r, taken)
        K = max((v for row in S for v in row), default=0)
        if K < m:
            break
        y, x = next((y, x) for y in range(H(g)) for x in range(W(g)) if S[y][x] == K)
        for dy in range(K):
            for dx in range(K):
                taken.add((y - dy, x - dx))
    return taken


SELECT = {'win': _windows, 'maxwin': _maxwin, 'greedy': _greedy,
          'compsq': lambda g, r, m: _comp_rect(g, r, m, True),
          'comprect': lambda g, r, m: _comp_rect(g, r, m, False)}


def _maxrects(g, r, minside=1):
    """all maximal-AREA axis rectangles made only of r with both sides >= minside (histogram method); (y0, x0, h, w)."""
    h, w = H(g), W(g)
    hist = [0] * w; best = 0; rects = []
    for y in range(h):
        for x in range(w):
            hist[x] = hist[x] + 1 if g[y][x] == r else 0
        for x0 in range(w):
            mh = 10 ** 9
            for x1 in range(x0, w):
                mh = min(mh, hist[x1])
                if mh == 0: break
                if mh < minside or x1 - x0 + 1 < minside: continue
                a = mh * (x1 - x0 + 1)
                if a > best: best, rects = a, [(y - mh + 1, x0, mh, x1 - x0 + 1)]
                elif a == best: rects.append((y - mh + 1, x0, mh, x1 - x0 + 1))
    return list(dict.fromkeys(rects))


def _cells_rect(y0, x0, hh, ww, shrink):
    return {(y, x) for y in range(y0 + shrink, y0 + hh - shrink) for x in range(x0 + shrink, x0 + ww - shrink)}


def _maxrect2(g, r, shrink):
    rs = _maxrects(g, r, 2)
    if len(rs) != 1: return set()
    return _cells_rect(*rs[0], shrink)


def _maxrect(g, r, shrink):
    rs = _maxrects(g, r)
    if len(rs) != 1: return set()          # the largest patch must be unique
    return _cells_rect(*rs[0], shrink)


def _maxsq(g, r, shrink):
    S = _sq(g, r); K = max((v for row in S for v in row), default=0)
    corners = [(y, x) for y in range(H(g)) for x in range(W(g)) if S[y][x] == K]
    if K < 2 or len(corners) != 1: return set()
    y, x = corners[0]
    return _cells_rect(y - K + 1, x - K + 1, K, K, shrink)


def _maxdiag(g, r, _):
    h, w = H(g), W(g); best, runs = 0, []
    for dy, dx in ((1, 1), (1, -1)):
        for y in range(h):
            for x in range(w):
                if g[y][x] != r: continue
                py, px = y - dy, x - dx
                if 0 <= py < h and 0 <= px < w and g[py][px] == r: continue   # not a run start
                run = []; a, b = y, x
                while 0 <= a < h and 0 <= b < w and g[a][b] == r: run.append((a, b)); a += dy; b += dx
                if len(run) > best: best, runs = len(run), [run]
                elif len(run) == best: runs.append(run)
    if best < 2 or len(runs) != 1: return set()
    return set(runs[0])


SELECT.update({'maxrect2': _maxrect2, 'maxrect': _maxrect, 'maxsq': _maxsq, 'maxdiag': _maxdiag})


def apply(g, rr, p, sel, k):
    r = bg_of(g) if rr == 'bg' else rr
    cells = SELECT[sel](g, r, k)
    if not cells:
        return None
    out = [row[:] for row in g]
    for y, x in cells:
        out[y][x] = p
    return out


def fam_fill_bg_windows(train):
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train):
        return
    cin, cout, per_bg = set(), set(), set()
    for p in train:
        gi, go = p['input'], p['output']
        ch = [(y, x) for y in range(H(gi)) for x in range(W(gi)) if gi[y][x] != go[y][x]]
        if not ch:
            return
        cin |= {gi[y][x] for y, x in ch}; cout |= {go[y][x] for y, x in ch}
        per_bg.add(gi[ch[0][0]][ch[0][1]] == bg_of(gi))
    if len(cin) != 1 or len(cout) != 1:
        return
    r, p = next(iter(cin)), next(iter(cout))
    roles = [r] + (['bg'] if per_bg == {True} and len({bg_of(q['input']) for q in train}) > 1 else [])
    n = 0
    for rr in roles:
        for sel, ks in (('win', (2, 3, 4, 5, 6)), ('maxwin', (2, 3)), ('compsq', (2, 1)), ('comprect', (2,)),
                        ('greedy', (2, 3)), ('maxrect', (0, 1)), ('maxrect2', (0, 1)), ('maxsq', (0, 1)), ('maxdiag', (0,))):
            for k in ks:
                ok = True
                for q in train:
                    o = apply(q['input'], rr, p, sel, k)
                    if o != q['output']:
                        ok = False
                        break
                if ok:
                    n += 1
                    tag = f"{sel}{k}" if sel == 'win' else f"{sel}:shrink{k}" if sel.startswith('max') and sel != 'maxwin' else f"{sel}>={k}"
                    yield (f"fill-bg-windows:{tag}[r{rr},p{p}]", 3,
                           lambda g, a=(rr, p, sel, k): apply(g, *a))
                    if n >= 3:
                        return


FAMILIES = (fam_fill_bg_windows,)
