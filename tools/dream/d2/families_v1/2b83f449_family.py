"""Family for ARC task 2b83f449 -- concept: MARBLE RUN (mechanics: marbles dropping level by level through a rack).

Reading of the task
-------------------
The grid is a rack of horizontal shelves (runs of the shelf colour) separated by gaps of background.  Each short
horizontal bar lying in a gap is a bracket: it becomes a vertical post (post colour) through its centre that
pierces the shelf above and the shelf below by `arm` cells, and the rest of the bar turns into shelf, i.e. a short
channel of shelf colour on both sides of the post that links the two shelves.  Posts cut shelves into troughs;
background cells inside a shelf row are walls too.

Marbles (marble colour) sit at the ends of troughs.  Under gravity a marble drains out of its trough through the
nearest opening in its floor (a shelf-coloured cell directly below), drops straight down the channel beside the
post, lands in the trough below, and keeps rolling away from the post it slid down beside to the far end of that
trough; if that trough has an opening it drains again, otherwise the marble comes to rest there.  Marbles that
come to rest at the same trough end stack side by side inward from that end.  A marble whose own trough has no
opening stays where it is.

Nothing is a task constant:
  * colour roles are induced from train: bar = only in inputs, post = only in outputs, and the remaining shared
    colours are (background, shelf, marble) in the one assignment that fits;
  * bars are maximal horizontal runs of the bar colour of any odd length; arm length is from a finite domain;
  * gravity direction is any of the 8 dihedral frames (first fitting frame wins), so rotated / mirrored racks work.

Parameters (declared finite domains, induced from train, first fit wins):
  frame in D4 (8 transforms), arm in {1, 2}, role assignment in permutations of the shared colours.
"""

from itertools import permutations

# ---------------------------------------------------------------- dihedral frames
_TF = {
    'id':   (lambda g: [r[:] for r in g], lambda g: [r[:] for r in g]),
    'fliplr': (lambda g: [r[::-1] for r in g], lambda g: [r[::-1] for r in g]),
    'flipud': (lambda g: [r[:] for r in g[::-1]], lambda g: [r[:] for r in g[::-1]]),
    'rot180': (lambda g: [r[::-1] for r in g[::-1]], lambda g: [r[::-1] for r in g[::-1]]),
    'transpose': (lambda g: [list(c) for c in zip(*g)], lambda g: [list(c) for c in zip(*g)]),
    'rot90': (lambda g: [list(c)[::-1] for c in zip(*g)], lambda g: [list(c) for c in zip(*g)][::-1]),
    'rot270': (lambda g: [list(c) for c in zip(*g)][::-1], lambda g: [list(c)[::-1] for c in zip(*g)]),
    'antitranspose': (lambda g: [list(c)[::-1] for c in zip(*g)][::-1],
                      lambda g: [list(c)[::-1] for c in zip(*g)][::-1]),
}


def _marble_run(g, bar, post, bg, shelf, marble, arm):
    H, W = len(g), len(g[0])
    out = [r[:] for r in g]
    # 1. brackets -> posts + side channels
    for r in range(H):
        c = 0
        while c < W:
            if g[r][c] != bar:
                c += 1
                continue
            e = c
            while e + 1 < W and g[r][e + 1] == bar:
                e += 1
            L = e - c + 1
            if L % 2 == 0:
                raise ValueError('even bar')
            m = (c + e) // 2
            for x in range(c, e + 1):
                out[r][x] = shelf
            for k in range(-arm, arm + 1):
                if 0 <= r + k < H:
                    out[r + k][m] = post
            c = e + 1
    # 2. marbles
    balls = [(r, c) for r in range(H) for c in range(W) if out[r][c] == marble]
    for r, c in balls:
        out[r][c] = shelf

    def passable(r, c):
        return 0 <= r < H and 0 <= c < W and out[r][c] == shelf

    def trough(r, c):
        a = c
        while passable(r, a - 1):
            a -= 1
        b = c
        while passable(r, b + 1):
            b += 1
        return a, b

    resting = []      # (row, end_col, step_inward) ; static balls first
    rolling = []
    for r0, c0 in balls:
        r, x, moved = r0, c0, False
        for _ in range(4 * H + 4):
            a, b = trough(r, x)
            holes = [y for y in range(a, b + 1) if passable(r + 1, y)]
            if not holes:
                break
            y = min(holes, key=lambda h: (abs(h - x), h))
            while passable(r + 1, y):
                r += 1
            x, moved = y, True
        a, b = trough(r, x)
        if not moved:
            resting.append((r, x, 0))
        else:
            end, step = (a, 1) if x - a > b - x else (b, -1)
            rolling.append((r, end, step))
    for r, x, _ in resting:
        out[r][x] = marble
    for r, x, step in rolling:
        while 0 <= x < W and out[r][x] == marble:
            x += step
        if not (0 <= x < W) or out[r][x] != shelf:
            raise ValueError('trough full')
        out[r][x] = marble
    return out


def fam_marble_run(train):
    cin, cout = set(), set()
    for p in train:
        for row in p['input']:
            cin.update(row)
        for row in p['output']:
            cout.update(row)
    bars, posts, shared = cin - cout, cout - cin, sorted(cin & cout)
    if len(bars) != 1 or len(posts) != 1 or not 2 <= len(shared) <= 3:
        return
    bar, post = next(iter(bars)), next(iter(posts))
    if len(shared) == 2:
        shared = shared + [-1]          # no marbles in train: marble role unused
    for tname, (fwd, inv) in _TF.items():
        for arm in (1, 2):
            for bg, shelf, marble in permutations(shared, 3):
                if bg == -1 or shelf == -1:
                    continue

                def fn(g, fwd=fwd, inv=inv, bg=bg, shelf=shelf, marble=marble, arm=arm):
                    return inv(_marble_run(fwd(g), bar, post, bg, shelf, marble, arm))
                try:
                    ok = all(fn(p['input']) == p['output'] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ('mechanics:marble_run[bar=%d,post=%d,bg=%d,shelf=%d,marble=%d,arm=%d,frame=%s]'
                           % (bar, post, bg, shelf, marble, arm, tname), 3, fn)
                    return


FAMILIES = (fam_marble_run,)
