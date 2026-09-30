"""Family for ARC task 9bbf930d -- concept: BALLISTIC BARREL (mechanics / ballistics).

Picture: a magazine of rounds (the moving colour) sits on the grid border.  A round fires only if it is
chambered at the breech of a *barrel*: a straight corridor of background whose two side walls are the
same colour.  The round travels down the barrel, following the barrel's bends (a bend is where the
barrel's own wall blocks the way and exactly one side is open), leaves through the muzzle, and then
flies in a straight line until it strikes an obstacle or reaches the grid edge, where it comes to rest.
If in flight it enters another barrel, that barrel guides it in the same way.  The chamber it left
becomes background, the resting cell takes the round's colour.

Everything is induced from the training pairs:
  background  = most common colour of the input
  ammo colour = the only colour that both vanishes from and appears on background in the training diffs
  launch dir  = the unique in-bounds background 4-neighbour of an ammo cell (the open side of the magazine)
Declared finite parameter domains, chosen by fitting the training pairs:
  flight in {"ballistic", "muzzle"}  -- after the muzzle keep flying until impact / stop at first cell outside
  guide  in {True, False}            -- whether a barrel entered in flight re-guides the round
  edge   in {"rest", "vanish"}       -- at the grid edge the round rests on the last cell / leaves the grid
"""
from collections import Counter

DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def most_common_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def changed_colours(train):
    """Colours that disappear (-> background) or appear (background ->) between input and output."""
    gone, came = set(), set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        bg = most_common_colour(a)
        for r in range(len(a)):
            for c in range(len(a[0])):
                x, y = a[r][c], b[r][c]
                if x == y:
                    continue
                if y == bg:
                    gone.add(x)
                elif x == bg:
                    came.add(y)
                else:
                    return None  # a colour-to-colour change is outside this concept
    return gone, came


def fly(g, bg, start, d, flight, guide, edge):
    """Trace one round.  Returns the resting cell, None if it left the grid, or 'nofire' if it never
    passed through a barrel (an unloaded chamber does not fire)."""
    H, W = len(g), len(g[0])

    def inb(r, c):
        return 0 <= r < H and 0 <= c < W

    def col(r, c):
        return g[r][c] if inb(r, c) else None

    def is_wall(r, c):
        return inb(r, c) and g[r][c] != bg

    def is_open(r, c):
        return inb(r, c) and g[r][c] == bg

    r, c = start
    dr, dc = d
    barrel = None          # colour of the barrel currently guiding the round
    ever_guided = False
    left_barrel = False    # has the round already exited a barrel (for flight == "muzzle")
    seen = set()
    # first step out of the chamber
    if not is_open(r + dr, c + dc):
        return "nofire"
    r, c = r + dr, c + dc
    while True:
        if (r, c, dr, dc) in seen:
            break
        seen.add((r, c, dr, dc))
        # side walls of the current cell relative to the direction of travel
        s1 = (r - dc, c + dr)   # one side  (d rotated by +90 degrees)
        s2 = (r + dc, c - dr)   # other side (d rotated by -90 degrees)
        a, b = col(*s1), col(*s2)
        wa, wb = is_wall(*s1), is_wall(*s2)
        if wa and wb and a == b:
            if guide or not left_barrel:   # without guiding, only the first barrel steers the round
                barrel = a
                ever_guided = True
        elif barrel is not None and ((wa and a == barrel and is_open(*s2)) or (wb and b == barrel and is_open(*s1))):
            pass  # bend cell / mouth: still inside the barrel
        else:
            if barrel is not None:
                left_barrel = True
                if flight == "muzzle":
                    return (r, c) if ever_guided else "nofire"
            barrel = None
        nr, nc = r + dr, c + dc
        if not inb(nr, nc):
            if not ever_guided:
                return "nofire"
            return (r, c) if edge == "rest" else None
        if is_open(nr, nc):
            r, c = nr, nc
            continue
        # blocked ahead: a barrel bend turns the round, anything else stops it
        front = g[nr][nc]
        if barrel is not None and front == barrel:
            opts = []
            for (sr, sc), (tr, tc) in ((s1, s2), (s2, s1)):
                if is_open(sr, sc) and is_wall(tr, tc) and g[tr][tc] == barrel:
                    opts.append((sr - r, sc - c))
            if len(opts) == 1:
                dr, dc = opts[0]
                continue
        break
    return (r, c) if ever_guided else "nofire"


def fire_all(g, bg, ammo, flight, guide, edge):
    H, W = len(g), len(g[0])
    out = [row[:] for row in g]
    for r in range(H):
        for c in range(W):
            if g[r][c] != ammo:
                continue
            opens = [(dr, dc) for dr, dc in DIRS
                     if 0 <= r + dr < H and 0 <= c + dc < W and g[r + dr][c + dc] == bg]
            if len(opens) != 1:
                continue
            res = fly(g, bg, (r, c), opens[0], flight, guide, edge)
            if res == "nofire":
                continue
            out[r][c] = bg
            if res is not None:
                out[res[0]][res[1]] = ammo
    return out


def fam_ballistic_barrel(train):
    ch = changed_colours(train)
    if ch is None:
        return
    gone, came = ch
    if len(gone) != 1 or gone != came:
        return
    ammo = next(iter(gone))
    for flight in ("ballistic", "muzzle"):
        for guide in (True, False):
            for edge in ("rest", "vanish"):
                def fn(g, flight=flight, guide=guide, edge=edge):
                    bg = most_common_colour(g)
                    if ammo == bg:
                        return [row[:] for row in g]
                    return fire_all(g, bg, ammo, flight, guide, edge)
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("mechanics:ballistic_barrel[ammo=changed-colour,flight=%s,guide=%s,edge=%s]"
                           % (flight, guide, edge), 3, fn)


FAMILIES = (fam_ballistic_barrel,)
