CARD = "891232d6"
READING = ("From each marker on the bottom edge a line climbs upward; whenever the cell above is an obstacle "
           "it marks the hit, turns and runs along beneath the obstacle bar to just past its end, then climbs "
           "again, ending with the marker colour at the top edge or where it is boxed in.")


def _rot(g):  # rotate 90 clockwise
    return [list(r) for r in zip(*g[::-1])]


def _flip(g):  # mirror left-right
    return [list(r)[::-1] for r in g]


def _id(g):
    return [list(r) for r in g]


def _compose(*fs):
    def h(g):
        for f in fs:
            g = f(g)
        return g
    return h


# the 8 symmetries as (forward, inverse)
_D8 = [
    (_id, _id),
    (_rot, _compose(_rot, _rot, _rot)),
    (_compose(_rot, _rot), _compose(_rot, _rot)),
    (_compose(_rot, _rot, _rot), _rot),
    (_flip, _flip),
    (_compose(_flip, _rot), _compose(_rot, _rot, _rot, _flip)),
    (_compose(_flip, _rot, _rot), _compose(_rot, _rot, _flip)),
    (_compose(_flip, _rot, _rot, _rot), _compose(_rot, _flip)),
]


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _roles(g):
    """bg = most common colour, obstacle = most common other colour."""
    cnt = _counts(g)
    order = sorted(cnt, key=lambda k: (-cnt[k], k))
    if len(order) < 3:
        return None
    return order[0], order[1]


def _trace(h, bg, ob):
    """Canonical orientation: markers on the bottom row climb upward and detour to the right.
    Returns dict (r,c)->role or None if markers are not all on the bottom row."""
    H, W = len(h), len(h[0])
    markers = [(i, j) for i in range(H) for j in range(W) if h[i][j] not in (bg, ob)]
    if not markers or any(i != H - 1 for i, j in markers):
        return None
    marks = {}
    for (r, c) in markers:
        steps = 0
        while steps < H * W:
            steps += 1
            nr = r - 1
            if nr < 0 or h[nr][c] != bg:
                marks[(r, c)] = 'end'
                break
            r = nr
            if r == 0:
                marks[(r, c)] = 'end'
                break
            if h[r - 1][c] == ob:
                c2 = c + 1
                path = []
                while c2 < W and h[r][c2] == bg and h[r - 1][c2] == ob:
                    path.append(c2)
                    c2 += 1
                if c2 >= W or h[r][c2] != bg:
                    marks[(r, c)] = 'end'
                    break
                marks[(r, c)] = 'turn'
                marks[(r - 1, c)] = 'hit'
                for p in path:
                    marks[(r, p)] = 'line'
                marks[(r, c2)] = 'resume'
                c = c2
            else:
                marks[(r, c)] = 'line'
    return marks


def _learn(train, k):
    f, inv = _D8[k]
    col = {}
    for ex in train:
        g, o = ex['input'], ex['output']
        ro = _roles(g)
        if ro is None:
            return None
        bg, ob = ro
        h, ho = f(g), f(o)
        if len(h) != len(ho) or len(h[0]) != len(ho[0]):
            return None
        m = _trace(h, bg, ob)
        if m is None:
            return None
        for (r, c), role in m.items():
            v = ho[r][c]
            if col.setdefault(role, v) != v:
                return None
    return col


def _make(k, col):
    f, inv = _D8[k]

    def fn(g):
        ro = _roles(g)
        if ro is None:
            return [list(r) for r in g]
        bg, ob = ro
        h = f(g)
        m = _trace(h, bg, ob)
        if m is None:
            return [list(r) for r in g]
        out = [list(r) for r in h]
        for (r, c), role in m.items():
            if role in col:
                out[r][c] = col[role]
        return inv(out)
    return fn


def fam(train):
    for k in range(8):
        col = _learn(train, k)
        if not col:
            continue
        fn = _make(k, col)
        try:
            if all(fn(ex['input']) == ex['output'] for ex in train):
                yield ('climb_detour_d8_%d' % k, 1 + k, fn)
                return
        except Exception:
            continue


FAMILIES = [fam]
