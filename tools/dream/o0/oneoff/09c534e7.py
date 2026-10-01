CARD = "09c534e7"
READING = ("Each connected structure of rooms holds one seed of another colour; every interior cell "
           "of its rooms (a wall-colour cell whose eight neighbours are all part of the structure) is "
           "filled with that seed's colour.")

from collections import deque


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _make(conn8_interior):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        bg = max(cnt, key=lambda k: cnt[k])
        rest = {k: v for k, v in cnt.items() if k != bg}
        if not rest:
            return [list(r) for r in g]
        wall = max(rest, key=lambda k: rest[k])
        out = [list(r) for r in g]
        seen = [[False] * W for _ in range(H)]
        if conn8_interior:
            nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
        else:
            nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]

        def interior(i, j):
            for a, b in nb:
                x, y = i + a, j + b
                if not (0 <= x < H and 0 <= y < W) or g[x][y] == bg:
                    return False
            return True

        for i in range(H):
            for j in range(W):
                if g[i][j] == bg or seen[i][j]:
                    continue
                comp = []
                q = deque([(i, j)])
                seen[i][j] = True
                while q:
                    a, b = q.popleft()
                    comp.append((a, b))
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            q.append((x, y))
                seeds = [(a, b) for a, b in comp if g[a][b] != wall]
                if not seeds:
                    continue
                # multi-source BFS inside the component: nearest seed colour
                own = {}
                q = deque()
                for a, b in seeds:
                    own[(a, b)] = g[a][b]
                    q.append((a, b))
                cs = set(comp)
                while q:
                    a, b = q.popleft()
                    for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        x, y = a + da, b + db
                        if (x, y) in cs and (x, y) not in own:
                            own[(x, y)] = own[(a, b)]
                            q.append((x, y))
                for a, b in comp:
                    if g[a][b] == wall and interior(a, b):
                        out[a][b] = own[(a, b)]
        return out
    return fn


def fam(train):
    for name, c8, cost in (("room_fill_8nb", True, 1), ("room_fill_4nb", False, 2)):
        fn = _make(c8)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield (name, cost, fn)


FAMILIES = [fam]
