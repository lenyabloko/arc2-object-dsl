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
A program is kept only if it reproduces every training output exactly.
"""
import sys
sys.path.insert(0, '/home/claude/work/widen')
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
                        ('greedy', (2, 3))):
            for k in ks:
                ok = True
                for q in train:
                    o = apply(q['input'], rr, p, sel, k)
                    if o != q['output']:
                        ok = False
                        break
                if ok:
                    n += 1
                    yield (f"fill-bg-windows:{sel}{'' if sel == 'win' else '>='}{k}[r{rr},p{p}]", 3,
                           lambda g, a=(rr, p, sel, k): apply(g, *a))
                    if n >= 3:
                        return


FAMILIES = (fam_fill_bg_windows,)
