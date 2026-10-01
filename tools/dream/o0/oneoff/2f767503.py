CARD = "2f767503"
READING = "The single odd-coloured cell sits beside a wall bar; a beam shoots from it through the wall and on to the grid edge, and every scattered-colour component the beam touches is erased to background."


def _count(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return cnt


def _make(conn8):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _count(g)
        bg = max(cnt, key=lambda k: cnt[k])
        singles = [k for k in cnt if cnt[k] == 1 and k != bg]
        out = [row[:] for row in g]
        if len(singles) != 1:
            return out
        em = singles[0]
        er, ec = [(r, c) for r in range(H) for c in range(W) if g[r][c] == em][0]
        dirs = []
        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            r, c = er + dr, ec + dc
            if 0 <= r < H and 0 <= c < W and g[r][c] != bg:
                dirs.append((dr, dc, g[r][c]))
        if len(dirs) != 1:
            return out
        dr, dc, wall = dirs[0]
        # beam cells: from the emitter, through the wall, to the edge
        r, c = er + dr, ec + dc
        while 0 <= r < H and 0 <= c < W and g[r][c] == wall:
            r += dr
            c += dc
        hits = []
        while 0 <= r < H and 0 <= c < W:
            if g[r][c] not in (bg, wall, em):
                hits.append((r, c))
            r += dr
            c += dc
        seen = set()
        for s in hits:
            if s in seen:
                continue
            col = g[s[0]][s[1]]
            st = [s]
            seen.add(s)
            while st:
                y, x = st.pop()
                out[y][x] = bg
                for a in (-1, 0, 1):
                    for b in (-1, 0, 1):
                        if (a or b) and (conn8 or not (a and b)):
                            q = (y + a, x + b)
                            if 0 <= q[0] < H and 0 <= q[1] < W and q not in seen and g[q[0]][q[1]] == col:
                                seen.add(q)
                                st.append(q)
        return out
    return fn


def fam(train):
    for name, cost, c8 in (("beam_erase_4conn", 1, False), ("beam_erase_8conn", 2, True)):
        fn = _make(c8)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
