"""Family for ARC task 88bcf3b4 -- concept: ROPE WRAP (mechanics).

Picture: a straight rigid pole (a straight one-colour segment) has a flexible rope (another component)
tied at one tip: the rope's knot is the rope cell beside the tip cell, perpendicular to the pole.
Somewhere beyond that tip, along the pole's axis, sits a peg (any other object on the rope's side of the
axis or on the axis itself).  The rope keeps its length (number of cells) but is re-laid: pulled taut
from the knot, one cell per step outward along the pole axis, straight to the peg, it wraps the peg's
silhouette on the rope's side (one cell outside the peg), then bends over the peg's far end and runs
off diagonally; whatever runs off the grid is lost.  The old rope is erased; pole and peg stay.

Local frame per pole tip E:  t = steps outward along the pole axis, u = lateral offset toward the rope's
side (the knot is at t=0, u=1).  wrap(t) = 1 + max u of peg cells at step t.

Everything is induced:
  background = most common colour;  poles = straight one-colour segments (>= 2 cells);
  rope = the component holding a knot beside a pole tip;  peg = nearest other object ahead of the tip
  on the rope's side (or on the axis) that the taut rope can reach.
Declared finite parameter domains, fitted on the training pairs:
  approach in {"linear", "diag_first", "diag_last"}  -- how the taut rope climbs from knot to peg
  release  in {"wrap", "hold", "mirror"}             -- past the peg: bend over its end / run straight /
                                                        mirror the approach
"""
from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _components(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            col = g[r][c]
            stack, cells = [(r, c)], []
            seen[r][c] = True
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
            comps.append((col, frozenset(cells)))
    return comps


def _straight(cells):
    """Return the axis unit vector of a straight contiguous segment of >= 2 cells, else None."""
    if len(cells) < 2:
        return None
    rows = {r for r, _ in cells}
    cols = {c for _, c in cells}
    if len(rows) == 1 and max(cols) - min(cols) + 1 == len(cells):
        return (0, 1)
    if len(cols) == 1 and max(rows) - min(rows) + 1 == len(cells):
        return (1, 0)
    return None


def _rope_profile(t0, t1, hug, length, approach, release):
    """Lateral offset u(t) for t = 0..length-1 of the re-laid rope."""
    us = []
    h0 = hug[t0]
    d = h0 - 1
    for t in range(length):
        if t == 0:
            u = 1
        elif t < t0:
            if approach == "linear":
                u = 1 + int((d * t) / t0 + (0.5 if d >= 0 else -0.5))
            elif approach == "diag_first":
                u = 1 + (min(t, abs(d)) * (1 if d >= 0 else -1))
            else:  # diag_last
                k = t - (t0 - abs(d))
                u = 1 + (max(0, k) * (1 if d >= 0 else -1))
        elif t <= t1:
            u = hug[t]
        else:
            k = t - t1
            if release == "wrap":
                u = hug[t1] - k
            elif release == "hold":
                u = hug[t1]
            else:  # mirror the approach about the peg's span
                m = t0 - k
                u = us[m] if m >= 0 else us[0]
        us.append(u)
    return us


def _relay(g, approach, release):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    comps = _components(g, bg)
    owner = {}
    for i, (_, cells) in enumerate(comps):
        for rc in cells:
            owner[rc] = i
    systems = []  # (pole idx, rope idx, E, a, l)
    for i, (_, cells) in enumerate(comps):
        ax = _straight(cells)
        if ax is None:
            continue
        ordered = sorted(cells)
        for E, a in ((ordered[0], (-ax[0], -ax[1])), (ordered[-1], ax)):
            for s in (1, -1):
                l = (ax[1] * s, ax[0] * s)
                A = (E[0] + l[0], E[1] + l[1])
                j = owner.get(A)
                if j is None or j == i:
                    continue
                if _straight(comps[j][1]) is not None and len(comps[j][1]) >= len(cells):
                    continue  # a straight bar at least as long is a pole, not a rope
                systems.append((i, j, E, a, l))
    if not systems:
        return None
    used = {k for sy in systems for k in (sy[0], sy[1])}
    out = [row[:] for row in g]
    draws = []
    for pole, rope, E, a, l in systems:
        best = None
        for k, (_, cells) in enumerate(comps):
            if k in used:
                continue
            tu = [((r - E[0]) * a[0] + (c - E[1]) * a[1], (r - E[0]) * l[0] + (c - E[1]) * l[1])
                  for r, c in cells]
            ts = [t for t, _ in tu]
            if min(ts) < 1 or max(u for _, u in tu) < 0:
                continue
            t0, t1 = min(ts), max(ts)
            hug = {}
            for t, u in tu:
                hug[t] = max(hug.get(t, u), u)
            for t in range(t0, t1 + 1):
                if t not in hug:
                    hug[t] = hug[t - 1]
                else:
                    hug[t] += 1
            if abs(hug[t0] - 1) > t0:
                continue
            key = (t0, abs(hug[t0] - 1))
            if best is None or key < best[0]:
                best = (key, t0, t1, hug)
        if best is None:
            return None
        _, t0, t1, hug = best
        length = len(comps[rope][1])
        us = _rope_profile(t0, t1, hug, length, approach, release)
        cells = []
        for t, u in enumerate(us):
            r, c = E[0] + t * a[0] + u * l[0], E[1] + t * a[1] + u * l[1]
            if 0 <= r < H and 0 <= c < W:
                cells.append((r, c))
        draws.append((comps[rope][0], comps[rope][1], cells))
    for _, old, _ in draws:
        for r, c in old:
            out[r][c] = bg
    for col, _, cells in draws:
        for r, c in cells:
            out[r][c] = col
    return out


def fam_rope_wrap(train):
    for release in ("wrap", "hold", "mirror"):
        for approach in ("linear", "diag_first", "diag_last"):
            def fn(g, approach=approach, release=release):
                return _relay(g, approach, release)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("mechanics:rope_wrap[approach=%s,release=%s]" % (approach, release), 3, fn)
                return


FAMILIES = (fam_rope_wrap,)
