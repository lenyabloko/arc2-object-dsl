CARD = "15113be4"
READING = ("The big framed region holds a scaled-up copy of a cell-sized pattern in a special colour; "
           "every grid cell whose marks cover that pattern has those pattern positions recoloured to the special colour.")

from collections import Counter


def _full_lines(g):
    h, w = len(g), len(g[0])
    rows = {}
    for r in range(h):
        if g[r][0] != 0 and all(v == g[r][0] for v in g[r]):
            rows[r] = g[r][0]
    cols = {}
    for c in range(w):
        col = [g[r][c] for r in range(h)]
        if col[0] != 0 and all(v == col[0] for v in col):
            cols[c] = col[0]
    return rows, cols


def _axis(idx, n):
    idx = sorted(idx)
    if len(idx) < 2:
        return None
    gaps = [b - a for a, b in zip(idx, idx[1:])]
    p = min(gaps)
    if p < 2:
        return None
    off = idx[0] % p
    return p, off


def _analyse(g):
    h, w = len(g), len(g[0])
    rows, cols = _full_lines(g)
    lc = Counter(list(rows.values()) + list(cols.values()))
    if not lc:
        return None
    L = lc.most_common(1)[0][0]
    ra = _axis([r for r, v in rows.items() if v == L], h)
    ca = _axis([c for c, v in cols.items() if v == L], w)
    if ra is None and ca is None:
        return None
    if ra is None:
        ra = ca
    if ca is None:
        ca = ra
    cnt = Counter(v for row in g for v in row if v not in (0, L))
    if len(cnt) < 2:
        return None
    m = cnt.most_common(1)[0][0]
    specials = [c for c in cnt if c != m]
    if len(specials) != 1:
        return None
    sc = specials[0]
    pts = [(r, c) for r in range(h) for c in range(w) if g[r][c] == sc]
    r0 = min(p[0] for p in pts); r1 = max(p[0] for p in pts)
    c0 = min(p[1] for p in pts); c1 = max(p[1] for p in pts)
    # extend to region bounded by L
    while r0 - 1 >= 0 and not all(g[r0 - 1][c] == L for c in range(c0, c1 + 1)):
        r0 -= 1
    while r1 + 1 < h and not all(g[r1 + 1][c] == L for c in range(c0, c1 + 1)):
        r1 += 1
    while c0 - 1 >= 0 and not all(g[r][c0 - 1] == L for r in range(r0, r1 + 1)):
        c0 -= 1
    while c1 + 1 < w and not all(g[r][c1 + 1] == L for r in range(r0, r1 + 1)):
        c1 += 1
    kr = ra[0] - 1
    kc = ca[0] - 1
    H, W = r1 - r0 + 1, c1 - c0 + 1
    if H % kr or W % kc:
        return None
    sr, scl = H // kr, W // kc
    P = [[any(g[r0 + i * sr + a][c0 + j * scl + b] == sc for a in range(sr) for b in range(scl))
          for j in range(kc)] for i in range(kr)]
    return dict(L=L, ra=ra, ca=ca, m=m, sc=sc, box=(r0, r1, c0, c1), P=P, kr=kr, kc=kc)


def _make(mode):
    def fn(g):
        A = _analyse(g)
        out = [row[:] for row in g]
        if A is None:
            return out
        h, w = len(g), len(g[0])
        (pr, offr), (pc, offc) = A['ra'], A['ca']
        kr, kc, P, m, sc = A['kr'], A['kc'], A['P'], A['m'], A['sc']
        r0b, r1b, c0b, c1b = A['box']
        starts_r = [r for r in range(h) if (r - offr) % pr == 1 and r + kr <= h]
        starts_c = [c for c in range(w) if (c - offc) % pc == 1 and c + kc <= w]
        if offr == 0 or True:
            # also allow a cell block starting at 0 if separator is not at 0
            if 0 not in starts_r and (0 - offr) % pr != 0 and kr <= h:
                if all((r - offr) % pr != 0 for r in range(0, kr)):
                    starts_r = [0] + starts_r
            if 0 not in starts_c and (0 - offc) % pc != 0 and kc <= w:
                if all((c - offc) % pc != 0 for c in range(0, kc)):
                    starts_c = [0] + starts_c
        for r in starts_r:
            for c in starts_c:
                if not (r + kr - 1 < r0b or r > r1b or c + kc - 1 < c0b or c > c1b):
                    continue
                cell = [[g[r + i][c + j] for j in range(kc)] for i in range(kr)]
                if any(v == sc or v == A['L'] for row in cell for v in row):
                    continue
                if mode == 'superset':
                    ok = all(cell[i][j] == m for i in range(kr) for j in range(kc) if P[i][j])
                else:
                    ok = all((cell[i][j] == m) == bool(P[i][j]) for i in range(kr) for j in range(kc))
                if ok and any(P[i][j] for i in range(kr) for j in range(kc)):
                    for i in range(kr):
                        for j in range(kc):
                            if P[i][j]:
                                out[r + i][c + j] = sc
        return out
    return fn


def fam(train):
    for name, cost, mode in (("cover_pattern_superset", 1, 'superset'), ("cover_pattern_exact", 2, 'exact')):
        fn = _make(mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
