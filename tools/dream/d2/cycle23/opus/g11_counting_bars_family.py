"""Group g11 "counting shown as bars" -- one family: the HISTOGRAM (statistics).

Mechanism: a full-length separator line splits the grid into a data panel (the busier side) and a
blank chart panel.  The colours of the data panel are tallied (frequency per colour); the colours
whose frequency satisfies an induced criterion are plotted as bars in the chart panel, standing on
an induced baseline.

Finite parameter domains (all induced by exact fit on the task's training pairs):
  sel  in {key, max, min}   which tallies are plotted: frequency == size of the key object already
                            drawn in the chart panel (a "scale" bar), the mode, or the rarest colour
  base in {sep, far}        baseline of the bars: the separator line or the opposite edge of the panel
  pos  in {occ, mid}        lateral position: every position along the separator where the colour
                            occurs in the data panel, or the single middle position
  len  in {count, unit}     bar length: the colour's frequency, or one cell
Colours by role: background = most frequent colour over the training inputs; separator = the only
full line of one non-background colour (row or column, so any orientation works).
"""
from collections import Counter
from itertools import product

SELECTORS = ('key', 'max', 'min')
BASES = ('sep', 'far')
POSITIONS = ('occ', 'mid')
LENGTHS = ('count', 'unit')


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _background(train):
    cnt = Counter(v for p in train for r in p['input'] for v in r)
    return cnt.most_common(1)[0][0] if cnt else 0


def _separator(g, bg):
    """The unique full row/column of a single non-background colour -> ('r'|'c', index)."""
    H, W = len(g), len(g[0])
    cands = [('r', r) for r in range(H) if g[r][0] != bg and len(set(g[r])) == 1]
    cands += [('c', c) for c in range(W)
              if g[0][c] != bg and len({g[r][c] for r in range(H)}) == 1]
    return cands[0] if len(cands) == 1 else None


def _histogram(g, bg, sel, base, pos, length):
    if not g or not g[0]:
        return None
    sep = _separator(g, bg)
    if sep is None:
        return None
    axis, s = sep
    work = _transpose(g) if axis == 'c' else [list(r) for r in g]
    H, W = len(work), len(work[0])
    top, bot = list(range(0, s)), list(range(s + 1, H))
    if not top or not bot:
        return None
    ink = lambda rows: sum(1 for r in rows for v in work[r] if v != bg)
    nt, nb = ink(top), ink(bot)
    if nt == nb:
        return None
    data, chart = (top, bot) if nt > nb else (bot, top)
    # chart rows ordered outward from the chosen baseline
    from_sep = sorted(chart, key=lambda r: abs(r - s))
    rows = from_sep if base == 'sep' else from_sep[::-1]

    tally = Counter(work[r][c] for r in data for c in range(W) if work[r][c] != bg)
    if not tally:
        return None
    key = sum(1 for r in chart for v in work[r] if v != bg)
    if sel == 'key':
        chosen = [c for c, n in tally.items() if n == key]
    elif sel == 'max':
        m = max(tally.values()); chosen = [c for c, n in tally.items() if n == m]
    else:
        m = min(tally.values()); chosen = [c for c, n in tally.items() if n == m]

    out = [row[:] for row in work]
    written = {}
    for col in chosen:
        n = tally[col] if length == 'count' else 1
        if n > len(rows):
            return None
        if pos == 'occ':
            xs = sorted({c for r in data for c in range(W) if work[r][c] == col})
        else:
            if W % 2 == 0 or len(chosen) != 1:
                return None
            xs = [W // 2]
        for x in xs:
            for r in rows[:n]:
                if work[r][x] != bg or written.get((r, x), col) != col:
                    return None          # bar would collide with ink or with another bar
                written[(r, x)] = col
                out[r][x] = col
    return _transpose(out) if axis == 'c' else out


def fam_histogram(train):
    if not train:
        return
    bg = _background(train)
    # cheap rejection: every training input needs a separator and the output keeps the size
    for p in train:
        gi, go = p['input'], p['output']
        if len(gi) != len(go) or len(gi[0]) != len(go[0]) or _separator(gi, bg) is None:
            return
    for sel, base, pos, length in product(SELECTORS, BASES, POSITIONS, LENGTHS):
        fn = (lambda g, a=(sel, base, pos, length): _histogram(g, bg, *a))
        if all(fn(p['input']) == p['output'] for p in train):
            yield (f'statistics:histogram[sel={sel},base={base},pos={pos},len={length}]', 3, fn)


FAMILIES = (fam_histogram,)
