"""compose_residual -- depth-2/3 residual composition over the G-DSL library (Dream lane 3).

SEARCH(task) -> [{"program", "preds"}] (best first, <= 3); every program reproduces all training pairs.

Search space
  A NODE is an intermediate task: train pairs (z_i, y_i), the current test grids, the forward steps applied
  so far, the output-side post-steps still to apply and an optional both-sides WRAP.  The ROOT is the task.
  Expanding a node enumerates the library ONCE on the node's own pairs, family by family (gdsl.FAMILIES
  without fam_codex -- so the parameter-inducing fam_*/prior_* families see the residual pairs -- plus an
  own pool of output-independent steps: crops (fg bbox, 48 object selectors, colour bbox, frame interior),
  panel k, halves, strip border, drop empty / duplicate / uniform lines, erase / keep colour, silhouette
  (fixed colour or colour role), fill-outside, hollow, fill-bbox, invert, swap-fg, one-cell shifts, erase
  selected object, block resize to the (constant) output size, plain / mirror tilings and upscales).
  Each enumerated program p is then
    * a SOLUTION if p(z_i) == y_i on every pair (optionally + one global colour map, as in gdsl.search):
      program = [wrap-in ;] forward steps ; p ; post-steps [; wrap-out];
    * a CHILD (intermediate z'_i = p(z_i)) if it makes PROGRESS on the training pairs:
        - z_i has y_i's shape: Hamming distance to y_i strictly decreases;
        - otherwise: z'_i reaches y_i's shape, or (y_i smaller than z_i) z'_i still contains y_i's best-matching
          window and is smaller (crop-like narrowing), or the best-window distance strictly decreases;
        - relaxed (penalised): the step may leave some pairs untouched if it makes progress on the others.
  Output-side normalisation at the root (reverse direction): exact block upscale of the outputs (target :=
  downscaled output, post-step := upscale), exact D8 tiling (target := one tile, post := tiling), a uniform
  non-background 1-cell output frame, the input shown beside / above / below a new block (target := the
  block, post := put the input back), and a D8 re-orientation of the target that brings it closer to the input.
  Both-sides normalisation (wraps, each a node searched like a root): COLOUR CANONICALISATION -- every grid's
  colours renamed by frequency rank (literal output colours reserved), outputs renamed with their input's map,
  predictions mapped back with the test input's inverse map -- used whenever the renaming differs between
  grids; a uniform frame kept around a transformed interior; in-place change inside a framed region;
  orientation by a single full-colour border wall.
Pruning / beam
  children are deduplicated by their train intermediates (D8-canonical before the output shape is reached,
  cheapest program kept), ranked by mean normalised remaining distance (then cost); at most KIDS per node
  (<= 2 per program stem) enter a best-first queue (wraps first, then children / reverse nodes by score,
  + 0.35 per forward depth).  Forward depth <= 2, i.e. programs have at most 3 library steps (+ post / wrap);
  a second forward step is taken only after an output-independent first step (own pool or core gdsl family)
  and must be one too.
Guards against over-fitting (compositions search a large space)
  * leave-one-out: the last step's family is re-induced on all pairs but one and the same-named program
    must reproduce the held-out pair (the colour-map post-step is fitted on all pairs); a colour-canonical
    wrap around ONE library step counts as a single step and is exempt;
  * low evidence: no composition when all training outputs are the same picture up to colour relabelling;
  * every returned program is re-verified end-to-end on the original training pairs.
Budget
  23 s wall per task: cooperative deadline checks between families / programs plus a SIGPROF-driven hard
  stop (BaseException, so family code cannot swallow it); per-family caps (root 2.5 s, deeper 1.2 s), root
  families with slow enumeration last, deeper nodes cheapest-first (root timing) with a 4 s node budget and
  a stop at the first solution.
Returns [] when a single step already fits (library family or own step): by default (INCLUDE_BASE False) the
engine reports only what composition adds; COMPOSE_INCLUDE_BASE=1 returns those single-step programs.
No task-specific code: every parameter is induced from the training pairs; fam_codex is not used.
"""
from __future__ import annotations
import os, re, sys, time, signal, heapq
from collections import Counter

sys.path.insert(0, '/home/claude/work/widen')
import gdsl
import numpy as np

H, W = gdsl.H, gdsl.W
INCLUDE_BASE = os.environ.get('COMPOSE_INCLUDE_BASE', '0') == '1'
BUDGET = float(os.environ.get('COMPOSE_BUDGET', '23'))
KIDS = 6                  # children kept per node
MAX_FWD = 2               # forward steps before the last library step
FAMILY_CAP = 2.5          # seconds per family enumeration at the root
CHILD_CAP = 1.2           # ... and at deeper nodes
DEBUG = os.environ.get('COMPOSE_DEBUG', '0') == '1'
LOO = os.environ.get('COMPOSE_LOO', '1') == '1'   # leave-one-out check of the last step
RELAX = os.environ.get('COMPOSE_RELAX', '1') == '1'   # allow a first step that leaves some pairs untouched
IDLE_PEN = 0.15
TRACE = []
FAMSTAT = []
FAMILIES = tuple(f for f in gdsl.FAMILIES if f.__name__ != 'fam_codex')
# Families measured (dev runs on training/half-A pairs) to be slow to enumerate (mean > 0.1 s); they run last,
# slowest last, so that a tight budget cuts them rather than the cheap ones.  Order only -- nothing is dropped.
SLOW = ("fam_periodic_fill", "fam_distance_layers", "fam_move_toward_anchor", "fam_shape", "fam_arith_residue",
        "fam_ranked_bars", "fam_complete_partial", "fam_region_by_property", "fam_move_by_vector", "fam_corner_rays",
        "fam_local_stencil", "fam_slide_until_contact")
ROOT_ORDER = tuple(f for f in FAMILIES if f.__name__ not in SLOW) + \
    tuple(sorted((f for f in FAMILIES if f.__name__ in SLOW), key=lambda f: SLOW.index(f.__name__)))
NODE_BUDGET = 4.0         # seconds per deeper node (cheap families first, lazy stop at the first solution)
# Both-sides normalisations tried (dev-set measurements: colour canon 16 exact / 0 wrong on 287 applicable
# tasks; fg-bbox region 1 exact / 1 wrong on 64 at ~4 s each -> off; orientation by mass 0 / 15 -> off).
REGION_KINDS = ("frame",)
ORIENT_FEATURES = ("wall",)

# ------------------------------------------------------------------ time budget (hard stop)
class Budget(BaseException):
    pass

_DL = [float('inf')]
_ARMED = [False]

def _tick(signum, frame):
    if _ARMED[0] and time.time() > _DL[-1]:
        raise Budget()

class within:
    """Nested wall-clock budget; an expired inner budget is swallowed if the outer one is still alive.
    The deadline stack is truncated to its entry depth on exit, so an interrupt anywhere cannot leave it
    misaligned."""
    def __init__(self, secs):
        self.secs = secs
    def __enter__(self):
        self.depth = len(_DL)
        _DL.append(min(_DL[-1], time.time() + self.secs)); return self
    def __exit__(self, et, ev, tb):
        del _DL[self.depth:]
        return et is Budget and time.time() <= _DL[-1]

def _left():
    return _DL[-1] - time.time()

# ------------------------------------------------------------------ grid utilities
def shape(g):
    return (len(g), len(g[0]))

def ham(a, b):
    return sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb))

def best_window(z, y):
    """Minimum Hamming distance between y and any same-size window of z (z at least as large as y)."""
    Z = np.asarray(z); Y = np.asarray(y)
    h, w = Y.shape
    if h > Z.shape[0] or w > Z.shape[1]: return None
    V = np.lib.stride_tricks.sliding_window_view(Z, (h, w))
    return int((V != Y).sum(axis=(2, 3)).min())

def key_of(grids):
    return tuple(tuple(tuple(r) for r in g) for g in grids)

# ------------------------------------------------------------------ own output-independent step pool
def _bg(g): return gdsl.bg_of(g)

def _crop_fg(g):
    bg = _bg(g); cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg]
    return gdsl.crop(g, gdsl.bbox(cells)) if cells else None

def _strip_border(g):
    if H(g) < 3 or W(g) < 3: return None
    b = [g[0][x] for x in range(W(g))] + [g[-1][x] for x in range(W(g))] + [g[y][0] for y in range(H(g))] + [g[y][-1] for y in range(H(g))]
    if len(set(b)) != 1: return None
    return [r[1:-1] for r in g[1:-1]]

def _erase(g, c):
    bg = _bg(g)
    if c == bg: return None
    return [[bg if v == c else v for v in r] for r in g]

def _keep(g, c):
    bg = _bg(g)
    if c == bg: return None
    return [[v if v == c else bg for v in r] for r in g]

def _silhouette(g, c):
    bg = _bg(g)
    return [[bg if v == bg else c for v in r] for r in g]

def _silhouette_role(g, role):
    """All foreground cells take the most (least) frequent foreground colour of this grid."""
    bg = _bg(g); cs = Counter(v for r in g for v in r if v != bg)
    if len(cs) < 2: return None
    mc = cs.most_common()
    if (role == "dominant" and mc[0][1] == mc[1][1]) or (role == "rarest" and mc[-1][1] == mc[-2][1]): return None
    return _silhouette(g, mc[0][0] if role == "dominant" else mc[-1][0])

def _fill_outside(g, c):
    """Background cells 4-connected to the border take colour c."""
    bg = _bg(g); h, w = H(g), W(g); out = [r[:] for r in g]
    st = [(y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and g[y][x] == bg]
    seen = set(st)
    while st:
        y, x = st.pop(); out[y][x] = c
        for yy, xx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= yy < h and 0 <= xx < w and (yy, xx) not in seen and g[yy][xx] == bg:
                seen.add((yy, xx)); st.append((yy, xx))
    return out

def _hollow(g):
    """Interior cells of objects (all 4 neighbours the same colour) become background."""
    bg = _bg(g); h, w = H(g), W(g); out = [r[:] for r in g]
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            v = g[y][x]
            if v != bg and g[y - 1][x] == v and g[y + 1][x] == v and g[y][x - 1] == v and g[y][x + 1] == v:
                out[y][x] = bg
    return out

def _fill_bbox(g, diag):
    """Background cells inside each single-colour object's bounding box take the object's colour."""
    bg = _bg(g); out = [r[:] for r in g]
    for ob in gdsl.objects(g, bg, diag, True):
        r0, c0, r1, c1 = gdsl.bbox(ob); v = g[ob[0][0]][ob[0][1]]
        for y in range(r0, r1 + 1):
            for x in range(c0, c1 + 1):
                if out[y][x] == bg: out[y][x] = v
    return out

def _invert(g):
    """Two-colour grid: swap background and foreground."""
    cs = gdsl.colours(g)
    if len(cs) != 2: return None
    a, b = sorted(cs)
    return [[b if v == a else a for v in r] for r in g]

def _shift(g, c, dy, dx):
    """Cells of colour c (None: all foreground) move one step (dy, dx); cells leaving the grid vanish."""
    bg = _bg(g); h, w = H(g), W(g)
    mv = [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg and (c is None or g[y][x] == c)]
    if not mv: return None
    out = [r[:] for r in g]
    for y, x in mv: out[y][x] = bg
    for y, x in mv:
        if 0 <= y + dy < h and 0 <= x + dx < w: out[y + dy][x + dx] = g[y][x]
    return out

def _swap_fg(g):
    """Exactly two foreground colours: exchange them."""
    bg = _bg(g); cs = sorted(gdsl.colours(g) - {bg})
    if len(cs) != 2: return None
    a, b = cs
    return [[b if v == a else a if v == b else v for v in r] for r in g]

def _drop_empty(g):
    bg = _bg(g)
    rows = [r for r in g if any(v != bg for v in r)]
    if not rows: return None
    cols = [x for x in range(W(g)) if any(r[x] != bg for r in rows)]
    return [[r[x] for x in cols] for r in rows]

def _dedup(g):
    rows = [g[0]] + [g[y] for y in range(1, H(g)) if g[y] != g[y - 1]]
    t = gdsl.T(rows)
    cols = [t[0]] + [t[x] for x in range(1, len(t)) if t[x] != t[x - 1]]
    return gdsl.T(cols)

def _drop_uniform_lines(g):
    """Remove full rows / columns of one colour (separators); what remains is concatenated."""
    rows = [r for r in g if len(set(r)) > 1]
    if not rows: return None
    t = gdsl.T(rows)
    cols = [c for c in t if len(set(c)) > 1]
    if not cols: return None
    return gdsl.T(cols)

def _panel(g, k):
    sp = gdsl.split_panels(g)
    if not sp: return None
    ps = sp[0]
    return ps[k] if k < len(ps) else None

def _half(g, k):
    h, w = H(g), W(g)
    if k == 0: return [r[:w // 2] for r in g] if w % 2 == 0 else None
    if k == 1: return [r[w // 2:] for r in g] if w % 2 == 0 else None
    if k == 2: return g[:h // 2] if h % 2 == 0 else None
    if k == 3: return g[h // 2:] if h % 2 == 0 else None

def _tile_with(g, pat):
    rows = []
    for prow in pat:
        blks = [gdsl.D8[k](g) for k in prow]
        if any(shape(b) != shape(blks[0]) for b in blks): return None
        for rr in range(H(blks[0])):
            rows.append(sum((b[rr] for b in blks), []))
    return rows

TILE_PATTERNS = {
    (1, 2): {"plain": [["id", "id"]], "mirror": [["id", "fh"]], "mirror-rev": [["fh", "id"]]},
    (2, 1): {"plain": [["id"], ["id"]], "mirror": [["id"], ["fv"]], "mirror-rev": [["fv"], ["id"]]},
    (2, 2): {"plain": [["id", "id"], ["id", "id"]], "mirror": [["id", "fh"], ["fv", "r180"]],
             "mirror-rev": [["r180", "fv"], ["fh", "id"]]},
}

def _upscale(g, kh, kw):
    return [[v for v in r for _ in range(kw)] for r in g for _ in range(kh)]

def _resize(g, h, w, mode):
    """Block downscale to a fixed size (h, w); the block size may differ from grid to grid."""
    if H(g) % h or W(g) % w or (H(g), W(g)) == (h, w): return None
    kh, kw = H(g) // h, W(g) // w; bg = _bg(g); out = []
    for a in range(h):
        row = []
        for b in range(w):
            blk = [v for r in g[a * kh:(a + 1) * kh] for v in r[b * kw:(b + 1) * kw]]
            nz = [v for v in blk if v != bg]
            if mode == "any":
                row.append(Counter(nz).most_common(1)[0][0] if nz else bg)
            else:
                row.append(Counter(blk).most_common(1)[0][0])
        out.append(row)
    return out

def own_ops(pairs):
    """Output-independent steps; colour parameters come from the inputs, sizes from the output/input ratio."""
    zs = [z for z, _ in pairs]; ys = [y for _, y in pairs]
    z0, y0 = zs[0], ys[0]
    bgs = {_bg(z) for z in zs}
    cols = sorted(set.intersection(*[gdsl.colours(z) for z in zs]) - bgs)
    anycols = sorted(set.union(*[gdsl.colours(z) for z in zs]) - bgs)
    yield ("crop:all-foreground", 2, _crop_fg)
    yield ("crop:frame-interior", 2, gdsl.frame_interior)
    yield ("strip-border", 2, _strip_border)
    yield ("drop-empty-lines", 2, _drop_empty)
    yield ("dedup-lines", 2, _dedup)
    yield ("drop-uniform-lines", 2, _drop_uniform_lines)
    for c in anycols:
        yield (f"erase[c{c}]", 2, lambda g, c=c: _erase(g, c))
    for c in cols:
        yield (f"keep-colour[c{c}]", 2, lambda g, c=c: _keep(g, c))
    for c in sorted(set.union(*[gdsl.colours(y) for y in ys])):
        yield (f"silhouette[c{c}]", 3, lambda g, c=c: _silhouette(g, c))
    for c in sorted(set.union(*[gdsl.colours(y) for y in ys]) - bgs):
        yield (f"fill-outside[c{c}]", 3, lambda g, c=c: _fill_outside(g, c))
    yield ("hollow", 2, _hollow)
    yield ("fill-bbox[4]", 2, lambda g: _fill_bbox(g, False))
    yield ("fill-bbox[8]", 2, lambda g: _fill_bbox(g, True))
    yield ("invert", 2, _invert)
    yield ("swap-fg", 2, _swap_fg)
    if all(shape(z) == shape(y) for z, y in pairs):
        for c in [None] + cols:
            for dn, (dy, dx) in gdsl.DIRV.items():
                yield (f"shift[{'fg' if c is None else f'c{c}'},{dn}]", 3, lambda g, c=c, dy=dy, dx=dx: _shift(g, c, dy, dx))
    for role in ("dominant", "rarest"):
        yield (f"silhouette[{role}]", 3, lambda g, role=role: _silhouette_role(g, role))
    sp = [gdsl.split_panels(z) for z in zs]
    if all(sp):
        n = min(len(s[0]) for s in sp)
        for k in range(min(n, 9)):
            yield (f"panel[{k}]", 3, lambda g, k=k: _panel(g, k))
    for k, nm in enumerate(("left", "right", "top", "bottom")):
        yield (f"half:{nm}", 3, lambda g, k=k: _half(g, k))
    for c in cols:
        for inner in (False, True):
            def cb(g, c=c, inner=inner):
                cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == c]
                if not cells: return None
                r0, c0, r1, c1 = gdsl.bbox(cells)
                if inner: r0, c0, r1, c1 = r0 + 1, c0 + 1, r1 - 1, c1 - 1
                if r1 < r0 or c1 < c0: return None
                return gdsl.crop(g, (r0, c0, r1, c1))
            yield (f"crop:colour-bbox{'-interior' if inner else ''}[c{c}]", 3, cb)
    for diag in (False, True):
        for byc in (True, False):
            for how in gdsl.SELECTORS:
                def fn(g, diag=diag, byc=byc, how=how):
                    bg = _bg(g); ob = gdsl.select(gdsl.objects(g, bg, diag, byc), g, how)
                    return gdsl.crop(g, gdsl.bbox(ob)) if ob else None
                yield (f"crop:object[{'8' if diag else '4'}{'' if byc else ',multi'}]:{how}", 3, fn)
    shapes_out = {shape(y) for y in ys}
    if len(shapes_out) == 1:
        h, w = next(iter(shapes_out))
        if any(shape(z) != (h, w) for z in zs):
            for mode in ("mode", "any"):
                yield (f"resize-to[{h}x{w},{mode}]", 3, lambda g, h=h, w=w, mode=mode: _resize(g, h, w, mode))
    for diag in (False, True):
        for how in ("largest", "smallest", "unique_colour", "unique_shape"):
            def eo(g, diag=diag, how=how):
                bg = _bg(g); ob = gdsl.select(gdsl.objects(g, bg, diag, True), g, how)
                if not ob: return None
                out = [r[:] for r in g]
                for y, x in ob: out[y][x] = bg
                return out
            yield (f"erase-object[{'8' if diag else '4'}]:{how}", 3, eo)
    # reshapes toward the output size (ratio from the first pair, verified by the progress test)
    if H(y0) % H(z0) == 0 and W(y0) % W(z0) == 0:
        n, m = H(y0) // H(z0), W(y0) // W(z0)
        for nm, pat in TILE_PATTERNS.get((n, m), {}).items():
            yield (f"tile-{nm}:{n}x{m}", 3, lambda g, pat=pat: _tile_with(g, pat))
        if (n, m) not in TILE_PATTERNS and 1 < n * m <= 16:
            yield (f"tile-plain:{n}x{m}", 3, lambda g, n=n, m=m: _tile_with(g, [["id"] * m for _ in range(n)]))
        if n * m > 1:
            yield (f"upscale:{n}x{m}", 2, lambda g, n=n, m=m: _upscale(g, n, m))

# ------------------------------------------------------------------ reverse (output-side) normalisations
def _is_upscale(y, kh, kw):
    if H(y) % kh or W(y) % kw: return False
    return all(y[r][c] == y[r - r % kh][c - c % kw] for r in range(H(y)) for c in range(W(y)))

def _down(y, kh, kw):
    return [[y[r][c] for c in range(0, W(y), kw)] for r in range(0, H(y), kh)]

def _pad(g, c):
    return [[c] * (W(g) + 2)] + [[c] + list(r) + [c] for r in g] + [[c] * (W(g) + 2)]

INV = {"r90": "r270", "r270": "r90", "r180": "r180", "fh": "fh", "fv": "fv", "T": "T", "aT": "aT"}

def _border_colour(g):
    if H(g) < 3 or W(g) < 3: return None
    b = {g[0][x] for x in range(W(g))} | {g[-1][x] for x in range(W(g))} | {g[y][0] for y in range(H(g))} | {g[y][-1] for y in range(H(g))}
    return b.pop() if len(b) == 1 else None

def both_side_normalisations(pairs):
    """Yield (in_name, in_fn, post_name, post_fn, new_outputs, rank): the input is normalised by in_fn, the
    output by the inverse of post_fn."""
    xs = [x for x, _ in pairs]; ys = [y for _, y in pairs]
    # a uniform frame of one colour kept unchanged around a transformed interior
    cs = {_border_colour(g) for g in xs + ys}
    if len(cs) == 1 and None not in cs and all(shape(x) == shape(y) for x, y in pairs):
        c = cs.pop()
        if all(x != y for x, y in pairs):
            def strip(g, c=c):
                return [r[1:-1] for r in g[1:-1]] if _border_colour(g) == c else None
            yield ("strip-frame", strip, f"frame[c{c}]", lambda g, c=c: _pad(g, c),
                   [[r[1:-1] for r in y[1:-1]] for y in ys], 0.1)

def reverse_normalisations(pairs):
    """Yield (name, new_outputs, post_fn, rank) with post_fn(new_output_i) == output_i on every pair."""
    xs = [x for x, _ in pairs]; ys = [y for _, y in pairs]
    # exact block upscale with a common factor
    best = None
    for kh in range(1, 6):
        for kw in range(1, 6):
            if kh * kw == 1: continue
            if all(_is_upscale(y, kh, kw) for y in ys):
                if best is None or kh * kw > best[0] * best[1]: best = (kh, kw)
    if best:
        kh, kw = best
        yield (f"upscale:{kh}x{kw}", [_down(y, kh, kw) for y in ys], lambda g, kh=kh, kw=kw: _upscale(g, kh, kw), 0.05)
    # exact tiling of one block by D8 images (pattern shared by all pairs); most blocks wins
    PREF = ("id", "fh", "fv", "r180", "T", "aT", "r90", "r270")
    bestt = None
    for n in range(1, 6):
        for m in range(1, 6):
            if n * m == 1 or any(H(y) % n or W(y) % m for y in ys): continue
            S = [[set(PREF) for _ in range(m)] for _ in range(n)]
            for y in ys:
                bh, bw = H(y) // n, W(y) // m
                blk = lambda a, b: [r[b * bw:(b + 1) * bw] for r in y[a * bh:(a + 1) * bh]]
                b0 = blk(0, 0)
                for a in range(n):
                    for b in range(m):
                        S[a][b] &= {k for k in S[a][b] if (bh == bw or k in ("id", "r180", "fh", "fv")) and gdsl.D8[k](b0) == blk(a, b)}
            if all(S[a][b] for a in range(n) for b in range(m)) and (bestt is None or n * m > bestt[0] * bestt[1]):
                pat = [[next(k for k in PREF if k in S[a][b]) for b in range(m)] for a in range(n)]
                bestt = (n, m, pat)
    if bestt:
        n, m, pat = bestt
        yield (f"tile{n}x{m}[{','.join('.'.join(r) for r in pat)}]",
               [[r[:W(y) // m] for r in y[:H(y) // n]] for y in ys],
               lambda g, pat=pat: _tile_with(g, pat), 0.05)
    # uniform 1-cell frame of one colour on every output
    fc = set()
    for y in ys:
        if H(y) < 3 or W(y) < 3: fc = None; break
        b = {y[0][x] for x in range(W(y))} | {y[-1][x] for x in range(W(y))} | {y[r][0] for r in range(H(y))} | {y[r][-1] for r in range(H(y))}
        if len(b) != 1: fc = None; break
        fc |= b
    if fc and len(fc) == 1:
        c = fc.pop()
        if all(gdsl.bg_of(y) != c for y in ys):
            yield (f"frame[c{c}]", [[r[1:-1] for r in y[1:-1]] for y in ys], lambda g, c=c: _pad(g, c), 0.1)
    # D8 re-orientation of the target that brings it closer to the input
    for k, f in gdsl.D8.items():
        if k == "id": continue
        inv = gdsl.D8[INV[k]]
        ny = [inv(y) for y in ys]
        ok = True; gain = 0.0
        for x, y, y2 in zip(xs, ys, ny):
            if shape(y2) != shape(x): ok = False; break
            d2 = ham(x, y2) / (H(x) * W(x))
            if shape(y) == shape(x):
                d1 = ham(x, y) / (H(x) * W(x))
                if d2 >= d1: ok = False; break
            gain += d2
        if ok:
            yield (f"orient:{k}", ny, f, 0.3 + gain / len(pairs))

# ------------------------------------------------------------------ node assessment
class Node:
    __slots__ = ("pairs", "tests", "steps", "post", "depth", "score", "cost", "stat", "oi", "wrap")
    def __init__(self, pairs, tests, steps, post, depth, score, cost, oi=True, wrap=None):
        self.pairs, self.tests, self.steps, self.post = pairs, tests, steps, post
        self.depth, self.score, self.cost, self.oi, self.wrap = depth, score, cost, oi, wrap
        self.stat = []
        for z, y in pairs:
            if shape(z) == shape(y):
                self.stat.append(("same", ham(z, y)))
            elif H(z) >= H(y) and W(z) >= W(y):
                self.stat.append(("big", best_window(z, y), H(z) * W(z)))
            else:
                self.stat.append(("other",))

def progress(r, st, y):
    """Normalised remaining distance of r to y if r is progress w.r.t. the pair state st, else None."""
    hy, wy = shape(y)
    if shape(r) == (hy, wy):
        d = ham(r, y)
        if st[0] == "same" and not (d < st[1] or d == st[1] == 0): return None
        return d / (hy * wy)
    if st[0] != "big" or H(r) < hy or W(r) < wy: return None
    d = best_window(r, y)
    if d < st[1] or (d == st[1] and H(r) * W(r) < st[2]):
        return 1.0 + d / (hy * wy)
    return None

def post_apply(g, post):
    for _, f in post:
        if g is None: return None
        g = gdsl.run(f, g)
    return g

def assess(node, cands, t_end, want_kids, sols, kids, src=None, oi=True):
    """Run programs on the node's pairs: exact fits (optionally + colour map) go to `sols`, progress
    programs to `kids` (keyed by their train intermediates, D8-canonical when not yet at the output shape)."""
    outs = [y for _, y in node.pairs]
    ins = [z for z, _ in node.pairs]
    for name, cost, fn in cands:
        if time.time() > t_end: break
        rs = []; ex = True; pg = want_kids; score = 0.0; idle = 0
        for (z, y), st in zip(node.pairs, node.stat):
            r = gdsl.run(fn, z)
            if r is None: ex = pg = False; break
            if ex and shape(r) != shape(y): ex = False
            if ex and not rs and gdsl.fit_cmap([r], [y]) is None: ex = False
            if pg:
                p = progress(r, st, y)
                if p is not None:
                    score += p
                elif RELAX and r == z and st[0] != "other":
                    idle += 1          # step does not act on this pair (allowed, penalised)
                    score += (st[1] / (H(y) * W(y))) + (1.0 if st[0] == "big" else 0.0)
                else:
                    pg = False
            if not ex and not pg: break
            rs.append(r)
        if not (ex or pg) or len(rs) != len(node.pairs): continue
        if pg and idle == len(rs): pg = False
        if ex:
            fin = None
            if rs == outs:
                fin = (name, cost, fn)
            else:
                m = gdsl.fit_cmap(rs, outs)
                if m and all(gdsl.apply_cmap(a, m) == b for a, b in zip(rs, outs)):
                    fin = (name + "+colour-map", cost + 1, lambda g, fn=fn, m=m: gdsl.apply_cmap(gdsl.run(fn, g), m))
            if fin:
                tp = [gdsl.run(fin[2], t) for t in node.tests]
                if all(p is not None for p in tp):
                    tp = [post_apply(p, node.post) for p in tp]
                    if all(p is not None for p in tp):
                        sols.append((fin[0], fin[1], fin[2], tp, src))
                continue
        if pg and rs != ins:
            sc = score / len(rs) + (IDLE_PEN if idle else 0.0)
            if any(shape(r) != shape(y) for r, (_, y) in zip(rs, node.pairs)):
                # not yet at the output shape: D8 variants are equivalent (window metric)
                k = min(key_of([gdsl.D8[d](r) for r in rs]) for d in gdsl.D8)
            else:
                k = key_of(rs)
            if k in kids and kids[k][:2] <= (sc, cost): continue
            kids[k] = (sc, cost, name, fn, rs, oi)

def OWN_SRC(prs):
    return list(own_ops(prs))

def expand(node, order, secs, want_kids, lazy, cap, timing=None, oi_only=False):
    """Enumerate the library on the node's pairs family by family (own steps first) and assess each batch.
    lazy: stop enumerating families once a solution was found ("lib": once a library family fits)."""
    train = [{"input": z, "output": y} for z, y in node.pairs]
    sols, kids = [], {}
    t_end = time.time() + secs
    with within(secs):
        try:
            own = list(own_ops(node.pairs))
        except Exception:
            own = []
        seen = {n for n, _, _ in own}
        assess(node, sorted(own, key=lambda x: x[1]), t_end, want_kids, sols, kids, OWN_SRC, True)
        for fam in order:
            if time.time() > t_end or (lazy and any(sl[4] is not OWN_SRC for sl in sols) if lazy == "lib" else (lazy and sols)): break
            t1 = time.time(); batch = []
            with within(cap):
                try:
                    for x in fam(train):
                        batch.append(x)
                except Exception:
                    pass
            if timing is not None: timing[fam] = time.time() - t1
            batch = batch + list(gdsl.compose_dihedral(batch))
            batch = [x for x in batch if x[0] not in seen]
            seen.update(n for n, _, _ in batch)
            batch.sort(key=lambda x: x[1])
            n0 = len(sols)
            assess(node, batch, t_end, want_kids and (fam.__module__ == "gdsl" or not oi_only), sols, kids,
                   lambda prs, fam=fam: _regen(fam, prs), fam.__module__ == "gdsl")
            if DEBUG:
                FAMSTAT.append((fam.__module__ + "." + fam.__name__, node.depth, round(time.time() - t1, 3), len(sols) - n0))
    sols.sort(key=lambda s: s[1])
    return sols, sorted(kids.values(), key=lambda x: (x[0], x[1]))

def _regen(fam, prs):
    b = list(fam([{"input": z, "output": y} for z, y in prs]))
    return b + list(gdsl.compose_dihedral(b))

def loo_ok(node, name, src, secs):
    """Leave-one-out check of a last step: re-induce its family on all pairs but one and require the
    same-named program to reproduce the held-out pair (a guard against memorising last steps)."""
    cm = name.endswith("+colour-map")
    base = name[:-len("+colour-map")] if cm else name
    n = len(node.pairs)
    if n < 2 or src is None: return True
    ok = False
    with within(secs):
        for j in range(n):
            rest = [p for i, p in enumerate(node.pairs) if i != j]
            try:
                progs = src(rest)
            except Exception:
                return False
            fn = next((f for nm, _, f in progs if nm == base), None)
            if fn is None: return False
            z, y = node.pairs[j]
            r = gdsl.run(fn, z)
            if r is None: return False
            if cm:      # the global colour map is a post-step: fitted on all pairs, only the base step is held out
                rs = [gdsl.run(fn, zz) for zz, _ in node.pairs]
                if any(x is None for x in rs): return False
                m = gdsl.fit_cmap(rs, [yy for _, yy in node.pairs])
                if not m: return False
                r = gdsl.apply_cmap(r, m)
            if r != y: return False
        ok = True
    return ok

def _stem(name):
    return re.split(r"[\[<>=]", name, maxsplit=1)[0]

def select_kids(kids, n, per_stem=2):
    """Best-ranked children, at most `per_stem` per program stem (diversity)."""
    out = []; per = Counter()
    for k in kids:
        s = _stem(k[2])
        if per[s] >= per_stem: continue
        per[s] += 1; out.append(k)
        if len(out) >= n: break
    return out

# ------------------------------------------------------------------ search
def _program(node, last):
    steps = [n for n, _ in node.steps] + ([last] if last else []) + [n for n, _ in node.post]
    if node.wrap:
        steps = ([node.wrap.pre_name] if node.wrap.pre_name else []) + steps + ([node.wrap.post_name] if node.wrap.post_name else [])
    return " ; ".join(steps)

def _verify(task, node, last_fn):
    """End-to-end re-check on the original training pairs; returns test predictions or None."""
    fns = [f for _, f in node.steps] + [last_fn] + [f for _, f in node.post]
    def app(g):
        ctx = None
        if node.wrap:
            g, ctx = node.wrap.pre(g)
            if g is None: return None
        for f in fns:
            g = gdsl.run(f, g)
            if g is None: return None
        if node.wrap:
            g = node.wrap.post(g, ctx)
        return g
    for p in task["train"]:
        if app(p["input"]) != p["output"]: return None
    preds = [app(t["input"]) for t in task["test"]]
    return preds if all(p is not None for p in preds) else None

RESULTS = []

class Canon:
    """Colour canonicalisation (both sides): the colours of a grid, ranked by (count desc, first appearance),
    are renamed 0,1,2,... skipping the task's literal output colours (colours an output shows although its
    input lacks them); outputs are renamed with their input's map, predictions are mapped back with the
    inverse map of the ORIGINAL test input.  Makes roles, not literal colours, visible to the library."""
    post_name, single = "colour-decanon", True
    def __init__(self, lit, rank="freq"):
        self.lit = set(lit); self.free = [c for c in range(10) if c not in self.lit]; self.rank = rank
        self.pre_name = "colour-canon" if rank == "freq" else f"colour-canon[{rank}]"
    def map_of(self, g):
        cnt = Counter(v for r in g for v in r); first = {}
        for y, r in enumerate(g):
            for x, v in enumerate(r): first.setdefault(v, (y, x))
        if self.rank == "freq":
            order = sorted(cnt, key=lambda c: (-cnt[c], first[c]))
        else:       # "bgfirst": the most frequent colour first, the others in order of first appearance
            bg = max(cnt, key=lambda c: (cnt[c], -first[c][0], -first[c][1]))
            order = [bg] + sorted((c for c in cnt if c != bg), key=lambda c: first[c])
        if len(order) > len(self.free) or any(c in self.lit for c in order): return None
        return {c: self.free[i] for i, c in enumerate(order)}
    def apply(self, g, m):
        return [[m.get(v, v) for v in r] for r in g]
    def pre(self, g):
        m = self.map_of(g)
        return (None, None) if m is None else (self.apply(g, m), m)
    def post(self, g, m):
        if g is None: return None
        inv = {b: a for a, b in m.items()}
        out = []
        for r in g:
            row = []
            for v in r:
                if v in inv: row.append(inv[v])
                elif v in self.lit: row.append(v)
                else: return None
            out.append(row)
        return out

def canon_setup(task, rank="freq"):
    tr = task["train"]
    lit = set()
    for p in tr:
        lit |= gdsl.colours(p["output"]) - gdsl.colours(p["input"])
    ins = set()
    for p in tr + task["test"]:
        ins |= gdsl.colours(p["input"])
    if lit & ins: return None
    cz = Canon(lit, rank)
    ms = [cz.map_of(p["input"]) for p in tr]; mt = [cz.map_of(t["input"]) for t in task["test"]]
    if any(m is None for m in ms + mt): return None
    if all(m == ms[0] for m in ms + mt): return None     # one fixed renaming everywhere: nothing to gain
    return cz

class Beside:
    """The output shows the ORIGINAL input as one block and a new block B beside / above / below it:
    target := B, post-step := put the input back next to the prediction."""
    pre_name, single = "", False
    def __init__(self, mode):
        self.mode = mode; self.post_name = f"beside-input:{mode}"
    def pre(self, g):
        return g, g
    def post(self, p, x):
        if p is None: return None
        if self.mode in ("right", "left"):
            if H(p) != H(x): return None
            return [list(a) + list(b) for a, b in zip(x, p)] if self.mode == "right" else [list(b) + list(a) for a, b in zip(x, p)]
        if W(p) != W(x): return None
        return [list(r) for r in x] + [list(r) for r in p] if self.mode == "below" else [list(r) for r in p] + [list(r) for r in x]

def beside_normalisations(pairs):
    for mode in ("right", "left", "below", "above"):
        nys = []
        for x, y in pairs:
            hx, wx = shape(x); hy, wy = shape(y)
            if mode in ("right", "left"):
                if hy != hx or wy <= wx: break
                blk, B = ([r[:wx] for r in y], [r[wx:] for r in y]) if mode == "right" else ([r[wy - wx:] for r in y], [r[:wy - wx] for r in y])
            else:
                if wy != wx or hy <= hx: break
                blk, B = (y[:hx], y[hx:]) if mode == "below" else (y[hy - hx:], y[:hy - hx])
            if blk != x: break
            nys.append(B)
        else:
            yield Beside(mode), nys

class Orient:
    """Orientation canonicalisation (both sides): each grid is rotated so that a feature points DOWN --
    'wall': the one border line filled by a single non-background colour; 'mass': the side holding most of
    the foreground (strict majority).  Outputs are rotated with their input's rotation; a prediction is
    rotated back with the inverse rotation of the ORIGINAL test input."""
    single = True
    ROT = ("id", "r90", "r180", "r270")
    def __init__(self, feature):
        self.feature = feature; self.pre_name = f"orient-canon[{feature}]"; self.post_name = "orient-back"
    def side(self, g):
        bg = _bg(g); h, w = H(g), W(g)
        if self.feature == "wall":
            lines = {"down": g[-1], "up": g[0], "left": [r[0] for r in g], "right": [r[-1] for r in g]}
            hits = [d for d, ln in lines.items() if len(set(ln)) == 1 and ln[0] != bg]
            return hits[0] if len(hits) == 1 else None
        cells = [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg]
        if not cells: return None
        n = len(cells)
        cnt = {"down": sum(1 for y, _ in cells if 2 * y > h - 1), "up": sum(1 for y, _ in cells if 2 * y < h - 1),
               "right": sum(1 for _, x in cells if 2 * x > w - 1), "left": sum(1 for _, x in cells if 2 * x < w - 1)}
        best = max(cnt.values())
        hits = [d for d, v in cnt.items() if v == best]
        return hits[0] if len(hits) == 1 and 3 * best > 2 * n else None
    def rot_of(self, g):
        # rotation k such that D8[k](g) has the feature at the bottom
        return {"down": "id", "left": "r270", "up": "r180", "right": "r90"}.get(self.side(g))
    def pre(self, g):
        k = self.rot_of(g)
        return (None, None) if k is None else (gdsl.D8[k](g), k)
    def post(self, p, k):
        if p is None: return None
        return gdsl.D8[INV.get(k, "id")](p)

def orient_setups(task):
    tr = task["train"]
    for feat in ORIENT_FEATURES:
        o = Orient(feat)
        ks = [o.rot_of(p["input"]) for p in tr] + [o.rot_of(t["input"]) for t in task["test"]]
        if any(k is None for k in ks) or len(set(ks[:len(tr)])) < 2: continue
        if any(gdsl.D8[k](p["input"]) is None for k, p in zip(ks, tr)): continue
        yield o, ks

def _frame_box(g):
    """Interior box of the largest rectangle whose whole border is one non-background colour."""
    bg = _bg(g); best = None
    for ob in gdsl.objects(g, bg, False, True):
        r0, c0, r1, c1 = gdsl.bbox(ob)
        if r1 - r0 < 2 or c1 - c0 < 2: continue
        col = g[ob[0][0]][ob[0][1]]
        if all(g[r0][x] == col and g[r1][x] == col for x in range(c0, c1 + 1)) and \
           all(g[y][c0] == col and g[y][c1] == col for y in range(r0, r1 + 1)):
            area = (r1 - r0) * (c1 - c0)
            if best is None or area > best[0]: best = (area, (r0 + 1, c0 + 1, r1 - 1, c1 - 1))
    return best[1] if best else None

def _fg_box(g):
    bg = _bg(g); cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg]
    return gdsl.bbox(cells) if cells else None

class Region:
    """In-place region (both sides): the change happens inside a region of the input (frame interior or
    foreground bounding box) and everything outside stays; solve on the cropped region, paste it back."""
    single = True
    BOX = {"frame": _frame_box, "fg": _fg_box}
    def __init__(self, kind):
        self.kind = kind; self.pre_name = f"region[{kind}]"; self.post_name = "paste-back"
    def box(self, g):
        return self.BOX[self.kind](g)
    def pre(self, g):
        b = self.box(g)
        if b is None or (b[2] - b[0] + 1, b[3] - b[1] + 1) == shape(g): return None, None
        return gdsl.crop(g, b), (g, b)
    def post(self, p, ctx):
        if p is None: return None
        g, (r0, c0, r1, c1) = ctx
        if shape(p) != (r1 - r0 + 1, c1 - c0 + 1): return None
        out = [list(r) for r in g]
        for y in range(r0, r1 + 1):
            out[y][c0:c1 + 1] = p[y - r0]
        return out

def region_setups(task):
    tr = task["train"]
    if any(shape(p["input"]) != shape(p["output"]) for p in tr): return
    for kind in REGION_KINDS:
        rg = Region(kind); ok = True; ny = []
        for p in tr:
            x, y = p["input"], p["output"]
            z, ctx = rg.pre(x)
            if z is None: ok = False; break
            r0, c0, r1, c1 = ctx[1]
            inside = gdsl.crop(y, ctx[1])
            if rg.post(inside, ctx) != y or inside == z: ok = False; break
            ny.append(inside)
        if ok and all(rg.pre(t["input"])[0] is not None for t in task["test"]):
            yield rg, ny

def _norm_colours(g):
    m = {}
    return tuple(tuple(m.setdefault(v, len(m)) for v in r) for r in g)

def low_evidence(train):
    """All training outputs are the same picture up to a relabelling of colours (e.g. 1x1 answers, fixed
    rings): only the colour choices carry evidence, too little to trust a composed program."""
    return len({_norm_colours(p["output"]) for p in train}) == 1

def _search(task, t0):
    train, test = task["train"], task["test"]
    root = Node([(p["input"], p["output"]) for p in train], [t["input"] for t in test], [], [], 0, 0.0, 0)
    found = []          # (depth, node_rank, cost, program, preds)
    seen_pred = set()
    base = []
    # root expansion = single-step library search + first-step children
    timing = {}
    with within(max(4.0, BUDGET * 0.55)):
        sols, kids = expand(root, ROOT_ORDER, max(4.0, BUDGET * 0.5), True, not INCLUDE_BASE, FAMILY_CAP, timing)
    frank = {f: i for i, f in enumerate(ROOT_ORDER)}
    order = sorted(ROOT_ORDER, key=lambda f: (timing.get(f, 99.0), frank[f]))    # cheap families first deeper down
    if sols:
        # a single step fits (library family or own-pool step): not a composition task
        for name, cost, fn, tp, src in sols:
            k = str(tp)
            if k in seen_pred: continue
            seen_pred.add(k); base.append({"program": name, "preds": tp})
        if DEBUG: TRACE.append(("base", [b["program"] for b in base]))
        return base[:3] if INCLUDE_BASE else []
    lowev = low_evidence(train)
    queue = []; tick = 0
    def push(node, prio):
        nonlocal tick
        tick += 1; heapq.heappush(queue, (prio, tick, node))
    tests = root.tests
    cz = canon_setup(task)
    if cz:
        ms = [cz.map_of(x) for x, _ in root.pairs]; mt = [cz.map_of(t) for t in tests]
        if all(m is not None for m in ms + mt):
            cnode = Node([(cz.apply(x, m), cz.apply(y, m)) for (x, y), m in zip(root.pairs, ms)],
                         [cz.apply(t, m) for t, m in zip(tests, mt)], [], [], 0, -1.0, 1, True, cz)
            if any(z != y for z, y in cnode.pairs):
                push(cnode, -1.0)
    for rg, ny in (region_setups(task) if not lowev else []):
        zs = [rg.pre(x)[0] for x, _ in root.pairs]
        push(Node(list(zip(zs, ny)), [rg.pre(t)[0] for t in tests], [], [], 0, -0.3, 1, True, rg), -0.3)
    for o, ks in orient_setups(task):
        onode = Node([(gdsl.D8[k](x), gdsl.D8[k](y)) for (x, y), k in zip(root.pairs, ks)],
                     [gdsl.D8[k](t) for t, k in zip(tests, ks[len(root.pairs):])], [], [], 0, -0.5, 1, True, o)
        push(onode, -0.5)
    for wr, ny in (beside_normalisations(root.pairs) if not lowev else []):
        push(Node([(x, b) for (x, _), b in zip(root.pairs, ny)], tests, [], [], 1, 0.05, 1, True, wr), 0.05)
    if lowev:
        if DEBUG: TRACE.append(("low-evidence",))
        kids = []
    for score, cost, name, fn, rs, oi in (select_kids(kids, KIDS) if not lowev else []):
        tr_ = [gdsl.run(fn, t) for t in tests]
        if any(t is None for t in tr_): continue
        nd = Node([(r, y) for r, (_, y) in zip(rs, root.pairs)], tr_, [(name, fn)], [], 1, score, cost, oi)
        push(nd, score)
    for name, ny, post, rank in (reverse_normalisations(root.pairs) if not lowev else []):
        nd = Node([(x, y2) for (x, _), y2 in zip(root.pairs, ny)], tests, [], [(name, post)], 1, rank, 1)
        push(nd, rank)
    for iname, ifn, pname, pfn, ny, rank in (both_side_normalisations(root.pairs) if not lowev else []):
        zs = [gdsl.run(ifn, x) for x, _ in root.pairs]; tz = [gdsl.run(ifn, t) for t in tests]
        if any(g is None for g in zs + tz): continue
        nd = Node(list(zip(zs, ny)), tz, [(iname, ifn)], [(pname, pfn)], 1, rank, 1)
        push(nd, rank)
    if DEBUG:
        TRACE.append(("root", len(timing), round(time.time() - t0, 2), [(round(q[0], 3), "/".join(n for n, _ in q[2].steps + q[2].post)) for q in sorted(queue)]))
    expanded = 0
    while queue and _left() > 0.5:
        prio, _, node = heapq.heappop(queue)
        expanded += 1
        sols, kids = [], []
        with within(_left() - 0.3):
            # a second forward step is only taken after an output-independent first step, and must be one too
            second = len(node.steps) > 0
            sols, kids = expand(node, order, min(_left() - 0.3, 8.0 if node.depth == 0 else NODE_BUDGET),
                                node.depth < MAX_FWD and node.oi and not lowev,
                                True, FAMILY_CAP if node.depth == 0 else CHILD_CAP, oi_only=second)
        if DEBUG:
            TRACE.append(("expand", "/".join(n for n, _ in node.steps + node.post), round(prio, 3), len(sols), len(kids), round(time.time() - t0, 2)))
        for name, cost, fn, tp, src in sols:
            preds = _verify(task, node, fn)
            if preds is None: continue
            k = str(preds)
            if k in seen_pred: continue
            if LOO and (node.steps or node.post or not (node.wrap and node.wrap.single)):   # canon + one step = single step
                lo = loo_ok(node, name, src, max(0.5, min(4.0, _left() - 0.3)))
                if DEBUG: TRACE.append(("loo", name, lo))
                if not lo: continue
            seen_pred.add(k)
            found.append((node.depth, prio, node.cost + cost, _program(node, name), preds))
            RESULTS.append({"program": _program(node, name), "preds": preds})
        if found:
            break
        for score, cost, name, fn, rs, oi in select_kids(kids, KIDS):
            tr_ = [gdsl.run(fn, t) for t in node.tests]
            if any(t is None for t in tr_) or (second and not oi): continue
            nd = Node([(r, y) for r, (_, y) in zip(rs, node.pairs)], tr_, node.steps + [(name, fn)], node.post,
                      node.depth + 1, score, node.cost + cost, node.oi and oi, node.wrap)
            push(nd, score + 0.35 * node.depth)
    found.sort(key=lambda f: (f[0], f[1], f[2]))
    return [{"program": f[3], "preds": f[4]} for f in found[:3]]

def SEARCH(task):
    t0 = time.time()
    TRACE.clear(); RESULTS.clear(); FAMSTAT.clear()
    del _DL[1:]
    _DL.append(t0 + BUDGET)
    old = signal.signal(signal.SIGPROF, _tick)
    _ARMED[0] = True
    signal.setitimer(signal.ITIMER_PROF, 0.05, 0.05)
    res = None
    try:
        try:
            res = _search(task, t0)
        except Budget:
            res = None
    except Budget:              # an interrupt inside the handler above
        res = None
    finally:
        while True:             # an interrupt can land here too: disarm first, retry until clean
            try:
                _ARMED[0] = False
                signal.setitimer(signal.ITIMER_PROF, 0, 0)
                signal.signal(signal.SIGPROF, old)
                del _DL[1:]
                break
            except Budget:
                continue
    return res if res is not None else list(RESULTS[:3])
