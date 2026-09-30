"""g11 'counting shown as bars' -- one mechanism: a HISTOGRAM / bar chart (statistics, graphics).

A full uniform line (the AXIS / separator, colour induced) splits the grid into a DATA side (the side
holding more non-background cells: the sample whose colours are counted) and a CANVAS side (empty, or
holding only a small LEGEND, the key). The output plots, on the canvas, a bar chart of the frequency
table of the data colours: for every selected colour a bar of that colour is drawn.

Induced per task from a small finite domain (nothing hard-coded, colours by role):
  sel    in (key, max, min, all)   which frequency classes are plotted: freq == legend size / mode / least / every colour
  pos    in (source, centre)       bar placed at the columns where the colour occurs, or at the centre column
  length in (count, one)           bar length = the colour's frequency, or one cell (a marker)
  anchor in (near, far)            bars stand on the axis, or on the far edge of the canvas
Axis may be a row or a column, data may lie on either side (handled by normalising the frame).
"""
from collections import Counter

_SEL = ('key', 'max', 'min', 'all')
_POS = ('source', 'centre')
_LEN = ('count', 'one')
_ANC = ('near', 'far')


def _T(g):
    return [list(r) for r in zip(*g)]


def _flipv(g):
    return [list(r) for r in g[::-1]]


def _bg_of(train):
    c = Counter()
    for p in train:
        for r in p['input']:
            c.update(r)
    return c.most_common(1)[0][0]


def _full_lines(g, orient, bg):
    """indices and colours of full uniform non-bg lines in g (orient 'row' or 'col')."""
    h = g if orient == 'row' else _T(g)
    return [(i, r[0]) for i, r in enumerate(h) if r[0] != bg and all(v == r[0] for v in r)]


def _induce_axis(train, bg):
    """(orient, colour) pairs such that every training input has exactly one full line of that colour."""
    out = []
    for orient in ('row', 'col'):
        sets = []
        for p in train:
            cnt = Counter(c for _, c in _full_lines(p['input'], orient, bg))
            sets.append({c for c, n in cnt.items() if n == 1})
        common = set.intersection(*sets) if sets else set()
        for c in sorted(common):
            out.append((orient, c))
    return out


def _normalise(g, orient, sep_colour, bg):
    """Return (grid, undo) with the axis as a row and the data side BELOW it, or None."""
    lines = [i for i, c in _full_lines(g, orient, bg) if c == sep_colour]
    if len(lines) != 1:
        return None
    h = _T(g) if orient == 'col' else [list(r) for r in g]
    r = lines[0]
    above = sum(1 for i in range(r) for v in h[i] if v != bg)
    below = sum(1 for i in range(r + 1, len(h)) for v in h[i] if v != bg)
    if above == below:
        return None
    flipped = above > below
    if flipped:
        h = _flipv(h)
        r = len(h) - 1 - r

    def undo(x):
        if flipped:
            x = _flipv(x)
        return _T(x) if orient == 'col' else x
    return h, r, undo


def _render(h, r, bg, sel, pos, length, anchor):
    """h: normalised grid (axis row r, canvas rows 0..r-1, data rows r+1..). Returns new grid."""
    H, W = len(h), len(h[0])
    freq = Counter(v for i in range(r + 1, H) for v in h[i] if v != bg)
    if not freq:
        return None
    key = sum(1 for i in range(r) for v in h[i] if v != bg)
    if sel == 'key':
        if key == 0:
            return None
        chosen = [c for c, n in freq.items() if n == key]
    elif sel == 'max':
        m = max(freq.values()); chosen = [c for c, n in freq.items() if n == m]
    elif sel == 'min':
        m = min(freq.values()); chosen = [c for c, n in freq.items() if n == m]
    else:
        chosen = list(freq)
    out = [list(row) for row in h]
    for c in chosen:
        if pos == 'source':
            cols = sorted({j for i in range(r + 1, H) for j in range(W) if h[i][j] == c})
        else:
            cols = sorted({(W - 1) // 2, W // 2})
        L = freq[c] if length == 'count' else 1
        L = min(L, r)
        rows = range(r - L, r) if anchor == 'near' else range(0, L)
        for i in rows:
            for j in cols:
                if out[i][j] == bg:
                    out[i][j] = c
    return out


def fam_histogram(train):
    if not train or any(len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0])
                        for p in train):
        return
    bg = _bg_of(train)
    for orient, sep in _induce_axis(train, bg):
        # quick shape check: normalisation must succeed on every pair
        if any(_normalise(p['input'], orient, sep, bg) is None for p in train):
            continue
        for sel in _SEL:
            for pos in _POS:
                for length in _LEN:
                    for anchor in _ANC:
                        def fn(g, orient=orient, sep=sep, bg=bg, sel=sel, pos=pos, length=length, anchor=anchor):
                            nz = _normalise(g, orient, sep, bg)
                            if nz is None:
                                return None
                            h, r, undo = nz
                            res = _render(h, r, bg, sel, pos, length, anchor)
                            return None if res is None else undo(res)
                        if all(fn(p['input']) == p['output'] for p in train):
                            yield (f"graphics:histogram[axis={orient}/{sep},sel={sel},pos={pos},len={length},anchor={anchor}]", 3, fn)


FAMILIES = (fam_histogram,)
