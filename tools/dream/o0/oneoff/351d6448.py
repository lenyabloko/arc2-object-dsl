CARD = "351d6448"
READING = ("The input is a sequence of panels separated by full lines; the change between consecutive "
           "panels is one fixed template of cell edits that moves by a constant offset each step, so the "
           "output is the last panel with that edit template applied once more at the next offset.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _panels(g):
    """Split by full uniform rows of one colour; return candidate panel lists, preferred first."""
    H, W = len(g), len(g[0])
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    bg = max(cnt, key=lambda k: (cnt[k], -k))
    seps = [r for r in range(H) if len(set(g[r])) == 1]
    colors = sorted(set(g[r][0] for r in seps), key=lambda c: (c == bg, c))
    cands = []
    for sc in colors:
        rows = [r for r in seps if g[r][0] == sc]
        cuts = [-1] + rows + [H]
        panels = []
        for a, b in zip(cuts, cuts[1:]):
            if b - a - 1 > 0:
                panels.append([list(x) for x in g[a + 1:b]])
        if len(panels) >= 3 and len(set((len(p), len(p[0])) for p in panels)) == 1:
            cands.append(panels)
    return cands


def _diff(a, b):
    d = {}
    for r in range(len(a)):
        for c in range(len(a[0])):
            if a[r][c] != b[r][c]:
                d[(r, c)] = (a[r][c], b[r][c])
    return d


def _filt(tmpl, k, s, P):
    H, W = len(P), len(P[0])
    out = {}
    for (r, c), (f, t) in tmpl.items():
        rr, cc = r + k * s[0], c + k * s[1]
        if 0 <= rr < H and 0 <= cc < W and P[rr][cc] == f:
            out[(rr, cc)] = (f, t)
    return out


def _model(panels, R):
    diffs = [_diff(panels[k], panels[k + 1]) for k in range(len(panels) - 1)]
    if not any(diffs):
        return None
    shifts = sorted([(dy, dx) for dy in range(-R, R + 1) for dx in range(-R, R + 1)],
                    key=lambda s: (abs(s[0]) + abs(s[1]), s))
    best = None
    for s in shifts:
        tmpl = {}
        ok = True
        for k, d in enumerate(diffs):
            for (r, c), v in d.items():
                key = (r - k * s[0], c - k * s[1])
                if key in tmpl and tmpl[key] != v:
                    ok = False
                    break
                tmpl[key] = v
            if not ok:
                break
        if not ok:
            continue
        if all(_filt(tmpl, k, s, panels[k]) == diffs[k] for k in range(len(diffs))):
            # prefer the most compressive template (smallest), then the smallest offset
            if best is None or len(tmpl) < len(best[0]):
                best = (tmpl, s)
    return best


def _predict(g, R):
    for tr in (False, True):
        h = _T(g) if tr else g
        for panels in _panels(h):
            m = _model(panels, R)
            if m is None:
                continue
            tmpl, s = m
            n = len(panels)
            last = [list(r) for r in panels[-1]]
            for (r, c), (f, t) in _filt(tmpl, n - 1, s, last).items():
                last[r][c] = t
            return _T(last) if tr else last
    return None


def fam(train):
    for R in (3,):
        def fn(g, R=R):
            return _predict(g, R)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("moving_edit_template", 3, fn)


FAMILIES = [fam]
