"""Line expansion for 995c5fa3: equal panels separated by empty lines; each panel's hole pattern names a colour
learned from the examples; output is one uniform row per panel, in panel order (test-blind; train pairs only)."""
from collections import Counter

CARD = "995c5fa3"
LINE = ("The input is a row of equal panels separated by empty columns; each panel's hole pattern stands for a colour "
        "(learned from the examples), and the output lists those colours as one uniformly coloured row per panel, "
        "in panel order.")
READING = {
    "generator": "Cut the input into its equal panels at the empty separator lines, look up each panel's hole pattern "
                 "in a pattern-to-colour table learned from the training pairs, and draw one line of that colour per "
                 "panel, stacked in panel order.",
    "stop": "One output line per panel; drawing stops after the last panel (output length = number of panels, "
            "line length from the induced width rule).",
    "params": "split ∈ {columns (row of panels, left-to-right), rows (column of panels, top-to-bottom)} · "
              "empty colour ∈ {colours that split every training input into ≥2 equal panels} · "
              "hole ∈ {cell = empty colour, cell ≠ panel's dominant non-empty colour} · "
              "key ∈ {hole mask, raw panel} · layout ∈ {one row per panel, one column per panel} · "
              "width ∈ {number of panels, constant learned from train, panel width, panel height} · "
              "unseen pattern → unique nearest learned pattern by Hamming distance (else fail)",
    "participants": "separator lines = full columns (or rows) entirely of the empty colour; panels = maximal runs of "
                    "the other columns (rows), each spanning the whole grid across; hole pattern = boolean mask of a "
                    "panel's hole cells; colour table = pattern → colour pairs read off the training outputs "
                    "(panel i ↔ output line i).",
    "preconditions": "Every training input splits into ≥2 equal-size panels by full empty lines; every training output "
                     "has one uniform line per panel; the same pattern never maps to two colours.",
}


def _runs(flags):
    out, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i - 1)); start = None
    if start is not None:
        out.append((start, len(flags) - 1))
    return out


def _panels(g, empty, split):
    """Return list of panels (each a list of rows) in panel order, or None if the split precondition fails."""
    if split == "rows":
        g = [list(r) for r in zip(*g)]          # work on columns of the transposed grid
    H, W = len(g), len(g[0])
    sep = [all(g[r][c] == empty for r in range(H)) for c in range(W)]
    if not any(sep):
        return None
    runs = _runs([not s for s in sep])
    if len(runs) < 2 or len({b - a for a, b in runs}) != 1:
        return None
    ps = []
    for a, b in runs:
        p = [list(g[r][a:b + 1]) for r in range(H)]
        if split == "rows":
            p = [list(r) for r in zip(*p)]       # back to original orientation
        ps.append(p)
    return ps


def _key(p, empty, hole, key):
    if key == "raw":
        return tuple(tuple(r) for r in p)
    if hole == "empty":
        return tuple(tuple(v == empty for v in r) for r in p)
    cnt = Counter(v for r in p for v in r if v != empty)
    if not cnt:
        return tuple(tuple(True for _ in r) for r in p)
    dom = min(cnt, key=lambda c: (-cnt[c], c))
    return tuple(tuple(v != dom for v in r) for r in p)


def _out_colours(o, n, layout):
    """Read the colour of each panel line from a training output; None if not one uniform line per panel."""
    lines = o if layout == "rows" else [list(r) for r in zip(*o)]
    if len(lines) != n or not lines or not lines[0]:
        return None
    cols = []
    for ln in lines:
        if len(set(ln)) != 1:
            return None
        cols.append(ln[0])
    return cols


def _width(mode, n, p, const):
    if mode == "npanels":
        return n
    if mode == "const":
        return const
    if mode == "panel_w":
        return len(p[0])
    return len(p)


def _lookup(table, k):
    if k in table:
        return table[k]
    best, bd, tie = None, None, False
    for kk, c in table.items():
        if len(kk) != len(k) or any(len(a) != len(b) for a, b in zip(kk, k)):
            continue
        d = sum(1 for a, b in zip(kk, k) for x, y in zip(a, b) if x != y)
        if bd is None or d < bd:
            best, bd, tie = c, d, False
        elif d == bd and c != best:
            tie = True
    if best is None or tie:
        raise ValueError("panel colours: unseen hole pattern")
    return best


def fam(train):
    if not train:
        return
    colours = sorted({v for p in train for r in p["input"] for v in r})
    opts = []
    for split, cs in (("columns", 0), ("rows", 1)):
        for empty in colours:
            pan = [_panels(p["input"], empty, split) for p in train]
            if any(x is None for x in pan):
                continue
            ce = 0 if empty == 0 else 1
            for hole, ch in (("empty", 0), ("dominant", 1)):
                for key, ck in (("mask", 0), ("raw", 2)):
                    if key == "raw" and hole != "empty":
                        continue
                    for layout, cl in (("rows", 0), ("cols", 1)):
                        table, ok, widths = {}, True, []
                        for p, ps in zip(train, pan):
                            oc = _out_colours(p["output"], len(ps), layout)
                            if oc is None:
                                ok = False; break
                            for q, c in zip(ps, oc):
                                k = _key(q, empty, hole, key)
                                if table.get(k, c) != c:
                                    ok = False; break
                                table[k] = c
                            if not ok:
                                break
                            o = p["output"]
                            widths.append(len(o[0]) if layout == "rows" else len(o))
                        if not ok:
                            continue
                        const = widths[0] if len(set(widths)) == 1 else None
                        for wm, cw in (("npanels", 0), ("const", 1), ("panel_w", 2), ("panel_h", 2)):
                            if wm == "const" and const is None:
                                continue
                            opts.append((10 + cs + ce + ch + ck + cl + cw, split, empty, hole, key, layout, wm,
                                         const, dict(table)))
    opts.sort(key=lambda t: t[:7])
    for cost, split, empty, hole, key, layout, wm, const, table in opts:
        def fn(grid, split=split, empty=empty, hole=hole, key=key, layout=layout, wm=wm, const=const, table=table):
            ps = _panels(grid, empty, split)
            if ps is None:
                raise ValueError("panel colours: input does not split into equal panels")
            n = len(ps)
            w = _width(wm, n, ps[0], const)
            rows = [[_lookup(table, _key(q, empty, hole, key))] * w for q in ps]
            if layout == "cols":
                rows = [list(r) for r in zip(*rows)]
            return rows
        ok = True
        for p in train:
            try:
                if fn(p["input"]) != [list(r) for r in p["output"]]:
                    ok = False; break
            except Exception:
                ok = False; break
        if ok:
            yield ("panel_colours[split=%s,empty=%d,hole=%s,key=%s,layout=%s,width=%s]"
                   % (split, empty, hole, key, layout, wm), cost, fn)


FAMILIES = [fam]
