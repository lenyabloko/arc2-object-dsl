"""Family for ARC task 8b9c3697 -- concept: LOCK AND KEY (mechanics; cf. the enzyme lock-and-key model).

Picture: rigid *locks* (one colour) have a keyway -- a slot bounded by two walls with a ward (a
protrusion) at its back.  Loose *keys* (the key colour) lie around.  Each key is pushed straight along
one of the four axes until it touches a lock.  It *seats* only if it is complementary to that lock:
  * the key's leading face presses on the lock along its whole width,
  * the ward it presses on is exactly as wide as the key (the profile matches), and
  * the seated key lies wholly inside the keyway (every key cell has the same lock on both flanks).
A seated key stays in the lock and the path it swept is marked with the trail colour; keys that fit no
lock are discarded (become background).

Induced from the training pairs (no constants in the code):
  background   = most common colour of each input grid
  key colour   = the non-background input colour whose cells change in the training diffs
  trail colour = the colour that background / key cells turn into (other than bg and key)
  lock         = every other non-background colour, split into 8-connected components
Declared finite parameter domain, chosen by fitting the training pairs:
  keys_block in {False, True} -- whether other (loose) keys obstruct a sliding key
"""
from collections import Counter

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def most_common_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def components(cells, conn8):
    cells = set(cells)
    seen, out = set(), []
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0) and (conn8 or a == 0 or b == 0)]
    for s in sorted(cells):
        if s in seen:
            continue
        stack, comp = [s], []
        seen.add(s)
        while stack:
            r, c = stack.pop()
            comp.append((r, c))
            for a, b in nb:
                q = (r + a, c + b)
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
        out.append(comp)
    return out


def induce_roles(train):
    """Return (key colour, trail colour) consistent with every training pair, or None."""
    keys, trails = set(), set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        bg = most_common_colour(a)
        for r in range(len(a)):
            for c in range(len(a[0])):
                x, y = a[r][c], b[r][c]
                if x != y and x != bg:
                    keys.add(x)
        for r in range(len(a)):
            for c in range(len(a[0])):
                x, y = a[r][c], b[r][c]
                if x != y and y != bg and y not in keys:
                    trails.add(y)
    if len(keys) != 1 or len(trails) != 1:
        return None
    return keys.pop(), trails.pop()


def seat(key, lock_of, key_cells_all, H, W, d, keys_block):
    """Slide `key` along d until it touches a lock.  Return (final cells, swept cells) if it seats."""
    dr, dc = d
    er, ec = (0, 1) if dr else (1, 0)          # lateral axis
    cur = set(key)
    swept = set(key)
    own = set(key)
    while True:
        nxt = {(r + dr, c + dc) for r, c in cur}
        if any(not (0 <= r < H and 0 <= c < W) for r, c in nxt):
            return None                         # slid off the board: touched no lock
        if any(q in lock_of for q in nxt):
            break
        if keys_block and any(q in key_cells_all and q not in own for q in nxt):
            return None
        cur = nxt
        swept |= cur
    # leading face: most-forward key cell on every lateral line
    lat = lambda p: p[0] * er + p[1] * ec
    fwd = lambda p: p[0] * dr + p[1] * dc
    front = {}
    for p in cur:
        l = lat(p)
        if l not in front or fwd(p) > fwd(front[l]):
            front[l] = p
    ward = [(p[0] + dr, p[1] + dc) for p in front.values()]
    if not all(q in lock_of for q in ward):
        return None                             # partial contact: key does not press with its full face
    ids = {lock_of[q] for q in ward}
    if len(ids) != 1:
        return None
    lid = ids.pop()
    lo, hi = min(front), max(front)
    wlo = (front[lo][0] + dr - er, front[lo][1] + dc - ec)
    whi = (front[hi][0] + dr + er, front[hi][1] + dc + ec)
    if wlo in lock_of or whi in lock_of:
        return None                             # ward wider than the key: profiles do not match
    for r, c in cur:                            # key must lie inside the keyway (walls on both flanks)
        for s in (1, -1):
            rr, cc = r + s * er, c + s * ec
            while 0 <= rr < H and 0 <= cc < W and (rr, cc) not in lock_of:
                rr, cc = rr + s * er, cc + s * ec
            if lock_of.get((rr, cc)) != lid:
                return None
    return cur, swept


def make_solver(key_col, trail_col, keys_block):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = most_common_colour(g)
        lock_cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] not in (bg, key_col)]
        lock_of = {}
        for i, comp in enumerate(components(lock_cells, True)):
            for q in comp:
                lock_of[q] = i
        key_cells = {(r, c) for r in range(H) for c in range(W) if g[r][c] == key_col}
        out = [[bg if v == key_col else v for v in row] for row in g]
        seated = []
        for key in components(key_cells, False):
            for d in DIRS:
                res = seat(key, lock_of, key_cells, H, W, d, keys_block)
                if res:
                    seated.append(res)
                    break
        for cur, swept in seated:
            for r, c in swept - cur:
                out[r][c] = trail_col
        for cur, _ in seated:
            for r, c in cur:
                out[r][c] = key_col
        return out
    return fn


def fam_lock_and_key(train):
    roles = induce_roles(train)
    if roles is None:
        return
    key_col, trail_col = roles
    for keys_block in (False, True):
        fn = make_solver(key_col, trail_col, keys_block)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("mechanics:lock_and_key[key=%d,trail=%d,keys_block=%s]" % (key_col, trail_col, keys_block), 3, fn)
            return


FAMILIES = (fam_lock_and_key,)
