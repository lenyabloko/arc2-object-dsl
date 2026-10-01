"""SYMMETRY image schema of the v10 description lattice (Fable guidance v10).

Synthetic only: no ARC data is read here.  Pure stdlib, deterministic.

Lattice
-------
A *configuration* binds every menu field (verb, stop, colour_rule, role:shape,
role:axis and the verb's params).  A *node* is a dict of choices
{field: value}; its generator family is the set of configurations compatible
with it.  Free fields are fitted from training pairs by ``family``.
Depth = number of specialisation steps (schema->verb, stop class->member,
parameter->value, role->selector) below the bare schema; nodes() lists every
distinct node of depth <= 2 (nodes with the same configuration set share a
key and are listed once).

Free values that are never menu choices (fitted per task): literal colour k,
occluder/mask colour m, per-panel dihedral transforms T, the axis line /
marker / pivot positions and colours, and the inferred symmetry centre.

draw(node, seed): seeds 4t..4t+3 form one task t (rule-level choices come
from the task index seed//4, instance-level variation from the seed).
"""
import hashlib
import random

SCHEMA = "SYMMETRY"

D8 = ("rot90", "rot180", "rot270", "flip_lr", "flip_ud", "transpose",
      "antitranspose")
D4_ORDER = ("id",) + D8

# symmetry groups about a centre (R, C) given in doubled coordinates
GROUP_OPS = {
    "H": ("H",), "V": ("V",), "HV": ("H", "V", "R180"), "rot180": ("R180",),
    "D": ("T",), "rot90": ("R90", "R180", "R270"),
    "D4": ("H", "V", "R180", "T", "AT", "R90", "R270"),
}
SQUARE_GROUPS = {"D", "rot90", "D4"}
OPS = {
    "H": lambda r, c, R, C: (r, C - c),
    "V": lambda r, c, R, C: (R - r, c),
    "R180": lambda r, c, R, C: (R - r, C - c),
    "T": lambda r, c, R, C: (c + (R - C) // 2, r - (R - C) // 2),
    "AT": lambda r, c, R, C: ((R + C) // 2 - c, (R + C) // 2 - r),
    "R90": lambda r, c, R, C: (c + (R - C) // 2, (R + C) // 2 - r),
    "R270": lambda r, c, R, C: ((R + C) // 2 - c, r - (R - C) // 2),
}

# ---------------------------------------------------------------- menus
MENU = {
    "verb": ["rotate", "symmetrize", "complete", "reflect", "turn", "fill"],
    "stop": ["none", "border", "occluder"],
    "colour_rule": ["own", "source", "literal", "context"],
    "role:shape": ["whole grid", "object crop", "each object", "panel"],
    "role:axis": ["grid centre", "grid border", "inferred centre", "line",
                  "object edge", "marker", "pivot cell", "object centre",
                  "separators"],
    "param:D": list(D8),
    "param:group": ["H", "V", "HV", "D", "rot90", "rot180", "D4"],
    "param:side": ["left", "right", "up", "down"],
    "param:mask": ["bg", "occluder"],
    "param:keep": ["true", "false"],
    "param:angle": ["90", "180", "270"],
    "param:panels": ["2", "3"],
}
FIELDS = list(MENU)

# provenance of each verb / menu item in the parsed SYMMETRY records
MENU_SOURCES = {
    "rotate": "dihedral D of whole grid or object crop: grp_M046, grp_M128",
    "symmetrize": "overlay G-images about grid centre (grp_M134, oo_47c1f68c, "
                  "oo_2697da3f) or extend grid by mirror copies (oo_6f473927)",
    "complete": "orbit-fill masked/occluded cells; crop occluder (grp_M022, "
                "grp_M147, grp_M169, grp_M072, grp_M054)",
    "reflect": "mirror objects across line / own bbox edge / edge facing a "
               "marker (grp_M021, grp_M052, grp_M155, oo_88207623, "
               "oo_2b01abd0, oo_2bcee788, oo_9d9215db, oo_dc2e9a9d, "
               "pc_mirror_symmetry_completion)",
    "turn": "rotate object +-90/180 about pivot cell or own centre "
            "(grp_M083, len_2b83f449, oo_ecaa0ec1)",
    "fill": "fill empty panels with per-panel dihedral copies of the source "
            "panel (oo_8e5a5113)",
    "not modelled": "d2_4c416de3 corner stamps, d2_db0c5428 annulus unfold, "
                    "grp_M100 compose, oo_bf32578f outline fill, "
                    "len_52df9849 occlusion swap, oo_93c31fbe bracket frames",
}


def _enumerate_configs():
    out = []

    def add(**kw):
        c = dict.fromkeys(FIELDS)
        for k, v in kw.items():
            c[k.replace("__", ":")] = v
        out.append(c)

    for shape in ("whole grid", "object crop"):
        for D in D8:
            add(verb="rotate", role__shape=shape, role__axis="grid centre",
                colour_rule="own", stop="none", param__D=D)
    for group in ("H", "V", "HV", "D", "rot90", "rot180"):
        for col in ("own", "literal"):
            add(verb="symmetrize", role__shape="whole grid",
                role__axis="grid centre", colour_rule=col, stop="none",
                param__group=group)
    for group, side in (("H", "right"), ("H", "left"), ("V", "down"),
                        ("V", "up"), ("HV", None), ("rot90", None)):
        for col in ("own", "literal"):
            add(verb="symmetrize", role__shape="whole grid",
                role__axis="grid border", colour_rule=col, stop="none",
                param__group=group, param__side=side)
    for group in MENU["param:group"]:
        centres = ["grid centre"]
        if group in ("H", "V", "HV", "rot180"):
            centres.append("inferred centre")
        for centre in centres:
            for mask, stop in (("bg", "none"), ("occluder", "none"),
                               ("occluder", "occluder")):
                add(verb="complete", role__shape="whole grid",
                    role__axis=centre, colour_rule="context", stop=stop,
                    param__group=group, param__mask=mask)
    for axis in ("line", "object edge", "marker"):
        cols = ("own", "literal") if axis == "object edge" else \
            ("own", "source", "literal")
        sides = MENU["param:side"] if axis == "object edge" else (None,)
        for side in sides:
            for keep in ("true", "false"):
                for col in cols:
                    for stop in ("none", "border"):
                        add(verb="reflect", role__shape="each object",
                            role__axis=axis, colour_rule=col, stop=stop,
                            param__side=side, param__keep=keep)
    for axis in ("pivot cell", "object centre"):
        for angle in ("90", "180", "270"):
            for keep in ("true", "false"):
                for col in ("own", "literal"):
                    for stop in ("none", "border"):
                        if axis == "object centre" and angle == "180" and \
                                stop == "border":
                            continue  # in-place 180 never leaves the bbox
                        add(verb="turn", role__shape="each object",
                            role__axis=axis, colour_rule=col, stop=stop,
                            param__angle=angle, param__keep=keep)
    for n in ("2", "3"):
        add(verb="fill", role__shape="panel", role__axis="separators",
            colour_rule="own", stop="none", param__panels=n)
    return out


CONFIGS = _enumerate_configs()
_CFG_STR = ["|".join(f"{f}={c[f]}" for f in FIELDS) for c in CONFIGS]
_FULL_VALUES = {f: sorted({str(c[f]) for c in CONFIGS}) for f in FIELDS}

# nodes removed after self-test (generator not drawable / recognisable);
# a pruned node also removes its specialisations.  Empty: the last
# self-test drew and recognised every node.
PRUNED = []


def _choices(node):
    return {f: v for f, v in node.items()
            if not f.startswith("_") and f in MENU}


def compatible(node):
    ch = _choices(node)
    return [i for i, c in enumerate(CONFIGS)
            if all(c.get(f) == v for f, v in ch.items())]


def key(node):
    idxs = compatible(node)
    if not idxs:
        return SCHEMA + "{bottom}"
    parts = []
    for f in FIELDS:
        vals = sorted({str(CONFIGS[i][f]) for i in idxs})
        if vals != _FULL_VALUES[f]:
            parts.append(f + "=" + "/".join(vals))
    h = hashlib.sha1("\n".join(sorted(_CFG_STR[i] for i in idxs))
                     .encode()).hexdigest()[:8]
    return SCHEMA + "{" + ";".join(parts) + "}#" + h


def nodes():
    singles = [(f, v) for f in FIELDS for v in MENU[f] if compatible({f: v})]
    seen = set()
    res = []
    pruned_sets = [frozenset(compatible(p)) for p in PRUNED]

    def push(ch, depth):
        idxs = frozenset(compatible(ch))
        if not idxs or idxs in seen:
            return
        seen.add(idxs)
        if any(idxs <= s for s in pruned_sets):
            return
        n = dict(ch)
        n["_depth"] = depth
        res.append(n)

    push({}, 0)
    for f, v in singles:
        push({f: v}, 1)
    for i, (f1, v1) in enumerate(singles):
        for f2, v2 in singles[i + 1:]:
            if f1 != f2:
                push({f1: v1, f2: v2}, 2)
    return res


# ---------------------------------------------------------------- grids
def dims(g):
    return len(g), (len(g[0]) if g else 0)


def copy(g):
    return [row[:] for row in g]


def blank(h, w, v=0):
    return [[v] * w for _ in range(h)]


def dihedral(op, g):
    h, w = dims(g)
    if op == "id":
        return copy(g)
    if op == "rot90":
        return [[g[h - 1 - j][i] for j in range(h)] for i in range(w)]
    if op == "rot180":
        return [[g[h - 1 - i][w - 1 - j] for j in range(w)] for i in range(h)]
    if op == "rot270":
        return [[g[j][w - 1 - i] for j in range(h)] for i in range(w)]
    if op == "flip_lr":
        return [row[::-1] for row in g]
    if op == "flip_ud":
        return [row[:] for row in g[::-1]]
    if op == "transpose":
        return [[g[j][i] for j in range(h)] for i in range(w)]
    if op == "antitranspose":
        return [[g[h - 1 - j][w - 1 - i] for j in range(h)] for i in range(w)]
    raise ValueError(op)


def crop_nonbg(g):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v]
    if not cells:
        return None
    r0, r1, c0, c1 = bbox(cells)
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def bbox(cells):
    rs = [r for r, _ in cells]
    cs = [c for _, c in cells]
    return min(rs), max(rs), min(cs), max(cs)


_COMP_CACHE = {}


def components(g):
    """8-connected multicolour components of non-zero cells (sorted)."""
    k = tuple(map(tuple, g))
    got = _COMP_CACHE.get(k)
    if got is not None:
        return got
    h, w = dims(g)
    seen = [[False] * w for _ in range(h)]
    comps = []
    for r0 in range(h):
        for c0 in range(w):
            if g[r0][c0] and not seen[r0][c0]:
                stack = [(r0, c0)]
                seen[r0][c0] = True
                cells = []
                while stack:
                    r, c = stack.pop()
                    cells.append((r, c))
                    for dr in (-1, 0, 1):
                        for dc in (-1, 0, 1):
                            rr, cc = r + dr, c + dc
                            if 0 <= rr < h and 0 <= cc < w and \
                                    not seen[rr][cc] and g[rr][cc]:
                                seen[rr][cc] = True
                                stack.append((rr, cc))
                cells.sort()
                comps.append(cells)
    if len(_COMP_CACHE) > 4096:
        _COMP_CACHE.clear()
    _COMP_CACHE[k] = comps
    return comps


def full_lines(g):
    h, w = dims(g)
    res = []
    for r in range(h):
        v = g[r][0]
        if v and all(x == v for x in g[r]):
            res.append(("row", r, v))
    for c in range(w):
        v = g[0][c]
        if v and all(g[r][c] == v for r in range(h)):
            res.append(("col", c, v))
    return res


def _paint(out, imgs, stop):
    h, w = dims(out)
    for (rr, cc), v in imgs:
        if 0 <= rr < h and 0 <= cc < w:
            if out[rr][cc] == 0:
                out[rr][cc] = v
        elif stop == "none":
            return False
    return True


def _mirror_side(r, c, box, side):
    r0, r1, c0, c1 = box
    if side == "right":
        return r, 2 * c1 + 1 - c
    if side == "left":
        return r, 2 * c0 - 1 - c
    if side == "down":
        return 2 * r1 + 1 - r, c
    return 2 * r0 - 1 - r, c


# ---------------------------------------------------------------- generators
def _apply_rotate(cfg, tp, g):
    src = g if cfg["role:shape"] == "whole grid" else crop_nonbg(g)
    if src is None:
        return None
    return dihedral(cfg["param:D"], src)


def _apply_symmetrize(cfg, tp, g):
    h, w = dims(g)
    group = cfg["param:group"]
    lit = cfg["colour_rule"] == "literal"
    k = tp.get("k")
    if lit and k is None:
        return None
    if not any(v for row in g for v in row):
        return None
    if cfg["role:axis"] == "grid centre":
        if group in SQUARE_GROUPS and h != w:
            return None
        ops = [OPS[o] for o in GROUP_OPS[group]]
        R, C = h - 1, w - 1
        out = copy(g)
        for r in range(h):
            for c in range(w):
                v = g[r][c]
                if not v:
                    continue
                for op in ops:
                    rr, cc = op(r, c, R, C)
                    if 0 <= rr < h and 0 <= cc < w and g[rr][cc] == 0 \
                            and out[rr][cc] == 0:
                        out[rr][cc] = k if lit else v
        return out
    if lit:
        def rec(b):
            return [[(k if v else 0) for v in row] for row in b]
    else:
        def rec(b):
            return b
    side = cfg["param:side"]
    if group == "H":
        m = rec(dihedral("flip_lr", g))
        if side == "right":
            return [a + b for a, b in zip(g, m)]
        return [b + a for a, b in zip(g, m)]
    if group == "V":
        m = rec(dihedral("flip_ud", g))
        return copy(g) + m if side == "down" else m + copy(g)
    if group == "HV":
        tl, tr = g, rec(dihedral("flip_lr", g))
        bl, br = rec(dihedral("flip_ud", g)), rec(dihedral("rot180", g))
    else:  # rot90 pinwheel
        if h != w:
            return None
        tl, tr = g, rec(dihedral("rot90", g))
        br, bl = rec(dihedral("rot180", g)), rec(dihedral("rot270", g))
    return [a + b for a, b in zip(tl, tr)] + [a + b for a, b in zip(bl, br)]


def _fill_sym(g, m, ops, R, C):
    h, w = dims(g)
    agree = 0
    for r in range(h):
        row = g[r]
        for c in range(w):
            v = row[c]
            if v == m:
                continue
            for op in ops:
                rr, cc = op(r, c, R, C)
                if 0 <= rr < h and 0 <= cc < w:
                    u = g[rr][cc]
                    if u != m:
                        if u != v:
                            return None
                        agree += 1
    out = copy(g)
    for r in range(h):
        for c in range(w):
            if g[r][c] == m:
                val = None
                for op in ops:
                    rr, cc = op(r, c, R, C)
                    if 0 <= rr < h and 0 <= cc < w and g[rr][cc] != m:
                        val = g[rr][cc]
                        break
                if val is None:
                    return None
                out[r][c] = val
    return out, agree


CENTRE_WIN = 5  # inferred centre searched within +-5 half-cells of grid centre


def _infer_fill(g, m, group, ops):
    h, w = dims(g)
    dRs = [0] if group == "H" else range(-CENTRE_WIN, CENTRE_WIN + 1)
    dCs = [0] if group == "V" else range(-CENTRE_WIN, CENTRE_WIN + 1)
    best = None
    for dR in dRs:
        for dC in dCs:
            res = _fill_sym(g, m, ops, h - 1 + dR, w - 1 + dC)
            if res is None:
                continue
            score = (res[1], -(abs(dR) + abs(dC)))
            if best is None or score > best[0]:
                best = (score, res)
    return best[1] if best else None


def _apply_complete(cfg, tp, g):
    h, w = dims(g)
    m = 0 if cfg["param:mask"] == "bg" else tp.get("m")
    if m is None:
        return None
    group = cfg["param:group"]
    nm = sum(row.count(m) for row in g)
    if nm == 0 or nm == h * w:
        return None
    ops = [OPS[o] for o in GROUP_OPS[group]]
    if cfg["role:axis"] == "grid centre":
        if group in SQUARE_GROUPS and h != w:
            return None
        res = _fill_sym(g, m, ops, h - 1, w - 1)
    else:
        res = _infer_fill(g, m, group, ops)
    if res is None:
        return None
    out = res[0]
    if cfg["stop"] == "occluder":
        cells = [(r, c) for r in range(h) for c in range(w) if g[r][c] == m]
        r0, r1, c0, c1 = bbox(cells)
        if len(cells) != (r1 - r0 + 1) * (c1 - c0 + 1):
            return None
        return [row[c0:c1 + 1] for row in out[r0:r1 + 1]]
    return out


def _apply_reflect(cfg, tp, g):
    h, w = dims(g)
    keep = cfg["param:keep"] == "true"
    col = cfg["colour_rule"]
    k = tp.get("k")
    if col == "literal" and k is None:
        return None
    axis = cfg["role:axis"]
    out = copy(g)
    imgs, erase = [], []
    if axis == "line":
        lines = full_lines(g)
        if len(lines) != 1:
            return None
        kind, L, a = lines[0]
        for r in range(h):
            for c in range(w):
                if not g[r][c] or (r == L if kind == "row" else c == L):
                    continue
                q = (2 * L - r, c) if kind == "row" else (r, 2 * L - c)
                v = g[r][c] if col == "own" else (a if col == "source" else k)
                imgs.append((q, v))
                erase.append((r, c))
        if not imgs:
            return None
    elif axis == "object edge":
        comps = components(g)
        if not comps:
            return None
        side = cfg["param:side"]
        for cells in comps:
            box = bbox(cells)
            for r, c in cells:
                imgs.append((_mirror_side(r, c, box, side),
                             g[r][c] if col == "own" else k))
                erase.append((r, c))
    else:  # marker
        comps = components(g)
        markers = [cs[0] for cs in comps if len(cs) == 1]
        objs = [cs for cs in comps if len(cs) >= 2]
        if not markers or not objs:
            return None
        used = []
        for cells in objs:
            box = bbox(cells)
            r0, r1, c0, c1 = box
            best = None
            for mr, mc in markers:
                if r0 <= mr <= r1 and mc > c1:
                    d = (mc - c1, "right")
                elif r0 <= mr <= r1 and mc < c0:
                    d = (c0 - mc, "left")
                elif c0 <= mc <= c1 and mr > r1:
                    d = (mr - r1, "down")
                elif c0 <= mc <= c1 and mr < r0:
                    d = (r0 - mr, "up")
                else:
                    continue
                if best is None or d[0] < best[0]:
                    best = (d[0], d[1], (mr, mc))
            if best is None:
                return None
            mr, mc = best[2]
            used.append((mr, mc))
            mcol = g[mr][mc]
            for r, c in cells:
                v = g[r][c] if col == "own" else (mcol if col == "source"
                                                  else k)
                imgs.append((_mirror_side(r, c, box, best[1]), v))
                erase.append((r, c))
        for mr, mc in used:
            out[mr][mc] = 0
    if not keep:
        for r, c in erase:
            out[r][c] = 0
    if not _paint(out, imgs, cfg["stop"]):
        return None
    return out


def _rot(r, c, R, C, angle):
    dr, dc = 2 * r - R, 2 * c - C
    if angle == "90":
        dr, dc = dc, -dr
    elif angle == "180":
        dr, dc = -dr, -dc
    else:
        dr, dc = -dc, dr
    return (R + dr) // 2, (C + dc) // 2


def _apply_turn(cfg, tp, g):
    comps = [cs for cs in components(g) if len(cs) >= 2]
    if not comps:
        return None
    angle = cfg["param:angle"]
    keep = cfg["param:keep"] == "true"
    col = cfg["colour_rule"]
    k = tp.get("k")
    if col == "literal" and k is None:
        return None
    out = copy(g)
    imgs, erase = [], []
    for cells in comps:
        if cfg["role:axis"] == "pivot cell":
            cnt = {}
            for r, c in cells:
                cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
            ones = [v for v, n in cnt.items() if n == 1]
            if len(cnt) < 2 or len(ones) != 1:
                return None
            P = next(p for p in cells if g[p[0]][p[1]] == ones[0])
            R, C = 2 * P[0], 2 * P[1]
            body = [p for p in cells if p != P]
        else:
            r0, r1, c0, c1 = bbox(cells)
            R, C = r0 + r1, c0 + c1
            if angle != "180" and (R - C) % 2:
                return None
            body = cells
        for r, c in body:
            imgs.append((_rot(r, c, R, C, angle),
                         g[r][c] if col == "own" else k))
        if not keep:
            erase.extend(body)
    for r, c in erase:
        out[r][c] = 0
    if not _paint(out, imgs, cfg["stop"]):
        return None
    return out


def _runs(n, seps):
    runs, cur = [], []
    for i in range(n):
        if i in seps:
            if cur:
                runs.append((cur[0], cur[-1]))
            cur = []
        else:
            cur.append(i)
    if cur:
        runs.append((cur[0], cur[-1]))
    return runs


def panels(g):
    h, w = dims(g)
    lines = full_lines(g)
    rows = {L for kind, L, _ in lines if kind == "row"}
    cols = {L for kind, L, _ in lines if kind == "col"}
    if (rows and cols) or not (rows or cols):
        return None
    if cols:
        boxes = [(0, h - 1, a, b) for a, b in _runs(w, cols)]
    else:
        boxes = [(a, b, 0, w - 1) for a, b in _runs(h, rows)]
    sizes = {(b[1] - b[0], b[3] - b[2]) for b in boxes}
    if len(boxes) < 2 or len(sizes) != 1:
        return None
    return boxes


def _sub(g, box):
    r0, r1, c0, c1 = box
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]


def _apply_fill(cfg, tp, g):
    boxes = panels(g)
    n = int(cfg["param:panels"])
    T = tp.get("T")
    if boxes is None or len(boxes) != n or T is None or len(T) != n - 1:
        return None
    src = _sub(g, boxes[0])
    if not any(any(row) for row in src):
        return None
    out = copy(g)
    for i in range(1, n):
        img = dihedral(T[i - 1], src)
        a0, a1, b0, b1 = boxes[i]
        if dims(img) != (a1 - a0 + 1, b1 - b0 + 1):
            return None
        for r in range(a1 - a0 + 1):
            out[a0 + r][b0:b1 + 1] = img[r]
    return out


APPLY = {"rotate": _apply_rotate, "symmetrize": _apply_symmetrize,
         "complete": _apply_complete, "reflect": _apply_reflect,
         "turn": _apply_turn, "fill": _apply_fill}


def apply_cfg(cfg, tp, g):
    if not g or not g[0]:
        return None
    return APPLY[cfg["verb"]](cfg, tp, g)


# ---------------------------------------------------------------- drawers
def _palette(rng, n, exclude=()):
    cols = [c for c in range(1, 10) if c not in exclude]
    rng.shuffle(cols)
    return cols[:n]


def _blob(rng, bh, bw):
    """4-connected random cell set whose bbox is exactly bh x bw."""
    cells = {(rng.randrange(bh), rng.randrange(bw))}
    lo = max(bh, bw)
    target = rng.randint(lo, max(lo, (bh * bw * 3) // 4))
    while True:
        rs = {r for r, _ in cells}
        cs = {c for _, c in cells}
        if len(rs) == bh and len(cs) == bw and len(cells) >= target:
            break
        front = sorted({(r + dr, c + dc) for r, c in cells
                        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))
                        if 0 <= r + dr < bh and 0 <= c + dc < bw} - cells)
        if not front:
            break
        cells.add(rng.choice(front))
    return sorted(cells)


def _put(g, cells, r0, c0, pal, rng):
    for r, c in cells:
        g[r0 + r][c0 + c] = rng.choice(pal)


def _draw_rotate(cfg, tp, rng):
    pal = _palette(rng, rng.randint(2, 3))
    if cfg["role:shape"] == "whole grid":
        h, w = rng.randint(3, 6), rng.randint(3, 6)
        g = [[rng.choice(pal) if rng.random() < 0.55 else 0
              for _ in range(w)] for _ in range(h)]
        s = rng.randrange(4)
        for i in range(h):
            for j in range(w):
                if (s == 0 and i == 0) or (s == 1 and i == h - 1) or \
                        (s == 2 and j == 0) or (s == 3 and j == w - 1):
                    g[i][j] = 0
        if sum(1 for row in g for v in row if v) < 3:
            return None
        return g, None
    H, W = rng.randint(7, 12), rng.randint(7, 12)
    bh, bw = rng.randint(2, 4), rng.randint(2, 4)
    if bh == bw == 2:
        bw = 3
    box = [[rng.choice(pal) if rng.random() < 0.6 else 0 for _ in range(bw)]
           for _ in range(bh)]
    cb = crop_nonbg(box)
    if cb is None or dims(cb) != (bh, bw):
        return None
    g = blank(H, W)
    r0, c0 = rng.randint(0, H - bh), rng.randint(0, W - bw)
    for r in range(bh):
        g[r0 + r][c0:c0 + bw] = box[r]
    return g, None


def _draw_symmetrize(cfg, tp, rng):
    group = cfg["param:group"]
    pal = _palette(rng, rng.randint(2, 3), exclude={tp["k"]})
    if cfg["role:axis"] == "grid centre":
        if group in SQUARE_GROUPS:
            h = w = rng.randint(4, 10)
        else:
            h, w = rng.randint(4, 12), rng.randint(4, 12)
        ops = [OPS[o] for o in GROUP_OPS[group]]
        R, C = h - 1, w - 1
        reps = []
        for r in range(h):
            for c in range(w):
                orb = {(r, c)} | {op(r, c, R, C) for op in ops}
                if len(orb) > 1 and (r, c) == min(orb):
                    reps.append((r, c))
        dens = rng.uniform(0.2, 0.45)
        g = blank(h, w)
        n = 0
        for r, c in reps:
            if rng.random() < dens:
                g[r][c] = rng.choice(pal)
                n += 1
        return (g, None) if n >= 2 else None
    if group in ("H", "V"):
        h, w = rng.randint(2, 7), rng.randint(2, 7)
    elif group == "HV":
        h, w = rng.randint(2, 6), rng.randint(2, 6)
    else:
        h = w = rng.randint(2, 6)
    g = [[rng.choice(pal) if rng.random() < 0.5 else 0 for _ in range(w)]
         for _ in range(h)]
    if sum(1 for row in g for v in row if v) < 2:
        return None
    return g, None


def _draw_complete(cfg, tp, rng):
    group = cfg["param:group"]
    ops = [OPS[o] for o in GROUP_OPS[group]]
    bgmask = cfg["param:mask"] == "bg"
    m = 0 if bgmask else tp["m"]
    if group in SQUARE_GROUPS:
        h = w = rng.randint(6, 12)
    else:
        h, w = rng.randint(6, 14), rng.randint(6, 14)
    R, C = h - 1, w - 1
    if cfg["role:axis"] == "inferred centre":
        dR = dC = 0
        while dR == 0 and dC == 0:
            dR = 0 if group == "H" else rng.randint(-4, 4)
            dC = 0 if group == "V" else rng.randint(-4, 4)
        R, C = R + dR, C + dC
    parent = {}

    def find(p):
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    cells = [(r, c) for r in range(h) for c in range(w)]
    for p in cells:
        parent[p] = p
    images = {}
    for r, c in cells:
        ims = []
        for op in ops:
            q = op(r, c, R, C)
            if 0 <= q[0] < h and 0 <= q[1] < w and q != (r, c):
                ims.append(q)
                a, b = find((r, c)), find(q)
                if a != b:
                    parent[max(a, b)] = min(a, b)
        images[(r, c)] = ims
    if bgmask:
        pal = _palette(rng, rng.randint(3, 5))
    else:
        pal = _palette(rng, rng.randint(2, 4), exclude={m})
        if rng.random() < 0.5:
            pal.append(0)
    colour = {}
    pic = blank(h, w)
    for p in cells:
        rt = find(p)
        if rt not in colour:
            colour[rt] = rng.choice(pal)
        pic[p[0]][p[1]] = colour[rt]
    masked = set()
    for _ in range(1 if not bgmask else rng.randint(1, 2)):
        for _a in range(40):
            if bgmask:
                rh, rw = rng.randint(1, 3), rng.randint(1, 3)
            else:
                rh, rw = rng.randint(2, 4), rng.randint(2, 4)
            r0, c0 = rng.randint(0, h - rh), rng.randint(0, w - rw)
            new = masked | {(r0 + i, c0 + j) for i in range(rh)
                            for j in range(rw)}
            if all(any(q not in new for q in images[p]) for p in new):
                masked = new
                break
    if not masked:
        return None
    inp = copy(pic)
    for r, c in masked:
        inp[r][c] = m
    if cfg["stop"] == "occluder":
        r0, r1, c0, c1 = bbox(list(masked))
        return inp, _sub(pic, (r0, r1, c0, c1))
    return inp, pic


def _draw_reflect(cfg, tp, rng):
    axis = cfg["role:axis"]
    border = cfg["stop"] == "border"
    k = tp["k"]
    if axis == "line":
        H, W = rng.randint(9, 15), rng.randint(9, 15)
        a = _palette(rng, 1, exclude={k})[0]
        pal = _palette(rng, rng.randint(1, 2), exclude={a, k})
        bh, bw = rng.randint(2, 4), rng.randint(2, 5)
        d = rng.randint(0, 2)
        if border:
            lo, hi = max(d + bh, H - d - bh), H - 2 - d
        else:
            lo, hi = d + bh, H - 1 - d - bh
        if lo > hi:
            return None
        L = rng.randint(lo, hi)
        g = blank(H, W)
        g[L] = [a] * W
        c0 = rng.randint(0, W - bw)
        _put(g, _blob(rng, bh, bw), L - d - bh, c0, pal, rng)
        if not border and rng.random() < 0.5:   # second object, same side
            bh2, bw2, d2 = rng.randint(1, 3), rng.randint(2, 3), \
                rng.randint(0, 2)
            r2 = L - d2 - bh2
            cands = [c for c in range(0, W - bw2 + 1)
                     if c + bw2 < c0 - 1 or c > c0 + bw]
            if r2 >= 0 and L + d2 + bh2 <= H - 1 and cands:
                _put(g, _blob(rng, bh2, bw2), r2, rng.choice(cands), pal, rng)
        if rng.random() < 0.5:
            g = dihedral("flip_ud", g)
        if rng.random() < 0.5:
            g = dihedral("transpose", g)
        return g, None
    H, W = rng.randint(8, 14), rng.randint(8, 14)
    g = blank(H, W)
    if axis == "object edge":
        pal = _palette(rng, rng.randint(1, 2), exclude={k})
        reserved = set()
        placed = 0
        for i in range(rng.randint(1, 2)):
            for _a in range(30):
                bh, bw = rng.randint(2, 4), rng.randint(2, 4)
                r0 = rng.randint(0, H - bh)
                if border and i == 0:
                    c1 = rng.randint(W - bw, W - 2)
                elif not border:
                    if bw - 1 > W - 1 - bw:
                        continue
                    c1 = rng.randint(bw - 1, W - 1 - bw)
                else:
                    c1 = rng.randint(bw - 1, W - 2)
                c0 = c1 - bw + 1
                if c0 < 0:
                    continue
                region = {(r, c) for r in range(r0 - 1, r0 + bh + 1)
                          for c in range(c0 - 1, c1 + bw + 2)}
                if region & reserved:
                    continue
                reserved |= region
                _put(g, _blob(rng, bh, bw), r0, c0, pal, rng)
                placed += 1
                break
        if not placed:
            return None
        op = {"right": "id", "left": "flip_lr", "down": "transpose",
              "up": "antitranspose"}[cfg["param:side"]]
        return dihedral(op, g), None
    # marker
    mk = _palette(rng, 1, exclude={k})[0]
    pal = _palette(rng, rng.randint(1, 2), exclude={mk, k})
    bh = rng.randint(2, 4)
    bw = rng.randint(3, 4) if border else rng.randint(2, 4)
    cells = _blob(rng, bh, bw)
    if len(cells) < 3:
        return None
    r0 = rng.randint(0, H - bh)
    if border:
        lo, hi = W - bw, W - 3
    else:
        lo, hi = bw - 1, W - 1 - max(bw, 2)
    if lo > hi:
        return None
    c1 = rng.randint(lo, hi)
    c0 = c1 - bw + 1
    _put(g, cells, r0, c0, pal, rng)
    g[rng.randint(r0, r0 + bh - 1)][c1 + 2] = mk
    op = rng.choice(["id", "flip_lr", "transpose", "antitranspose"])
    return dihedral(op, g), None


def _draw_turn(cfg, tp, rng):
    k = tp["k"]
    H, W = rng.randint(8, 14), rng.randint(8, 14)
    g = blank(H, W)
    reserved = set()
    placed = 0
    for i in range(rng.randint(1, 2)):
        for _a in range(30):
            if cfg["role:axis"] == "pivot cell":
                pv, bc = _palette(rng, 2, exclude={k})
                pr, pc = rng.randint(0, H - 1), rng.randint(0, W - 1)
                arm = []
                nb = [(pr + dr, pc + dc) for dr, dc in
                      ((1, 0), (-1, 0), (0, 1), (0, -1))]
                cur = rng.choice(nb)
                for _s in range(rng.randint(2, 4)):
                    if cur == (pr, pc) or cur in arm or \
                            max(abs(cur[0] - pr), abs(cur[1] - pc)) > 3:
                        break
                    arm.append(cur)
                    r, c = cur
                    cur = rng.choice([(r + 1, c), (r - 1, c), (r, c + 1),
                                      (r, c - 1)])
                if len(arm) < 2:
                    continue
                cells = [(pr, pc)] + arm
                if not all(0 <= r < H and 0 <= c < W for r, c in cells):
                    continue
                region = {(pr + a, pc + b) for a in range(-4, 5)
                          for b in range(-4, 5)}
                if region & reserved:
                    continue
                reserved |= region
                g[pr][pc] = pv
                for r, c in arm:
                    g[r][c] = bc
            else:
                bh = rng.randint(2, 4)
                if cfg["param:angle"] == "180":
                    bw = rng.randint(2, 4)
                else:
                    bw = rng.choice([x for x in (2, 3, 4) if (x - bh) % 2 == 0])
                r0, c0 = rng.randint(0, H - bh), rng.randint(0, W - bw)
                s = max(bh, bw)
                cr, cc = r0 + bh // 2, c0 + bw // 2
                region = {(cr + a, cc + b) for a in range(-s - 1, s + 2)
                          for b in range(-s - 1, s + 2)}
                if region & reserved:
                    continue
                reserved |= region
                pal = _palette(rng, 2, exclude={k})
                _put(g, _blob(rng, bh, bw), r0, c0, pal, rng)
            placed += 1
            break
    if not placed:
        return None
    return g, None


def _draw_fill(cfg, tp, rng):
    n = int(cfg["param:panels"])
    s = rng.randint(3, 5)
    pal = _palette(rng, rng.randint(2, 3))
    sep = _palette(rng, 1, exclude=set(pal))[0]
    for _a in range(30):
        src = [[rng.choice(pal) if rng.random() < 0.55 else 0
                for _ in range(s)] for _ in range(s)]
        imgs = {tuple(map(tuple, dihedral(op, src))) for op in D4_ORDER}
        if len(imgs) < 8:
            continue
        if any(len(set(row)) == 1 and row[0] for row in src) or \
                any(len({src[r][c] for r in range(s)}) == 1 and src[0][c]
                    for c in range(s)):
            continue
        break
    else:
        return None
    w = n * s + n - 1
    g = blank(s, w)
    for r in range(s):
        g[r][0:s] = src[r]
        for j in range(1, n):
            g[r][j * (s + 1) - 1] = sep
    if rng.random() < 0.5:
        g = dihedral("transpose", g)
    return g, None


DRAW = {"rotate": _draw_rotate, "symmetrize": _draw_symmetrize,
        "complete": _draw_complete, "reflect": _draw_reflect,
        "turn": _draw_turn, "fill": _draw_fill}


def _task_params(cfg, trng):
    tp = {"k": trng.randint(1, 9), "m": trng.randint(1, 9)}
    if cfg["verb"] == "fill":
        tp["T"] = [trng.choice(D8) for _ in range(int(cfg["param:panels"]) - 1)]
    return tp


def _differs_beyond_stop(a, b):
    return any(a[f] != b[f] for f in FIELDS if f != "stop")


def _benign(cfg, o):
    """o reproduces cfg on the drawn input but is ranked below it by
    family and agrees with it on every input drawn for cfg: a subgroup
    fill, or the inferred-centre version of a grid-centre fill."""
    if cfg["verb"] != "complete":
        return False
    diff = {f for f in FIELDS if f != "stop" and cfg[f] != o[f]}
    if not diff <= {"param:group", "role:axis"}:
        return False
    if "role:axis" in diff and not (cfg["role:axis"] == "grid centre" and
                                    o["role:axis"] == "inferred centre"):
        return False
    return set(GROUP_OPS[o["param:group"]]) <= \
        set(GROUP_OPS[cfg["param:group"]])


def draw(node, seed):
    idxs = compatible(node)
    if not idxs:
        return None
    kk = key(node)
    trng = random.Random(f"{kk}|task{seed // 4}")
    ci = idxs[trng.randrange(len(idxs))]
    cfg = CONFIGS[ci]
    tp = _task_params(cfg, trng)
    rng = random.Random(f"{kk}|seed{seed}")
    others = [CONFIGS[j] for j in idxs if j != ci and
              CONFIGS[j]["verb"] == cfg["verb"] and
              _differs_beyond_stop(cfg, CONFIGS[j]) and
              not _benign(cfg, CONFIGS[j])]
    alt_none = dict(cfg, stop="none") if cfg["stop"] == "border" else None
    for _attempt in range(80):
        got = DRAW[cfg["verb"]](cfg, tp, rng)
        if got is None:
            continue
        inp, expect = got
        out = apply_cfg(cfg, tp, inp)
        if out is None or out == inp:
            continue
        if expect is not None and out != expect:
            continue
        h, w = dims(out)
        if h > 20 or w > 20 or h < 1 or w < 1:
            continue
        if alt_none is not None:
            # clipped somewhere, yet part of the image stays visible
            if apply_cfg(alt_none, tp, inp) is not None:
                continue
            if not any(a == 0 and b != 0 for ra, rb in zip(inp, out)
                       for a, b in zip(ra, rb)):
                continue
        if any(apply_cfg(o, tp, inp) == out for o in others):
            continue
        return inp, out
    return None


# ---------------------------------------------------------------- family
VERB_COST = {"rotate": 1.0, "symmetrize": 1.5, "complete": 1.5,
             "reflect": 2.0, "turn": 2.0, "fill": 2.0}


def _cost(cfg):
    c = VERB_COST[cfg["verb"]]
    c += {"own": 0.0, "context": 0.0, "source": 0.1, "literal": 0.3}[
        cfg["colour_rule"]]
    c += {"none": 0.0, "border": 0.05, "occluder": 0.1}[cfg["stop"]]
    c += {"object crop": 0.2}.get(cfg["role:shape"], 0.0)
    c += {"grid border": 0.1, "inferred centre": 0.3, "object edge": 0.1,
          "marker": 0.2, "object centre": 0.1}.get(cfg["role:axis"], 0.0)
    if cfg["verb"] == "complete":   # prefer the largest consistent group
        c -= 0.03 * len(GROUP_OPS[cfg["param:group"]])
        c += 0.01 if cfg["param:mask"] == "occluder" else 0.0
    if cfg["param:keep"] == "false":
        c += 0.02
    return round(c, 4)


def _name(cfg, tp):
    parts = [f"{f.split(':')[-1]}={cfg[f]}" for f in FIELDS
             if f != "verb" and cfg[f] is not None]
    for t in ("k", "m", "T"):
        if t in tp:
            parts.append(f"{t}={tp[t]}")
    return f"{SCHEMA}/{cfg['verb']}(" + ",".join(parts) + ")"


def _norm_train(train):
    res = []
    for p in train:
        if isinstance(p, dict):
            res.append((p["input"], p["output"]))
        else:
            res.append((p[0], p[1]))
    return res


def _derive_m(cfg, train, cache):
    ck = (cfg["stop"], cfg["param:mask"])
    if ck in cache:
        return cache[ck]
    m = None
    if cfg["stop"] == "occluder":
        cand = None
        for x, y in train:
            h, w = dims(x)
            here = set()
            for colr in {v for row in x for v in row}:
                if colr == 0:
                    continue
                cells = [(r, c) for r in range(h) for c in range(w)
                         if x[r][c] == colr]
                r0, r1, c0, c1 = bbox(cells)
                if len(cells) == (r1 - r0 + 1) * (c1 - c0 + 1) and \
                        (r1 - r0 + 1, c1 - c0 + 1) == dims(y):
                    here.add(colr)
            cand = here if cand is None else cand & here
        if cand:
            m = min(cand)
    else:
        vals = set()
        for x, y in train:
            if dims(x) != dims(y):
                vals = None
                break
            for rx, ry in zip(x, y):
                for a, b in zip(rx, ry):
                    if a != b:
                        vals.add(a)
        if vals and len(vals) == 1:
            m = vals.pop()
    if m is not None:
        if cfg["param:mask"] == "bg" and m != 0:
            m = None
        if cfg["param:mask"] == "occluder" and m == 0:
            m = None
    cache[ck] = m
    return m


def _derive_T(cfg, train):
    n = int(cfg["param:panels"])
    cands = None
    for x, y in train:
        boxes = panels(x)
        if boxes is None or len(boxes) != n or dims(x) != dims(y):
            return None
        src = _sub(x, boxes[0])
        here = []
        for i in range(1, n):
            tgt = _sub(y, boxes[i])
            here.append([op for op in D4_ORDER if dihedral(op, src) == tgt])
        if cands is None:
            cands = here
        else:
            cands = [[op for op in a if op in b] for a, b in zip(cands, here)]
        if any(not c for c in cands):
            return None
    return [c[0] for c in cands]


def _precheck(verb, cfgs, train):
    same = all(dims(x) == dims(y) for x, y in train)
    if verb in ("reflect", "turn", "fill"):
        return cfgs if same else []
    if verb == "symmetrize":
        keep = []
        for c in cfgs:
            if c["role:axis"] == "grid centre":
                if same:
                    keep.append(c)
            else:
                g = c["param:group"]
                ok = True
                for x, y in train:
                    h, w = dims(x)
                    want = {"H": (h, 2 * w), "V": (2 * h, w)}.get(g, (2 * h, 2 * w))
                    if dims(y) != want:
                        ok = False
                        break
                if ok:
                    keep.append(c)
        return keep
    if verb == "complete":
        return [c for c in cfgs if (c["stop"] == "none") == same]
    return cfgs


def _fit_verb(verb, cfgs, train):
    cfgs = _precheck(verb, cfgs, train)
    mcache = {}
    for cfg in cfgs:
        tp = {}
        if verb == "complete":
            m = _derive_m(cfg, train, mcache)
            if m is None:
                continue
            tp["m"] = m
        if verb == "fill":
            T = _derive_T(cfg, train)
            if T is None:
                continue
            tp["T"] = T
        if cfg["colour_rule"] == "literal":
            probe = dict(tp, k=-1)
            ks = set()
            bad = False
            for x, y in train:
                z = apply_cfg(cfg, probe, x)
                if z is None or dims(z) != dims(y):
                    bad = True
                    break
                for rz, ry in zip(z, y):
                    for a, b in zip(rz, ry):
                        if a == -1:
                            ks.add(b)
                if len(ks) > 1:
                    bad = True
                    break
            if bad or len(ks) != 1 or 0 in ks:
                continue
            tp["k"] = ks.pop()
        if all(apply_cfg(cfg, tp, x) == y for x, y in train):
            yield (_name(cfg, tp), _cost(cfg),
                   (lambda g, _c=cfg, _t=dict(tp): apply_cfg(_c, _t, g)))


def family(node):
    by_verb = {}
    for i in compatible(node):
        c = CONFIGS[i]
        by_verb.setdefault(c["verb"], []).append(c)

    def fam(train):
        tr = _norm_train(train)
        if not tr:
            return
        progs = []
        for verb in MENU["verb"]:
            if verb in by_verb:
                progs.extend(_fit_verb(verb, by_verb[verb], tr))
        progs.sort(key=lambda p: (p[1], p[0]))
        for p in progs:
            yield p
    return fam
