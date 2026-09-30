"""OPTICS prior: occlusion, layering, amodal completion, projection and reflection of light in a flat scene.

Laws (the prior; every family below is a search over one of them)
----
A picture is a stack of opaque LAYERS (shapes, each of one colour) over a background, seen from above.
  L1 Painter's law      render(stack)[p] = colour of the front-most layer whose shape covers p, else bg.
  L2 Depth order        "A in front of B" is a strict partial order, inferred from overlaps only: A is in
                        front of B iff A is visible at a cell that B's (amodal) shape covers (or, for explicit
                        layers, iff A's colour wins where both are opaque in a training output).  It must be
                        acyclic; a comparison the evidence does not decide is never guessed: the program
                        refuses (fn -> None), so an under-determined scene cannot over-fire.
  L3 Amodal completion  the hidden part of a layer is the smallest admissible completion of its visible part
                        (Occam): diagonal / anti-diagonal segment, rectangle outline, solid rectangle (bbox);
                        irregular shapes only bridge row/column gaps (run closure).  Visible fragments of one
                        colour are one layer when their union completes (good continuation; rectangles need
                        aligned fragments).  Admissible = every hidden cell is covered by another colour:
                        nothing hides behind the background, and a hidden cell is never of the layer's colour.
  L4 Projection         light travels straight; an opaque body blocks it.  A body's image on a screen is the
                        sweep of its cells toward the screen, and a body nearer the screen occludes the images
                        of bodies behind it.
  L5 Reflection         a diagonal light ray bounces off opaque bodies like a mirror (the blocked velocity
                        component flips: angle of incidence = angle of reflection), passes transparent colours,
                        is absorbed or reflected by the grid walls.  Beams never interact, so two beams that
                        would meet (same cell in two colours, crossing between cells, hitting another source)
                        are outside the evidence and the program refuses.

Search space (every parameter induced from the training pairs; the harness verifies every program)
------------
  fam_overlay   optics:overlay[stack,order]           L1+L2 on explicit layers.
                  stack: equal panels (separator lattice, a x b grid with 0/1-wide uniform separators, the
                         four corner windows of a constant output size), equal-size windows (framed / holed
                         objects), fragments registered on a common anchor colour (the unique colour seen once
                         in every fragment), or the scene's amodal layers / colour classes slid into a common
                         corner or centre of a canvas as large as the largest;  transparent = the stack ground.
                  order: colour priority or layer-index priority induced as a partial order from training
                         overlaps (undecided test comparisons refuse), or size (smaller / larger in front).
  fam_scene     one scene parse (L3 layers + L2 depth order), three read-outs:
                  optics:depth[view]      depth order of the colour layers as a row / column (back->front or
                                          front->back) or the front-most / back-most colour (1x1); only for
                                          clean scenes (one completed layer per colour).
                  optics:disocclude[X]    occluder X (fixed colour absent from every output, or the rarest /
                                          most fragmented colour) removed; each hidden cell shows the front-most
                                          remaining layer covering it, else bg; whole grid or the hidden window.
                  optics:relayer[key]     the layers re-rendered with a new depth order: reversed, smaller in
                                          front, larger in front.
  fam_project   optics:project[screen,mode,paint]     L4.  screen = a fixed colour or the largest object;
                  each body cell shines along the unique axis direction in which the screen lies; mode: sweep
                  (paint the beam up to the first opaque cell), sweep-reach (only beams reaching the screen),
                  image (recolour the screen cell hit), land (paint the last free cell); paint = own / constant.
  fam_light     optics:light[emitter,transp,adopt,edge,paint]   L5.  emitters: L-triominoes (shine away from
                  the missing corner), diagonal segments (continue from free ends), grid-corner cells;
                  transparent colours (<= 2, passed and painted over); adopt the mirror colour after a bounce or
                  keep; walls absorb / reflect (all, left-right, top-bottom); paint own colour or a new colour.
Tested and dropped (0 tasks each): shadows cast away from a light source, x-ray reveal of hidden parts,
colour-filter transparency (colour of a layer seen through a translucent rectangle), cropping the front-most /
back-most completed layer, point sources shining in four diagonals.

Measured (eval_fam.py, 1000 training + 50 half-A tasks): 38 exact, WRONG 0 (4 of the 38 are the harness's own
identity+colour-map).  overlay 21 (281123b4 3d31c5b3 75b8110e e99362f0 ea9794b1 bc1d5164 25e02866 7c9b52a0
137eaa0f 20818e16 c8cbb738 6a11f6da 2dc579da a68b268e cf98881b e98196ab 0c9aba6e 506d28a5 ce4f8723 d19f7514
e133d23d); scene 6 (depth: 68bc2e87 1a2e2828; disocclude: b7955b3c 7e0986d6; relayer: 52df9849 ba97ae07);
project 4 (13713586 1f642eb9 2c608aff d43fd935); light 3 (7e2bad24 e179c5f4 508bd3b6).  Half-A 142ca369 fits
fam_light on all training pairs, but its test beams cross / hit other sources, so the program refuses.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from itertools import product
from gdsl import H, W, bg_of, objects, bbox, crop, split_panels

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


# ------------------------------------------------------------------ partial orders (L2)
class Order:
    """Strict partial order from pairwise 'a in front of b' evidence, with transitive closure."""
    def __init__(self):
        self.front = {}                          # a -> set of items a is in front of

    def add(self, a, b):
        if a == b: return True
        self.front.setdefault(a, set()).add(b)
        return True

    def close(self):
        """Transitive closure; False if a cycle exists."""
        items = set(self.front) | {b for s in self.front.values() for b in s}
        clo = {a: set(self.front.get(a, ())) for a in items}
        changed = True
        while changed:
            changed = False
            for a in items:
                add = set()
                for b in clo[a]: add |= clo.get(b, set())
                if not add <= clo[a]:
                    clo[a] |= add; changed = True
        self.clo = clo
        return all(a not in clo[a] for a in items)

    def above(self, a, b):
        return b in self.clo.get(a, ())

    def top(self, items):
        """The unique item in front of all others (decided by evidence), else None."""
        items = list(items)
        if len(items) == 1: return items[0]
        for a in items:
            if all(b == a or self.above(a, b) for b in items): return a
        return None

    def chain(self, items):
        """Back-to-front total order of items if the evidence decides it completely, else None."""
        items = list(items)
        srt = sorted(items, key=lambda a: sum(self.above(a, b) for b in items))
        for i in range(len(srt) - 1):
            if not self.above(srt[i + 1], srt[i]): return None
        return srt


# ------------------------------------------------------------------ explicit layer stacks (L1)
def split_grid(g, a, b, s):
    """a x b equal panels separated by s-wide uniform lines (s in {0,1}); reading order."""
    h, w = H(g), W(g)
    if (h - (a - 1) * s) % a or (w - (b - 1) * s) % b: return None
    ph, pw = (h - (a - 1) * s) // a, (w - (b - 1) * s) // b
    if ph < 1 or pw < 1: return None
    if s:
        seps = {g[i * (ph + s) + ph][x] for i in range(a - 1) for x in range(w)}
        seps |= {g[y][j * (pw + s) + pw] for j in range(b - 1) for y in range(h)}
        if len(seps) != 1: return None
    return [[row[j * (pw + s): j * (pw + s) + pw] for row in g[i * (ph + s): i * (ph + s) + ph]]
            for i in range(a) for j in range(b)]


def split_windows(g, diag):
    """Equal-size windows: multicolour components of non-background, all with the same bbox size."""
    bg = bg_of(g)
    obs = objects(g, bg, diag, False)
    if len(obs) < 2 or len(obs) > 12: return None
    boxes = sorted(bbox(o) for o in obs)
    if len({(r1 - r0, c1 - c0) for r0, c0, r1, c1 in boxes}) != 1: return None
    if boxes[0][2] == boxes[0][0] and boxes[0][3] == boxes[0][1]: return None
    return [crop(g, b) for b in boxes]


def splitters(train):
    """(name, fn(g) -> list of equal layers) whose layers have the output's shape on every training pair."""
    i0, o0 = train[0]["input"], train[0]["output"]
    if H(o0) > H(i0) or W(o0) > W(i0) or (H(o0), W(o0)) == (H(i0), W(i0)): return []
    cands = [("sep", lambda g: (lambda sp: sp[0] if sp else None)(split_panels(g)))]
    for a, b in product(range(1, 5), range(1, 5)):
        if a * b < 2: continue
        for s in (0, 1):
            cands.append((f"grid{a}x{b}s{s}", lambda g, a=a, b=b, s=s: split_grid(g, a, b, s)))
    cands.append(("win4", lambda g: split_windows(g, False)))
    cands.append(("win8", lambda g: split_windows(g, True)))
    if len({(H(p["input"]), W(p["input"])) for p in train}) == 1 and len({(H(p["output"]), W(p["output"])) for p in train}) == 1:
        h, w = H(o0), W(o0)
        def corners(g, h=h, w=w):
            if H(g) < h or W(g) < w or (H(g), W(g)) != (H(i0), W(i0)): return None
            return [crop(g, (r, c, r + h - 1, c + w - 1)) for r in (0, H(g) - h) for c in (0, W(g) - w)]
        cands.append(("corners", corners))
    out = []
    for name, fn in cands:
        ok = True
        for p in train:
            try:
                L = fn(p["input"])
            except Exception:
                L = None
            if not L or len(L) < 2 or any((H(x), W(x)) != (H(p["output"]), W(p["output"])) for x in L):
                ok = False; break
        if ok: out.append((name, fn))
    return out


def ground(panels):
    """Transparent colour of a panel stack: the most common colour over all panel cells."""
    return Counter(v for L in panels for r in L for v in r).most_common(1)[0][0]


# A STACK is (layers, h, w, t): each layer a dict {(y, x): colour} of its opaque cells in canvas coordinates,
# a canvas of h x w cells and the transparent ground colour t.
def panel_stack(panels):
    t = ground(panels)
    return [{(y, x): v for y, r in enumerate(P) for x, v in enumerate(r) if v != t} for P in panels], H(panels[0]), W(panels[0]), t


def anchor_stack(g, diag):
    """Fragments (multicolour components) that each hold exactly one cell of a common anchor colour,
    registered on that cell (the anchor colour is the unique colour occurring once in every fragment)."""
    bg = bg_of(g)
    obs = objects(g, bg, diag, False)
    if len(obs) < 2 or len(obs) > 12: return None
    cand = None
    for ob in obs:
        cnt = Counter(g[y][x] for y, x in ob)
        ones = {c for c, n in cnt.items() if n == 1}
        cand = ones if cand is None else cand & ones
    if not cand or len(cand) != 1: return None
    a = cand.pop(); rel = []
    for ob in obs:
        ay, ax = next((y, x) for y, x in ob if g[y][x] == a)
        rel.append({(y - ay, x - ax): g[y][x] for y, x in ob})
    ys = [y for L in rel for y, _ in L]; xs = [x for L in rel for _, x in L]
    y0, x0 = min(ys), min(xs)
    return [{(y - y0, x - x0): v for (y, x), v in L.items()} for L in rel], max(ys) - y0 + 1, max(xs) - x0 + 1, bg


def class_stack(g, source, align):
    """Layers = the scene's amodal layers (L3) or its colour classes, registered at a common corner or at
    their common centre on a canvas as large as the largest layer."""
    bg = bg_of(g)
    if source == "amodal":
        S = scene(g, bg)
        if not S or len(S) < 2 or any(L["model"] == "runs" for L in S): return None
        parts = [(L["colour"], L["M"]) for L in S]
    else:
        cells = {}
        for y, r in enumerate(g):
            for x, v in enumerate(r):
                if v != bg: cells.setdefault(v, set()).add((y, x))
        if len(cells) < 2: return None
        parts = sorted(cells.items())
    boxes = [bbox(M) for _, M in parts]
    h = max(r1 - r0 + 1 for r0, _, r1, _ in boxes); w = max(c1 - c0 + 1 for _, c0, _, c1 in boxes)
    layers = []
    for (c, M), (r0, c0, r1, c1) in zip(parts, boxes):
        if align == "centre":
            if (h - (r1 - r0 + 1)) % 2 or (w - (c1 - c0 + 1)) % 2: return None
            dy = (h - (r1 - r0 + 1)) // 2 - r0; dx = (w - (c1 - c0 + 1)) // 2 - c0
        else:
            dy = -r0 if align[0] == "t" else h - 1 - r1
            dx = -c0 if align[1] == "l" else w - 1 - c1
        layers.append({(y + dy, x + dx): c for y, x in M})
    return layers, h, w, bg


def stackers(train):
    """(name, fn(g) -> stack) whose canvas has the output's shape on every training pair."""
    i0, o0 = train[0]["input"], train[0]["output"]
    if H(o0) > H(i0) or W(o0) > W(i0) or (H(o0), W(o0)) == (H(i0), W(i0)): return []
    cands = [(n, lambda g, f=f: (lambda P: panel_stack(P) if P and len(P) >= 2 else None)(f(g))) for n, f in splitters(train)]
    cands += [(f"anchor{'8' if d else '4'}", lambda g, d=d: anchor_stack(g, d)) for d in (True, False)]
    cands += [(f"{s}-{a}", lambda g, s=s, a=a: class_stack(g, s, a))
              for s in ("amodal", "colour") for a in ("tl", "tr", "bl", "br", "centre")]
    out = []
    for name, fn in cands:
        ok = True
        for p in train:
            try:
                S = fn(p["input"])
            except Exception:
                S = None
            if not S or (S[1], S[2]) != (H(p["output"]), W(p["output"])): ok = False; break
        if ok: out.append((name, fn))
    return out


def induce_stack_order(train, stk, key):
    """Pairwise depth evidence from training outputs; key 'colour' (items are colours) or 'panel'
    (items are layer indices).  Returns a closed Order or None if the painter's law cannot explain a pair."""
    od = Order(); nlay = None
    for p in train:
        layers, h, w, t = stk(p["input"]); o = p["output"]
        if key == "panel":
            if nlay is None: nlay = len(layers)
            elif nlay != len(layers): return None
        for y in range(h):
            for x in range(w):
                vals = [(k, L[(y, x)]) for k, L in enumerate(layers) if (y, x) in L]
                v = o[y][x]
                if not vals:
                    if v != t: return None
                    continue
                if v not in {c for _, c in vals}: return None
                if key == "colour":
                    for _, c in vals:
                        if c != v: od.add(v, c)
                else:
                    win = [k for k, c in vals if c == v]
                    if len(win) == 1:
                        for k, c in vals:
                            if c != v: od.add(win[0], k)
    return od if od.close() else None


def compose(stack, key, od=None):
    """Painter's law (L1): each canvas cell shows its front-most opaque layer; undecided order -> None."""
    layers, h, w, t = stack
    out = [[t] * w for _ in range(h)]
    size = [len(L) for L in layers]
    for y in range(h):
        for x in range(w):
            vals = [(k, L[(y, x)]) for k, L in enumerate(layers) if (y, x) in L]
            if not vals: continue
            cols = {c for _, c in vals}
            if len(cols) == 1:
                out[y][x] = vals[0][1]; continue
            if key == "colour":
                win = od.top(cols)
            elif key == "panel":
                k = od.top([k for k, _ in vals])
                win = None if k is None else layers[k][(y, x)]
            else:
                best = (min if key == "small" else max)(size[k] for k, _ in vals)
                ws = {c for k, c in vals if size[k] == best}
                win = ws.pop() if len(ws) == 1 else None
            if win is None: return None
            out[y][x] = win
    return out


def fam_overlay(train):
    """L1+L2 on explicit layers (panels, windows, anchor-registered fragments, corner-stacked amodal layers)
    composed by the painter's law; depth order induced from training overlaps (by colour or layer index)
    or given by size (smaller / larger in front)."""
    for sname, stk in stackers(train):
        for key in ("colour", "panel", "small", "large"):
            if key in ("colour", "panel"):
                od = induce_stack_order(train, stk, key)
                if od is None: continue
            else:
                od = None
            def fn(g, stk=stk, od=od, key=key):
                S = stk(g)
                if not S or len(S[0]) < 2: return None
                if key == "panel" and od.clo and max(max(od.clo), max((b for s in od.clo.values() for b in s), default=0)) >= len(S[0]):
                    return None
                return compose(S, key, od)
            yield (f"optics:overlay[{sname},{key}]", 4, fn)


# ------------------------------------------------------------------ scene analysis: amodal completion (L3)
MODELS = ("diag", "anti", "outline", "rect")          # smallest completion first (Occam)


class Pic:
    """A grid with O(1) per-colour rectangle counts (2-D prefix sums)."""
    def __init__(self, g, bg):
        self.g, self.bg, self.h, self.w = g, bg, H(g), W(g)
        self.P = {}
        for c in {v for r in g for v in r}:
            P = [[0] * (self.w + 1) for _ in range(self.h + 1)]
            for y in range(self.h):
                acc = 0; row = g[y]; up = P[y]; cur = P[y + 1]
                for x in range(self.w):
                    acc += row[x] == c
                    cur[x + 1] = up[x + 1] + acc
            self.P[c] = P

    def count(self, c, r0, c0, r1, c1):
        P = self.P.get(c)
        if P is None or r1 < r0 or c1 < c0: return 0
        return P[r1 + 1][c1 + 1] - P[r0][c1 + 1] - P[r1 + 1][c0] + P[r0][c0]

    def ring(self, c, r0, c0, r1, c1):
        return (self.count(c, r0, c0, r0, c1) + self.count(c, r1, c0, r1, c1) +
                self.count(c, r0 + 1, c0, r1 - 1, c0) + self.count(c, r0 + 1, c1, r1 - 1, c1))


def fit_model(pic, V, col, box, model):
    """Is `model` an admissible completion of fragment V (colour col, bbox box)?  Hidden cells must all be
    covered by other colours: no background and no other cell of the layer's own colour inside the model."""
    r0, c0, r1, c1 = box
    if model == "rect":
        return pic.count(pic.bg, r0, c0, r1, c1) == 0 and pic.count(col, r0, c0, r1, c1) == len(V)
    if model == "outline":
        if r1 - r0 < 2 or c1 - c0 < 2: return False
        if any(r0 < y < r1 and c0 < x < c1 for y, x in V): return False
        return pic.ring(pic.bg, r0, c0, r1, c1) == 0 and pic.ring(col, r0, c0, r1, c1) == len(V)
    if model in ("diag", "anti"):
        if r1 == r0 or r1 - r0 != c1 - c0: return False
        if model == "diag":
            if len({y - x for y, x in V}) != 1: return False
            cells = [(r0 + k, c0 + k) for k in range(r1 - r0 + 1)]
        else:
            if len({y + x for y, x in V}) != 1: return False
            cells = [(r0 + k, c1 - k) for k in range(r1 - r0 + 1)]
        g = pic.g
        return all((y, x) in V or (g[y][x] != pic.bg and g[y][x] != col) for y, x in cells)
    return False


def model_cells(box, model):
    r0, c0, r1, c1 = box
    if model == "rect":
        return {(y, x) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)}
    if model == "outline":
        return {(y, x) for y in range(r0, r1 + 1) for x in (c0, c1)} | {(y, x) for y in (r0, r1) for x in range(c0, c1 + 1)}
    if model == "diag":
        return {(r0 + k, c0 + k) for k in range(r1 - r0 + 1)}
    return {(r0 + k, c1 - k) for k in range(r1 - r0 + 1)}


def best_model(pic, V, col, box=None):
    """Smallest admissible completion (Occam); irregular shapes fall back to run closure."""
    box = box or bbox(V)
    for m in MODELS:
        if fit_model(pic, V, col, box, m): return m, model_cells(box, m)
    return "runs", run_closure(pic.g, pic.bg, V)


def run_closure(g, bg, V):
    """Fallback completion of an irregular shape: a gap between two visible cells of the shape on one row
    or column is hidden (part of the shape) when every gap cell is covered by another colour."""
    M = set(V); col = g[next(iter(V))[0]][next(iter(V))[1]]
    rows, cols = {}, {}
    for y, x in V:
        rows.setdefault(y, []).append(x); cols.setdefault(x, []).append(y)
    for y, xs in rows.items():
        xs.sort()
        for a, b in zip(xs, xs[1:]):
            if b > a + 1 and all(g[y][x] != bg and g[y][x] != col for x in range(a + 1, b)):
                M |= {(y, x) for x in range(a + 1, b)}
    for x, ys in cols.items():
        ys.sort()
        for a, b in zip(ys, ys[1:]):
            if b > a + 1 and all(g[y][x] != bg and g[y][x] != col for y in range(a + 1, b)):
                M |= {(y, x) for y in range(a + 1, b)}
    return M


def _union_box(a, b):
    return min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])


def _aligned(a, b):
    return (a[0] <= b[2] and b[0] <= a[2]) or (a[1] <= b[3] and b[1] <= a[3])


_SCENES = {}


def scene(g, bg, skip=(), max_frag=80):
    """Layers of a picture: list of dicts {colour, V (visible cells), M (amodal cells), model}.
    Fragments of one colour (8-connected) are merged by good continuation when a non-trivial model of
    their union is admissible (rectangle merges also need aligned fragments).  Colours in `skip` are pure
    occluders (not layers).  Cached per grid."""
    key = (tuple(map(tuple, g)), bg, tuple(sorted(skip)))
    if key in _SCENES: return _SCENES[key]
    if len(_SCENES) > 64: _SCENES.clear()
    res = _scene(g, bg, skip, max_frag)
    _SCENES[key] = res
    return res


def _scene(g, bg, skip, max_frag):
    frags = {}
    for ob in objects(g, bg, True, True):
        c = g[ob[0][0]][ob[0][1]]
        if c in skip: continue
        frags.setdefault(c, []).append((set(ob), bbox(ob)))
    if sum(len(v) for v in frags.values()) > max_frag: return None
    pic = Pic(g, bg); layers = []
    for c, F in frags.items():
        if len(F) > 1:
            U = set().union(*(V for V, _ in F)); box = bbox(U)
            if any(fit_model(pic, U, c, box, m) for m in MODELS): F = [(U, box)]
        changed = True
        while changed and len(F) > 1:
            changed = False
            a = 0
            while a < len(F):
                b = a + 1
                while b < len(F):
                    (A, ba), (B, bb) = F[a], F[b]
                    U = A | B; box = _union_box(ba, bb)
                    ok = any(fit_model(pic, U, c, box, m) for m in ("diag", "anti", "outline")) or \
                        (_aligned(ba, bb) and fit_model(pic, U, c, box, "rect"))
                    if ok:
                        F[a] = (U, box); del F[b]; changed = True
                    else:
                        b += 1
                a += 1
        for V, box in F:
            m, M = best_model(pic, V, c, box)
            layers.append({"colour": c, "V": V, "M": M, "model": m})
    return layers


def layer_order(g, layers):
    """Occlusion evidence between layers (L2): layer j in front of layer i if j is visible inside M_i."""
    where = {}
    for j, L in enumerate(layers):
        for p in L["V"]: where[p] = j
    od = Order()
    for i, L in enumerate(layers):
        for p in L["M"] - L["V"]:
            j = where.get(p)
            if j is not None and j != i: od.add(j, i)
    for i in range(len(layers)): od.front.setdefault(i, set())
    return od if od.close() else None


def colour_order(layers, od):
    co = Order()
    for a, s in od.front.items():
        for b in s:
            ca, cb = layers[a]["colour"], layers[b]["colour"]
            if ca != cb: co.add(ca, cb)
    for L in layers: co.front.setdefault(L["colour"], set())
    return co if co.close() else None


# ------------------------------------------------------------------ depth-order summaries
VIEWS = ("row-b2f", "row-f2b", "col-b2f", "col-f2b", "top", "bottom")


def depth_view(g, view):
    bg = bg_of(g)
    layers = scene(g, bg)
    if not layers: return None
    od = layer_order(g, layers)
    if od is None: return None
    co = colour_order(layers, od)
    if co is None: return None
    cols = sorted({L["colour"] for L in layers})
    if len(cols) < 2 or len(cols) != len(layers) or any(L["model"] == "runs" for L in layers): return None
    if view in ("top", "bottom"):
        if view == "top":
            w = co.top(cols)
        else:
            w = [a for a in cols if all(b == a or co.above(b, a) for b in cols)]
            w = w[0] if len(w) == 1 else None
        return [[w]] if w is not None else None
    ch = co.chain(cols)
    if ch is None: return None
    if view.endswith("f2b"): ch = ch[::-1]
    return [ch] if view.startswith("row") else [[c] for c in ch]


def depth_programs(train):
    """Read-out 1: the depth order of the scene's colour layers (row/column list or front/back colour)."""
    o = train[0]["output"]
    if not (H(o) == 1 or W(o) == 1) or H(o) * W(o) > 10: return
    for view in VIEWS:
        if view in ("top", "bottom") and (H(o), W(o)) != (1, 1): continue
        if view.startswith("row") and H(o) != 1: continue
        if view.startswith("col") and W(o) != 1: continue
        yield (f"optics:depth[{view}]", 4, lambda g, view=view: depth_view(g, view))


# ------------------------------------------------------------------ disocclusion and re-layering
def _bottom(od, items):
    items = list(items)
    if len(items) == 1: return items[0]
    hits = [a for a in items if all(b == a or od.above(b, a) for b in items)]
    return hits[0] if len(hits) == 1 else None


def occluders(train):
    """Colours present in every training input and absent from every training output."""
    X = None
    for p in train:
        ci = {v for r in p["input"] for v in r}; co = {v for r in p["output"] for v in r}
        X = (ci - co) if X is None else X & (ci - co)
    return sorted(X or ())


def disocclude(g, X, out):
    cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == X]
    if not cells: return None
    rest = Counter(v for r in g for v in r if v != X)
    if not rest: return None
    bg = rest.most_common(1)[0][0]
    layers = scene(g, bg, skip={X})
    if layers is None: return None
    od = layer_order(g, layers)
    if od is None: return None
    res = [r[:] for r in g]
    for y, x in cells:
        cov = [j for j, L in enumerate(layers) if (y, x) in L["M"]]
        if not cov:
            res[y][x] = bg; continue
        cs = {layers[j]["colour"] for j in cov}
        if len(cs) == 1:
            res[y][x] = cs.pop(); continue
        w = od.top(cov)
        if w is None: return None
        res[y][x] = layers[w]["colour"]
    return res if out == "grid" else crop(res, bbox(cells))


def occluder_role(g, role):
    """Occluder colour of a grid by role: 'rare' = least frequent colour, 'frag' = the colour split into
    the most 8-connected pieces (scattered noise); unique or None."""
    cnt = Counter(v for r in g for v in r)
    if len(cnt) < 3: return None
    bg = cnt.most_common(1)[0][0]
    if role == "rare":
        m = min(n for c, n in cnt.items() if c != bg)
        hits = [c for c, n in cnt.items() if c != bg and n == m]
    else:
        pieces = Counter(g[o[0][0]][o[0][1]] for o in objects(g, bg, True, True))
        m = max(pieces.values())
        hits = [c for c, n in pieces.items() if n == m]
    return hits[0] if len(hits) == 1 else None


def disocclude_programs(train):
    """Read-out 2: remove an occluder; hidden cells show the front-most remaining amodal layer (L1-L3).
    The occluder is a fixed colour (absent from all outputs) or a per-grid role (rarest / most fragmented)."""
    i, o = train[0]["input"], train[0]["output"]
    same = (H(i), W(i)) == (H(o), W(o))
    out = "grid" if same else "patch"
    for X in occluders(train):
        yield (f"optics:disocclude[c{X},{out}]", 4, lambda g, X=X, out=out: disocclude(g, X, out))
    for role in ("rare", "frag"):
        if all(occluder_role(p["input"], role) is not None and occluder_role(p["input"], role) not in {v for r in p["output"] for v in r}
               for p in train):
            yield (f"optics:disocclude[{role},{out}]", 5,
                   lambda g, role=role, out=out: (lambda X: disocclude(g, X, out) if X is not None else None)(occluder_role(g, role)))


def relayer(g, key):
    bg = bg_of(g)
    layers = scene(g, bg)
    if not layers or len(layers) < 2: return None
    od = layer_order(g, layers)
    if od is None: return None
    res = [[bg] * W(g) for _ in range(H(g))]
    cover = {}
    for j, L in enumerate(layers):
        for p in L["M"]: cover.setdefault(p, []).append(j)
    for (y, x), cov in cover.items():
        cs = {layers[j]["colour"] for j in cov}
        if len(cs) == 1:
            res[y][x] = cs.pop(); continue
        if key == "reverse":
            w = _bottom(od, cov)
        else:
            sz = {j: len(layers[j]["M"]) for j in cov}
            best = (min if key == "small-front" else max)(sz.values())
            ws = {layers[j]["colour"] for j in cov if sz[j] == best}
            w = next(j for j in cov if sz[j] == best) if len(ws) == 1 else None
        if w is None: return None
        res[y][x] = layers[w]["colour"]
    return res


def relayer_programs(train):
    """Read-out 3: re-render the amodal layers with a new depth order (smaller/larger in front, reversed)."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(i), W(i)) != (H(o), W(o)): return
    for key in ("small-front", "large-front", "reverse"):
        yield (f"optics:relayer[{key}]", 4, lambda g, key=key: relayer(g, key))


def fam_scene(train):
    """One layered-scene parse (amodal layers L3 + depth order L2) with three read-outs:
    depth summary, disocclusion (occluder removed), re-layering (new depth order)."""
    yield from depth_programs(train)
    yield from disocclude_programs(train)
    yield from relayer_programs(train)


# ------------------------------------------------------------------ projection onto a screen (L4)
def screen_colour(g, bg, role):
    """Screen colour by role: a fixed colour, or the colour of the unique largest object."""
    if role == "largest":
        obs = objects(g, bg, False, True)
        if not obs: return None
        m = max(len(o) for o in obs)
        cs = {g[o[0][0]][o[0][1]] for o in obs if len(o) == m}
        return cs.pop() if len(cs) == 1 else None
    return role if any(role in r for r in g) else None


_BEAMS = {}


def beams(g, bg, sc):
    """Beam of every body cell toward the screen colour sc (cached per grid): (colour, path, end, reach)."""
    key = (tuple(map(tuple, g)), bg, sc)
    if key in _BEAMS: return _BEAMS[key]
    if len(_BEAMS) > 64: _BEAMS.clear()
    h, w = H(g), W(g); res = []
    ahead = {}                                        # screen cell ahead of (y, x) in each direction
    for d in N4:
        dy, dx = d
        ys = range(h) if dy <= 0 else range(h - 1, -1, -1)
        xs = range(w) if dx <= 0 else range(w - 1, -1, -1)
        seen = {}
        for y in ys:
            for x in xs:
                py, px = y + dy, x + dx
                nxt = (0 <= py < h and 0 <= px < w) and (g[py][px] == sc or seen.get((py, px), False))
                seen[(y, x)] = nxt
        ahead[d] = seen
    for y in range(h):
        for x in range(w):
            c = g[y][x]
            if c == bg or c == sc: continue
            ds = [d for d in N4 if ahead[d][(y, x)]]
            if len(ds) != 1: continue
            dy, dx = ds[0]; yy, xx = y + dy, x + dx; path = []
            while 0 <= yy < h and 0 <= xx < w and g[yy][xx] == bg:
                path.append((yy, xx)); yy += dy; xx += dx
            reach = 0 <= yy < h and 0 <= xx < w and g[yy][xx] == sc
            res.append((c, path, (yy, xx), reach))
    _BEAMS[key] = res
    return res


def project(g, role, mode, paint):
    """Every body cell (not bg, not screen) casts a beam toward the screen: the unique axis direction in
    which a screen cell lies ahead.  The beam crosses background and stops at the first opaque cell, so a
    body nearer the screen occludes the images of bodies behind it.
    mode: sweep (paint the beam), sweep-reach (only beams that reach the screen), image (recolour the first
    screen cell hit), land (paint the last free cell before the screen); paint: body colour or a constant."""
    bg = bg_of(g)
    sc = screen_colour(g, bg, role)
    if sc is None or sc == bg: return None
    out = [r[:] for r in g]; n = 0
    for c, path, (yy, xx), reach in beams(g, bg, sc):
        col = c if paint is None else paint
        if mode == "sweep" or (mode == "sweep-reach" and reach):
            for y, x in path: out[y][x] = col
            n += len(path)
        elif mode == "image" and reach:
            out[yy][xx] = col; n += 1
        elif mode == "land" and reach and path:
            out[path[-1][0]][path[-1][1]] = col; n += 1
    return out if n else None


def fam_project(train):
    """L4: bodies project onto a screen (fixed colour or the largest object) along the axis facing it."""
    i, o = train[0]["input"], train[0]["output"]
    if any((H(p["input"]), W(p["input"])) != (H(p["output"]), W(p["output"])) for p in train): return
    bg = bg_of(i)
    new = Counter(o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x])
    if not new: return
    cols = set.intersection(*[{v for r in p["input"] for v in r} for p in train]) - {bg}
    paints = [None] + [c for c, _ in new.most_common(2)]
    for role, mode, paint in product(sorted(cols) + ["largest"], ("sweep", "sweep-reach", "image", "land"), paints):
        fn = lambda g, role=role, mode=mode, paint=paint: project(g, role, mode, paint)
        try:
            if fn(i) != o: continue
        except Exception:
            continue
        yield (f"optics:project[{role},{mode},{'own' if paint is None else paint}]", 4, fn)


# ------------------------------------------------------------------ light rays and mirrors (L5)
def emitters(g, bg, kind):
    """Light sources (start cell, diagonal direction, colour): an L-triomino shines away from its missing
    corner; a diagonal segment continues from each free end; a single cell in a grid corner shines inward."""
    h, w = H(g), W(g); out = []
    for ob in objects(g, bg, True, True):
        c = g[ob[0][0]][ob[0][1]]; r0, c0, r1, c1 = bbox(ob); S = set(ob)
        if kind == "L" and len(ob) == 3 and r1 - r0 == 1 and c1 - c0 == 1:
            my, mx = next((y, x) for y in (r0, r1) for x in (c0, c1) if (y, x) not in S)
            cy, cx = r0 + r1 - my, c0 + c1 - mx; d = (cy - my, cx - mx)
            out.append(((cy + d[0], cx + d[1]), d, c, S))
        elif kind == "seg" and len(ob) >= 2 and r1 - r0 + 1 == len(ob) and c1 - c0 + 1 == len(ob):
            if len({y - x for y, x in ob}) == 1: ends = (((r0, c0), (-1, -1)), ((r1, c1), (1, 1)))
            elif len({y + x for y, x in ob}) == 1: ends = (((r0, c1), (-1, 1)), ((r1, c0), (1, -1)))
            else: continue
            for (y, x), d in ends:
                q = (y + d[0], x + d[1])
                if 0 <= q[0] < h and 0 <= q[1] < w: out.append((q, d, c, S))
        elif kind == "corner" and len(ob) == 1 and ob[0][0] in (0, h - 1) and ob[0][1] in (0, w - 1):
            y, x = ob[0]; d = (1 if y == 0 else -1, 1 if x == 0 else -1)
            out.append(((y + d[0], x + d[1]), d, c, S))
    return out


def trace(g, bg, out, start, d, col, transp, adopt, edge, lit, rid, sources):
    """Follow one diagonal ray (id rid), painting background (and transparent) cells.  Reflection law:
    when the vertical / horizontal neighbour in the direction of travel is opaque (a mirror) the
    corresponding velocity component flips; a head-on corner hit reverses the ray.  Grid edges absorb the
    ray, or reflect it (edge = all | x: left/right walls | y: top/bottom walls).  adopt: after a bounce the
    ray takes the mirror's colour.  lit maps painted cells to (colour, ray ids).  Returns the number of
    painted cells, or -1 when the picture is undecided: two beams lighting one cell with different colours,
    or a beam running into another light source -- interactions the training pairs never show."""
    h, w = H(g), W(g)
    def opaque(y, x, axis):
        if not (0 <= y < h and 0 <= x < w):
            return edge == "all" or (edge == "x" and axis == "h") or (edge == "y" and axis == "v")
        v = g[y][x]
        return v != bg and v not in transp
    def paint(y, x, col):
        c0, ids = lit.setdefault((y, x), (col, set()))
        if c0 != col: return False
        ids.add(rid); out[y][x] = col
        return True
    y, x = start; dy, dx = d
    if not (0 <= y < h and 0 <= x < w) or opaque(y, x, "d"): return 0
    seen = set(); n = 0
    while (y, x, dy, dx) not in seen:
        seen.add((y, x, dy, dx))
        if not paint(y, x, col): return -1
        n += 1
        for _ in range(2):
            vb, hb = opaque(y + dy, x, "v"), opaque(y, x + dx, "h")
            db = 0 <= y + dy < h and 0 <= x + dx < w and opaque(y + dy, x + dx, "d")
            if not (vb or hb or db): break
            src = (y + dy, x) if vb and not hb else (y, x + dx) if hb and not vb else (y + dy, x + dx)
            if src in sources or (vb and (y + dy, x) in sources) or (hb and (y, x + dx) in sources): return -1
            if vb and not hb: dy = -dy
            elif hb and not vb: dx = -dx
            else: dy, dx = -dy, -dx
            if adopt and 0 <= src[0] < h and 0 <= src[1] < w and g[src[0]][src[1]] != col:
                if lit[(y, x)][1] != {rid}: return -1
                col = g[src[0]][src[1]]; lit[(y, x)] = (col, {rid}); out[y][x] = col
        ny, nx = y + dy, x + dx
        if not (0 <= ny < h and 0 <= nx < w) or opaque(ny, nx, "d"): break
        y, x = ny, nx
    return n


def light(g, kind, transp, adopt, edge, paint=None):
    """All emitters shine; beams that cross each other between cells (an X of two different rays) are an
    interaction never shown in training -> undecided (None)."""
    bg = bg_of(g); out = [r[:] for r in g]; n = 0; lit = {}
    em = emitters(g, bg, kind)
    sources = set().union(*(S for *_, S in em)) if em else set()
    for rid, (start, d, c, S) in enumerate(em):
        k = trace(g, bg, out, start, d, c if paint is None else paint, transp, adopt, edge, lit, rid, sources - S)
        if k < 0: return None
        n += k
    if not n: return None
    ids = lambda y, x: lit.get((y, x), (None, set()))[1]
    for y in range(H(g) - 1):
        for x in range(W(g) - 1):
            a, d = ids(y, x) & ids(y + 1, x + 1), ids(y, x + 1) & ids(y + 1, x)
            if a and d and (a | d) != (a & d): return None
    return out


def _fits_up_to_bg(pred, o, bg):
    """pred equals o, except that the background may be rendered in one other colour."""
    if pred is None or (H(pred), W(pred)) != (H(o), W(o)): return False
    m = None
    for rp, ro in zip(pred, o):
        for a, b in zip(rp, ro):
            if a == b and a != bg: continue
            if a != bg: return False
            if m is None: m = b
            elif m != b: return False
    return True


def fam_light(train):
    """L5: diagonal light rays from emitters bounce off opaque bodies (mirrors), pass transparent colours."""
    i, o = train[0]["input"], train[0]["output"]
    if any((H(p["input"]), W(p["input"])) != (H(p["output"]), W(p["output"])) for p in train): return
    bg = bg_of(i)
    new = sorted(set.intersection(*[{v for r in p["output"] for v in r} - {v for r in p["input"] for v in r} for p in train]))
    for kind in ("L", "seg", "corner"):
        if not all(emitters(p["input"], bg_of(p["input"]), kind) for p in train): continue
        own = {c for _, _, c, _ in emitters(i, bg, kind)}
        cols = sorted({v for r in i for v in r} - {bg} - own)
        subsets = [()] + [(c,) for c in cols] + [(a, b) for k, a in enumerate(cols) for b in cols[k + 1:]]
        for transp, adopt, edge, paint in product(subsets, (False, True), ("none", "all", "x", "y"), [None] + new[:2]):
            if adopt and paint is not None: continue
            fn = lambda g, t=frozenset(transp), a=adopt, e=edge, k=kind, pc=paint: light(g, k, t, a, e, pc)
            if not _fits_up_to_bg(fn(i), o, bg): continue
            yield (f"optics:light[{kind},transp={''.join(map(str, transp)) or '-'},{'adopt' if adopt else 'keep'},"
                   f"edge={edge},paint={'own' if paint is None else paint}]", 5, fn)


FAMILIES = (fam_overlay, fam_scene, fam_project, fam_light)
