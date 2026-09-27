"""M1 occupancy probe: prior-concept layer + per-task conceptual lattice + RDR decision list.

Segmentation comes from registered ARCGraph abstractions. Attributes come only from a
fixed, task-independent prior layer (topology, geometry, number/extremes, property
chains). Rules are lattice concepts (extent = closure of a minimal generator of <= 2
attributes) arranged as an RDR-style decision list. No task identifiers; outputs are
used only on training pairs.
"""
from __future__ import annotations

import copy, json, os, signal, sys, time
from collections import Counter
from itertools import combinations
from types import SimpleNamespace

sys.path[:0] = ["/home/claude/work/stubs", "/home/claude/work/cand2"]
from image import Image  # noqa: E402

ABSTRACTIONS = ("nbccg", "ccgbr", "nbvcg", "nbhcg", "mcccg")
DIRS = {"up": (-1, 0), "down": (1, 0), "left": (0, -1), "right": (0, 1)}
MAX_RULES = 5


class Timeout(BaseException):
    pass


# ---------------------------------------------------------------- segmentation (ARCGraph)
def segment(grid, abstraction):
    image = Image(SimpleNamespace(stop_search=False, check_time_limit=lambda: False,
                                  max_abstract_nodes=64), grid=copy.deepcopy(grid), name="m1")
    graph = getattr(image, Image.abstraction_ops[abstraction])()
    nodes = []
    for _, d in graph.graph.nodes(data=True):
        pix = [tuple(p) for p in d["nodes"]]
        colors = {p: grid[p[0]][p[1]] for p in pix}
        vals = set(colors.values())
        nodes.append({"pix": frozenset(pix), "colors": colors,
                      "color": next(iter(vals)) if len(vals) == 1 else None})
    if not nodes or len(nodes) > 64:
        raise ValueError("node_count")
    return nodes


def background(grid):
    return Counter(c for row in grid for c in row).most_common(1)[0][0]


# ---------------------------------------------------------------- prior layer
def norm_shape(pix):
    r0 = min(r for r, _ in pix); c0 = min(c for _, c in pix)
    return frozenset((r - r0, c - c0) for r, c in pix)


def bbox(pix):
    rs = [r for r, _ in pix]; cs = [c for _, c in pix]
    return min(rs), min(cs), max(rs), max(cs)


def has_hole(pix):
    r0, c0, r1, c1 = bbox(pix)
    if r1 - r0 < 2 or c1 - c0 < 2:
        return False
    free = {(r, c) for r in range(r0 - 1, r1 + 2) for c in range(c0 - 1, c1 + 2)} - set(pix)
    stack = [(r0 - 1, c0 - 1)]; seen = set(stack)
    while stack:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (r + dr, c + dc)
            if q in free and q not in seen:
                seen.add(q); stack.append(q)
    return len(seen) < len(free)


def interior(pix):
    """Cells enclosed by pix (not reachable from outside its bbox)."""
    r0, c0, r1, c1 = bbox(pix)
    free = {(r, c) for r in range(r0 - 1, r1 + 2) for c in range(c0 - 1, c1 + 2)} - set(pix)
    stack = [(r0 - 1, c0 - 1)]; seen = set(stack)
    while stack:
        r, c = stack.pop()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (r + dr, c + dc)
            if q in free and q not in seen:
                seen.add(q); stack.append(q)
    return free - seen


def attributes(nodes, grid):
    """Return per-node attribute sets plus chain-valued color sources."""
    H, W = len(grid), len(grid[0])
    sizes = [len(n["pix"]) for n in nodes]
    shapes = [norm_shape(n["pix"]) for n in nodes]
    colors = [n["color"] for n in nodes]
    ccount = Counter(c for c in colors if c is not None)
    scount = Counter(shapes)
    boxes = [bbox(n["pix"]) for n in nodes]
    inner = [interior(n["pix"]) for n in nodes]
    owner = {}
    for i, n in enumerate(nodes):
        for p in n["pix"]:
            owner[p] = i
    out, sources = [], []
    for i, n in enumerate(nodes):
        a = set(); src = {}
        pix = n["pix"]; r0, c0, r1, c1 = boxes[i]; h, w = r1 - r0 + 1, c1 - c0 + 1
        c = colors[i]
        a.add(f"color={c}" if c is not None else "multicolor")
        a.add(f"size={sizes[i]}" if sizes[i] <= 12 else "size>12")
        if sizes[i] == max(sizes): a.add("largest")
        if sizes[i] == min(sizes): a.add("smallest")
        if sizes.count(sizes[i]) == 1: a.add("size_unique")
        if sizes[i] == 1: a.add("single_pixel")
        if h == 1 and w > 1: a.add("hline")
        if w == 1 and h > 1: a.add("vline")
        if len(pix) == h * w and h * w > 1: a.add("filled_rect")
        if h == w: a.add("square_bbox")
        if len(pix) == 2 * (h + w) - 4 and h > 2 and w > 2 and has_hole(pix): a.add("hollow_rect")
        if inner[i]: a.add("has_hole")
        s = shapes[i]
        if s == frozenset((r, w - 1 - cc) for r, cc in s): a.add("sym_lr")
        if s == frozenset((h - 1 - r, cc) for r, cc in s): a.add("sym_ud")
        a.add("shape_unique" if scount[s] == 1 else "shape_shared")
        if c is not None:
            if ccount[c] == 1: a.add("color_unique")
            if ccount[c] == max(ccount.values()): a.add("color_most_common")
            if ccount[c] == min(ccount.values()): a.add("color_least_common")
        if r0 == 0 or c0 == 0 or r1 == H - 1 or c1 == W - 1: a.add("touches_border")
        if r0 == min(b[0] for b in boxes): a.add("topmost")
        if r1 == max(b[2] for b in boxes): a.add("bottommost")
        if c0 == min(b[1] for b in boxes): a.add("leftmost")
        if c1 == max(b[3] for b in boxes): a.add("rightmost")
        # topology: touching / containment (RCC-style) and property chains
        touch = set()
        for (r, cc) in pix:
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                j = owner.get((r + dr, cc + dc))
                if j is not None and j != i:
                    touch.add(j)
        a.add("touches_other" if touch else "isolated")
        tcols = {colors[j] for j in touch if colors[j] is not None}
        for tc in tcols:
            a.add(f"adjColor={tc}")
        if len(tcols) == 1: src["adj"] = next(iter(tcols))
        containers = [j for j in range(len(nodes)) if j != i and pix <= inner[j]]
        if containers:
            a.add("inside_other")
            j = min(containers, key=lambda j: sizes[j])
            if colors[j] is not None:
                a.add(f"contextColor={colors[j]}"); src["ctx"] = colors[j]
        if any(nodes[j]["pix"] <= inner[i] for j in range(len(nodes)) if j != i): a.add("contains_other")
        aligned = {colors[j] for j in range(len(nodes)) if j != i and colors[j] is not None and
                   (not (boxes[j][2] < r0 or boxes[j][0] > r1) or not (boxes[j][3] < c0 or boxes[j][1] > c1))}
        for ac in aligned:
            a.add(f"alignedColor={ac}")
        if len(aligned) == 1: src["aligned"] = next(iter(aligned))
        big = max(range(len(nodes)), key=lambda j: sizes[j])
        small = min(range(len(nodes)), key=lambda j: sizes[j])
        if sizes.count(sizes[big]) == 1 and colors[big] is not None: src["largest"] = colors[big]
        if sizes.count(sizes[small]) == 1 and colors[small] is not None: src["smallest"] = colors[small]
        if ccount:
            least = [k for k, v in ccount.items() if v == min(ccount.values())]
            if len(least) == 1: src["least_common"] = least[0]
        same_shape_other = [j for j in range(len(nodes)) if j != i and shapes[j] == s and colors[j] is not None]
        if same_shape_other and len({colors[j] for j in same_shape_other}) == 1:
            src["same_shape"] = colors[same_shape_other[0]]
        out.append(a); sources.append(src)
    return out, sources


# ---------------------------------------------------------------- labels (training only)
def slide_distance(node, grid, bg, direction, others):
    dr, dc = DIRS[direction]
    H, W = len(grid), len(grid[0]); k = 0
    while True:
        nxt = [(r + dr * (k + 1), c + dc * (k + 1)) for r, c in node["pix"]]
        if any(not (0 <= r < H and 0 <= c < W) for r, c in nxt): return k
        if any(p in others for p in nxt): return k
        k += 1
        if k > 30: return k


def candidate_labels(node, src, grid, out, bg, others):
    H, W = len(out), len(out[0])
    cols = node["colors"]
    now = {p: out[p[0]][p[1]] for p in node["pix"]}
    labs = set()
    if all(now[p] == cols[p] for p in node["pix"]):
        labs.add("keep")
    vals = set(now.values())
    if node["color"] is not None and len(vals) == 1:
        v = next(iter(vals))
        if v != node["color"]:
            if v == bg: labs.add("remove")
            labs.add(f"recolor:const:{v}")
            for name, sc in src.items():
                if sc == v: labs.add(f"recolor:{name}")
    # translations
    p0 = next(iter(node["pix"]))
    for r in range(H):
        for c in range(W):
            if out[r][c] != cols[p0]: continue
            d = (r - p0[0], c - p0[1])
            if d == (0, 0): continue
            if all(0 <= p[0] + d[0] < H and 0 <= p[1] + d[1] < W and
                   out[p[0] + d[0]][p[1] + d[1]] == cols[p] for p in node["pix"]):
                labs.add(f"move:{d[0]},{d[1]}")
                for name, (dr, dc) in DIRS.items():
                    k = slide_distance(node, grid, bg, name, others)
                    if k and (dr * k, dc * k) == d: labs.add(f"slide:{name}")
    return labs


def apply_labels(grid, nodes, srcs, labels, bg, others_list):
    canvas = [row[:] for row in grid]
    H, W = len(grid), len(grid[0])
    paints = []
    for n, s, lab, others in zip(nodes, srcs, labels, others_list):
        if lab in ("keep", "refine"): continue
        if lab == "remove":
            for p in n["pix"]: canvas[p[0]][p[1]] = bg
            continue
        if lab.startswith("recolor:"):
            _, kind, *rest = lab.split(":")
            v = int(rest[0]) if kind == "const" else s.get(kind)
            if v is None: return None
            paints += [(p, v) for p in n["pix"]]
            continue
        if lab.startswith("move:"):
            d = tuple(int(x) for x in lab[5:].split(","))
        elif lab.startswith("slide:"):
            k = slide_distance(n, grid, bg, lab[6:], others)
            d = (DIRS[lab[6:]][0] * k, DIRS[lab[6:]][1] * k)
        else:
            return None
        for p in n["pix"]: canvas[p[0]][p[1]] = bg
        for p in n["pix"]:
            q = (p[0] + d[0], p[1] + d[1])
            if not (0 <= q[0] < H and 0 <= q[1] < W): return None
            paints.append((q, n["colors"][p]))
    for (r, c), v in paints:
        canvas[r][c] = v
    return canvas



import os
VOCAB = set(filter(None, os.environ.get("M1B_VOCAB", "").split(",")))
EFFECTS = [e for e in ("fill_interior", "ray", "connect", "border", "bbox_fill", "outline8") if e in VOCAB]


def effect_cells(name, node, grid, bg, owner_color):
    H, W = len(grid), len(grid[0]); pix = node["pix"]
    if name == "fill_interior":
        return [{q for q in interior(pix) if 0 <= q[0] < H and 0 <= q[1] < W and grid[q[0]][q[1]] == bg}]
    if name == "bbox_fill":
        r0, c0, r1, c1 = bbox(pix)
        return [{(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1) if grid[r][c] == bg}]
    if name == "border":
        r0, c0, r1, c1 = bbox(pix)
        return [{(r, c) for r in range(r0 - 1, r1 + 2) for c in range(c0 - 1, c1 + 2)
                 if 0 <= r < H and 0 <= c < W and not (r0 <= r <= r1 and c0 <= c <= c1) and grid[r][c] == bg}]
    if name == "outline8":
        hole = interior(pix)
        return [{(r + dr, c + dc) for r, c in pix for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                 if 0 <= r + dr < H and 0 <= c + dc < W and (r + dr, c + dc) not in pix and (r + dr, c + dc) not in hole
                 and grid[r + dr][c + dc] == bg}]
    if name == "ray":
        outs = []
        for dr, dc in list(DIRS.values()) + [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
            cells = set()
            for r, c in pix:
                q = (r + dr, c + dc)
                if q in pix: continue
                while 0 <= q[0] < H and 0 <= q[1] < W and grid[q[0]][q[1]] == bg:
                    cells.add(q); q = (q[0] + dr, q[1] + dc)
            outs.append(cells)
        return outs
    if name == "connect":
        cells = set()
        for r, c in pix:
            for dr, dc in DIRS.values():
                q = (r + dr, c + dc); walk = []
                if q in pix: continue
                while 0 <= q[0] < H and 0 <= q[1] < W and grid[q[0]][q[1]] == bg:
                    walk.append(q); q = (q[0] + dr, q[1] + dc)
                if walk and 0 <= q[0] < H and 0 <= q[1] < W and q not in pix and owner_color.get(q) == node["color"]:
                    cells.update(walk)
        return [cells]
    return []


def effect_options(node, src, grid, bg, owner_color, out=None, families=None):
    """All (effect, index, colorspec) options; with out given, keep those consistent with out."""
    opts = []
    for name in (families or EFFECTS):
        for idx, cells in enumerate(effect_cells(name, node, grid, bg, owner_color)):
            if not cells: continue
            if out is None:
                opts.append((f"{name}#{idx}", cells)); continue
            vals = {out[r][c] for r, c in cells}
            if len(vals) != 1: continue
            v = next(iter(vals))
            specs = [f"const:{v}"] + (["self"] if v == node["color"] else []) + [k for k, sv in src.items() if sv == v]
            opts.append((f"{name}#{idx}", cells, specs, v))
    return opts


def effect_labels(node, src, grid, out, bg, owner_color, changed, families=None):
    labs = set()
    for name, cells, specs, v in effect_options(node, src, grid, bg, owner_color, out, families):
        if cells & changed:
            labs |= {f"{name}@{s}" for s in specs}
    return labs or {"none"}


def apply_effects(canvas, grid, nodes, srcs, elabels, bg, owner_color):
    for n, s, lab in zip(nodes, srcs, elabels):
        if lab == "none": continue
        name, spec = lab.split("@")
        ename, idx = name.split("#")
        cells_list = effect_cells(ename, n, grid, bg, owner_color)
        idx = int(idx)
        if idx >= len(cells_list): return None
        if spec.startswith("const:"): v = int(spec[6:])
        elif spec == "self": v = n["color"]
        else: v = s.get(spec)
        if v is None: return None
        for r, c in cells_list[idx]: canvas[r][c] = v
    return canvas


# ---------------------------------------------------------------- DSL primitive: pixel refinement (cycle 3)
def px_attrs(node, grid, bg, nattrs):
    """Pixel-level concepts inside an object: position within the object's frame, boundary/interior,
    parity (checkerboard), neighbourhood colour, row/column alignment with outside colours."""
    H, W = len(grid), len(grid[0]); pix = node["pix"]
    r0, c0, r1, c1 = bbox(pix); h, w = r1 - r0 + 1, c1 - c0 + 1
    rowcols = {}; colcols = {}
    for r in range(H):
        for c in range(W):
            if (r, c) not in pix and grid[r][c] != bg:
                rowcols.setdefault(r, set()).add(grid[r][c]); colcols.setdefault(c, set()).add(grid[r][c])
    out = {}
    for (r, c) in pix:
        a = {"obj:" + x for x in nattrs}
        a.add(f"px:color={node['colors'][(r, c)]}")
        nb4 = [(r + 1, c), (r - 1, c), (r, c + 1), (r, c - 1)]
        a.add("px:boundary" if any(q not in pix for q in nb4) else "px:interior")
        if (r in (r0, r1)) and (c in (c0, c1)): a.add("px:corner")
        if r == r0: a.add("px:top_edge")
        if r == r1: a.add("px:bottom_edge")
        if c == c0: a.add("px:left_edge")
        if c == c1: a.add("px:right_edge")
        a.add(f"px:row_parity={(r - r0) % 2}"); a.add(f"px:col_parity={(c - c0) % 2}")
        a.add(f"px:checker={(r - r0 + c - c0) % 2}")
        if h % 2 and r - r0 == h // 2: a.add("px:mid_row")
        if w % 2 and c - c0 == w // 2: a.add("px:mid_col")
        if r - r0 < 3: a.add(f"px:row_from_top={r - r0}")
        if r1 - r < 3: a.add(f"px:row_from_bottom={r1 - r}")
        if c - c0 < 3: a.add(f"px:col_from_left={c - c0}")
        if c1 - c < 3: a.add(f"px:col_from_right={c1 - c}")
        for q in nb4:
            if 0 <= q[0] < H and 0 <= q[1] < W and q not in pix: a.add(f"px:adj={grid[q[0]][q[1]]}")
        for v in rowcols.get(r, ()): a.add(f"px:row_has={v}")
        for v in colcols.get(c, ()): a.add(f"px:col_has={v}")
        out[(r, c)] = a
    return out


def px_labels(node, out_grid):
    res = {}
    for (r, c) in node["pix"]:
        v = out_grid[r][c]
        res[(r, c)] = {"keep"} if v == node["colors"][(r, c)] else {f"pc:{v}"}
    return res


def apply_pixel_rules(canvas, grid, nodes, at, labels, rp, bg):
    for n, a, lab in zip(nodes, at, labels):
        if lab != "refine": continue
        pa = px_attrs(n, grid, bg, a)
        pl = predict_labels_default(rp, [pa[p] for p in sorted(pa)], "keep")
        for p, l in zip(sorted(pa), pl):
            if l.startswith("pc:"): canvas[p[0]][p[1]] = int(l[3:])
    return canvas

# ---------------------------------------------------------------- lattice / RDR decision list

def clarified(cases):
    """FCA attribute clarification: drop attributes with identical extents or full extent; cap for pair search."""
    n = len(cases); full = (1 << n) - 1
    ext = {}
    for i, (at, _) in enumerate(cases):
        for a in at: ext[a] = ext.get(a, 0) | (1 << i)
    seen, attrs = set(), []
    for a in sorted(ext):
        e = ext[a]
        if e == full or e in seen: continue
        seen.add(e); attrs.append(a)
    pair_attrs = attrs if len(attrs) <= 150 else sorted(attrs, key=lambda a: -bin(ext[a]).count("1"))[:150]
    return attrs, ext, pair_attrs

def learn(cases, specific=False, mode="greedy"):
    if mode == "inertia":
        return learn_inertia(cases, specific)
    return learn_greedy(cases, specific)


def learn_inertia(cases, specific=False, default="keep"):
    """RDR with an inertia root: default conclusion = no change; exceptions are lattice concepts
    whose extent contains no case that must stay unchanged-incompatible with the exception label."""
    n = len(cases)
    if not any(default in ls for _, ls in cases): return None
    attrs, ext, pair_attrs = clarified(cases)
    labels = sorted({l for _, ls in cases for l in ls} - {default})
    valid = {l: sum(1 << i for i, (_, ls) in enumerate(cases) if l in ls) for l in labels}
    need = sum(1 << i for i, (_, ls) in enumerate(cases) if default not in ls)
    gens = [(a,) for a in sorted(ext)] + list(combinations(pair_attrs, 2))
    uncovered = (1 << n) - 1; rules = []
    while uncovered & need:
        if len(rules) >= MAX_RULES - 1: return None
        best = None
        for g in gens:
            e = uncovered
            for a in g: e &= ext[a]
            if not (e & need): continue
            full = (1 << n) - 1
            for a in g: full &= ext[a]
            gen = bin(full).count("1")
            for l in labels:
                if e & ~valid[l]: continue
                key = (bin(e & need).count("1"), (len(g) if specific else -len(g)), gen, tuple(g), l)
                if best is None or key > best[0]: best = (key, g, l, e)
        if best is None: return None
        _, g, l, e = best
        rules.append((g, l)); uncovered &= ~e
    return rules + [((), default)]


def learn_greedy(cases, specific=False):
    """cases: list of (attrset, validlabelset). Greedy decision list of lattice concepts."""
    n = len(cases)
    attrs, ext, pair_attrs = clarified(cases)
    labels = sorted({l for _, ls in cases for l in ls})
    valid = {l: sum(1 << i for i, (_, ls) in enumerate(cases) if l in ls) for l in labels}
    uncovered = (1 << n) - 1
    rules = []
    gens = [()] + [(a,) for a in sorted(ext)] + list(combinations(pair_attrs, 2))
    while uncovered:
        if len(rules) >= MAX_RULES: return None
        best = None
        for g in gens:
            e = uncovered
            for a in g: e &= ext[a]
            if not e: continue
            cov = bin(e).count("1")
            full = (1 << n) - 1
            for a in g: full &= ext[a]
            gen = bin(full).count("1")  # maximal concept subsumption: prefer the more general concept
            for l in labels:
                if e & ~valid[l]: continue
                key = (cov, (len(g) if specific else -len(g)), gen, l != "keep", tuple(g), l)
                if best is None or key > best[0]:
                    best = (key, g, l, e)
        if best is None: return None
        _, g, l, e = best
        rules.append((g, l)); uncovered &= ~e
    return rules


def predict_labels(rules, attrsets):
    labs = []
    for at in attrsets:
        for g, l in rules:
            if all(a in at for a in g):
                labs.append(l); break
        else:
            labs.append("keep")
    return labs


# ---------------------------------------------------------------- task driver

def n_holes(pix):
    cells = interior(pix); comps = 0; seen = set()
    for q in cells:
        if q in seen: continue
        comps += 1; stack = [q]; seen.add(q)
        while stack:
            r, c = stack.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                x = (r + dr, c + dc)
                if x in cells and x not in seen:
                    seen.add(x); stack.append(x)
    return comps

def extra_attrs(nodes, grid):
    H, W = len(grid), len(grid[0])
    sizes = [len(n["pix"]) for n in nodes]; colors = [n["color"] for n in nodes]
    shapes = [norm_shape(n["pix"]) for n in nodes]; boxes = [bbox(n["pix"]) for n in nodes]
    inner = [interior(n["pix"]) for n in nodes]
    ranks = sorted(set(sizes), reverse=True)
    owner = {p: i for i, n in enumerate(nodes) for p in n["pix"]}
    res = []
    for i, n in enumerate(nodes):
        a = set(); r0, c0, r1, c1 = boxes[i]
        a.add(f"D1:size_rank={ranks.index(sizes[i])}" if ranks.index(sizes[i]) < 4 else "D1:size_rank>3")
        a.add(f"D1:size_rank_asc={sorted(set(sizes)).index(sizes[i])}")
        same = [j for j in range(len(nodes)) if colors[j] == colors[i]]
        a.add(f"D2:n_same_color={min(len(same),5)}")
        for j in range(len(nodes)):
            if j != i and shapes[j] == shapes[i] and colors[j] is not None: a.add(f"D3:shape_as_color={colors[j]}")
        touch = {owner[(r+dr, c+dc)] for r, c in n["pix"] for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)) if owner.get((r+dr, c+dc), i) != i}
        a.add(f"D4:n_touch={min(len(touch),4)}")
        a.add("D5:top_half" if (r0+r1)/2 < H/2 else "D5:bottom_half"); a.add("D5:left_half" if (c0+c1)/2 < W/2 else "D5:right_half")
        a.add(f"D8:height={r1-r0+1}"); a.add(f"D8:width={c1-c0+1}")
        for j in range(len(nodes)):
            if j != i and nodes[j]["pix"] <= inner[i] and colors[j] is not None: a.add(f"D7:contains_color={colors[j]}")
            if j != i and colors[j] is not None and not (boxes[j][2] < r0 or boxes[j][0] > r1): a.add(f"D9:row_with_color={colors[j]}")
            if j != i and colors[j] is not None and not (boxes[j][3] < c0 or boxes[j][1] > c1): a.add(f"D9:col_with_color={colors[j]}")
        if sizes[i] == max(sizes[j] for j in same): a.add("D10:largest_of_its_color")
        if sizes[i] == min(sizes[j] for j in same): a.add("D10:smallest_of_its_color")
        a.add(f"D11:n_cells_of_color_in_bbox={sum(1 for r in range(r0,r1+1) for c in range(c0,c1+1) if grid[r][c]==colors[i])==sizes[i]}")
        a.add(f"D12:n_holes={min(n_holes(n['pix']), 5)}")
        big = max(range(len(nodes)), key=lambda j: (sizes[j], -j))
        if big != i:
            br0, bc0, br1, bc1 = boxes[big]
            cy, cx = (r0 + r1) / 2, (c0 + c1) / 2; by, bx = (br0 + br1) / 2, (bc0 + bc1) / 2
            a.add("D13:above_largest" if cy < by else ("D13:below_largest" if cy > by else "D13:level_with_largest"))
            a.add("D13:left_of_largest" if cx < bx else ("D13:right_of_largest" if cx > bx else "D13:centered_on_largest"))
            if not (r1 < br0 or r0 > br1): a.add("D13:row_overlaps_largest")
            if not (c1 < bc0 or c0 > bc1): a.add("D13:col_overlaps_largest")
        dens = sizes[i] / ((r1 - r0 + 1) * (c1 - c0 + 1))
        a.add("D14:dense_full" if dens == 1 else ("D14:dense_high" if dens >= 0.5 else "D14:dense_low"))
        res.append(a)
    return res



# ---------------------------------------------------------------- Codex selectors as concepts (cycle 5)
_CODEX = None
_CODEX_CACHE = {}
ROLE_KEYS = ("role", "marker", "source", "separator", "foreground", "base", "color", "background")


def _codex():
    global _CODEX
    if _CODEX is None:
        import importlib, json as _j
        root = os.environ.get("CODEX_ROOT", "/mnt/user-data/uploads/arc_extended_arga")
        if root not in sys.path: sys.path.insert(0, root)
        cr = importlib.import_module("wake.composition_runtime")
        spec = _j.load(open(os.environ.get("CODEX_SELECTORS", "/home/claude/work/au/seltime.json")))
        _CODEX = [(name, getattr(cr, name), v["spec"]) for name, v in sorted(spec.items())]
    return _CODEX


def _cells(v, H, W):
    if isinstance(v, (list, tuple, set)) and v:
        items = list(v)[:2000]
        if all(isinstance(x, (list, tuple)) and len(x) == 2 and all(isinstance(y, int) for y in x) for x in items):
            cs = {(x[0], x[1]) for x in items}
            if all(0 <= r < H and 0 <= c < W for r, c in cs): return cs
    return None


def codex_features(grid):
    """Run each Codex selector on the grid; return (role attributes by colour, cell-set attributes, chain sources)."""
    key = tuple(map(tuple, grid))
    if key in _CODEX_CACHE: return _CODEX_CACHE[key]
    H, W = len(grid), len(grid[0])
    roles, cellsets, sources = {}, {}, {}
    for name, f, spec in _codex():
        try:
            out = f(grid, spec)
        except Exception:
            continue
        if not isinstance(out, dict): continue
        short = name[len("_select_"):] if name.startswith("_select_") else name
        for k, v in out.items():
            tag = f"cx:{short}.{k}"
            if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 9 and any(r in k for r in ROLE_KEYS):
                roles.setdefault(v, set()).add(tag); sources[tag] = v
            else:
                cs = _cells(v, H, W)
                if cs: cellsets[tag] = cs
    _CODEX_CACHE[key] = (roles, cellsets, sources)
    if len(_CODEX_CACHE) > 5000: _CODEX_CACHE.clear()
    return roles, cellsets, sources



# ---------------------------------------------------------------- S0 atoms (Codex detectors) as a fallback stratum (cycle 6)
_ATOMS = None
_ATOM_CACHE = {}
ATOM_ACTIVE = False


def _atoms():
    global _ATOMS
    if _ATOMS is None:
        import importlib, json as _j
        root = os.environ.get("CODEX_ROOT", "/home/claude/work/codex")
        if root not in sys.path: sys.path.insert(0, root)
        reps = _j.load(open(os.environ.get("S0_REPS", "/home/claude/work/s0/s0_reps.json")))
        if "S_atoms_used" in VOCAB or "S_atoms_primary" in VOCAB:
            used = set(_j.load(open(os.environ.get("S0_REPS_USED", "/home/claude/work/s0/s0_reps_used.json"))))
            reps = [r for r in reps if r in used]
        fns = []
        for name in sorted(reps):
            mod, fn = name.rsplit(".", 1)
            try:
                fns.append((name, getattr(importlib.import_module("detectors." + mod), fn)))
            except Exception:
                pass
        _ATOMS = fns
    return _ATOMS


def _collect_cells(ev, H, W, out):
    if isinstance(ev, dict):
        if isinstance(ev.get("row"), int) and isinstance(ev.get("col"), int):
            if 0 <= ev["row"] < H and 0 <= ev["col"] < W: out.add((ev["row"], ev["col"]))
        for v in ev.values(): _collect_cells(v, H, W, out)
    elif isinstance(ev, (list, tuple, set, frozenset)):
        if len(ev) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in ev):
            r, c = ev
            if 0 <= r < H and 0 <= c < W: out.add((r, c))
            return
        for v in ev: _collect_cells(v, H, W, out)


def atom_cells(grid):
    key = tuple(map(tuple, grid))
    if key in _ATOM_CACHE: return _ATOM_CACHE[key]
    H, W = len(grid), len(grid[0]); res = {}
    for name, fn in _atoms():
        try:
            ev = fn([row[:] for row in grid])
        except Exception:
            continue
        if not ev: continue
        cs = set(); _collect_cells(ev, H, W, cs)
        if cs: res["at:" + name.split(".", 1)[1][:-len("_evidence")] if name.endswith("_evidence") else "at:" + name] = cs
    _ATOM_CACHE[key] = res
    if len(_ATOM_CACHE) > 4000: _ATOM_CACHE.clear()
    return res


def prepare(grid, abstraction):
    nodes = segment(grid, abstraction)
    bg = background(grid)
    at, src = attributes(nodes, grid)
    if "S_holes" in VOCAB or "S_size" in VOCAB:
        holes = [n_holes(n["pix"]) for n in nodes]
        Hg, Wg = len(grid), len(grid[0])
        spans = [bbox(n["pix"])[0] == 0 or bbox(n["pix"])[1] == 0 or bbox(n["pix"])[2] == Hg - 1 or bbox(n["pix"])[3] == Wg - 1
                 for n in nodes]  # frames/separators anchored to the border are not reference tokens
        for i, s in enumerate(src):
            if nodes[i]["color"] is None: continue
            for key, vals in (("same_holes", holes), ("same_size", [len(n["pix"]) for n in nodes])):
                if ("S_holes" if key == "same_holes" else "S_size") not in VOCAB: continue
                cand = [j for j in range(len(nodes)) if j != i and vals[j] == vals[i] and not spans[j]
                        and nodes[j]["color"] is not None and nodes[j]["color"] != nodes[i]["color"]]
                if not cand: continue
                size_i = len(nodes[i]["pix"])
                gap = {j: abs(len(nodes[j]["pix"]) - size_i) for j in cand}
                best = [j for j in cand if gap[j] == min(gap.values())]
                cs = {nodes[j]["color"] for j in best}
                if len(cs) == 1:
                    s[key] = next(iter(cs)); at[i].add(f"exists_{key}")  # OWL existential restriction
    if "S_codex" in VOCAB:
        roles, cellsets, csrc = codex_features(grid)
        for n, a, s in zip(nodes, at, src):
            if n["color"] is not None:
                a |= roles.get(n["color"], set())
            for tag, cs in cellsets.items():
                if n["pix"] & cs: a.add(tag)
            for tag, v in csrc.items():
                s[tag] = v
    if ATOM_ACTIVE or "S_atoms_primary" in VOCAB:
        for tag, cs in atom_cells(grid).items():
            for n, a in zip(nodes, at):
                if n["pix"] & cs: a.add(tag)
    dv = {v for v in VOCAB if v.startswith("D")}
    if dv:
        for a, e in zip(at, extra_attrs(nodes, grid)):
            a |= {x for x in e if x.split(":")[0] in dv}
    allpix = [set().union(*[m["pix"] for j, m in enumerate(nodes) if j != i]) if len(nodes) > 1 else set()
              for i in range(len(nodes))]
    owner_color = {p: n["colors"][p] for n in nodes for p in n["pix"]}
    return nodes, bg, at, src, allpix, owner_color


def predict_grid(grid, rules, abstraction):
    rb, re_ = rules[:2]
    rp = rules[2] if len(rules) > 2 else None
    nodes, bg, at, src, others, oc = prepare(grid, abstraction)
    blabels = predict_labels(rb, at)
    canvas = apply_labels(grid, nodes, src, blabels, bg, others)
    if canvas is None: return None
    if rp:
        canvas = apply_pixel_rules(canvas, grid, nodes, at, blabels, rp, bg)
    if re_:
        groups, cur = [], None
        for item in re_:
            if isinstance(item, tuple) and len(item) == 1 and str(item[0]).startswith("#"):
                cur = []; groups.append(cur)
            else:
                cur.append(item)
        for fr in groups:
            el = predict_labels_default(fr, at, "none")
            canvas = apply_effects(canvas, grid, nodes, src, el, bg, oc)
            if canvas is None: return None
    return canvas


def predict_labels_default(rules, attrsets, default):
    labs = []
    for at in attrsets:
        for g, l in rules:
            if all(a in at for a in g):
                labs.append(l); break
        else:
            labs.append(default)
    return labs


def fit(pairs, abstraction, specific=False, mode="greedy"):
    cases, preps = [], []
    for p in pairs:
        gi, go = p["input"], p["output"]
        if (len(gi), len(gi[0])) != (len(go), len(go[0])): return None, "extent_change"
        pr = prepare(gi, abstraction)
        nodes, bg, at, src, others, oc = pr
        labs = [candidate_labels(n, s, gi, go, bg, o) for n, s, o in zip(nodes, src, others)]
        if PIXEL_ACTIVE:
            labs = [l if l else {"refine"} for l in labs]
        if EFFECTS:
            labs = [l if l else {"keep"} for l in labs]  # own pixels may be repainted by an effect
        if any(not l for l in labs): return None, "unlabelled_node"
        cases += list(zip(at, labs)); preps.append((gi, go, pr))
    rb = learn(cases, specific, mode)
    if rb is None: return None, "not_occupied"
    rp = None
    if PIXEL_ACTIVE and any(l == "refine" for _, l in rb):
        pcases = []
        for gi, go, (nodes, bg, at, src, others, oc) in preps:
            for n, a, lab in zip(nodes, at, predict_labels(rb, at)):
                if lab != "refine": continue
                pa, pl = px_attrs(n, gi, bg, a), px_labels(n, go)
                pcases += [(pa[p], pl[p]) for p in sorted(pa)]
        if pcases:
            rp = learn(pcases, specific, mode)
            if rp is None: return None, "not_occupied"
    re_ = None
    if EFFECTS:
        changes, residual_any = [], False
        for gi, go, (nodes, bg, at, src, others, oc) in preps:
            canvas = predict_grid(gi, (rb, None, rp), abstraction)
            if canvas is None: return None, "not_representable"
            changed = {(r, c) for r in range(len(gi)) for c in range(len(gi[0])) if canvas[r][c] != go[r][c]}
            residual_any |= bool(changed); changes.append(changed)
        if residual_any:
            re_ = []
            remaining = list(EFFECTS)
            while remaining and any(changes):
                best = None
                for fam in remaining:
                    ecases = []
                    for (gi, go, (nodes, bg, at, src, others, oc)), changed in zip(preps, changes):
                        ecases += list(zip(at, [effect_labels(n, s, gi, go, bg, oc, changed, [fam]) for n, s in zip(nodes, src)]))
                    if all(ls == {"none"} for _, ls in ecases): continue
                    fr = learn(ecases, specific, mode)
                    if fr is None or all(l == "none" for _, l in fr): continue
                    # MDL: residual cells this family explains, per rule
                    newchanges, explained = [], 0
                    for (gi, go, (nodes, bg, at, src, others, oc)), changed in zip(preps, changes):
                        canvas = [row[:] for row in gi]
                        for r, c in changed: canvas[r][c] = None
                        el = predict_labels_default(fr, at, "none")
                        canvas = apply_effects(canvas, gi, nodes, src, el, bg, oc)
                        if canvas is None: explained = -1; break
                        still = {(r, c) for r, c in changed if canvas[r][c] != go[r][c]}
                        explained += len(changed) - len(still); newchanges.append(still)
                    if explained <= 0: continue
                    key = (explained / len(fr), explained, fam)
                    if best is None or key > best[0]: best = (key, fam, fr, newchanges)
                if best is None: break
                _, fam, fr, changes = best
                remaining.remove(fam)
                re_ += [("#" + fam,)] + fr
            re_ = re_ or None
    rules = (rb, re_, rp)
    for gi, go, _ in preps:
        if predict_grid(gi, rules, abstraction) != go:
            return None, "not_representable"
    return rules, "occupied"


def run_rules(grid, rules, abstraction):
    return predict_grid(grid, rules, abstraction)


def nrules(rules):
    rb, re_ = rules[:2]
    rp = rules[2] if len(rules) > 2 else None
    return len(rb) + (sum(1 for x in re_ if not (len(x) == 1)) if re_ else 0) + (len(rp) if rp else 0)



# ---------------------------------------------------------------- DSL primitive: frame (cycle 3)
def frame_candidates(task, limit=3):
    """Select, by a lattice concept, the unique object whose bounding box becomes the output frame."""
    outs = []
    for ab in ("nbccg", "mcccg", "ccgbr"):
        try:
            per_pair = []
            for p in task["train"]:
                nodes, bg, at, src, others, oc = prepare(p["input"], ab)
                h, w = len(p["output"]), len(p["output"][0])
                dims = [(bbox(n["pix"])[2] - bbox(n["pix"])[0] + 1, bbox(n["pix"])[3] - bbox(n["pix"])[1] + 1) for n in nodes]
                per_pair.append((nodes, at, [d == (h, w) for d in dims]))
            tests = [prepare(t["input"], ab) for t in task["test"]]
        except Timeout:
            raise
        except Exception:
            continue
        if not all(any(c) for _, _, c in per_pair): continue
        attrs = sorted({x for _, at, _ in per_pair for a in at for x in a})
        gens = [(a,) for a in attrs] + list(combinations(attrs, 2))
        for g in gens:
            ok = True
            for nodes, at, cand in per_pair:
                hits = [i for i, a in enumerate(at) if all(x in a for x in g)]
                if len(hits) != 1 or not cand[hits[0]]: ok = False; break
            if not ok: continue
            thits = [[i for i, a in enumerate(tp[2]) if all(x in a for x in g)] for tp in tests]
            if any(len(h) != 1 for h in thits): continue
            sel = [nodes[[i for i, a in enumerate(at) if all(x in a for x in g)][0]] for nodes, at, _ in per_pair]
            tsel = [tp[0][h[0]] for tp, h in zip(tests, thits)]
            outs.append((ab, g, sel, tsel))
            if len(outs) >= limit: return outs
    return outs


def crop(grid, node):
    r0, c0, r1, c1 = bbox(node["pix"])
    return [row[c0:c1 + 1] for row in grid[r0:r1 + 1]]


def solve_frame(task):
    global FRAME_ACTIVE
    found = []
    FRAME_ACTIVE = True
    try:
        for ab, g, sel, tsel in frame_candidates(task):
            inner = {"train": [{"input": crop(p["input"], n), "output": p["output"]} for p, n in zip(task["train"], sel)],
                     "test": [{"input": crop(t["input"], n)} for t, n in zip(task["test"], tsel)]}
            att, _, fnd = solve(inner)
            for f in att:
                found.append(dict(f, frame=(ab, g), rules=f["rules"]))
            if found: break
    finally:
        FRAME_ACTIVE = False
    return found

FRAME_ACTIVE = False

PIXEL_ACTIVE = False


def solve(task, abstractions=ABSTRACTIONS):
    """Simpler vocabulary first (MDL): pixel refinement engages only if no object-level program exists."""
    global PIXEL_ACTIVE
    PIXEL_ACTIVE = False
    res = solve_once(task, abstractions)
    if not res[2] and "P_pixel" in VOCAB:
        PIXEL_ACTIVE = True
        try:
            res = solve_once(task, abstractions)
        finally:
            PIXEL_ACTIVE = False
    if not res[2] and ("S_atoms" in VOCAB or "S_atoms_used" in VOCAB):
        global ATOM_ACTIVE
        ATOM_ACTIVE = True
        try:
            res = solve_once(task, abstractions)
            if not res[2] and "P_pixel" in VOCAB:
                PIXEL_ACTIVE = True
                try: res = solve_once(task, abstractions)
                finally: PIXEL_ACTIVE = False
        finally:
            ATOM_ACTIVE = False
    if not res[2] and "P_frame" in VOCAB and not FRAME_ACTIVE and any(
            (len(p["input"]), len(p["input"][0])) != (len(p["output"]), len(p["output"][0])) for p in task["train"]):
        fr = solve_frame(task)
        if fr:
            res = (fr[:2], dict(res[1], frame="occupied"), fr)
    if not res[2] and "G_dsl" in VOCAB and not FRAME_ACTIVE:
        # whole-grid stratum (cycle 8): verified programs over grid primitives, engaged only when
        # the object lattice, pixel refinement, atoms and frame strata found no program
        import gdsl
        progs = gdsl.search(task)
        if progs:
            found = [{"abstraction": "gdsl", "specific": False, "mode": "gdsl", "rules": ([], []),
                      "program": p["program"], "preds": p["preds"]} for p in progs]
            res = (found[:2], dict(res[1], gdsl="occupied"), found)
    return res


def solve_once(task, abstractions=ABSTRACTIONS):
    found, statuses = [], {}
    for ab in abstractions:
        variants = ([(False, "inertia")] if "L_inertia" in VOCAB else []) + [(False, "greedy"), (True, "greedy")]
        for specific, mode in variants:
            try:
                rules, st = fit(task["train"], ab, specific, mode)
            except Timeout:
                raise
            except Exception as e:
                rules, st = None, f"error:{type(e).__name__}"
            statuses.setdefault(ab, st)
            if rules is None: continue
            try:
                preds = [run_rules(t["input"], rules, ab) for t in task["test"]]
            except Timeout:
                raise
            except Exception:
                continue
            if any(p is None for p in preds): continue
            found.append({"abstraction": ab, "specific": specific, "mode": mode, "rules": rules, "preds": preds})
    distinct = {json.dumps(f["preds"]) for f in found}
    if len(distinct) > 2:  # regeneration stability: concepts must survive leave-one-out
        for f in found:
            f["stable"] = bool(loo(task, [f]))
    attempts, seen = [], set()
    for f in sorted(found, key=lambda f: (not f.get("stable", True), nrules(f["rules"]))):
        key = json.dumps(f["preds"])
        if key not in seen:
            seen.add(key); attempts.append(f)
    return attempts[:2], statuses, found


def loo(task, found):
    if not found or len(task["train"]) < 2: return None
    f = found[0]
    for i in range(len(task["train"])):
        rest = task["train"][:i] + task["train"][i + 1:]
        try:
            rules, _ = fit(rest, f["abstraction"], f["specific"], f.get("mode", "greedy"))
            if rules is None or run_rules(task["train"][i]["input"], rules, f["abstraction"]) != task["train"][i]["output"]:
                return False
        except Timeout:
            raise
        except Exception:
            return False
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--challenges"); ap.add_argument("--solutions"); ap.add_argument("--keys", default="")
    ap.add_argument("--out"); ap.add_argument("--seconds", type=int, default=60)
    args = ap.parse_args()
    ch = json.load(open(args.challenges)); so = json.load(open(args.solutions))
    keys = sorted(ch) if not args.keys else [k.strip() for k in open(args.keys) if k.strip()]
    done = set()
    try:
        done = {json.loads(l)["task"] for l in open(args.out)}
    except FileNotFoundError:
        pass
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(Timeout()))
    for k in keys:
        if k in done: continue
        row = {"task": k}; t0 = time.time()
        try:
            signal.alarm(args.seconds)
            attempts, statuses, found = solve(ch[k])
            row["statuses"] = statuses
            row["occupied"] = bool(found)
            row["n_programs"] = len(found)
            sol = so[k]
            row["test_exact"] = bool(attempts) and all(
                any(a["preds"][i] == sol[i] for a in attempts) for i in range(len(sol)))
            row["loo"] = loo(ch[k], found)
            if attempts:
                rb, re_ = attempts[0]["rules"][:2]
                rp = attempts[0]["rules"][2] if len(attempts[0]["rules"]) > 2 else None
                row["rules"] = [[list(g), l] for g, l in rb] + [[list(x[0]), "effect:" + x[1]] if len(x) == 2 else ["family", x[0]] for x in (re_ or [])] + [[list(g), "pixel:" + l] for g, l in (rp or [])]
                row["n_rules"] = nrules(attempts[0]["rules"])
                row["abstraction"] = attempts[0]["abstraction"]
                if "program" in attempts[0]: row["program"] = attempts[0]["program"]
        except Timeout:
            row["status"] = "timeout"
        finally:
            signal.alarm(0)
        row["seconds"] = round(time.time() - t0, 2)
        with open(args.out, "a") as f:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
