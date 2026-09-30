"""Family: mathematical morphology -- binary OPENING.

Concept (image processing / mathematical morphology): the morphological opening of a
binary image A by a structuring element B is the union of all translates of B that fit
entirely inside A (erosion followed by dilation).  The output repaints the opening of
the source-colour mask (or, with mode 'tophat', its residue A minus opening) in a new
colour; every other cell is untouched.

Induced parameters
  src, dst  : the unique colour recoloured and the unique colour it becomes (from diffs)
  B         : structuring element, chosen from a small declared finite library of
              elementary shapes plus the shapes of the changed components seen in train
  mode      : 'open' (paint opening) | 'tophat' (paint A minus opening)
"""


def _norm(cells):
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells))


def _library():
    """Small declared finite domain of elementary structuring elements."""
    lib = []
    lib.append(((0, 1), (1, 0), (1, 1), (1, 2), (2, 1)))           # cross (von Neumann ball r=1)
    lib.append(((0, 0), (0, 2), (1, 1), (2, 0), (2, 2)))           # saltire (diagonal cross)
    for k in (2, 3):
        lib.append(tuple((r, c) for r in range(k) for c in range(k)))  # k x k square
    for k in (2, 3, 4):
        lib.append(tuple((0, c) for c in range(k)))                # horizontal segment
        lib.append(tuple((r, 0) for r in range(k)))                # vertical segment
    return lib


def _components(cells):
    cells = set(cells)
    out = []
    while cells:
        seed = cells.pop()
        comp, stack = [seed], [seed]
        while stack:
            r, c = stack.pop()
            for n in ((r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)):
                if n in cells:
                    cells.remove(n)
                    comp.append(n)
                    stack.append(n)
        out.append(comp)
    return out


def _opening(grid, src, se):
    h, w = len(grid), len(grid[0])
    sh = max(r for r, _ in se) + 1
    sw = max(c for _, c in se) + 1
    hit = set()
    for r in range(h - sh + 1):
        for c in range(w - sw + 1):
            if all(grid[r + dr][c + dc] == src for dr, dc in se):
                for dr, dc in se:
                    hit.add((r + dr, c + dc))
    return hit


def _make(src, dst, se, mode):
    def fn(grid):
        opened = _opening(grid, src, se)
        out = [row[:] for row in grid]
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                if v != src:
                    continue
                inside = (r, c) in opened
                if (mode == 'open' and inside) or (mode == 'tophat' and not inside):
                    out[r][c] = dst
        return out
    return fn


def fam_morphological_opening(train):
    # colour roles from the diffs: exactly one source colour and one target colour
    srcs, dsts, changed = set(), set(), []
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            return
        cells = []
        for r, (ra, rb) in enumerate(zip(a, b)):
            for c, (x, y) in enumerate(zip(ra, rb)):
                if x != y:
                    srcs.add(x)
                    dsts.add(y)
                    cells.append((r, c))
        changed.append(cells)
    if len(srcs) != 1 or len(dsts) != 1:
        return
    src, dst = srcs.pop(), dsts.pop()

    # candidate structuring elements: declared library + observed changed-component shapes
    cands = []
    for se in _library():
        if se not in cands:
            cands.append(se)
    for cells in changed:
        for comp in _components(cells):
            se = _norm(comp)
            if len(se) <= 16 and se not in cands:
                cands.append(se)

    for mode in ('open', 'tophat'):
        for se in cands:
            fn = _make(src, dst, se, mode)
            if all(fn(p["input"]) == p["output"] for p in train):
                h = max(r for r, _ in se) + 1
                w = max(c for _, c in se) + 1
                yield ("morphology:%s[src=%d,dst=%d,se=%dx%d:%s]" % (
                    'opening' if mode == 'open' else 'tophat', src, dst, h, w,
                    ''.join('1' if (r, c) in se else '0' for r in range(h) for c in range(w))), 3, fn)
                return


FAMILIES = (fam_morphological_opening,)
