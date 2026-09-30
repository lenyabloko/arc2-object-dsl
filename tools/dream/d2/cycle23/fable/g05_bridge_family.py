"""g05_bridge family -- concept: LINTEL / bridge deck (architecture, civil engineering).

Mechanism (one, applied to every facing pair of objects):
  Two objects ("piers") face each other along a row axis or a column axis when their extents perpendicular to that
  axis overlap and the corridor between their facing sides (over the whole overlap) is pure background.  A deck is
  laid across the corridor, from one pier face to the other.  The deck's cross-section is the overlap of the two
  piers' perpendicular extents, inset by `inset` cells on each side (a lintel sits inside the bearing, narrower than
  the piers).  Only nearest neighbours get a deck (any object inside the corridor blocks it).

Parameters, all induced per task from its training pairs, from finite declared domains:
  same_only : {True, False}       -- only same-coloured piers are spanned / any two piers are spanned
  inset     : {1, 0}              -- deck narrower than the common extent by `inset` on each side / full width
  colour    : 'const' (one deck colour read off the training outputs) or 'pier' (the piers' own colour)
No coordinates, sizes, counts or colour numbers are hard-coded; background = most common colour of the grid;
objects = 4-connected same-colour components.

Fits d6ad076f (same_only=False, inset=1, const colour) and f3b10344 (same_only=True, inset=1, const colour).
Does NOT fit af726779: there the new cell is displaced two rows away from the pair, only pairs with a single-cell
gap produce it, and the rule is iterated with alternating colours -- an elementary 1-D cellular automaton
(Wolfram rule 32 on a row stride of 2, i.e. brick-bond corbelling), a different mechanism.
"""
from collections import Counter, deque

SAME_ONLY_DOMAIN = (True, False)
INSET_DOMAIN = (1, 0)
COLOUR_DOMAIN = ('pier', 'const')   # role-based colour preferred over a constant when both fit


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    """4-connected same-colour components as (colour, r1, r2, c1, c2) bounding boxes."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            col = g[r][c]
            seen[r][c] = True
            q = deque([(r, c)])
            r1 = r2 = r
            c1 = c2 = c
            while q:
                y, x = q.popleft()
                if y < r1: r1 = y
                if y > r2: r2 = y
                if x < c1: c1 = x
                if x > c2: c2 = x
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                        seen[ny][nx] = True
                        q.append((ny, nx))
            comps.append((col, r1, r2, c1, c2))
    return comps


def _decks(g, same_only, inset):
    """Yield (cells, pier_colour_or_None) for every facing pair of piers with a clear corridor."""
    bg = _bg(g)
    comps = _components(g, bg)
    n = len(comps)
    for i in range(n):
        a = comps[i]
        for j in range(n):
            if i == j:
                continue
            b = comps[j]
            if same_only and a[0] != b[0]:
                continue
            pier_col = a[0] if a[0] == b[0] else None
            # a strictly left of b, rows overlap -> horizontal deck
            if a[4] < b[3]:
                lo, hi = max(a[1], b[1]), min(a[2], b[2])
                if lo <= hi:
                    g1, g2 = a[4] + 1, b[3] - 1
                    if g1 <= g2 and all(g[r][c] == bg for r in range(lo, hi + 1) for c in range(g1, g2 + 1)):
                        if lo + inset <= hi - inset:
                            yield ([(r, c) for r in range(lo + inset, hi - inset + 1) for c in range(g1, g2 + 1)],
                                   pier_col)
            # a strictly above b, columns overlap -> vertical deck
            if a[2] < b[1]:
                lo, hi = max(a[3], b[3]), min(a[4], b[4])
                if lo <= hi:
                    g1, g2 = a[2] + 1, b[1] - 1
                    if g1 <= g2 and all(g[r][c] == bg for r in range(g1, g2 + 1) for c in range(lo, hi + 1)):
                        if lo + inset <= hi - inset:
                            yield ([(r, c) for r in range(g1, g2 + 1) for c in range(lo + inset, hi - inset + 1)],
                                   pier_col)


def _make_fn(same_only, inset, colour_mode, const_col):
    def fn(g):
        out = [list(row) for row in g]
        for cells, pier_col in _decks(g, same_only, inset):
            col = const_col if colour_mode == 'const' else pier_col
            if col is None:
                continue
            for r, c in cells:
                out[r][c] = col
        return out
    return fn


def fam_lintel(train):
    # quick shape / additive pre-check: outputs only add cells on background, never remove or recolour objects
    new_cols = set()
    changed_any = False
    for p in train:
        a, b = p['input'], p['output']
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            return
        bg = _bg(a)
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y:
                    if x != bg:
                        return
                    new_cols.add(y)
                    changed_any = True
    if not changed_any:
        return
    const_col = next(iter(new_cols)) if len(new_cols) == 1 else None

    for same_only in SAME_ONLY_DOMAIN:
        for inset in INSET_DOMAIN:
            for colour_mode in COLOUR_DOMAIN:
                if colour_mode == 'const' and const_col is None:
                    continue
                if colour_mode == 'pier' and not same_only:
                    continue  # 'pier' colour only makes sense for same-coloured piers
                fn = _make_fn(same_only, inset, colour_mode, const_col)
                if all(fn(p['input']) == p['output'] for p in train):
                    tag = 'const%d' % const_col if colour_mode == 'const' else 'pier'
                    yield ('architecture:lintel[piers=%s,inset=%d,colour=%s]'
                           % ('same-colour' if same_only else 'any-colour', inset, tag), 3, fn)
                    return


FAMILIES = (fam_lintel,)
