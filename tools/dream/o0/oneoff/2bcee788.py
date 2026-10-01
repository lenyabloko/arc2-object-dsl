CARD = "2bcee788"
READING = "The marker-coloured cells adjacent to the shape mark a mirror line: reflect the shape across the edge between it and the marker (marker replaced), and repaint the background with the new colour."


def _learn(train, bg):
    vanish, newbg = set(), set()
    for p in train:
        ci = set(v for r in p['input'] for v in r) - {bg}
        co = set(v for r in p['output'] for v in r)
        vanish |= ci - co
        for ri, ro in zip(p['input'], p['output']):
            for a, b in zip(ri, ro):
                if a == bg:
                    newbg.add(b) if b not in ci else None
    return vanish, newbg


def _make(bg, nb, marker_pref):
    D = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    def f(g):
        h, w = len(g), len(g[0])
        cnt = {}
        for r in g:
            for v in r:
                if v != bg:
                    cnt[v] = cnt.get(v, 0) + 1
        if len(cnt) < 2:
            return [[nb if v == bg else v for v in r] for r in g]
        present = [m for m in marker_pref if m in cnt]
        mk = present[0] if present else min(cnt, key=lambda k: (cnt[k], k))
        mcells = [(r, c) for r in range(h) for c in range(w) if g[r][c] == mk]
        scells = [(r, c, g[r][c]) for r in range(h) for c in range(w) if g[r][c] not in (bg, mk)]
        sset = set((r, c) for r, c, _ in scells)
        dd = None
        for dr, dc in D:
            if all((r + dr, c + dc) in sset for r, c in mcells):
                dd = (dr, dc); break
        if dd is None:
            for dr, dc in D:
                if any((r + dr, c + dc) in sset for r, c in mcells):
                    dd = (dr, dc); break
        o = [[nb if v in (bg, mk) else v for v in r] for r in g]
        if dd is None:
            return o
        dr, dc = dd
        if dr:
            m = mcells[0][0]
            for r, c, v in scells:
                rr = 2 * m + dr - r
                if 0 <= rr < h:
                    o[rr][c] = v
        else:
            m = mcells[0][1]
            for r, c, v in scells:
                cc = 2 * m + dc - c
                if 0 <= cc < w:
                    o[r][cc] = v
        return o
    return f


def fam(train):
    bg = 0
    vanish, newbg = _learn(train, bg)
    nbs = sorted(newbg) if len(newbg) == 1 else []
    if not nbs:
        return
    nb = nbs[0]
    seen = set()
    for name, pref in (('mirror_at_marker_learned', sorted(vanish)), ('mirror_at_marker_minority', [])):
        f = _make(bg, nb, pref)
        if all(f(p['input']) == p['output'] for p in train):
            yield (name, len(seen) + 1, f)
            seen.add(name)


FAMILIES = [fam]
