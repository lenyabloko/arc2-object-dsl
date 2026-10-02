"""Line expansion for a644e277: ruled grid, broken intersections mark a rectangle to crop (test-blind; train pairs only)."""
from collections import Counter
from itertools import combinations

CARD = "a644e277"
LINE = ("The grid is ruled by lines of one colour; the few line intersections that break the line colour "
        "mark the corners of a rectangle, and the output is that rectangle cropped out.")
READING = {
    "generator": "Find the full-length horizontal and vertical lines of one colour, locate the line crossings whose cells are not "
                 "that colour, and copy out the sub-grid whose corners are those broken crossings.",
    "stop": "Nothing is drawn beyond a single crop: it stops at the rows/columns of the outermost marked crossings "
            "(their line bands included, or excluded for the interior variant).",
    "params": "tol ∈ {0, 0.1} (fraction of off-crossing line cells allowed to deviate) · "
              "corners ∈ {exact4, maxrect, bbox} · crop ∈ {closed (crossings included), open (interior only)}",
    "participants": "line colour = per input, a colour whose majority rows and columns survive the fixed point "
                    "'row stays a line iff its cells off the line columns are the colour (and vice versa)'; "
                    "line bands = runs of adjacent line rows / columns; crossings = band x band blocks; "
                    "broken crossing = a block containing any cell not of the line colour.",
    "preconditions": "Each input has a line colour with at least one horizontal and one vertical line (not covering the whole grid); "
                     "the broken crossings determine a rectangle under the chosen corners mode; the output is that crop.",
}


def _bands(idx):
    out = []
    for i in sorted(idx):
        if out and out[-1][1] == i - 1:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [tuple(b) for b in out]


def _lines(g, L, tol):
    H, W = len(g), len(g[0])
    R = {r for r in range(H) if sum(1 for v in g[r] if v == L) * 2 > W}
    C = {c for c in range(W) if sum(1 for r in range(H) if g[r][c] == L) * 2 > H}
    while True:
        offc = [c for c in range(W) if c not in C]
        nR = set()
        for r in R:
            if not offc or sum(1 for c in offc if g[r][c] != L) <= tol * len(offc):
                nR.add(r)
        offr = [r for r in range(H) if r not in nR]
        nC = set()
        for c in C:
            if not offr or sum(1 for r in offr if g[r][c] != L) <= tol * len(offr):
                nC.add(c)
        if nR == R and nC == C:
            break
        R, C = nR, nC
    if not R or not C or len(R) == H or len(C) == W:
        return None
    return R, C


def _rect(B, mode, Rb, Cb):
    if not B:
        return None
    if mode == "exact4":
        I = sorted({i for i, _ in B}); J = sorted({j for _, j in B})
        if len(I) != 2 or len(J) != 2 or len(B) != 4:
            return None
        return I[0], I[1], J[0], J[1]
    if mode == "maxrect":
        I = sorted({i for i, _ in B}); J = sorted({j for _, j in B})
        best = None
        for i0, i1 in combinations(I, 2):
            for j0, j1 in combinations(J, 2):
                if all(p in B for p in ((i0, j0), (i0, j1), (i1, j0), (i1, j1))):
                    area = (Rb[i1][1] - Rb[i0][0] + 1) * (Cb[j1][1] - Cb[j0][0] + 1)
                    key = (-area, i0, j0, i1, j1)
                    if best is None or key < best[0]:
                        best = (key, (i0, i1, j0, j1))
        return best[1] if best else None
    # bbox
    I = [i for i, _ in B]; J = [j for _, j in B]
    return min(I), max(I), min(J), max(J)


def _solve(g, tol, corners, crop):
    H, W = len(g), len(g[0])
    cands = []
    for L in sorted(Counter(v for row in g for v in row)):
        st = _lines(g, L, tol)
        if st:
            cands.append((-(len(st[0]) + len(st[1])), L, st))
    cands.sort(key=lambda t: (t[0], t[1]))
    for _, L, (R, C) in cands:
        Rb, Cb = _bands(R), _bands(C)
        B = set()
        for i, (r0, r1) in enumerate(Rb):
            for j, (c0, c1) in enumerate(Cb):
                if any(g[r][c] != L for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)):
                    B.add((i, j))
        rc = _rect(B, corners, Rb, Cb)
        if rc is None:
            continue
        i0, i1, j0, j1 = rc
        if crop == "closed":
            ra, rb, ca, cb = Rb[i0][0], Rb[i1][1], Cb[j0][0], Cb[j1][1]
        else:
            ra, rb, ca, cb = Rb[i0][1] + 1, Rb[i1][0] - 1, Cb[j0][1] + 1, Cb[j1][0] - 1
        if ra > rb or ca > cb:
            continue
        return [list(g[r][ca:cb + 1]) for r in range(ra, rb + 1)]
    return None


def fam(train):
    if not train:
        return
    # precondition: every training input is ruled by lines of some colour
    for p in train:
        g = p["input"]
        if not any(_lines(g, L, 0.1) for L in {v for row in g for v in row}):
            return
    opts = []
    for tol, ct in ((0, 0), (0.1, 2)):
        for corners, cc in (("exact4", 0), ("maxrect", 1), ("bbox", 2)):
            for crop, kc in (("closed", 0), ("open", 1)):
                opts.append((10 + ct + cc + kc, tol, corners, crop))
    opts.sort(key=lambda t: t[0])
    for cost, tol, corners, crop in opts:
        def fn(grid, tol=tol, corners=corners, crop=crop):
            out = _solve(grid, tol, corners, crop)
            if out is None:
                raise ValueError("ruled-grid crop: preconditions fail")
            return out
        ok = True
        for p in train:
            try:
                if fn(p["input"]) != [list(r) for r in p["output"]]:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield ("ruled_crop[tol=%s,corners=%s,crop=%s]" % (tol, corners, crop), cost, fn)


FAMILIES = [fam]
