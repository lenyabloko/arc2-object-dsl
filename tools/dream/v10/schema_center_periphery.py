"""CENTER-PERIPHERY image schema of the v10 description lattice (Fable guidance v10).

Synthetic only: menus were read off the parsed description records (results/o0/v10_records.json, schema ==
"CENTER-PERIPHERY"); no ARC task or solution file is used here.

A *generator* (full spec) assigns every dimension in DIMS (irrelevant ones are None).  A *node* is a partial
assignment {dim: value}; its completions are the full specs that agree with it.  key(node) is the closure of the
node (every dimension on which all completions agree), so two nodes with the same completion set get the same key.
Functionally identical specs were removed from the spec space (e.g. stamp(plus,k=1) at singletons == halo(manhattan,
k=1) at singletons), so equal generators have one spec.

Generator verbs (record verbs they cover):
  halo   paint background cells at distance 1..k from each centre       (ring, outline, inflate, surround, frame)
  rings  paint every reachable background cell by ring index d (period P) (continue, band, revolve, recolour)
  stamp  paint a fixed stencil (plus | x | box) around each anchor       (stamp, decorate, mark)
  centre paint the centre cell of odd-sized objects                     (paint)
  inset  recolour the inner concentric rings of solid rectangles        (draw, nest, revolve)
Colour rules: literal (one fitted constant), source (colour of the centre), sequence (one fitted constant per ring /
stencil offset).  Stops: thickness (fixed k), count (k = number of dots), obstacle (geodesic, blocked by objects),
border (to the grid edge), none (fixed stencil), innermost (to the core of the rectangle).

family(node)(train) yields (name, cost, fn) for every completion of the node whose free colours fit all training
pairs, cheapest first; fn(grid) returns the predicted grid or None when the program's preconditions fail.
"""
import random
import zlib
from collections import deque

SCHEMA = "CENTER-PERIPHERY"
BG = 0
DIMS = ("verb", "stop", "centre", "metric", "k", "period", "stencil", "colour", "erase")

MENU = {
    "verb": ["halo", "rings", "stamp", "centre", "inset"],
    "stop": ["thickness", "count", "obstacle", "border", "none", "innermost"],
    "centre": ["object", "singleton", "largest", "smallest", "unique_colour", "canvas", "midpoint", "crossing"],
    "metric": ["cheb", "manhattan"],
    "k": [1, 2, 3],
    "period": [1, 2, 3],
    "stencil": ["plus", "x", "box"],
    "colour": ["literal", "source", "sequence"],
    "erase": [False, True],
}

# Where each menu value comes from in the parsed records (documentation; not used by the code).
MENU_SOURCES = {
    "verb": {"halo": "ring | outline | inflate | surround | frame (grp_M059, grp_M129, oo_db93a21d, "
                     "pc_distance_rings_halo, oo_67a423a3, oo_52fd389e)",
             "rings": "continue | band | revolve | recolour (oo_f8c80d96, d2_13e47133, d2_45a5af55, grp_M014, "
                      "oo_5c2c9af4)",
             "stamp": "stamp | decorate | mark (grp_M081, grp_M004, oo_e9614598, pc_stamp_stencil_at_anchors)",
             "centre": "paint centre of odd square (oo_22806e14)",
             "inset": "concentric inner rings / nest (oo_8cb8642d, grp_M015, d2_45a5af55)"},
    "stop": {"thickness": "other:thickness_k | other:radius r", "count": "count (oo_52fd389e)",
             "obstacle": "obstacle | other:mask (d2_13e47133, grp_M014)", "border": "border",
             "none": "none (fixed stencil)", "innermost": "other:innermost ring (oo_8cb8642d)"},
    "centre": {"object": "object (balloon) | object", "singleton": "seed cell | single seed pixel | marker pixel",
               "largest": "solid rectangle with dots (largest object)", "smallest": "smallest object",
               "unique_colour": "unique-colour seed (grp_M004 select)",
               "canvas": "canvas border | grid border | room boundary",
               "midpoint": "midpoint of 2 markers | pair midpoint", "crossing": "line crossing | intersection"},
    "metric": "chebyshev | manhattan",
    "k": "k 1..5, radius 1..2, distance 1..3, thickness 1..4 (finite cut 1..3)",
    "period": "period 2..4, step 1..5 (finite cut 1..3)",
    "stencil": "plus | diagonals | 3x3 ring (box)",
    "colour": "literal | source (incl. context) | sequence (incl. table)",
    "erase": "erase_seed true | false",
}

# Nodes removed after the self-test (keys); their specialisations are removed too.
PRUNED = ()

N8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ----------------------------------------------------------------------------------------------- spec space
def _mk(**kw):
    return tuple(kw.get(d) for d in DIMS)


def _build_specs():
    out = []
    # halo
    for cen in ("object", "singleton", "largest", "smallest", "unique_colour", "canvas"):
        metrics = (None,) if cen == "canvas" else ("cheb", "manhattan")
        stops = [("thickness", k) for k in (1, 2, 3)]
        if cen in ("singleton", "largest", "smallest", "unique_colour"):
            stops += [("obstacle", k) for k in (2, 3)]      # obstacle k=1 == thickness k=1
        if cen == "largest":
            stops += [("count", None)]
        for m in metrics:
            for stop, k in stops:
                for col in ("literal", "source", "sequence"):
                    if col == "sequence" and k == 1:
                        continue                              # == literal
                    for er in (False, True):
                        out.append(_mk(verb="halo", stop=stop, centre=cen, metric=m, k=k, colour=col, erase=er))
    # rings
    for cen in ("object", "singleton", "largest", "canvas"):
        metrics = (None,) if cen == "canvas" else ("cheb", "manhattan")
        stops = ["border"] + (["obstacle"] if cen in ("singleton", "largest", "canvas") else [])
        erases = (False, True) if cen in ("singleton", "canvas") else (False,)
        for m in metrics:
            for stop in stops:
                for p in (2, 3):
                    for col in ("literal", "source", "sequence"):
                        for er in erases:
                            out.append(_mk(verb="rings", stop=stop, centre=cen, metric=m, period=p, colour=col,
                                           erase=er))
    # stamp
    for cen in ("singleton", "midpoint", "crossing"):
        erases = (False, True) if cen == "singleton" else (False,)
        for st in ("plus", "x", "box"):
            for k in (1, 2):
                if cen == "crossing" and (st == "plus" or (st == "box" and k == 1)):
                    continue                                  # nothing painted / == x k=1 on bg
                for col in ("literal", "source", "sequence"):
                    for er in erases:
                        if (cen == "singleton" and st in ("plus", "box") and k == 1 and not er
                                and col in ("literal", "source")):
                            continue                          # == halo(manhattan|cheb, k=1)
                        out.append(_mk(verb="stamp", stop="none", centre=cen, k=k, stencil=st, colour=col,
                                       erase=er))
    # centre
    for cen in ("object", "largest", "smallest"):
        out.append(_mk(verb="centre", stop="none", centre=cen, colour="literal", erase=False))
    # inset
    for cen in ("object", "largest", "smallest"):
        for p in (1, 2, 3):
            for col in ("literal", "sequence"):
                if col == "sequence" and p == 1:
                    continue
                out.append(_mk(verb="inset", stop="innermost", centre=cen, period=p, colour=col, erase=False))
    return out


SPECS = _build_specs()
_IDX = {d: i for i, d in enumerate(DIMS)}


class _S(object):
    """attribute view of a spec tuple"""
    __slots__ = DIMS + ("t",)

    def __init__(self, t):
        self.t = t
        for d, v in zip(DIMS, t):
            setattr(self, d, v)


def _stencil(st, k):
    if st == "plus":
        offs = [(dr * d, dc * d) for d in range(1, k + 1) for dr, dc in N4]
    elif st == "x":
        offs = [(dr * d, dc * d) for d in range(1, k + 1) for dr, dc in ((-1, -1), (-1, 1), (1, -1), (1, 1))]
    else:
        offs = [(dr, dc) for dr in range(-k, k + 1) for dc in range(-k, k + 1) if max(abs(dr), abs(dc)) == k]
    return sorted(offs)


def _nslots(s):
    if s.colour != "sequence":
        return 1
    if s.verb == "halo":
        return 3 if s.stop == "count" else s.k
    if s.verb in ("rings", "inset"):
        return s.period
    if s.verb == "stamp":
        return len(_stencil(s.stencil, s.k))
    return 1


_VCOST = {"halo": 1.0, "stamp": 1.0, "centre": 1.0, "rings": 1.5, "inset": 1.5}
_CCOST = {"object": 0.0, "singleton": 0.1, "canvas": 0.2, "largest": 0.3, "smallest": 0.3, "unique_colour": 0.4,
          "midpoint": 0.3, "crossing": 0.3}


def _cost(t):
    s = _S(t)
    c = _VCOST[s.verb] + _CCOST[s.centre]
    c += 0.05 if s.metric == "manhattan" else 0.0
    c += {"count": 0.3, "obstacle": 0.2}.get(s.stop, 0.0)
    c += 0.1 * (s.k or 0) + 0.1 * (s.period or 0)
    c += {"source": 0.0, "literal": 0.5, "sequence": 0.5 * _nslots(s)}[s.colour]
    c += 0.3 if s.erase else 0.0
    return round(c, 3)


# ----------------------------------------------------------------------------------------------- lattice
_COMP_CACHE = {}


def _choices(node):
    return tuple(sorted((d, node[d]) for d in node if d in _IDX))


def completions(node):
    ch = _choices(node)
    r = _COMP_CACHE.get(ch)
    if r is None:
        r = [t for t in SPECS if all(t[_IDX[d]] == v for d, v in ch)]
        r.sort(key=lambda t: (_cost(t), repr(t)))
        _COMP_CACHE[ch] = r
    return r


def _closure(node):
    comps = completions(node)
    if not comps:
        return None
    cl = []
    for i, d in enumerate(DIMS):
        vals = set(t[i] for t in comps)
        if len(vals) == 1:
            v = vals.pop()
            if v is not None:
                cl.append((d, v))
    return cl


def key(node):
    cl = _closure(node)
    if cl is None:
        return SCHEMA + "|EMPTY|" + ";".join("%s=%s" % dv for dv in _choices(node))
    return SCHEMA + "|" + ";".join("%s=%s" % dv for dv in cl)


def _pruned_closures():
    out = []
    for k in PRUNED:
        body = k.split("|", 1)[1]
        out.append(set(body.split(";")) if body else set())
    return out


_NODES = None


def nodes():
    """root + every depth-1 and depth-2 specialisation (one choice per dimension), deduplicated by key."""
    global _NODES
    if _NODES is not None:
        return [dict(n) for n in _NODES]
    items = [(d, v) for d in DIMS for v in MENU[d]]
    cands = [{}] + [{d: v} for d, v in items]
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i][0] != items[j][0]:
                cands.append({items[i][0]: items[i][1], items[j][0]: items[j][1]})
    pr = _pruned_closures()
    seen, res = set(), []
    for n in cands:
        if not completions(n):
            continue
        kk = key(n)
        if kk in seen:
            continue
        seen.add(kk)
        cl = set(kk.split("|", 1)[1].split(";")) if kk.split("|", 1)[1] else set()
        if any(p <= cl for p in pr):
            continue
        res.append(n)
    _NODES = res
    return [dict(n) for n in res]


# ----------------------------------------------------------------------------------------------- grid analysis
def _objects(g):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    objs = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != BG and not seen[r][c]:
                col = g[r][c]
                st = [(r, c)]
                seen[r][c] = True
                cells = []
                while st:
                    y, x = st.pop()
                    cells.append((y, x))
                    for dy, dx in N8:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] == col:
                            seen[ny][nx] = True
                            st.append((ny, nx))
                cells.sort()
                rs = [p[0] for p in cells]
                cs = [p[1] for p in cells]
                objs.append({"colour": col, "cells": cells, "size": len(cells),
                             "box": (min(rs), min(cs), max(rs), max(cs))})
    return objs


class _Ctx(object):
    def __init__(self, g, o=None):
        self.g, self.o = g, o
        self.H, self.W = len(g), len(g[0])
        self._objs = None
        self._sel = {}
        self._fld = {}
        if o is not None:
            p, e, rc = set(), set(), set()
            for r in range(self.H):
                gr, orow = g[r], o[r]
                for c in range(self.W):
                    a, b = gr[c], orow[c]
                    if a != b:
                        if a == BG:
                            p.add((r, c))
                        elif b == BG:
                            e.add((r, c))
                        else:
                            rc.add((r, c))
            self.painted, self.erased, self.recol = p, e, rc

    def objs(self):
        if self._objs is None:
            self._objs = _objects(self.g)
        return self._objs

    def select(self, cen):
        if cen in self._sel:
            return self._sel[cen]
        ob = self.objs()
        r = None
        if cen == "object":
            r = list(ob) or None
        elif cen == "singleton":
            r = [o for o in ob if o["size"] == 1] or None
        elif cen in ("largest", "smallest"):
            if ob:
                sz = [o["size"] for o in ob]
                v = max(sz) if cen == "largest" else min(sz)
                if sz.count(v) == 1:
                    r = [ob[sz.index(v)]]
        elif cen == "unique_colour":
            cnt = {}
            for o in ob:
                cnt[o["colour"]] = cnt.get(o["colour"], 0) + 1
            u = [o for o in ob if cnt[o["colour"]] == 1]
            if len(u) == 1 and len(ob) > 1:
                r = u
        elif cen == "canvas":
            # the canvas edge is the centre; its colour / erasable seed are the singleton cells (one colour)
            seeds = [o for o in ob if o["size"] == 1]
            cols = set(o["colour"] for o in seeds)
            col = cols.pop() if len(cols) == 1 else None
            r = [{"colour": col, "cells": [o["cells"][0] for o in seeds], "size": len(seeds), "box": None}]
        self._sel[cen] = r
        return r

    def field(self, cen, metric, obstacle):
        """levels: {d: [(cell, label)]} for background cells at distance d >= 1; cols[label] = colour."""
        kk = (cen, metric, obstacle)
        if kk in self._fld:
            return self._fld[kk]
        g, H, W = self.g, self.H, self.W
        cs = self.select(cen)
        if cs is None:
            self._fld[kk] = None
            return None
        levels = {}
        if cen == "canvas":
            if not obstacle:
                for r in range(H):
                    for c in range(W):
                        if g[r][c] == BG:
                            d = min(r, c, H - 1 - r, W - 1 - c) + 1
                            levels.setdefault(d, []).append(((r, c), 0))
                res = (levels, [cs[0]["colour"]])
                self._fld[kk] = res
                return res
            dist = [[-1] * W for _ in range(H)]
            q = deque()
            for r in range(H):
                for c in range(W):
                    if (r in (0, H - 1) or c in (0, W - 1)) and g[r][c] == BG:
                        dist[r][c] = 1
                        q.append((r, c))
            lab = None
            nb = N8
        else:
            dist = [[-1] * W for _ in range(H)]
            lab = [[-1] * W for _ in range(H)]
            q = deque()
            for i, ob in enumerate(cs):
                for (r, c) in ob["cells"]:
                    if dist[r][c] < 0:
                        dist[r][c] = 0
                        lab[r][c] = i
                        q.append((r, c))
            nb = N8 if metric == "cheb" else N4
        while q:
            r, c = q.popleft()
            d = dist[r][c] + 1
            l = lab[r][c] if lab is not None else 0
            for dr, dc in nb:
                nr, nc = r + dr, c + dc
                if 0 <= nr < H and 0 <= nc < W and dist[nr][nc] < 0:
                    if obstacle and g[nr][nc] != BG:
                        continue
                    dist[nr][nc] = d
                    if lab is not None:
                        lab[nr][nc] = l
                    q.append((nr, nc))
        for r in range(H):
            dr_, gr = dist[r], g[r]
            for c in range(W):
                d = dr_[c]
                if d > 0 and gr[c] == BG:
                    levels.setdefault(d, []).append(((r, c), lab[r][c] if lab is not None else 0))
        res = (levels, [o["colour"] for o in cs])
        self._fld[kk] = res
        return res


# ----------------------------------------------------------------------------------------------- generators
def _ins_halo(ctx, s):
    cs = ctx.select(s.centre)
    if cs is None:
        return None
    if s.stop == "count":
        k = sum(1 for o in ctx.objs() if o["size"] == 1 and o is not cs[0])
        if k == 0:
            return None
    else:
        k = s.k
    fld = ctx.field(s.centre, s.metric, s.stop == "obstacle")
    if fld is None:
        return None
    levels, cols = fld
    paint = []
    for d in range(1, k + 1):
        for cell, l in levels.get(d, ()):
            paint.append((cell, d - 1, cols[l]))
    erase = [cell for o in cs for cell in o["cells"]] if s.erase else []
    return paint, erase


def _ins_rings(ctx, s):
    cs = ctx.select(s.centre)
    if cs is None or (s.centre == "canvas" and s.erase and not cs[0]["cells"]):
        return None
    fld = ctx.field(s.centre, s.metric, s.stop == "obstacle")
    if fld is None:
        return None
    levels, cols = fld
    P = s.period
    seq = s.colour == "sequence"
    paint = []
    for d in sorted(levels):
        if seq:
            slot = (d - 1) % P
        elif d % P:
            continue
        else:
            slot = 0
        for cell, l in levels[d]:
            paint.append((cell, slot, cols[l]))
    erase = [cell for o in cs for cell in o["cells"]] if s.erase else []
    return paint, erase


def _anchors(ctx, cen):
    g = ctx.g
    if cen == "singleton":
        cs = ctx.select("singleton")
        return [(o["cells"][0], o["colour"]) for o in cs] if cs else None
    if cen == "midpoint":
        by = {}
        for o in ctx.objs():
            if o["size"] == 1:
                by.setdefault(o["colour"], []).append(o["cells"][0])
        res = []
        for col in sorted(by):
            p = by[col]
            if len(p) == 2 and (p[0][0] + p[1][0]) % 2 == 0 and (p[0][1] + p[1][1]) % 2 == 0:
                res.append((((p[0][0] + p[1][0]) // 2, (p[0][1] + p[1][1]) // 2), col))
        return res or None
    if cen == "crossing":
        rows = [r for r in range(ctx.H) if all(v != BG for v in g[r])]
        cols = [c for c in range(ctx.W) if all(g[r][c] != BG for r in range(ctx.H))]
        if not rows or not cols or len(rows) == ctx.H or len(cols) == ctx.W:
            return None
        return [((r, c), g[r][c]) for r in rows for c in cols]
    return None


def _ins_stamp(ctx, s):
    an = _anchors(ctx, s.centre)
    if an is None:
        return None
    offs = _stencil(s.stencil, s.k)
    g, H, W = ctx.g, ctx.H, ctx.W
    painted = {}
    for (ar, ac), col in an:
        for i, (dr, dc) in enumerate(offs):
            r, c = ar + dr, ac + dc
            if 0 <= r < H and 0 <= c < W and g[r][c] == BG and (r, c) not in painted:
                painted[(r, c)] = (i, col)
    paint = [(cell, i, col) for cell, (i, col) in painted.items()]
    erase = [a for a, _ in an] if s.erase else []
    return paint, erase


def _ins_centre(ctx, s):
    cs = ctx.select(s.centre)
    if cs is None:
        return None
    paint = []
    for o in cs:
        r0, c0, r1, c1 = o["box"]
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if h % 2 and w % 2 and (h > 1 or w > 1):
            cell = (r0 + h // 2, c0 + w // 2)
            if ctx.g[cell[0]][cell[1]] == o["colour"] and cell in set(o["cells"]):
                paint.append((cell, 0, o["colour"]))
    return paint, []


def _ins_inset(ctx, s):
    cs = ctx.select(s.centre)
    if cs is None:
        return None
    P = s.period
    seq = s.colour == "sequence"
    paint = []
    for o in cs:
        r0, c0, r1, c1 = o["box"]
        if o["size"] != (r1 - r0 + 1) * (c1 - c0 + 1):
            continue                                          # solid rectangles only
        for (r, c) in o["cells"]:
            d = min(r - r0, r1 - r, c - c0, c1 - c) + 1
            if d < 2:
                continue
            if seq:
                paint.append(((r, c), (d - 2) % P, o["colour"]))
            elif (d - 1) % P == 0:
                paint.append(((r, c), 0, o["colour"]))
    return paint, []


_INS = {"halo": _ins_halo, "rings": _ins_rings, "stamp": _ins_stamp, "centre": _ins_centre, "inset": _ins_inset}
_RECOLOUR = ("centre", "inset")


def _apply(s, table, g):
    ctx = _Ctx(g)
    ins = _INS[s.verb](ctx, s)
    if ins is None:
        return None
    paint, erase = ins
    out = [row[:] for row in g]
    for (r, c) in erase:
        out[r][c] = BG
    mode = s.colour
    for (r, c), slot, src in paint:
        if mode == "source":
            col = src
        elif mode == "literal":
            col = table["C"]
        else:
            col = table["pal"].get(slot)
        if col is None:
            return None
        out[r][c] = col
    return out


def _fit(s, ctxs):
    mode = s.colour
    C = None
    pal = {}
    rec = s.verb in _RECOLOUR
    for ctx in ctxs:
        ins = _INS[s.verb](ctx, s)
        if ins is None:
            return None
        paint, erase = ins
        target = ctx.recol if rec else ctx.painted
        if len(paint) != len(target):
            return None
        for cell, _, _ in paint:
            if cell not in target:
                return None
        if not rec:
            if len(erase) != len(ctx.erased) or (erase and set(erase) != ctx.erased):
                return None
        o = ctx.o
        for (r, c), slot, src in paint:
            v = o[r][c]
            if mode == "source":
                if v != src:
                    return None
            elif mode == "literal":
                if C is None:
                    C = v
                elif v != C:
                    return None
            else:
                pv = pal.get(slot)
                if pv is None:
                    pal[slot] = v
                elif pv != v:
                    return None
    if mode == "sequence" and len(set(pal.values())) < 2:
        return None                                           # a constant palette is the literal program
    return {"C": C, "pal": pal}


def _spec_name(t, table=None):
    parts = ["%s=%s" % (d, v) for d, v in zip(DIMS, t) if v is not None]
    if table is not None:
        if table.get("C") is not None:
            parts.append("C=%d" % table["C"])
        if table.get("pal"):
            parts.append("pal=" + ",".join("%d:%d" % kv for kv in sorted(table["pal"].items())))
    return "CP[" + ";".join(parts) + "]"


def _pairs(train):
    out = []
    for p in train:
        if isinstance(p, dict):
            out.append((p["input"], p["output"]))
        else:
            out.append((p[0], p[1]))
    return out


def family(node):
    specs = completions(node)

    def fam(train):
        pairs = _pairs(train)
        if not pairs or not specs:
            return
        for i, o in pairs:
            if not i or not o or len(i) != len(o) or len(i[0]) != len(o[0]):
                return                                        # every generator here keeps the grid shape
        ctxs = [_Ctx(i, o) for i, o in pairs]
        if any(not (c.painted or c.erased or c.recol) for c in ctxs):
            return                                            # identity pair: nothing to explain
        paint_ok = all(not c.recol for c in ctxs)
        recol_ok = all(not c.painted and not c.erased for c in ctxs)
        if not paint_ok and not recol_ok:
            return
        for t in specs:
            s = _S(t)
            rec = s.verb in _RECOLOUR
            if (rec and not recol_ok) or (not rec and not paint_ok):
                continue
            if not s.erase and not rec and any(c.erased for c in ctxs):
                continue
            table = _fit(s, ctxs)
            if table is None:
                continue
            yield (_spec_name(t, table), _cost(t), _make_fn(s, table))
    return fam


def _make_fn(s, table):
    def fn(grid):
        try:
            return _apply(s, table, grid)
        except Exception:
            return None
    return fn


# ----------------------------------------------------------------------------------------------- drawing
def _bdist(a, b):
    dr = max(0, b[0] - a[2], a[0] - b[2])
    dc = max(0, b[1] - a[3], a[1] - b[3])
    return max(dr, dc)


def _bbox(cells):
    rs = [p[0] for p in cells]
    cs = [p[1] for p in cells]
    return (min(rs), min(cs), max(rs), max(cs))


class _Board(object):
    def __init__(self, H, W):
        self.H, self.W = H, W
        self.g = [[BG] * W for _ in range(H)]
        self.boxes = []

    def put(self, cells, col, box=None):
        for r, c in cells:
            self.g[r][c] = col
        self.boxes.append(box or _bbox(cells))
        return cells

    def place(self, rng, rel, col, gap, margin, tries=150, extra=0):
        """put shape `rel` with colour `col`; its box grown by `extra` must keep `gap` to every box and `margin`
        to the border."""
        h = max(p[0] for p in rel) + 1
        w = max(p[1] for p in rel) + 1
        lo_r, hi_r = margin + extra, self.H - margin - extra - h
        lo_c, hi_c = margin + extra, self.W - margin - extra - w
        if hi_r < lo_r or hi_c < lo_c:
            return None
        for _ in range(tries):
            r0 = rng.randint(lo_r, hi_r)
            c0 = rng.randint(lo_c, hi_c)
            box = (r0 - extra, c0 - extra, r0 + h - 1 + extra, c0 + w - 1 + extra)
            if all(_bdist(box, b) >= gap for b in self.boxes):
                cells = [(r0 + r, c0 + c) for r, c in rel]
                return self.put(cells, col, box)
        return None


def _blob(rng, size, mh=3, mw=3):
    size = min(size, mh * mw)
    cells = {(0, 0)}
    guard = 0
    while len(cells) < size and guard < 500:
        guard += 1
        r, c = rng.choice(sorted(cells))
        dr, dc = rng.choice(N4)
        nr, nc = r + dr, c + dc
        rs = [p[0] for p in cells] + [nr]
        cs = [p[1] for p in cells] + [nc]
        if max(rs) - min(rs) < mh and max(cs) - min(cs) < mw:
            cells.add((nr, nc))
    r0 = min(p[0] for p in cells)
    c0 = min(p[1] for p in cells)
    return sorted((r - r0, c - c0) for r, c in cells)


def _rect(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


def _wall(b, rng, cells, col, length=3):
    """straight wall of `length` directly adjacent to a cell on one side of the shape's box."""
    r0, c0, r1, c1 = _bbox(cells)
    own = _bbox(cells)
    sides = ["N", "S", "E", "W"]
    rng.shuffle(sides)
    cs = set(cells)
    for side in sides:
        if side in ("N", "S"):
            rr = r0 if side == "N" else r1
            edge = [c for (r, c) in cells if r == rr]
            cc = rng.choice(edge)
            wr = rr - 1 if side == "N" else rr + 1
            wc = [(wr, cc - length // 2 + i) for i in range(length)]
        else:
            cc_ = c0 if side == "W" else c1
            edge = [r for (r, c) in cells if c == cc_]
            rr = rng.choice(edge)
            wcol = cc_ - 1 if side == "W" else cc_ + 1
            wc = [(rr - length // 2 + i, wcol) for i in range(length)]
        if not all(0 <= r < b.H and 0 <= c < b.W and b.g[r][c] == BG and (r, c) not in cs for r, c in wc):
            continue
        box = _bbox(wc)
        if all(_bdist(box, bx) >= 2 for bx in b.boxes if bx != own):
            return b.put(wc, col, box)
    return None


def _dims(rng, lo, hi):
    return rng.randint(lo, hi), rng.randint(lo, hi)


def _b_halo(s, rng, cols, seed, grow):
    kk = (seed % 3) + 1 if s.stop == "count" else s.k
    H, W = _dims(rng, 10 + grow, 14 + grow)
    H, W = min(H, 20), min(W, 20)
    b = _Board(H, W)
    sg, dg = 2 * kk + 2, kk + 2
    cen = s.centre
    srcs = []
    if cen == "canvas":
        if b.place(rng, [(0, 0)], cols[0], 1, kk + 1) is None:
            return None
        return b.g
    if cen == "object":
        n = rng.randint(2, 3)
        sizes = [1, rng.randint(3, 5), rng.randint(1, 5)][:n]
        rng.shuffle(sizes)
        for i in range(n):
            c = b.place(rng, _blob(rng, sizes[i]), cols[i], sg, kk)
            if c is None:
                return None
            srcs.append(c)
        dist = []
    elif cen == "singleton":
        for i in range(rng.randint(2, 3)):
            c = b.place(rng, [(0, 0)], cols[i], sg, kk)
            if c is None:
                return None
            srcs.append(c)
        dist = [(_blob(rng, rng.randint(3, 5)), cols[3 + j]) for j in range(rng.randint(1, 2))]
    elif cen == "largest":
        c = b.place(rng, _blob(rng, rng.randint(6, 9), 3, 4), cols[0], sg, kk)
        if c is None:
            return None
        srcs.append(c)
        lo = 2 if s.stop == "count" else 1
        dist = [(_blob(rng, rng.randint(lo, 4)), cols[0]), (_blob(rng, rng.randint(lo, 4)), cols[1])]
    elif cen == "smallest":
        c = b.place(rng, _blob(rng, 2), cols[0], sg, kk)
        if c is None:
            return None
        srcs.append(c)
        dist = [(_blob(rng, rng.randint(4, 6)), cols[0]), (_blob(rng, rng.randint(4, 6)), cols[1])]
    else:  # unique_colour
        c = b.place(rng, _blob(rng, 3), cols[0], sg, kk)
        if c is None:
            return None
        srcs.append(c)
        dist = [(_blob(rng, 1), cols[1]), (_blob(rng, 6), cols[1])]
    if s.stop == "obstacle":
        wcol = cols[1] if cen == "unique_colour" else cols[5]
        for c in srcs:
            if _wall(b, rng, c, wcol) is None:
                return None
    for rel, col in dist:
        if b.place(rng, rel, col, dg, 0) is None:
            return None
    if s.stop == "count":
        for _ in range(kk):
            if b.place(rng, [(0, 0)], cols[4], dg, 0) is None:
                return None
    return b.g


def _room(b, rng, col, gap, h=3, w=3):
    rel = [(r, c) for r in range(h) for c in range(w) if r in (0, h - 1) or c in (0, w - 1)]
    return b.place(rng, rel, col, gap, 1)


def _b_rings(s, rng, cols, seed, grow):
    H, W = _dims(rng, 8 + grow, 13 + grow)
    H, W = min(H, 20), min(W, 20)
    b = _Board(H, W)
    cen = s.centre
    if cen == "singleton":
        if b.place(rng, [(0, 0)], cols[0], 2, 1) is None:
            return None
        if b.place(rng, _blob(rng, rng.randint(3, 4)), cols[1], 2, 0) is None:
            return None
    elif cen == "object":
        n = rng.randint(1, 2)
        for i in range(n):
            if b.place(rng, _blob(rng, rng.randint(1, 4)), cols[i], 3, 1) is None:
                return None
    elif cen == "largest":
        if b.place(rng, _blob(rng, rng.randint(9, 12), 4, 4), cols[0], 2, 1) is None:
            return None
        for j in range(rng.randint(1, 2)):
            if b.place(rng, _blob(rng, rng.randint(1, 3)), cols[0] if j == 0 else cols[2], 2, 0) is None:
                return None
    else:  # canvas
        if s.colour == "source" or s.erase:
            if b.place(rng, [(0, 0)], cols[0], 2, 2) is None:
                return None
        elif rng.random() < 0.5:
            if b.place(rng, _blob(rng, rng.randint(2, 4)), cols[0], 2, 1) is None:
                return None
    if s.stop == "obstacle":
        if _room(b, rng, cols[3], 2) is None:
            return None
    return b.g


def _b_stamp(s, rng, cols, seed, grow):
    k = s.k
    H, W = _dims(rng, 9 + grow, 14 + grow)
    H, W = min(H, 20), min(W, 20)
    b = _Board(H, W)
    cen = s.centre
    if cen == "singleton":
        for i in range(rng.randint(2, 3)):
            if b.place(rng, [(0, 0)], cols[i], 2 * k + 2, k) is None:
                return None
        if b.place(rng, _blob(rng, rng.randint(3, 4)), cols[4], k + 2, 0) is None:
            return None
        return b.g
    if cen == "midpoint":
        for i in range(rng.randint(1, 2)):
            dr, dc = rng.choice(((0, 1), (1, 0), (1, 1), (1, -1)))
            h = rng.randint(k + 1, k + 3)
            ok = False
            for _ in range(150):
                mr = rng.randint(0, H - 1)
                mc = rng.randint(0, W - 1)
                a = (mr - dr * h, mc - dc * h)
                z = (mr + dr * h, mc + dc * h)
                cells = [a, z, (mr - k, mc - k), (mr + k, mc + k)]
                if not all(0 <= r < H and 0 <= c < W for r, c in cells):
                    continue
                box = _bbox(cells)
                if all(_bdist(box, bx) >= 2 for bx in b.boxes):
                    b.put([a, z], cols[i], box)
                    ok = True
                    break
            if not ok:
                return None
        return b.g
    # crossing
    r = rng.randint(k, H - 1 - k)
    nv = rng.randint(1, 2)
    vc = []
    for _ in range(100):
        vc = sorted(rng.sample(range(k, W - k), nv))
        if all(vc[i + 1] - vc[i] >= 2 * k + 2 for i in range(len(vc) - 1)):
            break
    else:
        return None
    ca = cols[0]
    cb = cols[0] if rng.random() < 0.3 else cols[1]
    for c in range(W):
        b.g[r][c] = ca
    for c in vc:
        for rr in range(H):
            b.g[rr][c] = cb
    return b.g


_ODD = ((3, 3), (3, 5), (5, 3), (5, 5), (3, 7), (7, 3), (5, 7), (7, 5))


def _b_centre(s, rng, cols, seed, grow):
    H, W = _dims(rng, 11 + grow, 15 + grow)
    H, W = min(H, 20), min(W, 20)
    b = _Board(H, W)
    cen = s.centre
    if cen == "object":
        n = rng.randint(2, 3)
        dims = [rng.choice(_ODD[1:])] + [rng.choice(_ODD) for _ in range(n - 1)]
        for i, (h, w) in enumerate(dims):
            if b.place(rng, _rect(h, w), cols[i], 2, 0) is None:
                return None
        h, w = rng.choice(((4, 4), (3, 4), (4, 3), (2, 2), (4, 5)))
        if b.place(rng, _rect(h, w), cols[3], 2, 0) is None:
            return None
        return b.g
    areas = {}
    for d in _ODD:
        areas.setdefault(d[0] * d[1], []).append(d)
    av = sorted(areas)
    n = rng.randint(2, 3)
    if cen == "smallest":
        av = [a for a in av if a > 9]
    pick = sorted(rng.sample(av, n))
    sel = pick[-1] if cen == "largest" else pick[0]
    order = [sel] + [a for a in pick if a != sel]
    for i, a in enumerate(order):
        h, w = rng.choice(areas[a])
        col = cols[0] if i <= 1 else cols[2]
        if b.place(rng, _rect(h, w), col, 2, 0) is None:
            return None
    return b.g


def _b_inset(s, rng, cols, seed, grow):
    P = s.period
    smin = 3 if (P == 1 and s.colour == "literal") else 2 * P + 1
    H, W = _dims(rng, 12 + grow, 16 + grow)
    H, W = min(H, 20), min(W, 20)
    b = _Board(H, W)
    cen = s.centre
    if cen == "object":
        n = 2
        dims = []
        for i in range(n):
            h, w = rng.randint(smin, smin + 2), rng.randint(smin, smin + 2)
            dims.append((h, w))
        h, w = dims[0]
        dims[0] = (max(h, smin + 1), w)            # interior wider than one cell (not a centre-cell task)
        if P == 2:
            dims[0] = (max(dims[0][0], 6), dims[0][1])
        for i, (h, w) in enumerate(dims):
            if b.place(rng, _rect(h, w), cols[i], 2, 0) is None:
                return None
        return b.g
    n = rng.randint(2, 3)
    dims = []
    seen = set()
    for _ in range(50):
        if len(dims) == n:
            break
        h, w = rng.randint(smin, smin + 3), rng.randint(smin, smin + 3)
        if h * w in seen:
            continue
        seen.add(h * w)
        dims.append((h, w))
    if len(dims) < 2:
        return None
    dims.sort(key=lambda d: d[0] * d[1])
    sel = dims[-1] if cen == "largest" else dims[0]
    if P == 2 and min(sel) < 6 and s.colour == "literal":
        sel = (6, max(sel[1], 5)) if cen == "largest" else sel
    rest = [d for d in dims if d is not sel and d != sel]
    order = [sel] + rest
    for i, (h, w) in enumerate(order):
        col = cols[0] if i <= 1 else cols[2]
        if b.place(rng, _rect(h, w), col, 2, 0) is None:
            return None
    return b.g


_BUILD = {"halo": _b_halo, "rings": _b_rings, "stamp": _b_stamp, "centre": _b_centre, "inset": _b_inset}

# a drawn pair must not also be produced by these neighbouring generators (keeps the node recognisable)
def _rivals(s):
    t = list(s.t)
    out = []
    if s.stop == "obstacle":
        t2 = list(t)
        t2[_IDX["stop"]] = "thickness" if s.verb == "halo" else "border"
        out.append(_S(tuple(t2)))
    return out


def _rule(s, rule_seed):
    rr = random.Random(rule_seed)
    n = _nslots(s)
    table = {"C": None, "pal": {}}
    used = []
    if s.colour == "literal":
        table["C"] = rr.randint(1, 9)
        used = [table["C"]]
    elif s.colour == "sequence":
        if n <= 4:
            pal = rr.sample(range(1, 10), n)
            used = list(pal)
        else:
            base = rr.sample(range(1, 10), 4)
            pal = [rr.choice(base) for _ in range(n)]
            pal[0], pal[1] = base[0], base[1]
            used = base
        table["pal"] = dict(enumerate(pal))
    return table, used


def draw_spec(t, seed, rule_seed=0):
    s = _S(tuple(t))
    table, used = _rule(s, rule_seed)
    pool = [c for c in range(1, 10) if c not in used]
    rng = random.Random(rule_seed * 1009 + seed)
    for attempt in range(40):
        cols = list(pool)
        rng.shuffle(cols)
        while len(cols) < 6:
            cols = cols + cols
        g = _BUILD[s.verb](s, rng, cols, seed, (attempt // 10) * 2)
        if g is None:
            continue
        out = _apply(s, table, g)
        if out is None or out == g:
            continue
        if any(_apply(r, table, g) == out for r in _rivals(s)):
            continue
        return g, out
    return None


def draw(node, seed):
    comps = completions(node)
    if not comps:
        return None
    kk = key(node)
    h = zlib.crc32(kk.encode("utf8"))
    t = comps[h % len(comps)]
    return draw_spec(t, seed, h & 0xFFFFFF)


def drawn_spec(node):
    """the completion that draw(node, .) uses (for diagnostics)"""
    comps = completions(node)
    if not comps:
        return None
    return comps[zlib.crc32(key(node).encode("utf8")) % len(comps)]
