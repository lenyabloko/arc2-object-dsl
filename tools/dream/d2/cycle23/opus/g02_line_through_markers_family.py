"""Family: geometry:Voronoi -- lines through markers + nearest-line (Voronoi) partition of the canvas.

Mechanism: every non-background marker is extended to a full line along one direction d.  Every canvas
cell is assigned to its nearest marker line, measured perpendicular to d (a 1-D Voronoi partition; ties
broken toward a fixed side).  A render mask is then painted in the owning marker's colour:
  lines  -> only the lines through the markers
  frame  -> the lines plus the canvas border (each border cell takes its Voronoi owner's colour)
  fill   -> the whole Voronoi cell (bands)
All parameters come from small finite domains and are induced from the task's training pairs:
  dir    in {row, col, diag, anti}   (line direction: horizontal, vertical, main diagonal, anti-diagonal)
  tie    in {low, high}              (equidistant cell goes to the line with the lower / higher key)
  render in {lines, frame, fill}
Background = most frequent colour of the input grid (by role, computed per grid).
"""
from collections import Counter

# key(r, c): cells on the same line share a key; |key difference| is the perpendicular distance (up to scale)
_DIRS = (
    ('row', lambda r, c: r),
    ('col', lambda r, c: c),
    ('diag', lambda r, c: r - c),
    ('anti', lambda r, c: r + c),
)
_TIES = ('low', 'high')
_RENDERS = ('lines', 'frame', 'fill')


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _line_colours(g, key):
    """Map line-key -> colour of the marker(s) on that line; None if a line holds two different colours."""
    bg = _bg(g)
    lines = {}
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != bg:
                k = key(r, c)
                if lines.setdefault(k, v) != v:
                    return None
    return lines


def _paint(g, key, tie, render):
    lines = _line_colours(g, key)
    if lines is None:
        raise ValueError('ambiguous line colours')
    out = [list(row) for row in g]
    if not lines:
        return out
    keys = sorted(lines)
    H, W = len(g), len(g[0])
    for r in range(H):
        border = r == 0 or r == H - 1
        for c in range(W):
            k = key(r, c)
            on_line = k in lines
            if render == 'lines' and not on_line:
                continue
            if render == 'frame' and not (on_line or border or c == 0 or c == W - 1):
                continue
            if on_line:
                out[r][c] = lines[k]
                continue
            # nearest line key; ties to the lower or higher key
            best, bd = None, None
            for kk in keys:
                d = abs(kk - k)
                if bd is None or d < bd or (d == bd and tie == 'high'):
                    best, bd = kk, d
            out[r][c] = lines[best]
    return out


def fam_voronoi(train):
    # quick structural rejection: same shape in/out, output only adds/repaints, some markers exist
    for p in train:
        I, O = p['input'], p['output']
        if len(I) != len(O) or any(len(a) != len(b) for a, b in zip(I, O)):
            return
    if all(p['input'] == p['output'] for p in train):
        return  # identity task: nothing is drawn, not this mechanism
    for dname, key in _DIRS:
        if any(_line_colours(p['input'], key) is None for p in train):
            continue
        for render in _RENDERS:
            ties = ('low',) if render == 'lines' else _TIES
            for tie in ties:
                def fn(g, key=key, tie=tie, render=render):
                    return _paint(g, key, tie, render)
                try:
                    ok = all(fn(p['input']) == p['output'] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ('geometry:voronoi[dir=%s,tie=%s,render=%s]' % (dname, tie, render), 3, fn)
                    return


FAMILIES = (fam_voronoi,)
