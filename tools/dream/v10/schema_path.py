"""PATH image schema of the v10 description lattice (Fable guidance v10).  Synthetic only: no ARC data is read.

A PATH record says: a SOURCE (picked by a role selector) emits a trajectory in the direction(s) given by a
DIRECTION RULE; the trajectory runs until a STOP; the cells it covers are painted by a COLOUR RULE.  The verb names
the kind of trajectory.  A full generator is one value per lattice dimension plus a few fitted constants:

  verb    cast    - ray(s) from the source, trail painted                     (cast/shoot/extend/smear/extrude ...)
          sweep   - full line through the source along an axis (both ways)    (sweep, row/col fill)
          project - only the landing cell of the ray is painted               (project, fire at range R)
          slide   - the source object itself moves along d                    (translate/slide/push/shift)
          bounce  - diagonal ray reflecting off other objects, absorbed at border   (bounce/reflect)
          connect - L / straight path between the two cells of a same-colour pair    (connect/route)
  stop    border | obstacle:{before,hit} | length:{k,size} | target:before
  dir     const d | orth4 | diag4 | all8 | edge (toward/away nearest border) | pointer (shape's own heading)
          | colour_table (source colour -> d) | pair (toward the partner cell; connect only)
  stride  1 | 2 (every other cell)
  source  singleton | marker (cells of the rarest colour) | corner (L-tromino corner) | smallest object
          | face (leading face of every multi-cell object) | odd_cell (odd-coloured cell of an object)
          | edge_cell (cell on the grid border)
  colour  source | literal | context (colour of the obstacle hit) | sequence (source/c alternation)
          | table (source colour -> colour) | own (moved object keeps its colours; slide only)
Fitted constants (MENU["fit"]): d, k, c, layer (under: rays pass behind objects / over), sense, order, phase,
ctab, dtab.  A lattice node binds some dimensions; the rest are enumerated and fitted by family(node).

Self-test (test_path.py): 358 nodes (1 schema + 35 depth-1 + 322 depth-2), all drawn and recognised for seeds 0..3
(held-out seeds 4..7: 355/358).  PRUNED is therefore empty.  family time: <= 0.1 s on the synthetic tasks,
<= ~0.5 s for the schema node on busy 30x30 grids.  Not modelled (see MENU["unmodelled"]): turning walks,
spirals, BFS routes, glyph tables, on-hit stamps, grid-size changes.
"""
import itertools
import random
import zlib
from collections import Counter
from functools import lru_cache

SCHEMA = "PATH"

DIRS = {"N": (-1, 0), "NE": (-1, 1), "E": (0, 1), "SE": (1, 1),
        "S": (1, 0), "SW": (1, -1), "W": (0, -1), "NW": (-1, -1)}
D8 = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
ORTH = ["N", "E", "S", "W"]
DIAG = ["NE", "SE", "SW", "NW"]
AXES = ["N", "E", "NE", "SE"]            # sweep: a line through the source, d and -d are the same axis
OPP = {"N": "S", "S": "N", "E": "W", "W": "E", "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
NAME = {v: k for k, v in DIRS.items()}

STOPS = {"border": ["border"], "obstacle": ["obstacle:before", "obstacle:hit"],
         "length": ["length:k", "length:size"], "target": ["target:before"]}
MEMBERS = [m for ms in STOPS.values() for m in ms]
STOP_CLASS = {m: c for c, ms in STOPS.items() for m in ms}

MENU = {
    "schema": SCHEMA,
    "verb": ["cast", "sweep", "project", "slide", "bounce", "connect"],
    "stop": STOPS,
    "dir": ["const", "orth4", "diag4", "all8", "edge", "pointer", "colour_table", "pair"],
    "stride": [1, 2],
    "source": ["singleton", "marker", "corner", "smallest", "face", "odd_cell", "edge_cell"],
    "colour": ["source", "literal", "context", "sequence", "table", "own"],
    "fit": {"d": D8, "k": list(range(1, 9)), "c": list(range(1, 10)), "layer": ["under", "over"],
            "sense": ["away", "toward"], "order": ["VH", "HV"], "phase": [0, 1],
            "ctab": "source colour -> paint colour", "dtab": "source colour -> direction"},
    # where the menu values come from in the parsed PATH records (results/o0/v10_records.json)
    "verb_synonyms": {
        "cast": ["cast", "shoot", "extend", "smear", "extrude", "emit", "fire", "draw", "complete", "justify"],
        "sweep": ["sweep", "fill", "project(row/col)"],
        "project": ["project", "fire(point R)"],
        "slide": ["translate", "slide", "push", "shift", "move"],
        "bounce": ["bounce", "reflect"],
        "connect": ["connect", "route", "navigate(straight)"]},
    "source_glosses": {
        "singleton": "isolated marker pixel / seed cell / coloured dot",
        "marker": "marker cells of the rarest colour (odd-coloured cell, emitter port)",
        "corner": "corner-shaped object (2x2 minus one), fires out of its corner",
        "smallest": "small object / smallest object",
        "face": "front cells of the source object (cross-section profile, rectangle rows/cols)",
        "odd_cell": "odd-coloured cell of an arrow / object (heading = body -> odd cell)",
        "edge_cell": "marker on an edge row/column (heading = away from that edge)"},
    "unmodelled": ["turn-at-wall walks", "spirals", "bfs routes around walls", "glyph tables",
                   "waypoint chains", "staircases", "on-hit stamps", "multi-panel frames"],
}

DIMS = ["verb", "stop", "dir", "stride", "source", "colour"]
_VALUES = {"verb": MENU["verb"], "stop": MEMBERS, "dir": MENU["dir"], "stride": MENU["stride"],
           "source": MENU["source"], "colour": MENU["colour"]}

# Nodes whose generator could not be drawn or recognised in the self-test (with all their specialisations).
PRUNED = []


# ----------------------------------------------------------------------------------------------- lattice

def _valid(v, s, r, t, l, c):
    if (v == "connect") != (r == "pair"):
        return False
    if (v == "slide") != (c == "own"):
        return False
    if v == "connect":
        return s == "target:before" and l in ("singleton", "marker") and c in ("source", "literal") and t == 1
    if v == "slide":
        if s not in ("border", "obstacle:before", "target:before", "length:k", "length:size"):
            return False
        if t != 1 or r not in ("const", "edge", "pointer", "colour_table"):
            return False
    if v == "sweep":
        if s != "border" or r not in ("const", "colour_table") or c not in ("source", "literal", "sequence", "table"):
            return False
    if v == "bounce":
        if s != "border" or r not in ("const", "diag4", "pointer") or t != 1:
            return False
        if c not in ("source", "literal", "context"):
            return False
        if l not in ("singleton", "marker", "corner", "odd_cell", "edge_cell"):
            return False
        if r == "pointer" and l != "corner":
            return False
    if v == "project":
        if t != 1 or c not in ("source", "literal", "context", "table"):
            return False
    if v == "cast" and c not in ("source", "literal", "context", "sequence", "table"):
        return False
    if c == "context" and v != "bounce" and s not in ("obstacle:before", "target:before"):
        return False
    if r == "pointer" and l not in ("corner", "odd_cell", "edge_cell"):
        return False
    if r == "edge" and l == "edge_cell":
        return False
    if c == "sequence" and t != 1:
        return False
    if t == 2 and (v not in ("cast", "sweep") or c not in ("source", "literal", "table")):
        return False
    return True


def _prior(comp):
    return sum(_VALUES[d].index(x) for d, x in zip(DIMS, comp))


_ALL = sorted((cp for cp in itertools.product(*[_VALUES[d] for d in DIMS]) if _valid(*cp)), key=lambda cp: (_prior(cp), cp))


def _match(node, comp):
    for i, d in enumerate(DIMS):
        if d not in node:
            continue
        want = node[d]
        if d == "stop":
            if comp[1] != want and STOP_CLASS[comp[1]] != want:
                return False
        elif comp[i] != want:
            return False
    return True


def _norm(node):
    return tuple(sorted((d, node[d]) for d in DIMS if d in node))


@lru_cache(maxsize=None)
def _comps_t(nt):
    node = dict(nt)
    return tuple(cp for cp in _ALL if _match(node, cp))


def _comps(node):
    return _comps_t(_norm(node))


def _closure(node):
    comps = _comps(node)
    if not comps:
        return None
    out = {}
    for i, d in enumerate(DIMS):
        vals = {cp[i] for cp in comps}
        if len(vals) == 1:
            out[d] = vals.pop()
    if "stop" not in out:
        cls = {STOP_CLASS[cp[1]] for cp in comps}
        if len(cls) == 1:
            out["stop"] = cls.pop()
    return out


def key(node):
    """Canonical string: the bindings implied by the node (its closure).  Nodes with the same set of full generators
    (completions) get the same key; different sets get different keys."""
    cl = _closure(node)
    if cl is None:
        return "PATH{unsatisfiable}"
    return "PATH{" + ",".join("%s=%s" % (d, cl[d]) for d in DIMS if d in cl) + "}"


def _pruned(node):
    mine = set(_comps(node))
    for p in PRUNED:
        if mine <= set(_comps(p)):
            return True
    return False


def nodes():
    """Every satisfiable node at depth <= 2 below the schema, deduplicated by key, minus pruned ones."""
    steps = [(d, v) for d in DIMS if d != "stop" for v in _VALUES[d]] + [("stop", c) for c in STOPS]
    out, seen = [], set()

    def add(n):
        if not _comps(n):
            return
        k = key(n)
        if k in seen or _pruned(n):
            return
        seen.add(k)
        out.append(n)

    add({})
    for d, v in steps:
        add({d: v})
    for i, (d, v) in enumerate(steps):
        if d == "stop":
            for m in STOPS[v]:
                add({"stop": m})
        for d2, v2 in steps[i + 1:]:
            if d2 != d:
                add({d: v, d2: v2})
    return out


# ----------------------------------------------------------------------------------------------- grid analysis

def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _objects(g, bg):
    H, W = len(g), len(g[0])
    seen = set()
    objs = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            stack, cells = [(r, c)], []
            seen.add((r, c))
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and (ny, nx) not in seen and g[ny][nx] != bg:
                            seen.add((ny, nx))
                            stack.append((ny, nx))
            objs.append(tuple(sorted(cells)))
    return objs


def _sign(x, tol=0.25):
    return 0 if abs(x) <= tol else (1 if x > 0 else -1)


def _sources(g, bg, sel, objs):
    """Role selector -> list of sources (own cells, emit cells, key colour, intrinsic heading or None)."""
    H, W = len(g), len(g[0])
    out = []
    if sel == "singleton":
        out = [(frozenset(o), o, g[o[0][0]][o[0][1]], None) for o in objs if len(o) == 1]
    elif sel == "marker":
        cnt = Counter(v for row in g for v in row if v != bg)
        if len(cnt) < 2:
            return []
        m = min(cnt.values())
        rare = [k for k, n in cnt.items() if n == m]
        if len(rare) != 1:
            return []
        col = rare[0]
        out = [(frozenset([(r, c)]), ((r, c),), col, None) for r in range(H) for c in range(W) if g[r][c] == col]
    elif sel == "corner":
        for o in objs:
            if len(o) != 3:
                continue
            rs = [r for r, _ in o]
            cs = [c for _, c in o]
            r0, c0 = min(rs), min(cs)
            if max(rs) - r0 != 1 or max(cs) - c0 != 1:
                continue
            box = {(r0 + i, c0 + j) for i in (0, 1) for j in (0, 1)}
            (mr, mc), = box - set(o)
            cr, cc = 2 * r0 + 1 - mr, 2 * c0 + 1 - mc
            out.append((frozenset(o), ((cr, cc),), g[cr][cc], NAME[(cr - mr, cc - mc)]))
    elif sel in ("smallest", "face"):
        if sel == "smallest":
            if len(objs) < 2:
                return []
            m = min(len(o) for o in objs)
            pick = [o for o in objs if len(o) == m]
            if len(pick) != 1:
                return []
        else:
            pick = [o for o in objs if len(o) >= 2]
        for o in pick:
            cnt = Counter(g[r][c] for r, c in o)
            col = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            out.append((frozenset(o), o, col, None))
    elif sel == "odd_cell":
        for o in objs:
            if len(o) < 3:
                continue
            cnt = Counter(g[r][c] for r, c in o)
            if len(cnt) != 2 or min(cnt.values()) != 1:
                continue
            oc = [k for k, n in cnt.items() if n == 1][0]
            (orr, occ), = [(r, c) for r, c in o if g[r][c] == oc]
            rest = [(r, c) for r, c in o if (r, c) != (orr, occ)]
            mr = sum(r for r, _ in rest) / len(rest)
            mc = sum(c for _, c in rest) / len(rest)
            v = (_sign(orr - mr), _sign(occ - mc))
            out.append((frozenset(o), ((orr, occ),), oc, NAME.get(v)))
    elif sel == "edge_cell":
        for r in range(H):
            for c in range(W):
                if g[r][c] == bg or not (r in (0, H - 1) or c in (0, W - 1)):
                    continue
                p = "S" if r == 0 else "N" if r == H - 1 else "E" if c == 0 else "W"
                out.append((frozenset([(r, c)]), ((r, c),), g[r][c], p))
    out.sort(key=lambda s: s[1][0])
    return out


class _Unseen(Exception):
    pass


class _Reject(Exception):
    """Raised while generating events when a background cell would be painted that the output leaves unchanged."""


def _dirs(cfg, src, H, W):
    r = cfg["dir"]
    if r == "const":
        ds = [cfg["d"]]
    elif r == "orth4":
        ds = ORTH
    elif r == "diag4":
        ds = DIAG
    elif r == "all8":
        ds = D8
    elif r == "edge":
        own = src[0]
        rs = [y for y, _ in own]
        cs = [x for _, x in own]
        dist = [(min(rs), "N"), (H - 1 - max(rs), "S"), (min(cs), "W"), (W - 1 - max(cs), "E")]
        m = min(x for x, _ in dist)
        near = [n for x, n in dist if x == m]
        if len(near) != 1:
            return []
        ds = [near[0] if cfg["sense"] == "toward" else OPP[near[0]]]
    elif r == "pointer":
        ds = [src[3]] if src[3] else []
    elif r == "colour_table":
        if src[2] not in cfg["dtab"]:
            raise _Unseen()
        ds = [cfg["dtab"][src[2]]]
    else:
        ds = []
    if cfg["verb"] == "sweep":
        ds = list(ds) + [OPP[d] for d in ds if OPP[d] not in ds]
    elif cfg["verb"] == "bounce":
        ds = [d for d in ds if d in DIAG]
    return ds


def _extent(own, d):
    dr, dc = DIRS[d]
    nr = len({r for r, _ in own})
    nc = len({c for _, c in own})
    if dc == 0:
        return nr
    if dr == 0:
        return nc
    return max(nr, nc)


# ----------------------------------------------------------------------------------------------- generator

def _events(cfg, g, bg, srcs, info=None, D=None):
    """Paint events (cell, source colour, context colour, index, force) for every verb except slide.  With D (the set
    of cells a training pair changes) generation aborts (_Reject) at the first background cell outside D."""
    H, W = len(g), len(g[0])
    verb, stop, stride = cfg["verb"], cfg["stop"], cfg["stride"]
    evs = []
    if verb == "connect":
        bycol = {}
        for s in srcs:
            bycol.setdefault(s[2], []).append(s[1][0])
        for col in sorted(bycol):
            cells = bycol[col]
            if len(cells) != 2:
                continue
            (ar, ac), (br, bc) = sorted(cells)
            dr, dc = br - ar, bc - ac
            path = []
            if dr == 0 or dc == 0 or abs(dr) == abs(dc):
                n = max(abs(dr), abs(dc))
                sr, sc = _sign(dr, 0), _sign(dc, 0)
                path = [(ar + i * sr, ac + i * sc) for i in range(1, n)]
            elif cfg["order"] == "VH":
                sr, sc = _sign(dr, 0), _sign(dc, 0)
                path = [(ar + i * sr, ac) for i in range(1, abs(dr) + 1)] + \
                       [(br, ac + i * sc) for i in range(1, abs(dc))]
            else:
                sr, sc = _sign(dr, 0), _sign(dc, 0)
                path = [(ar, ac + i * sc) for i in range(1, abs(dc) + 1)] + \
                       [(ar + i * sr, bc) for i in range(1, abs(dr))]
            for i, cell in enumerate(path):
                if D is not None and cell not in D and g[cell[0]][cell[1]] == bg:
                    raise _Reject()
                evs.append((cell, col, None, i + 1, False))
            if info is not None:
                info["per_src"].append(len(path))
                info["unaligned"] += int(not (dr == 0 or dc == 0 or abs(dr) == abs(dc)))
        return evs
    stopping = stop in ("obstacle:before", "obstacle:hit", "target:before")
    eager = D is not None and verb != "project" and stop != "target:before"
    for s in srcs:
        own = s[0]
        nsrc = 0
        for d in _dirs(cfg, s, H, W):
            dr, dc = DIRS[d]
            emits = [e for e in s[1] if (e[0] + dr, e[1] + dc) not in own] if len(s[1]) > 1 else s[1]
            lim = cfg["k"] if stop == "length:k" else _extent(own, d) if stop == "length:size" else None
            for e in emits:
                scol = g[e[0]][e[1]]
                if verb == "bounce":
                    n, nb = _bounce(g, bg, e, dr, dc, own, scol, evs, D)
                    nsrc += n
                    if info is not None:
                        info["bounces"] += nb
                        info["maxlen"] = max(info["maxlen"], n)
                    continue
                trail, hit, longer = [], None, False
                r, c = e[0] + dr, e[1] + dc
                while 0 <= r < H and 0 <= c < W:
                    if (r, c) not in own:
                        if lim is not None and len(trail) >= lim:
                            longer = True
                            break
                        v = g[r][c]
                        if stopping and v != bg:
                            hit = (r, c)
                            break
                        trail.append((r, c))
                        if eager and v == bg and (r, c) not in D and (stride == 1 or len(trail) % 2 == 1):
                            raise _Reject()
                    r += dr
                    c += dc
                if stop == "target:before" and hit is None:
                    trail = []
                ctx = g[hit[0]][hit[1]] if hit else None
                if info is not None:
                    if hit:
                        info["hits"] += 1
                    elif stopping:
                        info["nohit"] += 1
                    info["maxlen"] = max(info["maxlen"], len(trail))
                    info["full"] += int(longer)
                    info["rays"] += 1
                if verb == "project":
                    if stop == "obstacle:hit":
                        if hit:
                            evs.append((hit, scol, ctx, len(trail) + 1, True))
                            nsrc += 1
                    elif trail and (lim is None or len(trail) == lim):
                        cell = trail[-1]
                        if D is not None and cell not in D and g[cell[0]][cell[1]] == bg:
                            raise _Reject()
                        evs.append((cell, scol, ctx, len(trail), False))
                        nsrc += 1
                    continue
                for i, cell in enumerate(trail):
                    if stride == 2 and i % 2 == 1:
                        continue
                    if D is not None and cell not in D and g[cell[0]][cell[1]] == bg:
                        raise _Reject()
                    evs.append((cell, scol, ctx, i + 1, False))
                    nsrc += 1
                if stop == "obstacle:hit" and hit:
                    evs.append((hit, scol, ctx, len(trail) + 1, True))
                    nsrc += 1
        if info is not None:
            info["per_src"].append(nsrc)
    return evs


def _bounce(g, bg, e, dr, dc, own, scol, evs, D=None):
    H, W = len(g), len(g[0])

    def blocked(y, x):
        return 0 <= y < H and 0 <= x < W and g[y][x] != bg and (y, x) not in own
    r, c = e
    ctx, n, nb, seen = None, 0, 0, set()
    while (r, c, dr, dc) not in seen and n < 4 * (H + W):
        seen.add((r, c, dr, dc))
        hit = None
        if blocked(r + dr, c):
            hit = g[r + dr][c]
            dr = -dr
        if blocked(r, c + dc):
            hit = g[r][c + dc] if hit is None else hit
            dc = -dc
        if hit is None and blocked(r + dr, c + dc):
            hit = g[r + dr][c + dc]
            dr, dc = -dr, -dc
        if hit is not None:
            ctx = hit
            nb += 1
        r, c = r + dr, c + dc
        if not (0 <= r < H and 0 <= c < W) or blocked(r, c):
            break
        n += 1
        if D is not None and (r, c) not in D and g[r][c] == bg:
            raise _Reject()
        evs.append(((r, c), scol, ctx, n, False))
    return n, nb


def _colour(cfg, scol, ctx, idx):
    rule = cfg["colour"]
    if rule == "source":
        return scol
    if rule == "literal":
        return cfg["c"]
    if rule == "context":
        return scol if ctx is None else ctx
    if rule == "sequence":
        return scol if (idx + cfg["phase"]) % 2 == 1 else cfg["c"]
    if rule == "table":
        if scol not in cfg["ctab"]:
            raise _Unseen()
        return cfg["ctab"][scol]
    return scol


def _painted(cfg, g, bg, srcs, info=None, D=None):
    """First-wins list of events that actually paint a cell (layer filter applied)."""
    layer = cfg.get("layer") or "under"
    seen, pl = set(), []
    for cell, scol, ctx, idx, force in _events(cfg, g, bg, srcs, info, D):
        if cell in seen:
            continue
        if not force and g[cell[0]][cell[1]] != bg:
            if info is not None:
                info["crossed"] += 1
            if layer == "under":
                continue
        seen.add(cell)
        pl.append((cell, scol, ctx, idx))
    return pl


def _moves(cfg, g, bg, srcs):
    """Displacement (steps, unit vector) of every sliding source, computed on the input grid."""
    H, W = len(g), len(g[0])
    stop = cfg["stop"]
    moves = []
    for s in srcs:
        own = s[0]
        ds = _dirs(cfg, s, H, W)
        if len(ds) != 1:
            moves.append((s, 0, (0, 0)))
            continue
        d = ds[0]
        dr, dc = DIRS[d]
        if stop == "length:k":
            n = cfg["k"]
        elif stop == "length:size":
            n = _extent(own, d)
        else:
            n, blocked_by_obj = 0, False
            while True:
                nxt = [(r + (n + 1) * dr, c + (n + 1) * dc) for r, c in own]
                if any(not (0 <= y < H and 0 <= x < W) for y, x in nxt):
                    break
                if stop != "border" and any(g[y][x] != bg and (y, x) not in own for y, x in nxt):
                    blocked_by_obj = True
                    break
                n += 1
            if stop == "target:before" and not blocked_by_obj:
                n = 0
        moves.append((s, n, (dr, dc)))
    return moves


def _slide(cfg, g, bg, srcs, info=None):
    H, W = len(g), len(g[0])
    layer = cfg.get("layer") or "under"
    moves = _moves(cfg, g, bg, srcs)
    out = [row[:] for row in g]
    for s, n, _ in moves:
        if n:
            for r, c in s[0]:
                out[r][c] = bg
    if info is not None:
        dest = [(r + n * dr, c + n * dc) for s, n, (dr, dc) in moves for r, c in s[0]]
        info["collide"] = len(dest) != len(set(dest))
    for s, n, (dr, dc) in moves:
        if info is not None:
            info["per_src"].append(n)
            info["clipped"] += int(any(not (0 <= r + n * dr < H and 0 <= c + n * dc < W) for r, c in s[0]))
        if not n:
            continue
        for r, c in sorted(s[0]):
            y, x = r + n * dr, c + n * dc
            if 0 <= y < H and 0 <= x < W:
                if out[y][x] != bg:
                    if info is not None:
                        info["crossed"] += 1
                    if layer == "under":
                        continue
                out[y][x] = g[r][c]
    return out


def _new_info():
    return {"per_src": [], "hits": 0, "nohit": 0, "rays": 0, "maxlen": 0, "full": 0, "bounces": 0,
            "unaligned": 0, "clipped": 0, "crossed": 0}


def apply(cfg, grid, info=None):
    """The generator of a fully specified PATH program.  Returns the output grid, or None when the program does not
    apply (no source, unseen table colour)."""
    try:
        bg = _bg(grid)
        srcs = _sources(grid, bg, cfg["source"], _objects(grid, bg))
        if not srcs:
            return None
        if cfg["verb"] == "slide":
            return _slide(cfg, grid, bg, srcs, info)
        out = [row[:] for row in grid]
        for (r, c), scol, ctx, idx in _painted(cfg, grid, bg, srcs, info):
            out[r][c] = _colour(cfg, scol, ctx, idx)
        return out
    except _Unseen:
        return None


# ----------------------------------------------------------------------------------------------- family

class _Pair:
    __slots__ = ("i", "o", "H", "W", "bg", "D", "objs", "srcs", "cache", "rays")

    def __init__(self, i, o):
        self.i, self.o = i, o
        self.H, self.W = len(i), len(i[0])
        self.bg = _bg(i)
        self.D = {(r, c) for r in range(self.H) for c in range(self.W) if i[r][c] != o[r][c]}
        self.objs = _objects(i, self.bg)
        self.srcs = {}
        self.cache = {}
        self.rays = {}

    def covered(self, sel, ds):
        """Are all changed cells on some ray line (any stop) from the selected sources in directions ds?"""
        if sel not in self.rays:
            lines = {d: set() for d in D8}
            for own, emits, _, _ in self.sources(sel):
                for d in D8:
                    dr, dc = DIRS[d]
                    acc = lines[d]
                    for e in emits:
                        r, c = e[0] + dr, e[1] + dc
                        while 0 <= r < self.H and 0 <= c < self.W:
                            if (r, c) in acc:
                                break
                            if (r, c) not in own:
                                acc.add((r, c))
                            r += dr
                            c += dc
            self.rays[sel] = lines
        lines = self.rays[sel]
        return all(any(cell in lines[d] for d in ds) for cell in self.D)

    def covered_by(self, cfg):
        """Coverage for rules whose direction depends on the source (edge, pointer)."""
        k = ("by", cfg["source"], cfg["dir"], cfg.get("sense"), cfg["verb"])
        if k not in self.cache:
            acc = set()
            for s in self.sources(cfg["source"]):
                for d in _dirs(cfg, s, self.H, self.W):
                    dr, dc = DIRS[d]
                    for e in s[1]:
                        r, c = e[0] + dr, e[1] + dc
                        while 0 <= r < self.H and 0 <= c < self.W:
                            if (r, c) not in s[0]:
                                acc.add((r, c))
                            r += dr
                            c += dc
            self.cache[k] = self.D <= acc
        return self.cache[k]

    def sources(self, sel):
        if sel not in self.srcs:
            self.srcs[sel] = _sources(self.i, self.bg, sel, self.objs)
        return self.srcs[sel]


def _prep(train):
    P = []
    for p in train:
        i, o = (p["input"], p["output"]) if isinstance(p, dict) else (p[0], p[1])
        if not i or not o or len(i) != len(o) or len(i[0]) != len(o[0]):
            return None
        if any(len(row) != len(i[0]) for row in i) or any(len(row) != len(o[0]) for row in o):
            return None
        P.append(_Pair(i, o))
    if not P or all(not p.D for p in P):
        return None
    return P


def _struct_ok(pl, p):
    E = {cell for cell, _, _, _ in pl}
    if not p.D <= E:
        return False
    i, bg, D = p.i, p.bg, p.D
    for (r, c) in E:
        if i[r][c] == bg and (r, c) not in D:
            return False
    return True


def _fit_colour(rule, painted, P):
    if rule == "source":
        return {} if all(p.o[r][c] == s for pl, p in zip(painted, P) for (r, c), s, _, _ in pl) else None
    if rule == "literal":
        cs = {p.o[r][c] for pl, p in zip(painted, P) for (r, c), _, _, _ in pl}
        return {"c": cs.pop()} if len(cs) == 1 else None
    if rule == "context":
        ok = all(p.o[r][c] == (s if x is None else x) for pl, p in zip(painted, P) for (r, c), s, x, _ in pl)
        return {} if ok else None
    if rule == "sequence":
        for phase in (0, 1):
            cs, ok = set(), True
            for pl, p in zip(painted, P):
                for (r, c), s, _, idx in pl:
                    if (idx + phase) % 2 == 1:
                        if p.o[r][c] != s:
                            ok = False
                            break
                    else:
                        cs.add(p.o[r][c])
                if not ok:
                    break
            if ok and len(cs) == 1:
                return {"phase": phase, "c": cs.pop()}
        return None
    if rule == "table":
        m = {}
        for pl, p in zip(painted, P):
            for (r, c), s, _, _ in pl:
                if m.setdefault(s, p.o[r][c]) != p.o[r][c]:
                    return None
        return {"ctab": m}
    return None


def _layered(verb, stop):
    """Does the layer constant (rays/objects pass behind (under) or over other objects) change anything?"""
    return (verb in ("cast", "sweep") and stop in ("border", "length:k", "length:size")) or \
        (verb == "slide" and stop in ("length:k", "length:size"))


def _ddomain(verb):
    return DIAG if verb == "bounce" else AXES if verb == "sweep" else D8


def _fit_dtab(cfg, P, srcsP):
    """Per source colour, the directions under which that source alone is consistent with the output."""
    cand, score, cov = {}, Counter(), {}
    dom = _ddomain(cfg["verb"])
    under = (cfg.get("layer") or "under") == "under"
    slide = cfg["verb"] == "slide"
    for pi, (p, srcs) in enumerate(zip(P, srcsP)):
        for s in srcs:
            ok = set()
            for d in (cand[s[2]] if s[2] in cand else dom):
                c1 = dict(cfg, dir="const", d=d)
                if slide:
                    (_, n, (dr, dc)), = _moves(c1, p.i, p.bg, [s])
                    good, hits = True, 0
                    for r, c in s[0]:
                        y, x = r + n * dr, c + n * dc
                        if n and 0 <= y < p.H and 0 <= x < p.W:
                            if p.o[y][x] == p.i[r][c]:
                                hits += 1
                            elif under and p.i[y][x] != p.bg and (y, x) not in s[0]:
                                continue
                            else:
                                good = False
                                break
                    if good:
                        ok.add(d)
                        score[s[2], d] += hits
                else:
                    try:
                        pl = _painted(c1, p.i, p.bg, [s], D=p.D)
                    except _Reject:
                        continue
                    if all(cell in p.D for cell, _, _, _ in pl if under or p.i[cell[0]][cell[1]] == p.bg):
                        ok.add(d)
                        score[s[2], d] += len(pl)
                        cov.setdefault((pi, s[2], d), set()).update(cell for cell, _, _, _ in pl)
            cand[s[2]] = cand.get(s[2], ok) & ok
            if not cand[s[2]]:
                return
    cols = sorted(cand)
    lists = []
    for c in cols:                          # directions without any evidence are interchangeable: keep one
        ev = sorted((d for d in cand[c] if score[c, d] > 0), key=lambda d: (-score[c, d], dom.index(d)))
        lists.append(ev + [d for d in dom if d in cand[c] and score[c, d] == 0][:1])
    good = 0
    for n, combo in enumerate(itertools.product(*lists)):
        if n >= 512 or good >= 64:
            return
        if not slide:                       # union of single-source paint sets must cover the changed cells
            if not all(p.D <= set().union(*[cov.get((pi, c, d), ()) for c, d in zip(cols, combo)])
                       for pi, p in enumerate(P)):
                continue
        good += 1
        yield dict(zip(cols, combo))


def _param_space(cfg, P, srcsP):
    verb, stop, rdir = cfg["verb"], cfg["stop"], cfg["dir"]
    ks = MENU["fit"]["k"] if stop == "length:k" else [None]
    layers = ["under", "over"] if _layered(verb, stop) else ["under"]
    orders = ["VH", "HV"] if verb == "connect" else [None]
    for layer, order in itertools.product(layers, orders):
        if rdir == "colour_table":
            for k in ks:
                for dt in _fit_dtab(dict(cfg, k=k, layer=layer, order=order), P, srcsP):
                    yield dict(cfg, k=k, layer=layer, order=order, dtab=dt)
            continue
        dps = [{"d": d} for d in _ddomain(verb)] if rdir == "const" else \
            [{"sense": x} for x in ("away", "toward")] if rdir == "edge" else [{}]
        for dp in dps:
            for k in ks:                    # k innermost: fam prunes larger k after a rejection (monotone trails)
                yield dict(cfg, k=k, layer=layer, order=order, **dp)


def _name(cfg):
    parts = [cfg["verb"], cfg["stop"], cfg["dir"]]
    for f in ("d", "sense", "dtab", "k", "order"):
        if cfg.get(f) is not None:
            parts.append("%s=%s" % (f, cfg[f]))
    parts += ["stride=%d" % cfg["stride"], cfg["source"], cfg["colour"]]
    for f in ("c", "phase", "ctab"):
        if cfg.get(f) is not None:
            parts.append("%s=%s" % (f, cfg[f]))
    if cfg.get("layer") == "over":
        parts.append("over")
    return "PATH[" + ",".join(parts) + "]"


MAX_YIELD = 6


def family(node):
    """fam(train) yields (name, cost, fn) for every completion of the node whose fitted constants reproduce all
    training pairs (at most MAX_YIELD, cheapest description first; see _cost)."""
    comps = _comps(node)
    groups = {}
    for cp in comps:
        groups.setdefault(cp[:5], []).append(cp[5])

    def fam(train):
        P = _prep(train)
        if P is None:
            return
        found = []
        for (verb, stop, rdir, stride, sel), colours in groups.items():
            srcsP = [p.sources(sel) for p in P]
            if any(not s for s in srcsP):
                continue
            base = {"verb": verb, "stop": stop, "dir": rdir, "stride": stride, "source": sel, "colour": colours[0]}
            if verb in ("cast", "project", "sweep") and rdir in ("orth4", "diag4", "all8"):
                ds = ORTH if rdir == "orth4" else DIAG if rdir == "diag4" else D8
                if not all(p.covered(sel, ds) for p in P):
                    continue
            dead = set()
            for cfg in _param_space(base, P, srcsP):
                if verb in ("cast", "project", "sweep") and rdir == "const":
                    ds = [cfg["d"], OPP[cfg["d"]]] if verb == "sweep" else [cfg["d"]]
                    if not all(p.covered(sel, ds) for p in P):
                        continue
                elif verb in ("cast", "project") and rdir in ("edge", "pointer"):
                    if not all(p.covered_by(cfg) for p in P):
                        continue
                mono = stop == "length:k" and verb in ("cast", "sweep") and rdir != "colour_table"
                if mono:
                    mk = (cfg["layer"], cfg.get("d"), cfg.get("sense"))
                    if mk in dead:
                        continue
                try:
                    if verb == "slide":
                        if all(_slide(cfg, p.i, p.bg, s) == p.o for p, s in zip(P, srcsP)):
                            found.append(dict(cfg, colour="own"))
                        continue
                    painted = []
                    for p, s in zip(P, srcsP):
                        try:
                            pl = _painted(cfg, p.i, p.bg, s, D=p.D)
                        except _Reject:
                            if mono:
                                dead.add(mk)
                            break
                        if not _struct_ok(pl, p):
                            break
                        painted.append(pl)
                    else:
                        for rule in colours:
                            fit = _fit_colour(rule, painted, P)
                            if fit is None:
                                continue
                            full = dict(cfg, colour=rule, **fit)
                            if all(apply(full, p.i) == p.o for p in P):
                                found.append(full)
                except _Unseen:
                    continue
        progs = sorted(((_cost(c), i, c) for i, c in enumerate(found)), key=lambda t: (t[0], t[1]))
        for cost, _, c in progs[:MAX_YIELD]:
            yield _name(c), cost, (lambda grid, _c=c: apply(_c, grid))
    return fam


_WEIGHT = {
    "verb": {"cast": 0, "sweep": .1, "project": .2, "slide": .2, "bounce": .3, "connect": .3},
    "stop": {"border": 0, "obstacle:before": .1, "obstacle:hit": .2, "length:k": .2, "length:size": .2,
             "target:before": .2},
    "dir": {"const": .1, "orth4": .1, "diag4": .1, "all8": .15, "edge": .2, "pointer": .15, "colour_table": .3,
            "pair": 0},
    "stride": {1: 0, 2: .1},
    "source": {"singleton": 0, "marker": .1, "corner": .15, "smallest": .15, "face": .15, "odd_cell": .15,
               "edge_cell": .15},
    "colour": {"source": 0, "literal": .1, "context": .15, "sequence": .25, "table": .2, "own": 0}}


def _cost(cfg):
    """Description length of a fitted program: dimension values + constants (table entries cost extra)."""
    cost = 1.0 + sum(_WEIGHT[d][cfg[d]] for d in DIMS)
    if cfg["dir"] == "colour_table":
        cost += .1 * len(cfg["dtab"])
    if cfg["colour"] == "table":
        cost += .1 * len(cfg["ctab"])
    if cfg.get("layer") == "over":
        cost += .05
    if cfg["stop"] == "length:k":
        cost += .01 * cfg["k"]
    return round(cost, 3)


# ----------------------------------------------------------------------------------------------- synthetic drawer

def _crc(s):
    return zlib.crc32(s.encode())


def _task_params(comp, rng):
    verb = comp[0]
    cols = list(range(1, 10))
    rng.shuffle(cols)
    prm = {"c": cols[0], "tabsrc": cols[1:3], "ctab": {cols[1]: cols[3], cols[2]: cols[4]},
           "k": rng.randint(2, 4), "layer": rng.choice(["under", "over"]), "sense": rng.choice(["away", "toward"]),
           "order": rng.choice(["VH", "HV"]), "phase": rng.choice([0, 1]), "off": rng.randrange(8)}
    dom = _ddomain(verb)
    prm["d"] = rng.choice(dom)
    while True:
        a, b = rng.sample(dom, 2)
        if verb == "sweep" or OPP[a] != b:
            break
    prm["dtab"] = {cols[1]: a, cols[2]: b}
    prm["avoid"] = {cols[0], cols[3], cols[4]} | (set(cols[1:3]) if comp[2] == "colour_table" or comp[5] == "table" else set())
    return prm


def _cfg_of(comp, prm):
    cfg = dict(zip(DIMS, comp))
    cfg.update({"d": prm["d"], "k": prm["k"], "sense": prm["sense"], "order": prm["order"],
                "phase": prm["phase"], "c": prm["c"], "ctab": prm["ctab"], "dtab": prm["dtab"]})
    cfg["layer"] = prm["layer"] if _layered(comp[0], comp[1]) else "under"
    return cfg


def _ring(cells):
    return {(r + dy, c + dx) for r, c in cells for dy in (-1, 0, 1) for dx in (-1, 0, 1)}


class _Canvas:
    def __init__(self, H, W, rng):
        self.H, self.W, self.rng = H, W, rng
        self.g = [[0] * W for _ in range(H)]
        self.occ = set()

    def fits(self, cells, interior=False):
        for r, c in cells:
            if not (0 <= r < self.H and 0 <= c < self.W) or (r, c) in self.occ:
                return False
            if interior and (r in (0, self.H - 1) or c in (0, self.W - 1)):
                return False
        return True

    def put(self, cells, colours):
        for (r, c), col in zip(cells, colours):
            self.g[r][c] = col
        self.occ |= _ring(cells)

    def place(self, shape, colours, interior=True, at=None, tries=60):
        """shape: list of relative cells; returns absolute cells or None."""
        hs = max(r for r, _ in shape) + 1
        ws = max(c for _, c in shape) + 1
        for _ in range(tries):
            if at is None:
                r0 = self.rng.randint(0, self.H - hs)
                c0 = self.rng.randint(0, self.W - ws)
            else:
                r0, c0 = at
            cells = [(r0 + r, c0 + c) for r, c in shape]
            if self.fits(cells, interior):
                self.put(cells, colours)
                return cells
            if at is not None:
                return None
        return None


def _bar(n, orient):
    if orient == "h":
        return [(0, i) for i in range(n)]
    if orient == "v":
        return [(i, 0) for i in range(n)]
    if orient == "d":
        return [(i, i) for i in range(n)]
    return [(i, n - 1 - i) for i in range(n)]


def _rect(h, w):
    return [(r, c) for r in range(h) for c in range(w)]


def _draw_attempt(cfg, prm, rng, seed=0):
    H, W = rng.randint(9, 15), rng.randint(9, 15)
    cv = _Canvas(H, W, rng)
    verb, stop, rdir, sel, rule = cfg["verb"], cfg["stop"], cfg["dir"], cfg["source"], cfg["colour"]
    tabled = rdir == "colour_table" or rule == "table"
    pool = [x for x in range(1, 10) if x not in prm["avoid"]]
    rng.shuffle(pool)
    interior = sel == "edge_cell"           # only sources may touch the border
    placed = []                             # list of emit-cell tuples (for selector check)
    # ---- sources
    if verb == "connect":
        if sel == "marker":
            mcol = pool[0]
            pair_cols = [mcol]
            for _ in range(2):              # a same-colour singleton pair of a commoner colour (not a marker)
                if not cv.place([(0, 0)], [pool[1]], interior=False):
                    return None
            if not cv.place(_bar(3, rng.choice("hv")), [pool[1]] * 3, interior=False):
                return None
        else:
            pair_cols = pool[:rng.randint(1, 2)] if rule != "literal" else pool[:rng.randint(1, 2)]
        for pc in pair_cols:
            for _ in range(2):
                cells = cv.place([(0, 0)], [pc], interior=False)
                if not cells:
                    return None
                placed.append((cells[0],))
    else:
        if sel == "smallest":
            ns = 1
        elif tabled:
            ns = rng.randint(2, 3)
        elif sel == "face":
            ns = rng.randint(1, 2)
        else:
            ns = rng.randint(1, 3)
        if tabled and (ns == 1 or sel == "marker"):
            scols = [prm["tabsrc"][seed % 2]] * ns
        elif tabled:
            scols = list(prm["tabsrc"]) + [rng.choice(prm["tabsrc"]) for _ in range(ns - 2)]
            rng.shuffle(scols)
        elif sel == "marker":
            scols = [pool[0]] * ns
        else:
            scols = [rng.choice(pool[:3]) for _ in range(ns)]
        body_pool = [x for x in pool if x not in scols] or pool
        for i in range(ns):
            col = scols[i]
            if sel in ("singleton", "marker"):
                cells = cv.place([(0, 0)], [col], interior=False)
                if not cells:
                    return None
                placed.append((cells[0],))
            elif sel == "edge_cell":
                side = rng.choice("NSWE")
                if side in "NS":
                    at = (0 if side == "N" else H - 1, rng.randint(1, W - 2))
                else:
                    at = (rng.randint(1, H - 2), 0 if side == "W" else W - 1)
                cells = cv.place([(0, 0)], [col], interior=False, at=at)
                if not cells:
                    return None
                placed.append((cells[0],))
            elif sel == "corner":
                miss = rng.randrange(4)
                shape = [x for j, x in enumerate(_rect(2, 2)) if j != miss]
                cells = cv.place(shape, [col] * 3, interior=False)
                if not cells:
                    return None
                placed.append(tuple(sorted(cells)))
            elif sel in ("smallest", "face"):
                if sel == "smallest":
                    shape = _bar(2, rng.choice("hv"))
                else:
                    shape = rng.choice([_bar(2, "h"), _bar(3, "h"), _bar(2, "v"), _bar(3, "v"), _rect(2, 2), _rect(2, 3)])
                cells = cv.place(shape, [col] * len(shape), interior=False)
                if not cells:
                    return None
                placed.append(tuple(sorted(cells)))
            elif sel == "odd_cell":
                n = rng.randint(3, 4)
                shape = _bar(n, rng.choice("hvda"))
                body = rng.choice(body_pool)
                if rng.random() < 0.5:
                    colours = [col] + [body] * (n - 1)
                else:
                    colours = [body] * (n - 1) + [col]
                cells = cv.place(shape, colours, interior=False)
                if not cells:
                    return None
                placed.append(tuple(sorted(cells)))
        if sel == "marker":                  # distractor singletons of a commoner colour
            for _ in range(ns + 1):
                if not cv.place([(0, 0)], [pool[3]], interior=False):
                    return None
        elif sel == "edge_cell":             # interior singletons that are not on the border
            for _ in range(rng.randint(1, 2)):
                if not cv.place([(0, 0)], [rng.choice(pool[:3])], interior=True):
                    return None
    # ---- obstacles (non-sources), the first one on some ray's path
    srcs0 = _sources(cv.g, 0, "face" if sel == "smallest" else sel, _objects(cv.g, 0))
    if not srcs0:
        return None
    obs_pool = [x for x in pool[4:] + pool[1:3] if x not in set(v for row in cv.g for v in row)] or pool[4:] or pool
    n_obs = rng.randint(1, 3)
    need_path = stop in ("obstacle:before", "obstacle:hit", "target:before") or verb == "bounce" or \
        _layered(verb, stop) or rng.random() < 0.7
    for j in range(n_obs):
        ocol = obs_pool[j % len(obs_pool)]
        if sel == "face":
            shapes = [[(0, 0)]]
        elif sel == "smallest":
            shapes = [_bar(3, "h"), _bar(3, "v"), _rect(2, 2), _bar(4, "h"), _bar(4, "v")]
        else:
            shapes = [_bar(2, "h"), _bar(2, "v"), _bar(3, "h"), _bar(3, "v"), _rect(2, 2)]
        if verb == "bounce":
            shapes = [_bar(3, "h"), _bar(3, "v"), _bar(4, "h"), _bar(4, "v")]
        shape = rng.choice(shapes)
        if j == 0 and need_path and verb != "connect":
            s = rng.choice(srcs0)
            try:
                ds = _dirs(cfg, s, H, W)
            except _Unseen:
                return None
            if not ds:
                return None
            d = rng.choice(ds)
            dr, dc = DIRS[d]
            e = rng.choice(s[1])
            walk = []
            r, c = e[0] + dr, e[1] + dc
            while 0 <= r < H and 0 <= c < W:
                if (r, c) not in s[0]:
                    walk.append((r, c))
                r, c = r + dr, c + dc
            if len(walk) < 3:
                return None
            hi = len(walk) - 1
            if stop == "length:k":
                hi = min(hi, cfg["k"] - 1)
            elif stop == "length:size":
                hi = min(hi, _extent(s[0], d) - 1)
            if hi < 1:
                return None
            tr, tc = walk[rng.randint(1, hi)]
            ar, ac = rng.choice(shape)
            if not cv.place(shape, [ocol] * len(shape), interior=interior, at=(tr - ar, tc - ac)):
                return None
        else:
            if sel == "smallest" and j == n_obs - 1 and rng.random() < 0.6:
                ocol = srcs0[0][2]          # a big object sharing the source colour (source is then no marker)
            cv.place(shape, [ocol] * len(shape), interior=interior)
    # ---- checks
    g = cv.g
    srcs = _sources(g, 0, sel, _objects(g, 0))
    if sorted(tuple(sorted(s[0])) for s in srcs) != sorted(placed):
        return None
    if _bg(g) != 0:
        return None
    if rdir in ("edge", "pointer"):         # the heading must vary across seeds
        dom = ORTH if rdir == "edge" else DIAG if sel == "corner" else D8 if sel == "odd_cell" else ORTH
        want = dom[(seed + prm["off"]) % len(dom)]
        try:
            if not any(want in _dirs(cfg, x, H, W) for x in srcs):
                return None
        except _Unseen:
            return None
    info = _new_info()
    out = apply(cfg, g, info)
    if out is None or out == g:
        return None
    if _layered(verb, stop):
        if not info["crossed"] or apply(dict(cfg, layer="over" if cfg["layer"] == "under" else "under"), g) == out:
            return None
    for sel2 in MENU["source"]:             # the selector must be visible in every pair
        if sel2 != sel and apply(dict(cfg, source=sel2), g) == out:
            return None
    if verb == "connect":
        if not info["per_src"] or min(info["per_src"]) < 1 or not info["unaligned"]:
            return None
        return g, out
    if not info["per_src"] or max(info["per_src"]) < 1 or (stop != "target:before" and min(info["per_src"]) < 1):
        return None
    if stop == "target:before" and {x[2] for x, n in zip(srcs, info["per_src"]) if n} != {x[2] for x in srcs}:
        return None                         # every source colour must show its effect (tables, colour rules)
    comp = tuple(cfg[d] for d in DIMS)
    for d, alts in (("stop", ("border", "obstacle:before", "obstacle:hit", "length:size", "target:before")),
                    ("stride", (1, 2)), ("dir", ("orth4", "diag4", "all8", "pointer"))):
        if d not in prm["free"]:
            continue                        # free dimensions must be visible in every pair
        i = DIMS.index(d)
        for a in alts:
            alt = comp[:i] + (a,) + comp[i + 1:]
            if a != cfg[d] and _valid(*alt) and apply(dict(cfg, **{d: a}), g) == out:
                return None
    if verb == "slide":
        if info["clipped"] or info.get("collide"):
            return None
        return g, out
    if stop in ("obstacle:before", "obstacle:hit", "target:before") and not info["hits"]:
        return None
    if stop in ("obstacle:before", "target:before") and info["rays"] > 1 and not info["nohit"]:
        return None
    if verb == "bounce" and not info["bounces"]:
        return None
    if (rule == "sequence" or cfg["stride"] == 2) and info["maxlen"] < 3:
        return None
    if rule in ("sequence", "literal"):
        changed = {out[r][c] for r in range(H) for c in range(W) if out[r][c] != g[r][c]}
        if prm["c"] not in changed:
            return None
    if stop in ("length:k", "length:size") and not info["full"]:
        return None
    return g, out


def _draw_cfg(cfg, prm, k, seed, attempts=400):
    rng = random.Random(_crc("%s|%d" % (k, seed)))
    for _ in range(attempts):
        res = _draw_attempt(cfg, prm, rng, seed)
        if res is not None:
            return res
    return None


@lru_cache(maxsize=None)
def _task(k, nt):
    """The concrete generator a node's synthetic task is drawn from: a completion picked by the key hash (the first
    one, in hash order, that can be drawn for seeds 0..3) plus task-level constants."""
    comps = _comps_t(nt)
    h = _crc(k)
    rng = random.Random(h)
    order = list(range(len(comps)))
    rng.shuffle(order)
    first = None
    free = frozenset(d for d in DIMS if d not in dict(nt) or (d == "stop" and dict(nt)[d] in STOPS
                                                                 and len(STOPS[dict(nt)[d]]) > 1))
    for idx in order[:6]:
        comp = comps[idx]
        prm = _task_params(comp, random.Random(h * 31 + idx))
        prm["free"] = free
        cfg = _cfg_of(comp, prm)
        if first is None:
            first = (cfg, prm)
        if all(_draw_cfg(cfg, prm, k, s, attempts=150) is not None for s in range(4)):
            return cfg, prm
    return first


def task_config(node):
    return _task(key(node), _norm(node))[0]


def draw(node, seed):
    """Deterministic synthetic pair (inp, out) drawn from the node, or None."""
    if not _comps(node):
        return None
    k = key(node)
    cfg, prm = _task(k, _norm(node))
    return _draw_cfg(cfg, prm, k, seed)
