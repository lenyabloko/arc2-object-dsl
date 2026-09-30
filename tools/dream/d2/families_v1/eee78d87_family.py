"""Family for ARC task eee78d87 -- concept: STENCIL WALLPAPER (graphics: a periodic wallpaper printed through a
stencil motif, with the original canvas lit up as a viewport in the centre).

Reading of the task
-------------------
The input is a blank canvas (background colour) carrying one small shape.  The shape's bounding box is a stencil:
shape cells are holes, the other cells are solid.  The output is wallpaper printed with that stencil: the canvas' H x W
cells become an H x W lattice of stencil centres spaced one stencil apart (so the sheet is (H-1)*p+1 by (W-1)*q+1 for a
p x q stencil), holes show the ink colour, solid parts keep the paper colour.  The original canvas, placed in the
centre of the sheet (an H x W frame), is a lit viewport: holes seen inside it show the light colour instead.

Nothing task-specific is stored: background = most common input colour, stencil = bounding box of the other cells,
period = stencil size, sheet size / phase / viewport from small declared domains, and every output colour is a role
(paper = input background, shape colour) or a constant induced from the training outputs.

Parameters (declared finite domains, induced from train; first fit wins):
  size    in {lattice, scale, const}   sheet side = (n-1)*p+1 | n*p | the (shared) training output size
  phase   in {centre, corner}          stencil centre / top-left corner sits on the lattice points
  window  in {frame, none}             viewport = centred box of the input's size | no viewport
  colour of each (hole|solid) x (inside|outside viewport) slot in {bg, fg, const c}
"""

from collections import Counter
from itertools import product

SIZES = ("lattice", "scale", "const")
PHASES = ("centre", "corner")
WINDOWS = ("frame", "none")


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _stencil(g):
    """(background, hole mask of the non-background bounding box, dominant shape colour) or None."""
    bg = _bg(g)
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
    if not cells:
        return None
    r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
    c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
    mask = [[g[r][c] != bg for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
    fg = Counter(g[r][c] for r, c in cells).most_common(1)[0][0]
    return bg, mask, fg


def _side(rule, n, p, const):
    if rule == "lattice":
        return (n - 1) * p + 1
    if rule == "scale":
        return n * p
    return const


def _layout(g, size, phase, window, const_hw):
    """Slot label of every sheet cell: (is_hole, in_viewport); plus bg/fg roles.  None if not applicable."""
    st = _stencil(g)
    if st is None:
        return None
    bg, mask, fg = st
    H, W = len(g), len(g[0])
    p, q = len(mask), len(mask[0])
    OH = _side(size, H, p, const_hw[0] if const_hw else None)
    OW = _side(size, W, q, const_hw[1] if const_hw else None)
    if not OH or not OW or OH <= 0 or OW <= 0:
        return None
    oy, ox = (p // 2, q // 2) if phase == "centre" else (0, 0)
    if window == "frame":
        wy, wx = (OH - H) // 2, (OW - W) // 2
        inwin = lambda r, c: wy <= r < wy + H and wx <= c < wx + W
    else:
        inwin = lambda r, c: False
    slots = [[(mask[(r + oy) % p][(c + ox) % q], inwin(r, c)) for c in range(OW)] for r in range(OH)]
    return slots, bg, fg


def _resolve(src, bg, fg):
    return bg if src == "bg" else fg if src == "fg" else src[1]


def _induce_colours(train, size, phase, window, const_hw):
    """For each slot pick the first source in (bg, fg, const) consistent with every training output."""
    seen = {}  # slot -> list of (bg, fg, colour)
    for pr in train:
        lay = _layout(pr["input"], size, phase, window, const_hw)
        if lay is None:
            return None
        slots, bg, fg = lay
        out = pr["output"]
        if len(out) != len(slots) or len(out[0]) != len(slots[0]):
            return None
        per = {}
        for r, row in enumerate(slots):
            for c, s in enumerate(row):
                if per.setdefault(s, out[r][c]) != out[r][c]:
                    return None  # a slot must be one colour within a pair
        for s, col in per.items():
            seen.setdefault(s, []).append((bg, fg, col))
    srcs = {}
    for s, obs in seen.items():
        cands = ["bg", "fg"] + [("const", obs[0][2])]
        for cand in cands:
            if all(_resolve(cand, bg, fg) == col for bg, fg, col in obs):
                srcs[s] = cand
                break
        else:
            return None
    # an unseen viewport slot falls back to its outside counterpart (plain wallpaper)
    for hole in (True, False):
        if (hole, True) not in srcs and (hole, False) in srcs:
            srcs[(hole, True)] = srcs[(hole, False)]
    return srcs


def _fmt(src):
    return src if isinstance(src, str) else "c%d" % src[1]


def fam_stencil_wallpaper(train):
    shapes = {(len(p["output"]), len(p["output"][0])) for p in train}
    const_hw = next(iter(shapes)) if len(shapes) == 1 else None
    for size, phase, window in product(SIZES, PHASES, WINDOWS):
        if size == "const" and const_hw is None:
            continue
        srcs = _induce_colours(train, size, phase, window, const_hw)
        if not srcs or (False, False) not in srcs or (True, False) not in srcs:
            continue

        def fn(g, size=size, phase=phase, window=window, srcs=srcs):
            lay = _layout(g, size, phase, window, const_hw)
            if lay is None:
                return None
            slots, bg, fg = lay
            return [[_resolve(srcs[s], bg, fg) for s in row] for row in slots]

        if all(fn(p["input"]) == p["output"] for p in train):
            name = "graphics:stencil_wallpaper[size=%s,phase=%s,window=%s,hole=%s,solid=%s,lit_hole=%s,lit_solid=%s]" % (
                size, phase, window, _fmt(srcs[(True, False)]), _fmt(srcs[(False, False)]),
                _fmt(srcs[(True, True)]), _fmt(srcs[(False, True)]))
            yield (name, 3, fn)
            return


FAMILIES = (fam_stencil_wallpaper,)
