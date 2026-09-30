"""Family for ARC task 71e489b6 -- concept: DESPECKLE (graphics / image restoration, salt-and-pepper noise).

Picture: a picture made of solid regions has been sprinkled with speckle noise -- single pixels or tiny
clusters whose colour disagrees with the region they sit in (including notches bitten into a region's
edge).  A despeckle filter finds them: a pixel is a speck when, among its in-grid 4-neighbours, some other
colour strictly outnumbers its own colour (plurality vote); flipping such pixels to that colour and
repeating until nothing changes restores the clean picture, and the specks are exactly the pixels whose
colour changed.  Genuine structure survives: straight edges, corners and even 1-pixel-wide lines never lose
the vote.  What the filter then DOES with a speck depends on the speck's colour -- the familiar QA choice
between wiping debris away and circling a flaw:
    erase   -- the speck takes the restored colour (plain despeckle)
    keep    -- the speck is left as it was
    outline -- the speck is kept and every non-speck cell of its neighbourhood is painted a marker colour
               (a flaw-inspection ring; it paints over whatever is there, the restored picture included)

Everything is induced from the training pairs; declared finite parameter domains:
  action[c] in {"erase", "keep", "outline"}  for every colour c that occurs as a speck in training
                                            (colours never seen as specks default to "erase")
  marker    in colours present in training outputs
  nbhd      in {4, 8}                        -- ring neighbourhood of an outlined speck
"""
from collections import Counter
from itertools import product

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def despeckle(g):
    """Iterated plurality vote over in-grid 4-neighbours until stable. Returns the restored grid."""
    H, W = len(g), len(g[0])
    cur = [row[:] for row in g]
    for _ in range(H * W):
        nxt = [row[:] for row in cur]
        changed = False
        for r in range(H):
            for c in range(W):
                cnt = Counter(cur[r + dr][c + dc] for dr, dc in N4 if 0 <= r + dr < H and 0 <= c + dc < W)
                own = cnt.pop(cur[r][c], 0)
                if not cnt:
                    continue
                (m, k), *rest = cnt.most_common(2)
                if rest and rest[0][1] == k:
                    continue  # no unique challenger
                if k > own:
                    nxt[r][c] = m
                    changed = True
        cur = nxt
        if not changed:
            break
    return cur


def make(action, marker, nbhd):
    offs = N8 if nbhd == 8 else N4

    def fn(g):
        H, W = len(g), len(g[0])
        clean = despeckle(g)
        specks = {(r, c) for r in range(H) for c in range(W) if g[r][c] != clean[r][c]}
        out = [row[:] for row in g]
        ringed = set()
        for (r, c) in specks:
            a = action.get(g[r][c], "erase")
            if a == "erase":
                out[r][c] = clean[r][c]
            elif a == "outline":
                ringed.add((r, c))
        for (r, c) in ringed:
            for dr, dc in offs:
                y, x = r + dr, c + dc
                if 0 <= y < H and 0 <= x < W and (y, x) not in ringed:
                    out[y][x] = marker
        return out

    return fn


def fam_despeckle(train):
    for p in train:
        a, b = p["input"], p["output"]
        if not a or len(a) != len(b) or len(a[0]) != len(b[0]):
            return
    speck_cols = set()
    for p in train:
        g = p["input"]
        clean = despeckle(g)
        speck_cols |= {g[r][c] for r in range(len(g)) for c in range(len(g[0])) if g[r][c] != clean[r][c]}
    if not speck_cols:
        return
    speck_cols = sorted(speck_cols)
    out_cols = sorted({v for p in train for row in p["output"] for v in row})
    new_cols = sorted(set(out_cols) - {v for p in train for row in p["input"] for v in row})
    markers = new_cols + [c for c in out_cols if c not in new_cols]
    for acts in product(("erase", "keep", "outline"), repeat=len(speck_cols)):
        action = dict(zip(speck_cols, acts))
        uses_marker = "outline" in acts
        for marker in (markers if uses_marker else [None]):
            for nbhd in ((8, 4) if uses_marker else (4,)):
                fn = make(action, marker, nbhd)
                if all(fn(p["input"]) == p["output"] for p in train):
                    desc = ",".join(f"{c}:{a}" for c, a in action.items())
                    extra = f";marker={marker};nbhd={nbhd}" if uses_marker else ""
                    yield (f"graphics:despeckle[{desc}{extra}]", 3, fn)
                    return


FAMILIES = (fam_despeckle,)
