CARD = "2b01abd0"
READING = "Reflect the shape across the full-length axis line; the reflection keeps the original colours while the original shape has its two colours swapped."


def _axis(g, bg):
    h, w = len(g), len(g[0])
    for r in range(h):
        if g[r][0] != bg and all(v == g[r][0] for v in g[r]):
            return ('row', r, g[r][0])
    for c in range(w):
        if g[0][c] != bg and all(g[r][c] == g[0][c] for r in range(h)):
            return ('col', c, g[0][c])
    return None


def _make(bg, swap_orig):
    def f(g):
        h, w = len(g), len(g[0])
        ax = _axis(g, bg)
        if ax is None:
            return [list(r) for r in g]
        kind, a, ac = ax
        cells = [(r, c, g[r][c]) for r in range(h) for c in range(w)
                 if g[r][c] not in (bg,) and not ((kind == 'row' and r == a) or (kind == 'col' and c == a))]
        cols = sorted(set(v for _, _, v in cells))
        sw = {}
        if len(cols) == 2:
            sw = {cols[0]: cols[1], cols[1]: cols[0]}
        o = [list(r) for r in g]
        for r, c, v in cells:
            mr, mc = (2 * a - r, c) if kind == 'row' else (r, 2 * a - c)
            vo, vm = (sw.get(v, v), v) if swap_orig else (v, sw.get(v, v))
            o[r][c] = vo
            if 0 <= mr < h and 0 <= mc < w:
                o[mr][mc] = vm
        return o
    return f


def fam(train):
    bg = 0
    for i, (name, so) in enumerate((('mirror_swap_original', True), ('mirror_swap_reflection', False))):
        f = _make(bg, so)
        if all(f(p['input']) == p['output'] for p in train):
            yield (name, i + 1, f)


FAMILIES = [fam]
