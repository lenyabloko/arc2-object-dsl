"""Family for 291dc1e1 -- typography: WRITING MODE (text direction / reading order).

The input is a page of "text": a corner cell marks where reading starts (the origin), and the two
ruler lines along the page edges declare the writing mode.  Glyphs (solid multi-coloured blocks) sit
on lines (bands of constant thickness separated by background).  The page may be written in any
writing mode: horizontal-tb (Latin), horizontal right-to-left (Arabic/Hebrew), vertical-rl
(CJK: columns right-to-left, top-to-bottom), vertical-lr (Mongolian), ...  The output re-sets the
text in the canonical mode: glyphs in reading order, one glyph per line, lines stacked top-to-bottom,
each glyph aligned (centred) in a column as wide as the widest glyph.  Glyph orientation follows the
CSS writing-mode convention: glyphs in horizontal modes are upright; glyphs in vertical modes are set
sideways, so they are turned back by the rotation that maps the inline direction onto 'rightwards'.

Parameters (small finite declared domains, induced from train):
  inline  : how the inline (along-line) axis is read from the page:
            ('marker', c) -> the ruler line of colour c runs parallel to the lines of text
                             (c ranges over ruler colours seen in training),
            ('structure',) -> the axis whose lines split into solid glyphs (no blank cross-section).
  glyphs  : 'typographic' (CSS: horizontal upright, vertical sideways) | 'rotational' (always the
            proper rotation mapping inline direction to rightwards).
  align   : 'center' | 'start' | 'end'   (odd slack in 'center' goes to the end side).
Background = most frequent colour of the page body; padding uses it.  No coordinates, sizes, counts or
colour numbers are hard-coded.
"""
from collections import Counter


def _header(g):
    """Find the unique grid corner whose edge row and edge column are uniform ruler lines of colours
    different from the corner cell.  Returns (r0, c0, row_line_colour, col_line_colour) or None."""
    H, W = len(g), len(g[0])
    if H < 3 or W < 3:
        return None
    found = []
    for r0 in sorted({0, H - 1}):
        for c0 in sorted({0, W - 1}):
            row = {g[r0][c] for c in range(W) if c != c0}
            col = {g[r][c0] for r in range(H) if r != r0}
            if len(row) == 1 and len(col) == 1:
                a, b, k = row.pop(), col.pop(), g[r0][c0]
                if k != a and k != b:
                    found.append((r0, c0, a, b))
    return found[0] if len(found) == 1 else None


def _page(g):
    """Return (r0, c0, row_colour, col_colour, dr, dc, bg) for a page with a header, else None."""
    h = _header(g)
    if h is None:
        return None
    r0, c0, a, b = h
    H, W = len(g), len(g[0])
    dr = 1 if r0 == 0 else -1          # direction away from the header row
    dc = 1 if c0 == 0 else -1          # direction away from the header column
    body = [g[r][c] for r in range(H) if r != r0 for c in range(W) if c != c0]
    bg = Counter(body).most_common(1)[0][0]
    if bg in (a, b, g[r0][c0]):
        return None
    return r0, c0, a, b, dr, dc, bg


def _canonical(g, pg, axis):
    """Resample the page body so that inline -> rightwards and block -> downwards."""
    r0, c0, a, b, dr, dc, bg = pg
    H, W = len(g), len(g[0])
    if axis == 'h':
        d_in, d_bl, n_bl, n_in = (0, dc), (dr, 0), H - 1, W - 1
    else:
        d_in, d_bl, n_bl, n_in = (dr, 0), (0, dc), W - 1, H - 1
    orr, occ = r0 + dr, c0 + dc
    C = [[g[orr + i * d_bl[0] + j * d_in[0]][occ + i * d_bl[1] + j * d_in[1]] for j in range(n_in)]
         for i in range(n_bl)]
    return C, d_in, d_bl


def _runs(flags):
    out, s = [], None
    for i, f in enumerate(flags + [False]):
        if f and s is None:
            s = i
        elif not f and s is not None:
            out.append((s, i)); s = None
    return out


def _glyphs(C, bg):
    """Lines = runs of non-blank rows; glyphs = runs of non-blank columns within a line."""
    res = []
    for a, b in _runs([any(v != bg for v in row) for row in C]):
        cols = [any(C[i][j] != bg for i in range(a, b)) for j in range(len(C[0]))]
        for s, e in _runs(cols):
            res.append([C[i][s:e] for i in range(a, b)])
    return res


def _solid(glyph, bg):
    return all(any(v != bg for v in row) for row in glyph)


def _structural_axis(g, pg):
    ok = []
    for axis in ('h', 'v'):
        C, _, _ = _canonical(g, pg, axis)
        gl = _glyphs(C, pg[6])
        if gl and all(_solid(x, pg[6]) for x in gl):
            ok.append(axis)
    return ok[0] if len(ok) == 1 else None


def _make(inline, glyph_rule, align):
    def fn(g):
        pg = _page(g)
        if pg is None:
            return None
        r0, c0, a, b, dr, dc, bg = pg
        axis = None
        if inline[0] == 'marker':
            c = inline[1]
            if a == c and b != c:
                axis = 'h'                       # horizontal ruler parallel to lines
            elif b == c and a != c:
                axis = 'v'
        if axis is None:
            axis = _structural_axis(g, pg)
        if axis is None:
            return None
        C, d_in, d_bl = _canonical(g, pg, axis)
        out_glyphs = []
        for gl in _glyphs(C, bg):
            if glyph_rule == 'typographic' and axis == 'h':
                # upright: restore original page orientation
                if dr == -1:
                    gl = gl[::-1]
                if dc == -1:
                    gl = [row[::-1] for row in gl]
            else:
                # proper rotation mapping the inline direction onto 'rightwards'
                u = (d_in[1], -d_in[0])
                if u != d_bl:
                    gl = gl[::-1]
            out_glyphs.append(gl)
        if not out_glyphs:
            return None
        width = max(len(x[0]) for x in out_glyphs)
        out = []
        for gl in out_glyphs:
            slack = width - len(gl[0])
            left = {'center': slack // 2, 'start': 0, 'end': slack}[align]
            for row in gl:
                out.append([bg] * left + list(row) + [bg] * (slack - left))
        return out
    return fn


def fam_writing_mode(train):
    pages = [_page(p["input"]) for p in train]
    if any(pg is None for pg in pages):
        return
    ruler_colours = sorted({pg[2] for pg in pages} | {pg[3] for pg in pages})
    inline_dom = [('marker', c) for c in ruler_colours] + [('structure',)]
    for inline in inline_dom:
        for glyph_rule in ('typographic', 'rotational'):
            for align in ('center', 'start', 'end'):
                fn = _make(inline, glyph_rule, align)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    iname = 'marker=%d' % inline[1] if inline[0] == 'marker' else 'structure'
                    yield ("typography:writing_mode[inline=%s,glyphs=%s,align=%s]"
                           % (iname, glyph_rule, align), 3, fn)
                    return


FAMILIES = (fam_writing_mode,)
