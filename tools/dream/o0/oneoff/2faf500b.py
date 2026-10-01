CARD = "2faf500b"
READING = "Each shape is crossed by a band of marker cells spanning it fully; the marker cells vanish and the shape splits along the band, each half (taking its half of the band) sliding away from the band by half the band's thickness."


def _count(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return cnt


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = set()
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            st = [(r, c)]
            seen.add((r, c))
            comp = []
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        q = (y + a, x + b)
                        if 0 <= q[0] < H and 0 <= q[1] < W and q not in seen and g[q[0]][q[1]] != bg:
                            seen.add(q)
                            st.append(q)
            out.append(comp)
    return out


def _make(markers, shift_mode):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _count(g)
        bg = max(cnt, key=lambda k: cnt[k])
        out = [[bg] * W for _ in range(H)]
        for comp in _comps(g, bg):
            M = [q for q in comp if g[q[0]][q[1]] in markers]
            body = [q for q in comp if g[q[0]][q[1]] not in markers]
            if not M:
                for (r, c) in body:
                    out[r][c] = g[r][c]
                continue
            sr0, sr1 = min(r for r, _ in comp), max(r for r, _ in comp)
            sc0, sc1 = min(c for _, c in comp), max(c for _, c in comp)
            mr0, mr1 = min(r for r, _ in M), max(r for r, _ in M)
            mc0, mc1 = min(c for _, c in M), max(c for _, c in M)
            full_h = (mr0, mr1) == (sr0, sr1)
            full_w = (mc0, mc1) == (sc0, sc1)
            if full_h and (not full_w or (mc1 - mc0) <= (mr1 - mr0)):
                vert, b0, b1 = True, mc0, mc1      # band of columns: split left/right
            elif full_w:
                vert, b0, b1 = False, mr0, mr1     # band of rows: split top/bottom
            else:
                for (r, c) in body:
                    out[r][c] = g[r][c]
                continue
            t = b1 - b0 + 1
            half = t // 2 if shift_mode == "half" else 1
            if half < 1:
                half = 1
            cut = b0 + (t + 1) // 2  # coordinate < cut -> first side
            for (r, c) in body:
                k = c if vert else r
                d = -half if k < cut else half
                rr, cc = (r, c + d) if vert else (r + d, c)
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr][cc] = g[r][c]
        return out
    return fn


def _markers(train):
    gone = None
    for p in train:
        ci = {v for row in p["input"] for v in row}
        co = {v for row in p["output"] for v in row}
        s = ci - co
        gone = s if gone is None else gone & s
    return frozenset(gone or ())


def fam(train):
    mk = _markers(train)
    if not mk:
        return
    for name, cost, sm in (("band_split_half", 1, "half"), ("band_split_one", 2, "one")):
        fn = _make(mk, sm)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
