"""move.by_vector: every mover object is translated rigidly by a vector computed from its own properties.

One parametrised primitive  translate(seg, sel, rule, edge, collide):
  seg     : object segmentation   c4 | c8 (single colour) | m8 (multicolour 8-conn)
  sel     : which objects move    all | nonstatic-colour | interior (not touching grid edge) | shared-colour
  rule    : v(obj) = unit(obj) * mag(obj)
              unit : one of 8 constant directions | toward nearest anchor | toward same-colour anchor
                     | toward grid centre | toward attached marker
              mag  : 1 | 2 | 3 | cell count | width | height | number of marker cells
            or v(obj) = table[key(obj)], key in {const, colour, part-role in composite (top/mid/bottom)}
  edge    : clip (cells leaving the grid vanish) | wrap (toroidal)
  collide : over (movers paint over) | block (advance at most |v| unit steps while landing on background)
Markers = colours present in inputs but absent from outputs (induced); they are erased, or absorbed into the
object whose bounding box contains them (recoloured) when the rule is 'toward attached marker'.
All parameters are induced from training pairs; candidates are pre-filtered with per-object displacement sets
and fully verified on all training pairs before being yielded.
"""
import sys; sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox, static_colours

DIR8 = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1), "NW": (-1, -1), "NE": (-1, 1), "SW": (1, -1), "SE": (1, 1)}
SEGS = ("c4", "c8", "m8")
SELS = ("all", "nonstatic", "interior", "shared")
UNITS = tuple(DIR8) + ("anchor", "anchor_same", "centre", "marker")
MAGS = (1, 2, 3, "size", "w", "h", "mk")
TABLES = ("const", "colour", "role")


def sgn(v): return (v > 0) - (v < 0)


def marker_colours(train):
    m = None
    for p in train:
        ci = {v for r in p["input"] for v in r}; co = {v for r in p["output"] for v in r}
        m = (ci - co) if m is None else (m & (ci - co)) | (m - ci)
    return m or set()


def segment(g, bg, seg, markers):
    gg = [[bg if v in markers else v for v in r] for r in g]
    obs = objects(gg, bg, diag=seg != "c4", by_colour=seg != "m8")
    return [[(y, x, g[y][x]) for y, x in ob] for ob in obs]


def select(obs, g, sel, st):
    h, w = H(g), W(g)
    if sel == "all": mv = [True] * len(obs)
    elif sel == "nonstatic": mv = [not all(c in st for _, _, c in ob) for ob in obs]
    elif sel == "interior": mv = [not any(y in (0, h - 1) or x in (0, w - 1) for y, x, _ in ob) for ob in obs]
    else:
        cnt = Counter(frozenset(c for _, _, c in ob) for ob in obs)
        mv = [cnt[frozenset(c for _, _, c in ob)] >= 2 for ob in obs]
    return [ob for ob, m in zip(obs, mv) if m], [ob for ob, m in zip(obs, mv) if not m]


def attach_markers(g, movers, markers):
    """Marker cells inside a mover's bounding box join it, recoloured to the mover's main colour."""
    h, w = H(g), W(g); out = []
    for ob in movers:
        cells = {(y, x) for y, x, _ in ob}
        main = Counter(c for _, _, c in ob).most_common(1)[0][0]
        r0, c0, r1, c1 = bbox(list(cells))
        mk = {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1) if g[y][x] in markers}
        out.append((ob + [(y, x, main) for y, x in mk], mk))
    return out


def centre(cells):
    r0, c0, r1, c1 = bbox([(y, x) for y, x, *_ in cells])
    return (r0 + r1) / 2, (c0 + c1) / 2, (r0, c0, r1, c1)


def toward(ob, target_cells):
    """Unit step from object toward target; the component along an axis where projections overlap is 0."""
    _, _, (r0, c0, r1, c1) = centre(ob)
    _, _, (a0, b0, a1, b1) = centre(target_cells)
    dy = 0 if (a0 <= r1 and r0 <= a1) else sgn(a0 - r0)
    dx = 0 if (b0 <= c1 and c0 <= b1) else sgn(b0 - c0)
    return dy, dx


class Ctx:
    """Everything about one grid needed to evaluate a rule."""
    def __init__(self, g, seg, sel, markers, st, attach):
        self.g = g; self.bg = bg = bg_of(g); self.markers = markers
        obs = segment(g, bg, seg, markers)
        mov, rest = select(obs, g, sel, st)
        if attach:
            am = attach_markers(g, mov, markers)
            mov = [a for a, _ in am]; self.mk = [m for _, m in am]
        else:
            self.mk = [set() for _ in mov]
        # role items: split multicolour movers into colour parts
        self.parts = None
        if seg == "m8":
            parts = []
            for ob in mov:
                byc = {}
                for y, x, c in ob: byc.setdefault(c, []).append((y, x, c))
                ps = sorted(byc.values(), key=lambda p: centre(p)[0])
                for k, p in enumerate(ps):
                    rl = "solo" if len(ps) == 1 else "top" if k == 0 else "bottom" if k == len(ps) - 1 else "mid"
                    parts.append((p, rl))
            self.parts = parts
        self.movers, self.anchors = mov, rest
        self.nmk = sum(v in markers for r in g for v in r)

    def unit(self, i, u):
        ob = self.movers[i]
        if u in DIR8: return DIR8[u]
        if u == "centre":
            h, w = H(self.g), W(self.g)
            return toward(ob, [((h - 1) // 2, (w - 1) // 2), (h // 2, w // 2)])
        if u == "marker":
            if not self.mk[i]: return (0, 0)
            cy, cx, _ = centre(ob); my, mx, _ = centre(list(self.mk[i]))
            return sgn(my - cy), sgn(mx - cx)
        cands = self.anchors
        if u == "anchor_same":
            cs = {c for _, _, c in ob}
            cands = [a for a in cands if {c for _, _, c in a} & cs]
        if not cands: return (0, 0)
        cy, cx, _ = centre(ob)
        best = min(cands, key=lambda a: min(abs(y - cy) + abs(x - cx) for y, x, _ in a))
        return toward(ob, best)

    def mag(self, i, m):
        if isinstance(m, int): return m
        ob = self.movers[i]; r0, c0, r1, c1 = centre(ob)[2]
        return {"size": len(ob), "w": c1 - c0 + 1, "h": r1 - r0 + 1, "mk": self.nmk}[m]

    def items(self, table):
        """(cells, key) list for table rules."""
        if table == "role":
            return [(p, r) for p, r in self.parts] if self.parts is not None else None
        if table == "const": return [(ob, 0) for ob in self.movers]
        return [(ob, ob[0][2]) for ob in self.movers if len({c for _, _, c in ob}) == 1] \
            if all(len({c for _, _, c in ob}) == 1 for ob in self.movers) else None


def paint(g, bg, items, edge, collide):
    """items: list of (cells, (dy,dx), unit or None, steps)."""
    h, w = H(g), W(g); out = [r[:] for r in g]
    for cells, *_ in items:
        for y, x, _ in cells: out[y][x] = bg
    base = [r[:] for r in out]
    for cells, (dy, dx), unit, steps in items:
        if collide == "block":
            k = 0
            while k < steps:
                ny, nx = (k + 1) * unit[0], (k + 1) * unit[1]
                ok = True
                for y, x, _ in cells:
                    yy, xx = y + ny, x + nx
                    if not (0 <= yy < h and 0 <= xx < w) or base[yy][xx] != bg: ok = False; break
                if not ok: break
                k += 1
            dy, dx = k * unit[0], k * unit[1]
        for y, x, c in cells:
            yy, xx = y + dy, x + dx
            if edge == "wrap": yy %= h; xx %= w
            if 0 <= yy < h and 0 <= xx < w: out[yy][xx] = c
    return out


def disp_ok(o, cells, d):
    h, w = H(o), W(o); dy, dx = d
    for y, x, c in cells:
        yy, xx = y + dy, x + dx
        if 0 <= yy < h and 0 <= xx < w and o[yy][xx] != c: return False
    return True


def fam_move_by_vector(train):
    i0, o0 = train[0]["input"], train[0]["output"]
    if any((H(p["input"]), W(p["input"])) != (H(p["output"]), W(p["output"])) for p in train): return
    if all(p["input"] == p["output"] for p in train): return
    markers = marker_colours(train)
    st = static_colours(train)
    yielded = 0
    for seg in SEGS:
        for sel in SELS:
            if sel == "nonstatic" and not st: continue
            for attach in ((False, True) if markers else (False,)):
                ctxs = []
                for p in train:
                    c = Ctx(p["input"], seg, sel, markers, st, attach)
                    if not c.movers or len(c.movers) > 40: ctxs = None; break
                    ctxs.append(c)
                if not ctxs: continue
                progs = []
                # ---- unit * magnitude rules
                units = [u for u in UNITS if (u != "marker") == (not attach)]
                if attach: units = ["marker"]
                for u in units:
                    if u == "anchor_same" and seg == "m8": continue
                    ulist = [[c.unit(k, u) for k in range(len(c.movers))] for c in ctxs]
                    if all(v == (0, 0) for ul in ulist for v in ul): continue
                    for m in MAGS:
                        if m == "mk" and (not markers or attach): continue
                        mlist = [[c.mag(k, m) for k in range(len(c.movers))] for c in ctxs]
                        # prefilter: exact displacement must be consistent (ignoring blocking)
                        pre = all(disp_ok(p["output"], c.movers[k], (ul[k][0] * ml[k], ul[k][1] * ml[k]))
                                  for p, c, ul, ml in zip(train, ctxs, ulist, mlist) for k in range(len(c.movers)))
                        modes = [("over", "clip"), ("over", "wrap")] if pre else []
                        if not isinstance(m, int) or m <= 3: modes.append(("block", "clip"))
                        for collide, edge in modes:
                            progs.append((f"{u}*{m}", u, m, None, None, collide, edge))
                # ---- table rules: vector looked up by key
                for tb in TABLES:
                    if tb == "role" and seg != "m8": continue
                    if attach: continue
                    tabs = {}; good = True
                    for p, c in zip(train, ctxs):
                        its = c.items(tb)
                        if its is None: good = False; break
                        for cells, key in its:
                            h, w = H(p["output"]), W(p["output"])
                            y0, x0, col = cells[0]
                            D = {(yy - y0, xx - x0) for yy in range(h) for xx in range(w) if p["output"][yy][xx] == col}
                            D = {d for d in D if disp_ok(p["output"], cells, d)}
                            tabs[key] = tabs[key] & D if key in tabs else D
                            if not tabs[key]: good = False; break
                        if not good: break
                    if not good or not tabs: continue
                    tab = {k: min(v, key=lambda d: (abs(d[0]) + abs(d[1]), d)) for k, v in tabs.items()}
                    if all(v == (0, 0) for v in tab.values()): continue
                    if tb == "const" and sum(v != (0, 0) for v in tab.values()) == 0: continue
                    for edge in ("clip", "wrap"):
                        progs.append((f"{tb}", None, None, tb, tab, "over", edge))
                for name, u, m, tb, tab, collide, edge in progs:
                    fn = make(seg, sel, attach, markers, st, u, m, tb, tab, collide, edge)
                    if all(fn(p["input"]) == p["output"] for p in train):
                        yield (f"move-by-vector:{name}[{seg},{sel},{collide},{edge}{',attach' if attach else ''}]",
                               (4 if tb is None else 5) + (edge == 'wrap'), fn)
                        yielded += 1
                        if yielded >= 6: return
                        break


def make(seg, sel, attach, markers, st, u, m, tb, tab, collide, edge):
    def fn(g):
        c = Ctx(g, seg, sel, markers, st, attach)
        if not c.movers: return None
        g2 = [[c.bg if v in markers else v for v in r] for r in g]
        if tb is None:
            items = []
            for k, ob in enumerate(c.movers):
                un = c.unit(k, u); mg = c.mag(k, m)
                items.append((ob, (un[0] * mg, un[1] * mg), un, mg))
        else:
            its = c.items(tb)
            if its is None: return None
            items = []
            for cells, key in its:
                if key not in tab: return None
                items.append((cells, tab[key], None, 0))
        return paint(g2, c.bg, items, edge, collide)
    return fn


FAMILIES = (fam_move_by_vector,)
