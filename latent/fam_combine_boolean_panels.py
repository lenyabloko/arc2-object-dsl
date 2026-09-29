"""combine.boolean_panels (+ combine.region_select_panels): per-cell table over aligned source panels.

A grid yields k aligned "source" layers (separator panels, equal halves/thirds, or the grid and one of its
mirrors).  Every output cell is a function T(key) of the corresponding source cells, where the key is
  bits   : which sources are foreground at that cell (boolean combination, k<=3), or
  region : which side of a divider drawn in the first source the cell lies on (divider / marker side / other).
T maps each key to one value option induced from the training pairs:
  copy source i | source i overlaid on source j | a constant output colour.
Output placement: the panel itself, or the input with its single blank panel filled in.
Background: one task-level colour (most frequent over all training sources) or per grid.

Why gdsl.fam_panels misses these tasks: it takes bg_of(whole grid) per grid, which flips to the ink colour
whenever ink outnumbers background in some pair (fafffa47, 1b2d62fb, 94f9d214, ...); it only allows a constant
"on" colour (not copy/overlay per key, d47aa2ff) and never pairs a grid with its own mirror (ce039d91, a8610ef7).
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
import gdsl
from gdsl import H, W, colours, split_panels

MIRRORS = {"fh": gdsl.fh, "fv": gdsl.fv, "r180": gdsl.r180, "T": gdsl.T, "aT": gdsl.at}


def _cut(g, axis, k):
    h, w = H(g), W(g)
    if axis == "LR":
        if w % k or w // k < 2: return None
        s = w // k; return [[r[i * s:(i + 1) * s] for r in g] for i in range(k)]
    if h % k or h // k < 2: return None
    s = h // k; return [g[i * s:(i + 1) * s] for i in range(k)]


def _uniform(p): return len(colours(p)) == 1


def sources(g, mode):
    """-> (list of source layers, target index or None).  target = index of the blank panel to fill."""
    kind = mode[0]
    if kind == "sep":
        sp = split_panels(g)
        if not sp: return None
        ps = sp[0]
        if mode[1] == "fill":
            blank = [i for i, p in enumerate(ps) if _uniform(p)]
            if len(blank) != 1 or len(ps) < 3: return None
            return [p for i, p in enumerate(ps) if i != blank[0]], blank[0]
        return ps, None
    if kind == "cut":
        ps = _cut(g, mode[1], mode[2]); return (ps, None) if ps else None
    if kind == "mirror":
        if mode[1] in ("T", "aT") and H(g) != W(g): return None
        return [g, MIRRORS[mode[1]](g)], None
    return None


def place_fill(g, panel):
    """Write panel into the blank separator panel of g."""
    sp = split_panels(g)
    h, w = H(g), W(g); sc = sp[1]
    rows = [-1] + [r for r in range(h) if all(v == sc for v in g[r])] + [h]
    cols = [-1] + [c for c in range(w) if all(g[r][c] == sc for r in range(h))] + [w]
    out = [r[:] for r in g]
    for a in range(len(rows) - 1):
        for b in range(len(cols) - 1):
            y0, y1, x0, x1 = rows[a] + 1, rows[a + 1], cols[b] + 1, cols[b + 1]
            if y1 - y0 < 2 or x1 - x0 < 2: continue
            if len({g[y][x] for y in range(y0, y1) for x in range(x0, x1)}) == 1:
                for y in range(y0, y1):
                    for x in range(x0, x1): out[y][x] = panel[y - y0][x - x0]
                return out
    return None


# ---------------------------------------------------------------- per-cell keys
def keys_bits(ps, bg):
    return [[tuple(int(p[y][x] != bg) for p in ps) for x in range(W(ps[0]))] for y in range(H(ps[0]))]


def keys_region(ps, bg):
    """Divider = largest 8-connected ink component of source 0; other ink = markers.
    Cells not on the divider split into 4-connected regions; regions holding a marker -> 'A', others -> 'B'."""
    m = ps[0]; h, w = H(m), W(m)
    comps = gdsl.objects(m, bg, diag=True, by_colour=False)
    if len(comps) < 2: return None
    comps.sort(key=len, reverse=True)
    if len(comps[0]) == len(comps[1]): return None
    div = set(comps[0]); marks = {c for cc in comps[1:] for c in cc}
    lab = [[None] * w for _ in range(h)]
    for y, x in div: lab[y][x] = "D"
    seen = set(div); nA = nB = 0
    for sy in range(h):
        for sx in range(w):
            if (sy, sx) in seen: continue
            st, comp = [(sy, sx)], []; seen.add((sy, sx))
            while st:
                y, x = st.pop(); comp.append((y, x))
                for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                    if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen:
                        seen.add((yy, xx)); st.append((yy, xx))
            t = "A" if any(c in marks for c in comp) else "B"
            nA += t == "A"; nB += t == "B"
            for y, x in comp: lab[y][x] = t
    if not nA or not nB: return None
    return lab


FEATURES = {"bits": keys_bits, "region": keys_region}


def value(opt, ps, bg, y, x):
    if opt[0] == "copy": return ps[opt[1]][y][x]
    if opt[0] == "over":
        v = ps[opt[1]][y][x]; return v if v != bg else ps[opt[2]][y][x]
    return opt[1]


def options(k, feat, out_cols):
    lo = 1 if feat == "region" else 0          # region: source 0 is the mask, values come from the rest
    ops = [("copy", i) for i in range(lo, k)]
    ops += [("over", i, j) for i in range(lo, k) for j in range(lo, k) if i != j]
    ops += [("const", c) for c in sorted(out_cols)]
    return ops


def grid_bg(ps):
    return Counter(v for p in ps for r in p for v in r).most_common(1)[0][0]


def induce(train, mode, feat, bgpol):
    data = []
    for p in train:
        s = sources(p["input"], mode)
        if not s: return None
        ps, tgt = s
        o = p["output"]
        if tgt is None:
            tgt_out = o
        else:
            if (H(o), W(o)) != (H(p["input"]), W(p["input"])): return None
            so = split_panels(o)
            if not so or len(so[0]) != len(ps) + 1: return None
            tgt_out = so[0][tgt]
        if any((H(q), W(q)) != (H(tgt_out), W(tgt_out)) for q in ps): return None
        if feat == "bits" and len(ps) > 3: return None
        if feat == "region" and len(ps) < 3: return None
        data.append((ps, tgt_out))
    if bgpol == "task":
        pooled = Counter(v for ps, _ in data for q in ps for r in q for v in r)
        bg = pooled.most_common(1)[0][0]
        if not all(any(bg in colours(q) for q in ps) for ps, _ in data): return None
    k = len(data[0][0])
    if any(len(ps) != k for ps, _ in data): return None
    out_cols = set.intersection(*[colours(o) for _, o in data]) | {v for _, o in data for r in o for v in r}
    cand = {}
    for ps, o in data:
        b = bg if bgpol == "task" else grid_bg(ps)
        ks = FEATURES[feat](ps, b)
        if ks is None: return None
        for y in range(H(o)):
            for x in range(W(o)):
                key = ks[y][x]
                if key not in cand: cand[key] = options(k, feat, out_cols)
                cand[key] = [op for op in cand[key] if value(op, ps, b, y, x) == o[y][x]]
                if not cand[key]: return None
    table = {key: ops[0] for key, ops in cand.items()}
    # reject trivial tables: every key copies the same source (output == a source)
    if len({v for v in table.values()}) == 1 and table[next(iter(table))][0] == "copy": return None
    return table, (bg if bgpol == "task" else None), k


def make(mode, feat, table, tbg, k):
    def fn(g):
        s = sources(g, mode)
        if not s: return None
        ps, tgt = s
        if len(ps) != k or any((H(q), W(q)) != (H(ps[0]), W(ps[0])) for q in ps): return None
        b = tbg if tbg is not None else grid_bg(ps)
        ks = FEATURES[feat](ps, b)
        if ks is None: return None
        out = []
        for y in range(H(ps[0])):
            row = []
            for x in range(W(ps[0])):
                op = table.get(ks[y][x])
                if op is None: return None
                row.append(value(op, ps, b, y, x))
            out.append(row)
        return out if tgt is None else place_fill(g, out)
    return fn


MODES = [("sep", "all"), ("sep", "fill")] + [("cut", a, k) for a in ("LR", "TB") for k in (2, 3)] + \
        [("mirror", m) for m in MIRRORS]


def fam_panel_table(train):
    i, o = train[0]["input"], train[0]["output"]
    same = (H(i), W(i)) == (H(o), W(o))
    for mode in MODES:
        if mode == ("sep", "fill") or mode[0] == "mirror":
            if not same: continue
        elif same: continue
        for feat in ("bits", "region"):
            seen = set()
            for bgpol in ("task", "grid"):
                r = induce(train, mode, feat, bgpol)
                if not r: continue
                table, tbg, k = r
                sig = str(sorted(table.items()))
                if sig in seen: continue
                seen.add(sig)
                cost = 3 + (feat == "region") + (bgpol == "grid") + (len(table) > 4)
                name = f"panel-table[{':'.join(map(str, mode))},{feat},bg={bgpol}]"
                yield (name, cost, make(mode, feat, table, tbg, k))


FAMILIES = (fam_panel_table,)
