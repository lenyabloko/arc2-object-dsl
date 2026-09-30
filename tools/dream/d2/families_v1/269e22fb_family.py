"""Family: vision:registration.

Concept (computer vision / medical imaging): IMAGE REGISTRATION.
Every training output is the same reference picture (a fixed "atlas"), seen in some pose
(one of the 8 rigid symmetries of the square) and painted with some palette.  Each input is
a partial observation (a fragment seen through a rectangular window) of that atlas.
Solving = register the fragment against the atlas: find the pose + translation + colour
bijection under which the fragment coincides with a window of the atlas, then render the
whole atlas in that pose and palette.

Everything is induced from the training pairs:
  * the atlas itself = the training outputs, after checking they are all one picture up to
    pose and palette (otherwise the family does not apply);
  * sym   in {"id", "D4"}   : poses allowed for registration (smallest that fits train);
  * palette in {"fixed", "perm"} : whether colours must match literally or only up to a
    bijection (smallest that fits train).
"""
from collections import Counter


# ---------------------------------------------------------------- grid helpers
def rot90(g):
    return [list(r) for r in zip(*g[::-1])]


def flip_lr(g):
    return [list(r[::-1]) for r in g]


def poses(g, sym):
    """All distinct poses of grid g under the symmetry group `sym`."""
    if sym == "id":
        return [[list(r) for r in g]]
    out, h = [], [list(r) for r in g]
    for _ in range(4):
        out.append(h)
        out.append(flip_lr(h))
        h = rot90(h)
    uniq = []
    for p in out:
        if p not in uniq:
            uniq.append(p)
    return uniq


def palette_canon(g):
    """Relabel colours by first appearance in raster order (palette-free signature)."""
    m = {}
    return tuple(tuple(m.setdefault(x, len(m)) for x in r) for r in g)


def equivalent(a, b, sym, palette):
    """Is b equal to a under some pose in `sym` (and palette bijection if allowed)?"""
    key = palette_canon if palette == "perm" else (lambda g: tuple(map(tuple, g)))
    kb = key(b)
    return any(key(p) == kb for p in poses(a, sym))


def window_bijection(ref, top, left, frag, palette):
    """If the window of `ref` at (top,left) with frag's size matches frag
    (literally, or via a colour bijection), return the ref->frag colour map, else None."""
    fwd, bwd = {}, {}
    for i, row in enumerate(frag):
        rrow = ref[top + i]
        for j, c in enumerate(row):
            r = rrow[left + j]
            if palette == "fixed":
                if r != c:
                    return None
                continue
            if fwd.setdefault(r, c) != c or bwd.setdefault(c, r) != r:
                return None
    if palette == "fixed":
        return {}
    return fwd


def register(atlas, frag, sym, palette):
    """All renderings of the atlas under which frag is a window of it."""
    H, W = len(frag), len(frag[0])
    results = []
    for p in poses(atlas, sym):
        R, C = len(p), len(p[0])
        if H > R or W > C:
            continue
        for top in range(R - H + 1):
            for left in range(C - W + 1):
                m = window_bijection(p, top, left, frag, palette)
                if m is None:
                    continue
                # atlas colours never seen through the window keep their own value
                out = [[m.get(v, v) for v in r] for r in p]
                if out not in results:
                    results.append(out)
    return results


# ---------------------------------------------------------------- family
SYMS = ("id", "D4")
PALETTES = ("fixed", "perm")


def fam_registration(train):
    outs = [p["output"] for p in train]
    if not outs:
        return
    atlas = outs[0]
    for sym in SYMS:
        for palette in PALETTES:
            # the training outputs must all be the same picture up to (sym, palette)
            if not all(equivalent(atlas, o, sym, palette) for o in outs):
                continue

            def fn(grid, sym=sym, palette=palette, atlas=atlas):
                cands = register(atlas, grid, sym, palette)
                if not cands:
                    return None
                # several consistent registrations: keep the first in the fixed search
                # order (identity pose first, then top-left-most window)
                return cands[0]

            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("vision:registration[sym=%s,palette=%s]" % (sym, palette), 3, fn)
                return


FAMILIES = (fam_registration,)
