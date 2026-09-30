"""Family for ARC task b0039139 -- concept: STENCIL PRINTING (a print run from a stencil; printing / graphics).

The input is a strip of panels separated by thin full-length divider lines (a legend / print order):
  * a STENCIL panel  -- a single figure on the panel background: the mask to be printed,
  * a TALLY panel    -- a number of separate marks: the number of impressions N (the print run),
  * an INK panel     -- a panel of one uniform colour: the colour laid through the stencil,
  * a PAPER panel    -- a panel of one uniform colour: the substrate / background of the print.
The output is the print run: N impressions of the stencil (cropped to its bounding box), inked where the stencil is
open and paper elsewhere, laid side by side along the strip's axis with a paper margin between impressions.

Roles, not colour numbers:
  divider  = the colour all of whose cells lie on full rows (or full columns) and whose lines cut the grid into the
             most panels (a uniform panel is also made of full lines, but it is one thick run at most);
  uniform panels (one colour) are ink / paper, the other two panels are stencil / tally;
  panel background = most common colour over the non-uniform panels;
  count = number of connected components of non-background cells in the tally panel.

Induced parameters (small finite domains):
  stencil_outer in {True, False} -- stencil is the non-uniform panel farther from (vs nearer to) the colour panels
  ink_inner     in {True, False} -- ink is the uniform panel nearer to (vs farther from) the stencil/tally panels
  (both are reading-direction free, so a reversed or rotated strip is read the same way)
  conn   in {4, 8}                  -- connectivity used to count tally marks
  axis   in {'along', 'across'}     -- impressions laid along the strip axis or across it
  gap    in {0, 1, 2}               -- paper margin between consecutive impressions
"""
from collections import Counter
from itertools import product


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _split_rows(g):
    """Find the divider colour among full rows; return list of row-panels (sub-grids) or None."""
    H = len(g)
    full = {}
    for r, row in enumerate(g):
        if len(set(row)) == 1:
            full.setdefault(row[0], []).append(r)
    best = None
    for c, rows in full.items():
        rows_set = set(rows)
        # every cell of colour c must lie on one of its full rows
        if any(v == c and r not in rows_set for r, row in enumerate(g) for v in row):
            continue
        panels, cur = [], []
        for r in range(H):
            if r in rows_set:
                if cur:
                    panels.append(cur)
                cur = []
            else:
                cur.append(g[r])
        if cur:
            panels.append(cur)
        # divider lines must be thin (runs of width 1)
        if any(r + 1 in rows_set for r in rows):
            continue
        if best is None or len(panels) > len(best[1]):
            best = (c, panels)
    return best


def _panels(g):
    """Return (axis, panels) with axis 'rows' (panels stacked vertically) or 'cols'; panels in row-major form."""
    a = _split_rows(g)
    b = _split_rows(_transpose(g))
    cands = []
    if a:
        cands.append((len(a[1]), 'rows', a[1]))
    if b:
        cands.append((len(b[1]), 'cols', [_transpose(p) for p in b[1]]))
    if not cands:
        return None
    cands.sort(key=lambda t: -t[0])
    n, axis, panels = cands[0]
    if n < 2:
        return None
    return axis, panels


def _uniform(p):
    return len({v for row in p for v in row}) == 1


def _components(cells, conn):
    cells = set(cells)
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    seen, n = set(), 0
    for s in cells:
        if s in seen:
            continue
        n += 1
        stack = [s]
        seen.add(s)
        while stack:
            r, c = stack.pop()
            for dr, dc in nb:
                q = (r + dr, c + dc)
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
    return n


def _make(stencil_outer, ink_inner, conn, axis_mode, gap):
    def fn(g):
        res = _panels(g)
        if res is None:
            return None
        axis, panels = res
        ui = [i for i, p in enumerate(panels) if _uniform(p)]
        ni = [i for i, p in enumerate(panels) if not _uniform(p)]
        if len(ui) != 2 or len(ni) != 2:
            return None
        # order each pair by distance from the other pair (inner = nearer), so a reversed strip reads the same
        cu, cn = sum(ui) / 2.0, sum(ni) / 2.0
        ni.sort(key=lambda i: -abs(i - cu))      # outer non-uniform panel first
        ui.sort(key=lambda i: abs(i - cn))       # inner uniform panel first
        stencil_p, tally_p = [panels[i] for i in (ni if stencil_outer else ni[::-1])]
        ink_p, paper_p = [panels[i] for i in (ui if ink_inner else ui[::-1])]
        ink, paper = ink_p[0][0], paper_p[0][0]
        bg = Counter(v for p in (stencil_p, tally_p) for row in p for v in row).most_common(1)[0][0]
        open_cells = [(r, c) for r, row in enumerate(stencil_p) for c, v in enumerate(row) if v != bg]
        marks = [(r, c) for r, row in enumerate(tally_p) for c, v in enumerate(row) if v != bg]
        if not open_cells or not marks:
            return None
        r0 = min(r for r, _ in open_cells); r1 = max(r for r, _ in open_cells)
        c0 = min(c for _, c in open_cells); c1 = max(c for _, c in open_cells)
        oc = set(open_cells)
        imp = [[ink if (r, c) in oc else paper for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
        n = _components(marks, conn)
        vertical = (axis == 'rows') == (axis_mode == 'along')
        h, w = len(imp), len(imp[0])
        if vertical:
            out = []
            for k in range(n):
                if k:
                    out += [[paper] * w for _ in range(gap)]
                out += [row[:] for row in imp]
        else:
            out = []
            for row in imp:
                line = []
                for k in range(n):
                    if k:
                        line += [paper] * gap
                    line += row
                out.append(line)
        return out
    return fn


def fam_stencil_print(train):
    for fs, fi, conn, ax, gap in product((True, False), (True, False), (4, 8), ('along', 'across'), (1, 0, 2)):
        fn = _make(fs, fi, conn, ax, gap)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("printing:stencil_print[stencil_outer=%s,ink_inner=%s,conn=%d,axis=%s,gap=%d]"
                   % (fs, fi, conn, ax, gap), 3, fn)
            return


FAMILIES = (fam_stencil_print,)
