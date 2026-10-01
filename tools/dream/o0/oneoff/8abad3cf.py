CARD = "8abad3cf"
READING = ("Count the cells of each non-background colour and redraw each colour as a solid square of that "
           "area, the squares lined up from smallest to largest, aligned along one edge and separated by "
           "background columns.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _isqrt(n):
    s = int(n ** 0.5)
    while s * s > n:
        s -= 1
    while (s + 1) * (s + 1) <= n:
        s += 1
    return s


def _build(g, desc, bottom, gap):
    cnt = _counts(g)
    bg = max(cnt, key=lambda k: (cnt[k], -k))
    items = [(cnt[k], k) for k in cnt if k != bg]
    if not items:
        return [list(r) for r in g]
    items.sort(reverse=desc)
    sides = []
    for n, k in items:
        s = _isqrt(n)
        if s * s != n:
            s += 1
        sides.append((s, k))
    H = max(s for s, k in sides)
    W = sum(s for s, k in sides) + gap * (len(sides) - 1)
    out = [[bg] * W for _ in range(H)]
    x = 0
    for s, k in sides:
        top = H - s if bottom else 0
        for i in range(top, top + s):
            for j in range(x, x + s):
                out[i][j] = k
        x += s + gap
    return out


def fam(train):
    n = 0
    for gap in (1, 0, 2):
        for desc in (False, True):
            for bottom in (True, False):
                fn = (lambda d, b, gp: (lambda g: _build(g, d, b, gp)))(desc, bottom, gap)
                try:
                    if all(fn(ex['input']) == ex['output'] for ex in train):
                        yield ('area_squares_%s_%s_gap%d' % ('desc' if desc else 'asc',
                                                             'bottom' if bottom else 'top', gap),
                               1 + gap + desc + (not bottom), fn)
                        n += 1
                        if n >= 2:
                            return
                except Exception:
                    continue


FAMILIES = [fam]
