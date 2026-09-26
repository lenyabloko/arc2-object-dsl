"""M1 occupancy probe: prior-concept layer + per-task conceptual lattice + RDR decision list.

Segmentation comes from registered ARCGraph abstractions. Attributes come only from a
fixed, task-independent prior layer (topology, geometry, number/extremes, property
chains). Rules are lattice concepts (extent = closure of a minimal generator of <= 2
attributes) arranged as an RDR-style decision list. No task identifiers; outputs are
used only on training pairs.
"""
from __future__ import annotations

import copy, json, signal, sys, time
from collections import Counter
from itertools import combinations
from types import SimpleNamespace

sys.path[:0] = [__import__("os").environ.get("ARC_STUBS", "stubs"), __import__("os").environ.get("ARC_CANDIDATE", "candidate")]
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
        if lab == "keep": continue
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


# ---------------------------------------------------------------- lattice / RDR decision list
def learn(cases, specific=False):
    """cases: list of (attrset, validlabelset). Greedy decision list of lattice concepts."""
    n = len(cases)
    attrs = sorted({a for at, _ in cases for a in at})
    ext = {a: sum(1 << i for i, (at, _) in enumerate(cases) if a in at) for a in attrs}
    labels = sorted({l for _, ls in cases for l in ls})
    valid = {l: sum(1 << i for i, (_, ls) in enumerate(cases) if l in ls) for l in labels}
    uncovered = (1 << n) - 1
    rules = []
    gens = [()] + [(a,) for a in attrs] + (list(combinations(attrs, 2)) if len(attrs) <= 120 else [])
    while uncovered:
        if len(rules) >= MAX_RULES: return None
        best = None
        for g in gens:
            e = uncovered
            for a in g: e &= ext[a]
            if not e: continue
            cov = bin(e).count("1")
            for l in labels:
                if e & ~valid[l]: continue
                # closure intent size (specificity) for tie-breaking toward/away from closed intent
                key = (cov, (len(g) if specific else -len(g)), l != "keep", tuple(g), l)
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
def prepare(grid, abstraction):
    nodes = segment(grid, abstraction)
    bg = background(grid)
    at, src = attributes(nodes, grid)
    allpix = [set().union(*[m["pix"] for j, m in enumerate(nodes) if j != i]) if len(nodes) > 1 else set()
              for i in range(len(nodes))]
    return nodes, bg, at, src, allpix


def fit(pairs, abstraction, specific=False):
    cases, preps = [], []
    for p in pairs:
        gi, go = p["input"], p["output"]
        if (len(gi), len(gi[0])) != (len(go), len(go[0])): return None, "extent_change"
        nodes, bg, at, src, others = prepare(gi, abstraction)
        labs = [candidate_labels(n, s, gi, go, bg, o) for n, s, o in zip(nodes, src, others)]
        if any(not l for l in labs): return None, "unlabelled_node"
        cases += list(zip(at, labs)); preps.append((gi, go, nodes, bg, at, src, others))
    rules = learn(cases, specific)
    if rules is None: return None, "not_occupied"
    for gi, go, nodes, bg, at, src, others in preps:
        if apply_labels(gi, nodes, src, predict_labels(rules, at), bg, others) != go:
            return None, "not_representable"
    return rules, "occupied"


def run_rules(grid, rules, abstraction):
    nodes, bg, at, src, others = prepare(grid, abstraction)
    return apply_labels(grid, nodes, src, predict_labels(rules, at), bg, others)


def solve(task, abstractions=ABSTRACTIONS):
    found, statuses = [], {}
    for ab in abstractions:
        for specific in (False, True):
            try:
                rules, st = fit(task["train"], ab, specific)
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
            found.append({"abstraction": ab, "specific": specific, "rules": rules, "preds": preds})
    attempts, seen = [], set()
    for f in sorted(found, key=lambda f: len(f["rules"])):
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
            rules, _ = fit(rest, f["abstraction"], f["specific"])
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
                row["rules"] = [[list(g), l] for g, l in attempts[0]["rules"]]
                row["abstraction"] = attempts[0]["abstraction"]
        except Timeout:
            row["status"] = "timeout"
        finally:
            signal.alarm(0)
        row["seconds"] = round(time.time() - t0, 2)
        with open(args.out, "a") as f:
            f.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    main()
