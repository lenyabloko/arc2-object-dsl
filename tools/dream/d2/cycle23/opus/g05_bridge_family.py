"""Group family g05 'bridges between two objects'.

Concept (civil engineering): BEAM BRIDGE -- a deck spans the free gap between two abutments that face each
other along a row or column (clear line of sight, nothing in between); the deck's width is the part of the two
faces that overlap, set back from each edge of that shared face by a bearing margin.

Mechanism, generally: objects = single-colour 4-connected components on the background (most frequent colour).
Scan every row (horizontal spans) and/or column (vertical spans): each run of background cells lying between two
consecutive object cells belonging to two DIFFERENT objects A,B (optionally: of the same / of different colours)
is a candidate span cell of the abutment pair (A,B).  A candidate cell becomes deck iff the `margin` cells on
both sides of it, perpendicular to the span, are candidate cells of the same pair (erosion of the shared face).
Deck colour: one colour induced from the training outputs, or the abutments' own colour.

Finite parameter domains:
    axes    in {hv, h, v}               which spans are built (rows / columns / both)
    margin  in {0, 1, 2}                bearing set-back from each edge of the shared face
    pairing in {any, same, diff}        which abutment pairs get a bridge (by colour role)
    colour  in {<induced>, pair}        deck colour: the single colour added in training, or the abutments' colour
"""

from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _label(g, bg):
    """single-colour 4-connected components -> label grid (-1 on background) and colour per label"""
    H, W = len(g), len(g[0])
    lab = [[-1] * W for _ in range(H)]
    cols = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or lab[r][c] >= 0:
                continue
            k = len(cols); col = g[r][c]; cols.append(col)
            lab[r][c] = k; st = [(r, c)]
            while st:
                y, x = st.pop()
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < H and 0 <= xx < W and lab[yy][xx] < 0 and g[yy][xx] == col:
                        lab[yy][xx] = k; st.append((yy, xx))
    return lab, cols


def _spans(g, bg, lab, cols, axis, pairing):
    """candidate span cells: {(r,c): (A,B)} for background runs between two consecutive object cells of
    different objects along the axis ('h' = along rows, 'v' = along columns)."""
    H, W = len(g), len(g[0])
    out = {}
    lines = range(H) if axis == 'h' else range(W)
    n = W if axis == 'h' else H
    for i in lines:
        cell = (lambda j: (i, j)) if axis == 'h' else (lambda j: (j, i))
        prev = None
        for j in range(n):
            r, c = cell(j)
            if g[r][c] == bg:
                continue
            if prev is not None and j - prev > 1:
                pr, pc = cell(prev)
                a, b = lab[pr][pc], lab[r][c]
                ok = a != b and (pairing == 'any' or (pairing == 'same') == (cols[a] == cols[b]))
                if ok:
                    for k in range(prev + 1, j):
                        out[cell(k)] = (a, b)
            prev = j
    return out


def _deck(spans, axis, margin):
    """keep span cells whose perpendicular neighbours within `margin` belong to the same abutment pair"""
    keep = {}
    for (r, c), key in spans.items():
        good = True
        for d in range(1, margin + 1):
            for s in (d, -d):
                q = (r + s, c) if axis == 'h' else (r, c + s)
                if spans.get(q) != key:
                    good = False; break
            if not good:
                break
        if good:
            keep[(r, c)] = key
    return keep


def _build(g, axes, margin, pairing, colour):
    bg = _bg(g)
    lab, cols = _label(g, bg)
    out = [row[:] for row in g]
    for axis in axes:
        for (r, c), (a, b) in _deck(_spans(g, bg, lab, cols, axis, pairing), axis, margin).items():
            out[r][c] = cols[a] if colour == 'pair' else colour
    return out


def fam_beam_bridge(train):
    if not train:
        return
    added = set()
    for p in train:
        I, O = p['input'], p['output']
        if len(I) != len(O) or any(len(a) != len(b) for a, b in zip(I, O)):
            return
        bg = _bg(I)
        for a, b in zip(I, O):
            for x, y in zip(a, b):
                if x != y:
                    if x != bg:          # a bridge only ever occupies free (background) cells
                        return
                    added.add(y)
    if not added:
        return
    colours = ([next(iter(added))] if len(added) == 1 else []) + ['pair']
    for margin in (0, 1, 2):
        for pairing in ('any', 'same', 'diff'):
            for axes in ('hv', 'h', 'v'):
                for colour in colours:
                    if colour == 'pair' and pairing == 'diff':
                        continue
                    fn = (lambda g, a=axes, m=margin, pr=pairing, co=colour: _build(g, a, m, pr, co))
                    if all(fn(p['input']) == p['output'] for p in train):
                        yield (f'civil-engineering:beam-bridge[axes={axes},margin={margin},pairing={pairing},'
                               f'colour={"abutment" if colour == "pair" else "induced:" + str(colour)}]', 3, fn)


FAMILIES = (fam_beam_bridge,)
