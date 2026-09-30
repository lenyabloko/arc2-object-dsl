"""Family for ARC task 13e47133 -- concept: DISTANCE TRANSFORM (graphics / image processing).

Walls partition the canvas into rooms.  Inside every room each cell's colour is a periodic function of its
distance to the room's boundary (walls or the canvas edge): the cell lies on iso-distance ring k, and ring k is
painted palette[k mod P].  The palette is "printed" by the seed pixels already in the room: a seed on ring k
fixes palette[k]; rings up to the deepest seed that carry no seed keep the background colour; P = deepest seed
ring + 1.  Rooms without seeds are left alone.  (Contour banding of a distance field, i.e. isodistance lines.)

Roles (no colour numbers): background = most frequent colour of the grid; wall = most frequent other colour.
Declared finite domain: METRIC in {chebyshev (8-neighbour rings), manhattan (4-neighbour rings)}.
"""
from collections import Counter, deque

METRICS = {
    'chebyshev': ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)),
    'manhattan': ((-1, 0), (1, 0), (0, -1), (0, 1)),
}


def _roles(g):
    cnt = Counter(v for row in g for v in row).most_common()
    bg = cnt[0][0]
    wall = cnt[1][0] if len(cnt) > 1 else None
    return bg, wall


def _rooms(g, wall):
    """4-connected components of non-wall cells."""
    H, W = len(g), len(g[0])
    lab = [[-1] * W for _ in range(H)]
    rooms = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == wall or lab[r][c] >= 0:
                continue
            idx = len(rooms); cells = [(r, c)]; lab[r][c] = idx; q = deque(cells)
            while q:
                y, x = q.popleft()
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and lab[ny][nx] < 0 and g[ny][nx] != wall:
                        lab[ny][nx] = idx; cells.append((ny, nx)); q.append((ny, nx))
            rooms.append(cells)
    return rooms, lab


def _ring_index(room, H, W, steps):
    """Distance transform: ring k = (distance to nearest cell outside the room, canvas exterior included) - 1."""
    inside = set(room)
    dist = {}
    q = deque()
    for (y, x) in room:
        for dy, dx in steps:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < H and 0 <= nx < W) or (ny, nx) not in inside:
                dist[(y, x)] = 0; q.append((y, x)); break
    while q:
        y, x = q.popleft()
        for dy, dx in steps:
            n = (y + dy, x + dx)
            if n in inside and n not in dist:
                dist[n] = dist[(y, x)] + 1; q.append(n)
    return dist


def make_distance_transform(metric):
    steps = METRICS[metric]

    def fn(g):
        H, W = len(g), len(g[0])
        bg, wall = _roles(g)
        out = [row[:] for row in g]
        if wall is None:
            return out
        rooms, _ = _rooms(g, wall)
        for room in rooms:
            ring = _ring_index(room, H, W, steps)
            seeds = {}
            for (y, x) in room:
                if g[y][x] != bg:
                    k = ring[(y, x)]
                    if seeds.setdefault(k, g[y][x]) != g[y][x]:
                        raise ValueError('two seed colours on one ring')
            if not seeds:
                continue
            P = max(seeds) + 1
            palette = [seeds.get(k, bg) for k in range(P)]
            for (y, x) in room:
                out[y][x] = palette[ring[(y, x)] % P]
        return out

    return fn


def fam_distance_transform(train):
    for p in train:
        if len(p['input']) != len(p['output']) or len(p['input'][0]) != len(p['output'][0]):
            return
    for metric in METRICS:
        fn = make_distance_transform(metric)
        try:
            ok = all(fn(p['input']) == p['output'] for p in train)
        except ValueError:
            ok = False
        if ok:
            yield ('graphics:distance_transform[metric=%s,palette=seed-rings-cyclic]' % metric, 3, fn)


FAMILIES = (fam_distance_transform,)
