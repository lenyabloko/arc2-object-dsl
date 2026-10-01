CARD = "2ccd9fef"
READING = "The grid is a strip of equal panels showing a sequence plus a blank template panel; the output is the next panel, where every changing shape keeps changing by the same step (each run's two ends move linearly along the motion axis, else the changed cells are copied forward by the bounding-box edge shift)."


def _split(g):
    """Return (panels, axis) for the best equal split into >=2 panels."""
    H, W = len(g), len(g[0])
    best = None
    for axis in (0, 1):
        n = H if axis == 0 else W
        for k in range(2, n + 1):
            if n % k:
                continue
            s = n // k
            if axis == 0:
                ps = [[row[:] for row in g[i * s:(i + 1) * s]] for i in range(k)]
            else:
                ps = [[row[i * s:(i + 1) * s] for row in g] for i in range(k)]
            if len(ps[0]) < 2 or len(ps[0][0]) < 2:
                continue
            # agreement of every panel with the template candidates (first and last)
            tot = agree = 0
            for t in (ps[0], ps[-1]):
                for p in ps:
                    for r in range(len(p)):
                        for c in range(len(p[0])):
                            tot += 1
                            agree += p[r][c] == t[r][c]
            sc = agree / tot
            key = (sc, -k)
            if best is None or key > best[0]:
                best = (key, ps, axis)
    return best[1], best[2]


def _palette(p, tmpl):
    return sorted({p[r][c] for r in range(len(p)) for c in range(len(p[0])) if p[r][c] != tmpl[r][c]})


def _comps(cells, conn8=True):
    cells = set(cells)
    seen, out = set(), []
    for s in sorted(cells):
        if s in seen:
            continue
        st, comp = [s], []
        seen.add(s)
        while st:
            r, c = st.pop()
            comp.append((r, c))
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (dr or dc) and (conn8 or not (dr and dc)):
                        q = (r + dr, c + dc)
                        if q in cells and q not in seen:
                            seen.add(q)
                            st.append(q)
        out.append(comp)
    return out


def _bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


def _step(pa, pb, tmpl):
    """Extrapolate one step: pa -> pb -> result."""
    h, w = len(pb), len(pb[0])
    out = [row[:] for row in pb]
    nt = set()
    for r in range(h):
        for c in range(w):
            if pa[r][c] != tmpl[r][c] or pb[r][c] != tmpl[r][c]:
                nt.add((r, c))
    for obj in _comps(nt):
        objs = set(obj)
        ca = [q for q in obj if pa[q[0]][q[1]] != tmpl[q[0]][q[1]]]
        cb = [q for q in obj if pb[q[0]][q[1]] != tmpl[q[0]][q[1]]]
        ch = [q for q in obj if pa[q[0]][q[1]] != pb[q[0]][q[1]]]
        if not ch or not ca or not cb:
            continue
        a0, a1, a2, a3 = _bbox(ca)
        b0, b1, b2, b3 = _bbox(cb)
        dr = (b0 - a0) if b0 != a0 else (b1 - a1)
        dc = (b2 - a2) if b2 != a2 else (b3 - a3)
        if dr == 0 and dc == 0:
            continue
        for (r, c) in sorted(ch):
            rr, cc = r + dr, c + dc
            if 0 <= rr < h and 0 <= cc < w:
                out[rr][cc] = pb[r][c]
    return out


def _runs(pos):
    pos = sorted(pos)
    out = []
    for p in pos:
        if out and p == out[-1][1] + 1:
            out[-1][1] = p
        else:
            out.append([p, p])
    return out


def _step_runs(pa, pb, tmpl):
    """Per colour, per line along its motion axis: extrapolate the single run's two ends linearly.
    Returns None when some line has more than one run (or appears/vanishes)."""
    h, w = len(pb), len(pb[0])
    cols = set()
    for r in range(h):
        for c in range(w):
            for p in (pa, pb):
                if p[r][c] != tmpl[r][c]:
                    cols.add(p[r][c])
    paint = []
    clear = []
    for col in sorted(cols):
        A = [(r, c) for r in range(h) for c in range(w) if pa[r][c] == col and pa[r][c] != tmpl[r][c]]
        B = [(r, c) for r in range(h) for c in range(w) if pb[r][c] == col and pb[r][c] != tmpl[r][c]]
        if not A or not B:
            return None
        a0, a1, a2, a3 = _bbox(A)
        b0, b1, b2, b3 = _bbox(B)
        if (a0, a1) != (b0, b1):
            vert = True
        elif (a2, a3) != (b2, b3):
            vert = False
        else:
            if set(A) != set(B):
                return None
            continue
        clear.extend(B)
        la, lb = {}, {}
        for (r, c) in A:
            la.setdefault(c if vert else r, []).append(r if vert else c)
        for (r, c) in B:
            lb.setdefault(c if vert else r, []).append(r if vert else c)
        if set(la) != set(lb):
            return None
        for line in la:
            ra, rb = _runs(la[line]), _runs(lb[line])
            if len(ra) != 1 or len(rb) != 1:
                return None
            s0 = 2 * rb[0][0] - ra[0][0]
            s1 = 2 * rb[0][1] - ra[0][1]
            if s1 < s0:
                return None
            for q in range(s0, s1 + 1):
                rr, cc = (q, line) if vert else (line, q)
                if 0 <= rr < h and 0 <= cc < w:
                    paint.append((rr, cc, col))
    out = [row[:] for row in pb]
    for (r, c) in clear:
        out[r][c] = tmpl[r][c]
    for (r, c, col) in paint:
        out[r][c] = col
    return out


def _make(tmpl_last):
    def fn(g):
        ps, _ = _split(g)
        if not tmpl_last:
            ps = ps[::-1]
        tmpl, seq = ps[-1], ps[:-1]
        n = len(seq)
        if n == 1:
            return [row[:] for row in seq[0]]
        # lag: smallest L whose phase-matched panels share a palette
        lag = 1
        for L in range(1, n // 2 + 1):
            if n - 2 * L < 0:
                break
            if _palette(seq[n - L], tmpl) == _palette(seq[n - 2 * L], tmpl):
                lag = L
                break
        pa, pb = seq[n - 2 * lag], seq[n - lag]
        o = _step_runs(pa, pb, tmpl)
        return o if o is not None else _step(pa, pb, tmpl)
    return fn


def fam(train):
    for name, cost, tl in (("seq_next_tmpl_last", 1, True), ("seq_next_tmpl_first", 2, False)):
        fn = _make(tl)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
