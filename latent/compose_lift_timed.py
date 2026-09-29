"""compose_lift: lift the whole G-DSL library from grids to PARTS of grids.

A program here is   partition -> (pair | select | group) -> library program on parts -> reassemble,
every step induced from the training pairs; the whole program is verified on all training pairs.

Search space
  partitions   sep      panels between full-length lines of one non-background colour (any thickness)
               bgsep    rectangles between all-background rows / columns (bands in one or both axes)
               frame    interiors of closed single-colour rectangular frames
               lines    every row (or every column)
               blocks   equal tiles, nh x nw split (SELECT only)
               obj      connected objects: 4/8-connected, single-/multi-colour, pad 0/1, masked object or
                        whole bbox crop
               layers   one full-size part per colour
  modes        INPLACE  same-size task: parts keep their regions.  Regions (panels, bands, frames, lines):
                        disjoint, output part = output crop, the rest unchanged.  Masked objects: layered -
                        all objects erased, each transformed part's foreground painted back (boxes may overlap;
                        every changed cell must lie in a box).  Bbox crops: pasted, overlaps must agree.
                        The (in,out) part pairs of ALL training pairs are pooled and the library searched once.
               GROUP    INPLACE / OBJMAP / LAYERS when no single program fits: parts grouped by one attribute
                        (colour, size, shape, extremal size, border contact, holes, orientation, adjacent colours,
                        minority-colour count, contains colour c, line parity ...); one program per group
                        (>= 2 examples from >= 2 training pairs); never-changing groups get the identity; the
                        changing groups must share ONE mechanism (family) whose parameter varies by group.
               SELIN    same-size task where only ONE selected part changes (selectors as in SELECT).
               OBJMAP   same-size task whose objects change extent: each object becomes a part of dims
                        rule(h,w) (transpose, grow/shrink by one ring or along one axis, x2, x3) anchored at its
                        centre or a corner, painted on the background canvas (disjoint parts).
               LAYERS   same-size task: every colour layer transformed (one program, or one per colour).
               SELECT   output = library(one selected part): extreme attribute (size, area, colours, density,
                        position), odd-one-out (unique colour set / shape / content / size / symmetry / holes),
                        contains / lacks / most of a marker colour, or fixed index when the part count is fixed.
                        Hypotheses selecting the same training parts share one library search.
               PANELMAP input panel lattice (separators or background gaps) and output with the same R x C
                        layout (own separators / margins, or bare R x C or C x R blocks): library on the pooled
                        panel pairs, output re-assembled as induced.
  library      gdsl.candidates() on the pooled part pairs (every family induces its parameters from the part
               pairs; at most INDUCE pairs, changed first, used for induction) + identity / erase + optional
               global colour map, verified exactly on every part pair.  Parts of the scene see the scene
               background (bg_of is wrapped while a part-level program runs).  Fallback: the same search on
               colour-ROLE-normalised parts (colours renamed by frequency rank, mapped back at test).
Generalisation check (against over-firing): a program is kept only if the same program, re-induced on the parts
of all training pairs but one, predicts the held-out pair's parts exactly: last changed pair, plus the first
one for programs of cost >= 3 (occam) and always for SELECT / SELIN / GROUP.  Test predictions proposed by
several hypotheses are ranked first (votes); at most 3 programs with distinct predictions are returned.
Budget: <= 19 s wall per task, shared by the modes (same-size: INPLACE 11 s of which plain pooled search 7 s,
then LAYERS 5 s, OBJMAP 3 s, SELIN 3 s, each only while nothing is found; other tasks: PANELMAP 4 s, SELECT
the rest); every library call has a wall cap polled by a periodic ITIMER_PROF (SIGALRM is left to the harness);
hypotheses in prior order, identical part sets deduplicated, context-free fits required (_functional).
"""
import sys, time, signal, re
sys.path.insert(0, '/home/claude/work/widen')
import gdsl
from gdsl import H, W, colours, bbox
from collections import Counter, defaultdict

TOTAL_BUDGET = 19.0
INDUCE = 10
DIAG = Counter()                 # per-task diagnostics: library searches, fits, generalisation checks
DEBUG = False
MAX_PARTS = 40
_ORIG_BG = gdsl.bg_of


# ------------------------------------------------------------------ budget / timers
class _Timeout(BaseException):
    pass


class Budget:
    def __init__(self, total, parent=None):
        self.t0 = time.time(); self.end = self.t0 + total
        if parent is not None: self.end = min(self.end, parent.end)
    def left(self):
        return self.end - time.time()
    def sub(self, sec):
        """A share of the remaining time for one mode (unused time flows to the next mode)."""
        return Budget(sec, self)


_DEADLINES = []          # stack of [wall deadline, fired]; outermost first


def _on_prof(signum, frame):
    now = time.time()
    for e in _DEADLINES:
        if not e[1] and now > e[0]:
            e[1] = True
            raise _Timeout()


class wall_cap:
    """Raise _Timeout (once) when `sec` wall seconds have passed.  Polled every 20 ms of process CPU time by
    a periodic ITIMER_PROF (SIGPROF) installed by SEARCH: never touches SIGALRM, which belongs to the harness."""
    def __init__(self, sec):
        self.sec = max(0.05, sec)
    def __enter__(self):
        _DEADLINES.append([time.time() + self.sec, False])
    def __exit__(self, *a):
        _DEADLINES.pop()
        return False


class prof_timer:
    def __enter__(self):
        self.old = signal.signal(signal.SIGPROF, _on_prof)
        signal.setitimer(signal.ITIMER_PROF, 0.02, 0.02)
    def __exit__(self, *a):
        del _DEADLINES[:]                       # nothing left for a late SIGPROF to fire
        signal.setitimer(signal.ITIMER_PROF, 0)
        signal.signal(signal.SIGPROF, self.old)
        return False


# ------------------------------------------------------------------ scene background forced on part-level runs
_FORCED = [None]


def _bg_patched(g):
    f = _FORCED[0]
    return f if f is not None else _ORIG_BG(g)


def _install_patch():
    """Every module holding gdsl.bg_of gets a wrapper that is transparent unless a part-level run forces the
    scene background (an object crop's own majority colour is not the scene's background)."""
    done = []
    for mod in list(sys.modules.values()):
        try:
            if mod is not None and getattr(mod, 'bg_of', None) is _ORIG_BG:
                setattr(mod, 'bg_of', _bg_patched); done.append(mod)
        except Exception:
            pass
    return done


def _remove_patch(done):
    for mod in done:
        try:
            setattr(mod, 'bg_of', _ORIG_BG)
        except Exception:
            pass


class forced_bg:
    def __init__(self, c):
        self.c = c
    def __enter__(self):
        self.old = _FORCED[0]; _FORCED[0] = self.c
    def __exit__(self, *a):
        _FORCED[0] = self.old
        return False


# ------------------------------------------------------------------ grid helpers
def region_crop(g, r0, c0, h, w, bg):
    hh, ww = H(g), W(g); out = []
    for y in range(r0, r0 + h):
        if 0 <= y < hh:
            row = g[y]
            out.append([row[x] if 0 <= x < ww else bg for x in range(c0, c0 + w)])
        else:
            out.append([bg] * w)
    return out


def paste(canvas, sub, r0, c0, only_fg=None):
    hh, ww = H(canvas), W(canvas)
    for dy, row in enumerate(sub):
        y = r0 + dy
        if not 0 <= y < hh: continue
        for dx, v in enumerate(row):
            x = c0 + dx
            if 0 <= x < ww and (only_fg is None or v != only_fg):
                canvas[y][x] = v


def copyg(g):
    return [r[:] for r in g]


def dims(g):
    return (H(g), W(g))


def _ident(g):
    return [r[:] for r in g]


def _erase(g):
    bg = _bg_patched(g)
    return [[bg] * W(g) for _ in range(H(g))]


# ------------------------------------------------------------------ parts
class Part:
    __slots__ = ('r0', 'c0', 'h', 'w', 'g', 'cells', 'a')
    def __init__(self, r0, c0, h, w, g, cells=None):
        self.r0, self.c0, self.h, self.w, self.g, self.cells = r0, c0, h, w, g, cells
        self.a = {}


def _intervals(seps, n):
    s = set(seps); out = []; y = 0
    while y < n:
        if y in s:
            y += 1; continue
        y1 = y
        while y1 + 1 < n and y1 + 1 not in s: y1 += 1
        out.append((y, y1)); y = y1 + 1
    return out


def sep_layout(g):
    """(separator colour, row intervals, col intervals) for full-length lines of one non-background colour."""
    h, w = H(g), W(g); bg = _ORIG_BG(g); best = None
    for sc in colours(g):
        if sc == bg: continue
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols: continue
        if len(rows) == h or len(cols) == w: continue
        ri, ci = _intervals(rows, h), _intervals(cols, w)
        n = len(ri) * len(ci)
        if n < 2: continue
        if best is None or n > best[0]: best = (n, sc, ri, ci)
    return best[1:] if best else None


def part_sep(g):
    lay = sep_layout(g)
    if lay is None: return None
    _, ri, ci = lay
    return [Part(a, b, a1 - a + 1, b1 - b + 1, [row[b:b1 + 1] for row in g[a:a1 + 1]]) for a, a1 in ri for b, b1 in ci]


def part_bgsep(g, axes):
    h, w = H(g), W(g); bg = _ORIG_BG(g)
    rows = [r for r in range(h) if all(v == bg for v in g[r])] if 'r' in axes else []
    cols = [c for c in range(w) if all(g[r][c] == bg for r in range(h))] if 'c' in axes else []
    ri, ci = _intervals(rows, h), _intervals(cols, w)
    out = []
    for a, a1 in ri:
        for b, b1 in ci:
            sub = [row[b:b1 + 1] for row in g[a:a1 + 1]]
            if any(v != bg for r in sub for v in r):
                out.append(Part(a, b, a1 - a + 1, b1 - b + 1, sub))
    return out if len(out) >= 2 else None


def part_blocks(g, nh, nw):
    h, w = H(g), W(g)
    if h % nh or w % nw: return None
    bh, bw = h // nh, w // nw
    return [Part(a, b, bh, bw, [row[b:b + bw] for row in g[a:a + bh]]) for a in range(0, h, bh) for b in range(0, w, bw)]


def part_lines(g, axis):
    if axis == 'r':
        return [Part(y, 0, 1, W(g), [g[y][:]]) for y in range(H(g))]
    return [Part(0, x, H(g), 1, [[g[y][x]] for y in range(H(g))]) for x in range(W(g))]


def part_frame(g):
    """Interiors of closed single-colour rectangular frames (4-connected objects owning their whole bbox border)."""
    bg = _ORIG_BG(g); out = []
    for ob in gdsl.objects(g, bg, False, True):
        r0, c0, r1, c1 = bbox(ob)
        if r1 - r0 < 2 or c1 - c0 < 2: continue
        col = g[ob[0][0]][ob[0][1]]
        if any(g[y][x] != col for y in (r0, r1) for x in range(c0, c1 + 1)): continue
        if any(g[y][x] != col for x in (c0, c1) for y in range(r0, r1 + 1)): continue
        p = Part(r0 + 1, c0 + 1, r1 - r0 - 1, c1 - c0 - 1, [row[c0 + 1:c1] for row in g[r0 + 1:r1]])
        p.a['fcol'] = col
        out.append(p)
    return out or None


def part_obj(g, diag, byc, pad, masked):
    bg = _ORIG_BG(g)
    obs = gdsl.objects(g, bg, diag, byc)
    if not obs or len(obs) > MAX_PARTS: return None
    out = []
    for ob in obs:
        r0, c0, r1, c1 = bbox(ob)
        r0 -= pad; c0 -= pad; r1 += pad; c1 += pad
        hh, ww = r1 - r0 + 1, c1 - c0 + 1
        if masked:
            sub = [[bg] * ww for _ in range(hh)]
            for y, x in ob: sub[y - r0][x - c0] = g[y][x]
        else:
            sub = region_crop(g, r0, c0, hh, ww, bg)
        out.append(Part(r0, c0, hh, ww, sub, ob))
    return out


def part_layers(g):
    """One full-size part per foreground colour (that colour's cells on the background)."""
    bg = _ORIG_BG(g)
    cols = sorted(colours(g) - {bg})
    return [Part(0, 0, H(g), W(g), [[v if v == c else bg for v in row] for row in g]) for c in cols] or None


def partition(spec, g):
    try:
        k = spec[0]
        if k == 'lines': ps = part_lines(g, spec[1])
        elif k == 'layers': ps = part_layers(g)
        elif k == 'sep': ps = part_sep(g)
        elif k == 'bgsep': ps = part_bgsep(g, spec[1])
        elif k == 'frame': ps = part_frame(g)
        elif k == 'blocks': ps = part_blocks(g, spec[1], spec[2])
        elif k == 'obj': ps = part_obj(g, spec[1], spec[2], spec[3], spec[4])
        else: ps = None
    except _Timeout:
        raise
    except Exception:
        return None
    if not ps or len(ps) > (30 if k == 'lines' else MAX_PARTS): return None
    _attrs(ps, g)
    return ps


def spec_name(spec):
    k = spec[0]
    if k == 'obj':
        return f"obj[{'8' if spec[1] else '4'}{'' if spec[2] else ',multi'}{',pad' + str(spec[3]) if spec[3] else ''}{'' if spec[4] else ',bbox'}]"
    if k == 'blocks':
        return f"blocks[{spec[1]}x{spec[2]}-split]"
    if k == 'bgsep':
        return f"bgsep[{spec[1]}]"
    if k == 'lines':
        return 'rows' if spec[1] == 'r' else 'cols'
    return k


# ------------------------------------------------------------------ part attributes
def _shape_key(cells):
    r0, c0, _, _ = bbox(cells)
    return tuple(sorted((y - r0, x - c0) for y, x in cells))


def _has_hole(cells):
    """True when the cell set encloses background (4-connected region not reaching its padded bbox border)."""
    r0, c0, r1, c1 = bbox(cells)
    h, w = r1 - r0 + 3, c1 - c0 + 3
    occ = [[False] * w for _ in range(h)]
    for y, x in cells: occ[y - r0 + 1][x - c0 + 1] = True
    seen = [[False] * w for _ in range(h)]
    st = [(0, 0)]; seen[0][0] = True; n = 1
    while st:
        y, x = st.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and not occ[yy][xx]:
                seen[yy][xx] = True; st.append((yy, xx)); n += 1
    return n + len(cells) < h * w


def _attrs(ps, g):
    bg = _ORIG_BG(g); hh, ww = H(g), W(g)
    for p in ps:
        a = p.a
        if p.cells is not None:
            cells = p.cells
            cols = Counter(g[y][x] for y, x in cells)
            r0, c0, r1, c1 = bbox(cells)
        else:
            cols = Counter(v for r in p.g for v in r if v != bg)
            cells = [(y, x) for y, r in enumerate(p.g) for x, v in enumerate(r) if v != bg]
            r0, c0, r1, c1 = p.r0, p.c0, p.r0 + p.h - 1, p.c0 + p.w - 1
        a['size'] = sum(cols.values())
        a['shape'] = _shape_key(cells) if cells else ()
        a['bh'], a['bw'] = r1 - r0 + 1, c1 - c0 + 1
        a['border'] = r0 <= 0 or c0 <= 0 or r1 >= hh - 1 or c1 >= ww - 1
        a['top'], a['left'], a['bottom'], a['right'] = r0, c0, r1, c1
        a['colours'] = frozenset(cols)
        a['colour'] = next(iter(cols)) if len(cols) == 1 else ('multi', len(cols))
        a['ncol'] = len(cols)
        a['major'] = cols.most_common(1)[0][0] if cols else bg
        a['area'] = a['bh'] * a['bw']
        a['density'] = a['size'] / (p.h * p.w)
        a['content'] = str(p.g)
        a['sym'] = p.g == [r[::-1] for r in p.g] or p.g == p.g[::-1]
        a['solid'] = a['size'] == a['area']
        a['mcount'] = min(cols.most_common()[-1][1], 3) if len(cols) >= 2 else 0
        a['orient'] = 'h' if a['bw'] > a['bh'] else ('v' if a['bh'] > a['bw'] else 's')
        a['hole'] = _has_hole(cells) if cells and a['size'] < a['area'] and a['area'] <= 900 else False
        if p.cells is not None:                     # colours touching the object from outside (context)
            own = set(p.cells); adj = set()
            for y, x in p.cells:
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < hh and 0 <= xx < ww and (yy, xx) not in own and g[yy][xx] != bg:
                        adj.add(g[yy][xx])
            a['adj'] = frozenset(adj)
    if all(p.h == 1 and p.w == ww for p in ps) or all(p.w == 1 and p.h == hh for p in ps):
        for p in ps:
            p.a['par'] = (p.r0 + p.c0) % 2          # parity of a line's index (rows / cols only)
    sizes = [p.a['size'] for p in ps]
    mx, mn = max(sizes), min(sizes)
    ranks = sorted(set(sizes), reverse=True)
    shc = Counter(p.a['shape'] for p in ps)
    for p in ps:
        p.a['extreme'] = 'max' if p.a['size'] == mx else ('min' if p.a['size'] == mn else 'mid')
        p.a['srank'] = ranks.index(p.a['size'])
        p.a['shape_n'] = min(shc[p.a['shape']], 3)


# ------------------------------------------------------------------ library search on part pairs
def _applier(fn, m, fbg):
    def ap(g):
        with forced_bg(fbg):
            r = gdsl.run(fn, g)
            if r is not None and m is not None: r = gdsl.apply_cmap(r, m)
            return r
    return ap


def _base(name):
    return name[:-5] if name.endswith('+cmap') else name


def lib_search(pairs, tests, budget, cap=3.0, maxp=2, fbg=None, stats=None, want=None, names=None):
    """Library programs verified on pooled (in, out) part pairs: [(name, cost, test_preds, apply)].
    names: only these programs (re-induced on these pairs).  want: return every program whose test
    predictions equal it (generalisation check)."""
    seen = set(); P = []
    for i, o in pairs:
        k = (str(i), str(o))
        if k not in seen:
            seen.add(k); P.append((i, o))
    changed = [io for io in P if io[0] != io[1]]
    if not changed: return []
    changed.sort(key=lambda io: -(H(io[1]) * W(io[1])))
    P = changed + [io for io in P if io[0] == io[1]]
    t_start = time.time()
    cap = min(cap, budget.left() - 0.3)
    if cap <= 0.1: return []
    # families induce their parameters from at most INDUCE pairs (changed ones first); every candidate is then
    # verified on all pairs, so the cap only trades recall for speed on large pools
    train = [{'input': i, 'output': o} for i, o in P[:INDUCE]]
    outs = [o for _, o in P]
    found = []
    with forced_bg(fbg):
        try:
            with wall_cap(cap):
                cands = [('identity', 0, _ident), ('erase', 0, _erase)] + gdsl.candidates(train)
                i0, o0 = P[0]
                for name, cost, fn in cands:
                    if names is not None and name not in names: continue
                    r = gdsl.run(fn, i0)
                    if r is None or dims(r) != dims(o0): continue
                    if r == o0:
                        if any(gdsl.run(fn, i) != o for i, o in P[1:]): continue
                        prog = (name, cost, fn, None)
                    else:
                        m = gdsl.fit_cmap([r], [o0])
                        if m is None: continue
                        preds = [r]; ok = True
                        for i, o in P[1:]:
                            rr = gdsl.run(fn, i)
                            if rr is None or dims(rr) != dims(o): ok = False; break
                            preds.append(rr)
                        if not ok: continue
                        m = gdsl.fit_cmap(preds, outs)
                        if not m or any(gdsl.apply_cmap(a, m) != b for a, b in zip(preds, outs)): continue
                        prog = (name + '+cmap', cost + 1, fn, m)
                    ap = _applier(prog[2], prog[3], fbg)
                    tp = []
                    for t in tests:
                        r = ap(t)
                        if r is None: break
                        tp.append(r)
                    if len(tp) != len(tests): continue
                    if not tests:                     # no test parts given: keep distinct programs
                        found.append((prog[0], prog[1], tp, ap))
                        if len(found) >= maxp: break
                        continue
                    if want is not None:
                        if tp == want:
                            found.append((prog[0], prog[1], tp, ap))
                            if names is None: break
                        continue
                    if any(tp == f[2] for f in found): continue
                    found.append((prog[0], prog[1], tp, ap))
                    if len(found) >= maxp: break
        except _Timeout:
            pass
    if stats is not None:
        stats.append(round(time.time() - t_start, 2))
    if want is None:
        DIAG['search'] += 1
        DIAG['search_fit'] += bool(found)
    if DEBUG:
        print(f"   lib_search n={len(P)} changed={len(changed)} tests={len(tests)} want={want is not None} "
              f"-> {[f[0] for f in found]} {time.time() - t_start:.2f}s", flush=True)
    return found


def _held_out(meta, first=False):
    """Index of the training pair held out by the generalisation check (last, or first, pair with a changed
    part), or None when fewer than two training pairs show a change."""
    js = sorted({m[3] for m in meta if m[1] != m[2]})
    if len(js) < 2: return None
    return js[0] if first else js[-1]


def loo_filter(meta, res, budget, fbg, stats, folds=1, occam=False):
    """Generalisation check: keep the programs of `res` that, re-induced on the parts of all training pairs but
    one, predict the held-out pair's parts exactly (fold 1: last changed pair; fold 2: also the first).
    occam: the second fold only for programs of cost >= 3 (more capacity, more evidence required)."""
    if not res: return []
    ok = {_base(r[0]) for r in res}
    for first in (False, True)[:folds]:
        need = {_base(r[0]) for r in res if not (first and occam and r[1] < 3)} & ok
        if not need: continue
        jh = _held_out(meta, first)
        if jh is None: return []
        rest = [(i, o) for _, i, o, j in meta if j != jh]
        held = [(i, o) for _, i, o, j in meta if j == jh]
        got = lib_search(rest, [i for i, _ in held], budget, cap=3.0, fbg=fbg, stats=stats, want=[o for _, o in held],
                         names=need)
        ok -= need - {_base(r[0]) for r in got}
        if not ok:
            DIAG['loo_reject'] += 1
            return []
    DIAG['loo_pass'] += 1
    return [r for r in res if _base(r[0]) in ok]


# ------------------------------------------------------------------ colour-role normalisation of parts
class Norm:
    """Colours of a part renamed by role: its non-background colours ranked by (count desc, first occurrence)
    become canonical colours 1, 2, ... (background and the task's constant new output colours kept), so a
    library program induced on normalised parts binds colour ROLES instead of absolute colours."""
    def __init__(self, bg, keep):
        self.bg, self.keep = bg, keep
        self.canon = [c for c in (1, 2, 3, 4, 5, 6, 7, 8, 9, 0) if c != bg and c not in keep]

    def fwd(self, g):
        cnt = Counter(); first = {}
        for y, row in enumerate(g):
            for x, v in enumerate(row):
                if v != self.bg:
                    cnt[v] += 1
                    first.setdefault(v, (y, x))
        order = sorted(cnt, key=lambda c: (-cnt[c], first[c]))
        if len(order) > len(self.canon) or any(c in self.keep for c in order): return None
        m = {self.bg: self.bg}
        for k, c in enumerate(order): m[c] = self.canon[k]
        return m

    def apply(self, ap, g):
        m = self.fwd(g)
        if m is None: return None
        r = ap([[m[v] for v in row] for row in g])
        if r is None: return None
        inv = {v: k for k, v in m.items()}
        for c in self.keep: inv[c] = c
        if any(v not in inv for row in r for v in row): return None
        return [[inv[v] for v in row] for row in r]


def norm_meta(meta, bg):
    """Normalised copy of part pairs (None when normalisation cannot apply or changes nothing)."""
    keep = set()
    for m in meta: keep |= colours(m[2]) - colours(m[1]) - {bg}
    if len({frozenset(colours(m[1]) - {bg}) for m in meta}) < 2: return None, None
    N = Norm(bg, keep)
    out = []
    for pt, i, o, j in meta:
        mp = N.fwd(i)
        if mp is None: return None, None
        if any(v not in mp and v not in keep for row in o for v in row): return None, None
        out.append((pt, [[mp[v] for v in row] for row in i], [[mp.get(v, v) for v in row] for row in o], j))
    return N, out


def norm_search(meta, budget, fbg, nbg, stats, folds, maxp=4, occam=False):
    """Library search on colour-normalised parts (background nbg kept); returns [(name, cost, None, apply)]
    whose apply maps the part to roles, runs the program and maps the roles back."""
    N, nmeta = norm_meta(meta, nbg if nbg is not None else 0)
    if N is None: return []
    res = lib_search([(m[1], m[2]) for m in nmeta], [], budget, cap=2.5, maxp=maxp, fbg=fbg, stats=stats)
    res = loo_filter(nmeta, res, budget, fbg, stats, folds=folds, occam=occam)
    return [(name + '@norm', cost + 2, None, (lambda g, ap=ap: N.apply(ap, g))) for name, cost, _, ap in res]


# ------------------------------------------------------------------ helpers for hypotheses
def _same_bg(grids):
    bgs = {_ORIG_BG(g) for g in grids}
    return bgs.pop() if len(bgs) == 1 else None


def _task_bg(task):
    return _same_bg([p['input'] for p in task['train']] + [t['input'] for t in task['test']])


def _disjoint(parts, h, w):
    occ = set()
    for p in parts:
        for y in range(max(0, p.r0), min(h, p.r0 + p.h)):
            for x in range(max(0, p.c0), min(w, p.c0 + p.w)):
                if (y, x) in occ: return None
                occ.add((y, x))
    return occ


def _functional(pairs):
    """Identical input parts must have identical output parts (else no context-free part program exists)."""
    m = {}
    for i, o in pairs:
        if m.setdefault(str(i), str(o)) != str(o): return False
    return True


def _regions_key(pl):
    return tuple((p.r0, p.c0, p.h, p.w, p.a.get('content')) for p in pl)


# ------------------------------------------------------------------ GROUP (attribute-dependent programs)
GROUP_ATTRS = ('colour', 'extreme', 'size', 'shape', 'border', 'ncol', 'shape_n', 'bh', 'bw', 'major', 'sym', 'srank',
               'fcol', 'solid', 'hole', 'orient', 'adj', 'mcount', 'par')


def try_group(meta, tflat, builder, prefix, budget, fbg, emit, stats, gcalls, max_calls=6):
    """One library program per attribute group; groups whose parts never change get the identity.  Every
    changing group needs >= 2 examples from >= 2 training pairs, and the grouped hypothesis must pass the
    held-out-pair check group by group."""
    jh = _held_out(meta)
    if jh is None: return
    pal = set()
    for m in meta: pal |= m[0].a.get('colours', frozenset())
    extra = []
    if len(pal) <= 6:
        for c in sorted(pal):
            extra.append(('has', c))
            for pt in [m[0] for m in meta] + list(tflat):
                pt.a[('has', c)] = c in pt.a.get('colours', ())
    cands = []; tried = set()
    for an in GROUP_ATTRS + tuple(extra):
        groups = defaultdict(list)
        for m in meta:
            if an not in m[0].a: break
            groups[m[0].a[an]].append(m)
        else:
            if len(groups) < 2 or len(groups) > 4: continue
            if any(pt.a.get(an) not in groups for pt in tflat): continue
            sig = frozenset(frozenset(id(m) for m in v) for v in groups.values())
            if sig in tried: continue
            tried.add(sig)
            bad = False
            for v in groups.values():
                ch = [m for m in v if m[1] != m[2]]
                if ch and (len(v) < 2 or len({m[3] for m in v}) < 2): bad = True
                if not _functional([(m[1], m[2]) for m in v]): bad = True
            if bad: continue
            n_ident = sum(all(m[1] == m[2] for m in v) for v in groups.values())
            if n_ident == len(groups): continue
            # groups that are purely changed or purely unchanged separate the rule's domain cleanly
            mixed = sum(any(m[1] == m[2] for m in v) and any(m[1] != m[2] for m in v) for v in groups.values())
            cands.append((mixed, len(groups) - n_ident, -n_ident, len(cands), an, groups))
    cands.sort(key=lambda c: c[:4])
    folds = [jx for jx in (jh, _held_out(meta, first=True)) if jx is not None]   # last and first changed pair
    for _, n_search, _, _, an, groups in cands:
        if budget.left() < 1.0 or gcalls[0] + n_search > max_calls: return
        progs = {}; ok = True
        for val, v in sorted(groups.items(), key=lambda kv: str(kv[0])):
            if all(m[1] == m[2] for m in v):
                progs[val] = ('id', _ident); continue
            if budget.left() < 0.8: return
            gcalls[0] += 1
            tg = [pt.g for pt in tflat if pt.a.get(an) == val]
            res = lib_search([(m[1], m[2]) for m in v], tg, budget, cap=2.5, maxp=3, fbg=fbg, stats=stats)
            res = _group_loo(v, res, folds, budget, fbg, stats)
            if not res: ok = False; break
            progs[val] = (res[0][0], res[0][3])
        if not ok: continue
        fams = {_family(p[0]) for p in progs.values()} - {None}
        if len(fams) > 1: continue          # one mechanism whose parameter depends on the attribute
        F = builder(lambda pt, progs=progs, an=an: progs[pt.a.get(an)][1] if pt.a.get(an) in progs else None)
        name = f"{prefix}:group-by-{an}(" + '; '.join(f"{k}->{v[0]}" for k, v in sorted(progs.items(), key=lambda kv: str(kv[0]))) + ')'
        if emit(name, 30, F):
            gcalls[0] = max_calls + 1          # one grouped explanation is enough
            return


def _family(name):
    """Mechanism of a program name (None for the neutral identity / erase / pure colour map)."""
    b = _base(name)
    if b in ('id', 'identity', 'erase'): return None
    return re.split(r'[\[:]', b, 1)[0]


def _group_loo(v, res, folds, budget, fbg, stats):
    """Held-out-pair check for one group: each program of `res`, re-induced on the group's parts outside the
    held-out training pair, must predict the group's parts inside it (for every fold)."""
    ok = {_base(r[0]) for r in res}
    for jx in folds:
        held = [m for m in v if m[3] == jx]
        rest = [m for m in v if m[3] != jx]
        if not held: continue
        if not any(m[1] != m[2] for m in rest): return []
        got = lib_search([(m[1], m[2]) for m in rest], [m[1] for m in held], budget, cap=2.5, fbg=fbg, stats=stats,
                         want=[m[2] for m in held], names=ok)
        ok &= {_base(r[0]) for r in got}
        if not ok: return []
    return [r for r in res if _base(r[0]) in ok]


# ------------------------------------------------------------------ INPLACE
INPLACE_SPECS = [('sep',), ('obj', False, True, 0, True), ('obj', True, False, 0, True), ('frame',),
                 ('bgsep', 'rc'), ('bgsep', 'r'), ('bgsep', 'c'), ('obj', True, True, 0, True), ('obj', False, False, 0, True),
                 ('obj', False, True, 1, True), ('obj', True, False, 1, True), ('obj', True, True, 1, True),
                 ('obj', False, False, 1, True), ('obj', True, True, 0, False), ('obj', False, True, 0, False),
                 ('lines', 'r'), ('lines', 'c')]


def _block_specs(grids, limit=3):
    """Equal tiles as an nh x nw split (<= 4 per axis, >= 4 cells per tile) valid for every given grid;
    fewest tiles first."""
    specs = []
    for nh in range(1, 5):
        for nw in range(1, 5):
            if nh * nw < 2: continue
            if all(H(g) % nh == 0 and W(g) % nw == 0 and (H(g) // nh) * (W(g) // nw) >= 4 for g in grids):
                specs.append((nh * nw, ('blocks', nh, nw)))
    specs.sort(key=lambda s: s[0])
    return [s for _, s in specs[:limit]]


def _obj_targets(ps, gi, go, bg):
    """Output part of every object (layered semantics, bboxes may overlap): inside its (padded) box, its own
    cells and the changed cells owned by no other object take the output colour; the rest is background."""
    owner = {}
    for k, pt in enumerate(ps):
        for c in pt.cells: owner[c] = k
    covered = set(); outs = []
    for k, pt in enumerate(ps):
        t = [[bg] * pt.w for _ in range(pt.h)]
        for y in range(max(0, pt.r0), min(H(gi), pt.r0 + pt.h)):
            for x in range(max(0, pt.c0), min(W(gi), pt.c0 + pt.w)):
                o = owner.get((y, x))
                if o == k or (o is None and gi[y][x] != go[y][x]):
                    t[y - pt.r0][x - pt.c0] = go[y][x]
                    covered.add((y, x))
        outs.append(t)
    return outs, covered


def inplace_setup(task, spec):
    """Region semantics (panels, bands, frames, lines): disjoint regions, output part = output crop, cells
    outside every region unchanged.  Object semantics: every changed cell inside some (padded) object box,
    output part = _obj_targets; the lifted program erases the objects and paints the transformed parts."""
    meta = []            # (part, in, out, train index)
    is_obj = spec[0] == 'obj' and spec[4]
    overlap_ok = spec[0] == 'obj' and not spec[4]          # whole bbox crops: overlapping boxes allowed
    whole = True
    for j, p in enumerate(task['train']):
        gi, go = p['input'], p['output']
        ps = partition(spec, gi)
        if not ps: return None
        whole = whole and len(ps) == 1 and ps[0].r0 <= 0 and ps[0].c0 <= 0 and \
            ps[0].r0 + ps[0].h >= H(gi) and ps[0].c0 + ps[0].w >= W(gi)
        bg = _ORIG_BG(gi)
        if is_obj:
            outs, covered = _obj_targets(ps, gi, go, bg)
            for y in range(H(gi)):
                for x in range(W(gi)):
                    if gi[y][x] != go[y][x] and (y, x) not in covered: return None
            for pt, t in zip(ps, outs):
                meta.append((pt, pt.g, t, j))
            continue
        if overlap_ok:
            occ = set()
            for pt in ps:
                occ |= {(y, x) for y in range(max(0, pt.r0), min(H(gi), pt.r0 + pt.h))
                        for x in range(max(0, pt.c0), min(W(gi), pt.c0 + pt.w))}
        else:
            occ = _disjoint(ps, H(gi), W(gi))
            if occ is None: return None
        for y in range(H(gi)):
            ry, oy = gi[y], go[y]
            for x in range(W(gi)):
                if ry[x] != oy[x] and (y, x) not in occ: return None
        for pt in ps:
            meta.append((pt, pt.g, region_crop(go, pt.r0, pt.c0, pt.h, pt.w, bg), j))
    if whole: return None           # one part covering every training grid: that is the whole-grid library's job
    if all(m[1] == m[2] for m in meta): return None
    tparts = []
    for t in task['test']:
        ps = partition(spec, t['input'])
        if not ps or (not is_obj and not overlap_ok and _disjoint(ps, H(t['input']), W(t['input'])) is None): return None
        tparts.append(ps)
    return meta, tparts


def lifted_inplace(spec, chooser):
    """Whole-grid program: partition, transform each part by chooser(part) (an apply fn), put it back
    (regions: pasted; objects: all objects erased, then every transformed part's foreground painted)."""
    is_obj = spec[0] == 'obj' and spec[4]
    overlap_ok = spec[0] == 'obj' and not spec[4]
    def F(g):
        ps = partition(spec, g)
        if not ps: return None
        if not is_obj and not overlap_ok and _disjoint(ps, H(g), W(g)) is None: return None
        canvas = copyg(g); bg = _ORIG_BG(g)
        if is_obj:
            for pt in ps:
                for y, x in pt.cells: canvas[y][x] = bg
        for pt in ps:
            ap = chooser(pt)
            if ap is None: return None
            r = ap(pt.g)
            if r is None or dims(r) != (pt.h, pt.w): return None
            paste(canvas, r, pt.r0, pt.c0, only_fg=bg if is_obj else None)
        return canvas
    return F


def _pad_stable(task, spec, F, ap):
    """The margin of padded object parts must not be an arbitrary choice: if the same program with one more cell
    of margin also reproduces every training pair, both margins are consistent with the evidence and they must
    agree on the test inputs (else the transformed objects may need more room than the margin allows)."""
    wider = spec[:3] + (spec[3] + 1,) + spec[4:]
    G = lifted_inplace(wider, lambda pt: ap)
    try:
        if any(G(p['input']) != p['output'] for p in task['train']): return True     # the margin is determined
        return all(F(t['input']) == G(t['input']) for t in task['test'])
    except _Timeout:
        raise
    except Exception:
        return True


def try_inplace(task, budget_all, emit, stats, specs):
    seen = set(); setups = []; ok_pad0 = set(); calls = 0
    tbg = _task_bg(task)
    n_ok = 0; n_norm = 0
    budget = budget_all.sub(7.0)                 # plain pooled search; the rest is left for GROUP
    for spec in specs:
        if budget.left() < 1.0 or calls >= 6 or n_ok >= 3: break
        if spec[0] == 'obj' and spec[3] and (spec[1], spec[2]) in ok_pad0: continue
        st = inplace_setup(task, spec)
        if st is None: continue
        if spec[0] == 'obj' and not spec[3] and spec[4]: ok_pad0.add((spec[1], spec[2]))
        meta, tparts = st
        key = (_regions_key([m[0] for m in meta]), tuple(_regions_key(ps) for ps in tparts))
        if key in seen: continue
        seen.add(key)
        fbg = tbg if spec[0] in ('obj', 'frame', 'lines', 'bgsep') else None
        tflat = [pt for ps in tparts for pt in ps]
        pairs = [(m[1], m[2]) for m in meta]
        if DEBUG: print(' INPLACE', spec_name(spec), 'parts', len(meta), 'functional', _functional(pairs), flush=True)
        res = []
        if _functional(pairs) and _held_out(meta) is not None:
            calls += 1
            res = lib_search(pairs, [pt.g for pt in tflat], budget, cap=3.0, maxp=4, fbg=fbg, stats=stats)
            res = loo_filter(meta, res, budget, fbg, stats, folds=2, occam=True)
            if not res and n_norm < 2 and budget.left() > 2.0:
                n_norm += 1
                res = norm_search(meta, budget, fbg, tbg, stats, folds=2, occam=True)
            for name, cost, tp, ap in res:
                F = lifted_inplace(spec, lambda pt, ap=ap: ap)
                if spec[0] == 'obj' and spec[3] and not _pad_stable(task, spec, F, ap): continue
                n_ok += 2 * emit(f"lift[{spec_name(spec)}]:{name}", 10 + cost, F)
        if not res and sum(m[1] != m[2] for m in meta) >= 2 and spec[0] != 'blocks':
            setups.append((spec, meta, tparts, fbg))
    gcalls = [0]
    for spec, meta, tparts, fbg in (setups if not n_ok else []):
        if budget_all.left() < 1.5 or gcalls[0] >= 6: break
        try_group(meta, [pt for ps in tparts for pt in ps], lambda ch, spec=spec: lifted_inplace(spec, ch),
                  f"lift[{spec_name(spec)}]", budget_all, fbg, emit, stats, gcalls)


# ------------------------------------------------------------------ SELIN (only the selected part changes)
SELIN_SPECS = [('obj', False, True, 0, True), ('obj', True, False, 0, True), ('sep',), ('frame',), ('bgsep', 'rc'),
               ('obj', True, True, 0, True), ('obj', False, False, 0, True), ('obj', False, True, 1, True),
               ('obj', True, False, 1, True)]


def lifted_selin(spec, sel, ap, isolate=False):
    """The selected part transformed in place; the rest kept (or, isolate, cleared to the background)."""
    def F(g):
        ps = partition(spec, g)
        if not ps: return None
        c = select(ps, sel)
        if c is None: return None
        r = ap(c.g)
        if r is None or dims(r) != (c.h, c.w): return None
        canvas = [[_ORIG_BG(g)] * W(g) for _ in range(H(g))] if isolate else copyg(g)
        paste(canvas, r, c.r0, c.c0)
        return canvas
    return F


def try_selin(task, budget, emit, stats, max_calls=6):
    train, test = task['train'], task['test']
    tin = [p['input'] for p in train]
    tbg = _task_bg(task)
    diffs = [{(y, x) for y in range(H(p['input'])) for x in range(W(p['input'])) if p['input'][y][x] != p['output'][y][x]}
             for p in train]
    cands = []; seen = set()
    for spec in SELIN_SPECS:
        if budget.left() < 1.0: break
        pin = [partition(spec, g) for g in tin]
        if any(not ps or len(ps) < 2 for ps in pin): continue
        pte = [partition(spec, t['input']) for t in test]
        if any(not ps for ps in pte): continue
        ns = {len(ps) for ps in pin + pte}
        sels = _selectors(tin, ns.pop() if len(ns) == 1 and spec[0] in ('sep', 'bgsep', 'frame') else 0)
        for sel in sels:
            ch = [select(ps, sel) for ps in pin]
            if any(c is None for c in ch): continue
            inside = lambda c, y, x: c.r0 <= y < c.r0 + c.h and c.c0 <= x < c.c0 + c.w
            keep = all(inside(c, y, x) for c, d in zip(ch, diffs) for y, x in d)
            isolate = not keep and all(p['output'][y][x] == _ORIG_BG(p['input'])
                                       for c, p in zip(ch, train) for y in range(H(p['output'])) for x in range(W(p['output']))
                                       if not inside(c, y, x))
            if not keep and not isolate: continue
            pairs = [(c.g, region_crop(p['output'], c.r0, c.c0, c.h, c.w, _ORIG_BG(p['input']))) for c, p in zip(ch, train)]
            if keep and sum(i != o for i, o in pairs) < 2: continue
            ct = [select(ps, sel) for ps in pte]
            if any(c is None for c in ct): continue
            key = (str(pairs), tuple(str(c.g) for c in ct), isolate)
            if key in seen: continue
            seen.add(key)
            cands.append((spec, sel, pairs, [c.g for c in ct], isolate))
    n = 0
    for spec, sel, pairs, tg, isolate in cands:
        if budget.left() < 1.0 or n >= max_calls: break
        tag = 'isolate' if isolate else 'keep'
        if all(i == o for i, o in pairs):          # isolate the selected part unchanged
            if emit(f"lift-selin[{spec_name(spec)},{tag}]:select-{sel[0]}-{sel[1]}", 8, lifted_selin(spec, sel, _ident, isolate)):
                return
            continue
        n += 1
        fbg = tbg if spec[0] in ('obj', 'frame', 'bgsep') else None
        meta = [(None, i, o, j) for j, (i, o) in enumerate(pairs)]
        res = lib_search(pairs, tg, budget, cap=2.5, maxp=4, fbg=fbg, stats=stats)
        res = loo_filter(meta, res, budget, fbg, stats, folds=2)
        if not res and budget.left() > 2.0:
            res = norm_search(meta, budget, fbg, tbg, stats, folds=2)
        for name, cost, tp, ap in res:
            if emit(f"lift-selin[{spec_name(spec)},{tag}]:select-{sel[0]}-{sel[1]}>{name}", 14 + cost,
                    lifted_selin(spec, sel, ap, isolate)):
                return


# ------------------------------------------------------------------ LAYERS (one part per colour)
def layers_setup(task):
    meta = []
    for j, p in enumerate(task['train']):
        gi, go = p['input'], p['output']
        bg = _ORIG_BG(gi)
        ps = partition(('layers',), gi)
        if not ps: return None
        cin = colours(gi) - {bg}
        if not colours(go) - {bg} <= cin: return None
        for pt in ps:
            c = pt.a['colour']
            meta.append((pt, pt.g, [[v if v == c else bg for v in row] for row in go], j))
    if all(m[1] == m[2] for m in meta) or max(Counter(m[3] for m in meta).values()) < 2: return None
    tparts = []
    for t in task['test']:
        ps = partition(('layers',), t['input'])
        if not ps: return None
        tparts.append(ps)
    return meta, tparts


def lifted_layers(chooser):
    def F(g):
        bg = _ORIG_BG(g)
        ps = partition(('layers',), g)
        if not ps: return None
        canvas = [[bg] * W(g) for _ in range(H(g))]
        for pt in ps:
            ap = chooser(pt)
            if ap is None: return None
            r = ap(pt.g)
            if r is None or dims(r) != dims(g): return None
            for y in range(H(g)):
                for x in range(W(g)):
                    v = r[y][x]
                    if v != bg:
                        if canvas[y][x] != bg and canvas[y][x] != v: return None
                        canvas[y][x] = v
        return canvas
    return F


def try_layers(task, budget, emit, stats):
    st = layers_setup(task)
    if st is None: return
    meta, tparts = st
    fbg = _task_bg(task)
    tflat = [pt for ps in tparts for pt in ps]
    pairs = [(m[1], m[2]) for m in meta]
    if _functional(pairs) and _held_out(meta) is not None:
        plain = budget.sub(2.5)                   # the rest is left for the per-colour grouping
        res = lib_search(pairs, [pt.g for pt in tflat], plain, cap=2.0, maxp=4, fbg=fbg, stats=stats)
        res = loo_filter(meta, res, budget, fbg, stats, folds=2, occam=True)
        ok = False
        for name, cost, tp, ap in res:
            ok = emit(f"lift[layers]:{name}", 12 + cost, lifted_layers(lambda pt, ap=ap: ap)) or ok
        if ok: return
    if sum(m[1] != m[2] for m in meta) >= 2:
        try_group(meta, tflat, lifted_layers, "lift[layers]", budget, fbg, emit, stats, [0], max_calls=4)


# ------------------------------------------------------------------ OBJMAP (objects change extent in place)
ANCHORS = ('centre', 'tl', 'tr', 'bl', 'br')
DIM_RULES = {
    'T': lambda h, w: (w, h),
    'grow1': lambda h, w: (h + 2, w + 2),
    'shrink1': lambda h, w: (h - 2, w - 2) if h > 2 and w > 2 else None,
    'x2': lambda h, w: (2 * h, 2 * w),
    'x3': lambda h, w: (3 * h, 3 * w),
    'w+1': lambda h, w: (h, w + 1), 'w-1': lambda h, w: (h, w - 1) if w > 1 else None,
    'h+1': lambda h, w: (h + 1, w), 'h-1': lambda h, w: (h - 1, w) if h > 1 else None,
    'w+2': lambda h, w: (h, w + 2), 'w-2': lambda h, w: (h, w - 2) if w > 2 else None,
    'h+2': lambda h, w: (h + 2, w), 'h-2': lambda h, w: (h - 2, w) if h > 2 else None,
}


def _anchor_pt(r0, c0, r1, c1, a):
    if a == 'centre': return (r0 + r1, c0 + c1)
    if a == 'tl': return (r0, c0)
    if a == 'tr': return (r0, c1)
    if a == 'bl': return (r1, c0)
    return (r1, c1)


def _place(pt, h, w, a):
    if a == 'centre':
        sy, sx = pt
        if (sy - h + 1) % 2 or (sx - w + 1) % 2: return None
        return (sy - h + 1) // 2, (sx - w + 1) // 2
    if a == 'tl': return pt
    if a == 'tr': return pt[0], pt[1] - w + 1
    if a == 'bl': return pt[0] - h + 1, pt[1]
    return pt[0] - h + 1, pt[1] - w + 1


def _out_region(pt, anchor, rule):
    d = DIM_RULES[rule](pt.a['bh'], pt.a['bw'])
    if d is None: return None
    pos = _place(_anchor_pt(*bbox(pt.cells), anchor), d[0], d[1], anchor)
    if pos is None: return None
    return pos[0], pos[1], d[0], d[1]


def objmap_setup(task, diag, byc, anchor, rule):
    """Each object is replaced by a part of dims rule(h, w) anchored at the same point; the output is the
    background canvas with every transformed part's foreground painted on it."""
    spec = ('obj', diag, byc, 0, True)
    meta = []; resized = False
    for j, p in enumerate(task['train']):
        gi, go = p['input'], p['output']
        bg = _ORIG_BG(gi)
        ps = partition(spec, gi)
        if not ps or len(ps) < 2: return None
        canvas = copyg(gi)
        for pt in ps:
            for y, x in pt.cells: canvas[y][x] = bg
        regs = []
        for pt in ps:
            reg = _out_region(pt, anchor, rule)
            if reg is None: return None
            regs.append(Part(reg[0], reg[1], reg[2], reg[3], None))
            if (reg[2], reg[3]) != (pt.h, pt.w): resized = True
            if reg[2] * reg[3] * 2 > H(go) * W(go): return None          # a part as large as the scene: not per-object
            op = region_crop(go, reg[0], reg[1], reg[2], reg[3], bg)
            paste(canvas, op, reg[0], reg[1], only_fg=bg)
            meta.append((pt, pt.g, op, j))
        if canvas != go: return None
        if _disjoint(regs, H(go), W(go)) is None: return None      # every output cell explained by one part
    if not resized: return None                                     # same extents: INPLACE covers it
    tparts = []
    for t in task['test']:
        ps = partition(spec, t['input'])
        if not ps: return None
        tparts.append(ps)
    return meta, tparts


def lifted_objmap(diag, byc, anchor, rule, chooser):
    spec = ('obj', diag, byc, 0, True)
    def F(g):
        bg = _ORIG_BG(g)
        ps = partition(spec, g)
        if not ps: return None
        canvas = copyg(g)
        for pt in ps:
            for y, x in pt.cells: canvas[y][x] = bg
        for pt in ps:
            ap = chooser(pt)
            if ap is None: return None
            r = ap(pt.g)
            if r is None: return None
            reg = _out_region(pt, anchor, rule)
            if reg is None or (reg[2], reg[3]) != dims(r): return None
            paste(canvas, r, reg[0], reg[1], only_fg=bg)
        return canvas
    return F


def try_objmap(task, budget, emit, stats):
    fbg = _task_bg(task)
    seen = set(); setups = []; calls = 0
    for diag, byc in ((False, True), (True, False), (True, True), (False, False)):
        for rule in DIM_RULES:
            for anchor in ANCHORS:
                if budget.left() < 1.0: return
                st = objmap_setup(task, diag, byc, anchor, rule)
                if st is None: continue
                meta, tparts = st
                key = str([(m[1], m[2]) for m in meta]) + str([[pt.g for pt in ps] for ps in tparts])
                if key in seen: continue
                seen.add(key)
                tflat = [pt for ps in tparts for pt in ps]
                pairs = [(m[1], m[2]) for m in meta]
                pre = f"lift-objmap[{spec_name(('obj', diag, byc, 0, True))},{anchor},{rule}]"
                res = []
                if _functional(pairs) and _held_out(meta) is not None and calls < 4:
                    calls += 1
                    res = lib_search(pairs, [pt.g for pt in tflat], budget, cap=3.0, maxp=4, fbg=fbg, stats=stats)
                    res = loo_filter(meta, res, budget, fbg, stats, folds=2, occam=True)
                for name, cost, tp, ap in res:
                    emit(f"{pre}:{name}", 12 + cost, lifted_objmap(diag, byc, anchor, rule, lambda pt, ap=ap: ap))
                if not res and sum(m[1] != m[2] for m in meta) >= 2:
                    setups.append((diag, byc, anchor, rule, meta, tflat, pre))
    gcalls = [0]
    for diag, byc, anchor, rule, meta, tflat, pre in setups:
        if budget.left() < 1.5 or gcalls[0] >= 4: break
        try_group(meta, tflat, lambda ch, d=diag, b=byc, a=anchor, r=rule: lifted_objmap(d, b, a, r, ch), pre, budget, fbg,
                  emit, stats, gcalls, max_calls=4)


# ------------------------------------------------------------------ SELECT
SELECT_SPECS = [('sep',), ('obj', False, True, 0, True), ('obj', True, True, 0, True), ('frame',),
                ('obj', True, False, 0, True), ('obj', False, False, 0, True), ('obj', True, False, 0, False),
                ('obj', False, True, 0, False), ('bgsep', 'rc'), ('bgsep', 'r'), ('bgsep', 'c')]


def _selectors(train_inputs, fixed_n):
    common = None
    for g in train_inputs:
        cs = colours(g) - {_ORIG_BG(g)}
        common = cs if common is None else common & cs
    sels = []
    for an in ('size', 'area', 'ncol', 'bh', 'bw', 'density'):
        sels.append(('max', an)); sels.append(('min', an))
    sels += [('min', 'top'), ('min', 'left'), ('max', 'bottom'), ('max', 'right')]
    for an in ('colours', 'shape', 'content', 'size', 'ncol', 'sym', 'colour', 'area', 'fcol', 'solid', 'hole', 'orient'):
        sels.append(('unique', an))
    for c in sorted(common or ()):
        sels += [('has', c), ('lacks', c), ('maxcount', c), ('touch', c)]
    if fixed_n:
        sels += [('index', k) for k in range(fixed_n)]
    return sels


def select(ps, sel):
    kind, an = sel
    if kind == 'index':
        return ps[an] if len(ps) > an else None
    if kind in ('max', 'min'):
        vals = [p.a.get(an) for p in ps]
        if any(v is None for v in vals): return None
        best = max(vals) if kind == 'max' else min(vals)
        hits = [p for p, v in zip(ps, vals) if v == best]
    elif kind == 'unique':
        if len(ps) < 3: return None
        vals = [p.a.get(an) for p in ps]
        if any(v is None for v in vals): return None
        cnt = Counter(vals)
        hits = [p for p, v in zip(ps, vals) if cnt[v] == 1]
    elif kind in ('has', 'lacks'):
        hits = [p for p in ps if (any(v == an for r in p.g for v in r)) == (kind == 'has')]
    elif kind == 'touch':                         # the one object touched by a cell of colour c
        if any('adj' not in p.a for p in ps): return None
        hits = [p for p in ps if an in p.a['adj']]
    elif kind == 'maxcount':
        vals = [sum(v == an for r in p.g for v in r) for p in ps]
        best = max(vals)
        if best == 0: return None
        hits = [p for p, v in zip(ps, vals) if v == best]
    else:
        return None
    return hits[0] if len(hits) == 1 else None


def _dim_rel(pairs):
    """Strength of the size relation part -> output (lower is stronger); None when no relation holds."""
    rels = None
    for i, o in pairs:
        (h, w), (oh, ow) = dims(i), dims(o)
        r = set()
        if (h, w) == (oh, ow): r.add('eq')
        if (h, w) == (ow, oh): r.add('T')
        if oh % h == 0 and ow % w == 0: r.add(('up', oh // h, ow // w))
        if h % oh == 0 and w % ow == 0: r.add(('down', h // oh, w // ow))
        r.add(('const', oh, ow))
        if oh <= h and ow <= w: r.add('le')
        rels = r if rels is None else rels & r
    if not rels: return None
    if 'eq' in rels or 'T' in rels: return 0
    if any(isinstance(x, tuple) and x[0] in ('up', 'down') for x in rels): return 1
    if 'le' in rels: return 2
    return 3


def lifted_select(spec, sel, ap):
    def F(g):
        ps = partition(spec, g)
        if not ps: return None
        c = select(ps, sel)
        return ap(c.g) if c is not None else None
    return F


def try_select(task, budget, emit, stats):
    train, test = task['train'], task['test']
    tin = [p['input'] for p in train]
    tbg = _task_bg(task)
    cands = []; seen = set()
    for spec in SELECT_SPECS + _block_specs(tin + [t['input'] for t in test], limit=2):
        if budget.left() < 1.0: break
        pin = [partition(spec, g) for g in tin]
        if any(not ps for ps in pin): continue
        pte = [partition(spec, t['input']) for t in test]
        if any(not ps for ps in pte): continue
        ns = {len(ps) for ps in pin + pte}
        sels = _selectors(tin, ns.pop() if len(ns) == 1 and spec[0] in ('sep', 'bgsep', 'frame', 'blocks') else 0)
        for sel in sels:
            ch = [select(ps, sel) for ps in pin]
            if any(c is None for c in ch): continue
            if all((c.h, c.w) == dims(g) for c, g in zip(ch, tin)): continue     # not a selection: whole grid
            ct = [select(ps, sel) for ps in pte]
            if any(c is None for c in ct): continue
            key = (tuple(str(c.g) for c in ch), tuple(str(c.g) for c in ct))
            if key in seen: continue
            seen.add(key)
            pairs = [(c.g, p['output']) for c, p in zip(ch, train)]
            rel = _dim_rel(pairs)
            if rel is None: continue
            cands.append((rel, len(cands), spec, sel, pairs, [c.g for c in ct]))
    cands.sort(key=lambda x: (x[0], x[1]))
    n_id = 0
    for rel, _, spec, sel, pairs, tg in cands:          # the selected part is the output itself
        if all(i == o for i, o in pairs):
            n_id += emit(f"lift[{spec_name(spec)}]:select-{sel[0]}-{sel[1]}", 5, lifted_select(spec, sel, _ident))
    if n_id: return
    # hypotheses selecting the same training parts share one library search (they differ only at test)
    groups = {}
    for rel, idx, spec, sel, pairs, tg in cands:
        if all(i == o for i, o in pairs): continue
        fbg = tbg if spec[0] in ('obj', 'frame') else None
        k = (str(pairs), fbg)
        if k not in groups: groups[k] = (rel, idx, pairs, fbg, [])
        groups[k][4].append((spec, sel))
    n = 0
    for rel, _, pairs, fbg, members in sorted(groups.values(), key=lambda g: g[:2]):
        if budget.left() < 1.0 or n >= 8: break
        n += 1
        meta = [(None, i, o, j) for j, (i, o) in enumerate(pairs)]
        res = lib_search(pairs, [], budget, cap=2.5, maxp=6, fbg=fbg, stats=stats)
        res = loo_filter(meta, res, budget, fbg, stats, folds=2)
        semantic = any(s[0] in ('obj', 'frame', 'sep') for s, _ in members)
        if not res and semantic and budget.left() > 2.0:
            res = norm_search(meta, budget, fbg, tbg, stats, folds=2)
        for name, cost, tp, ap in res:
            for spec, sel in members:
                if name.endswith('@norm') and spec[0] not in ('obj', 'frame', 'sep'): continue
                emit(f"lift[{spec_name(spec)}]:select-{sel[0]}-{sel[1]}>{name}", 12 + cost, lifted_select(spec, sel, ap))


# ------------------------------------------------------------------ PANELMAP
def in_layout(kind, g):
    """Input panel lattice: (panels in reading order, R, C, separator colour) from separator lines ('sep') or
    from all-background rows / columns when every lattice cell holds something ('bgsep')."""
    if kind == 'sep':
        lay = sep_layout(g)
        if lay is None: return None
        sc, ri, ci = lay
    else:
        h, w = H(g), W(g); sc = _ORIG_BG(g)
        ri = _intervals([r for r in range(h) if all(v == sc for v in g[r])], h)
        ci = _intervals([c for c in range(w) if all(g[r][c] == sc for r in range(h))], w)
        if len(ri) * len(ci) < 2: return None
    ps = [[row[b:b1 + 1] for row in g[a:a1 + 1]] for a, a1 in ri for b, b1 in ci]
    if kind == 'bgsep' and any(all(v == sc for r in p for v in r) for p in ps): return None
    return ps, len(ri), len(ci), sc


def _out_layout(train, kind):
    """Output layout rule, constant over pairs: the input's R x C panel grid with the output's own separators
    ('sep', colour 'same'|c, row sep, col sep, top, bottom, left, right margins); or R x C equal blocks
    ('blocks',); or C x R equal blocks in reading order ('blocksT',)."""
    struct = set(); same = True; outc = set(); blocks = blocksT = True
    for p in train:
        li, lo = in_layout(kind, p['input']), sep_layout(p['output'])
        if li is None: return None
        _, R, C, sci = li
        go = p['output']
        if H(go) % R or W(go) % C: blocks = False
        if H(go) % C or W(go) % R or R == C: blocksT = False
        if lo is None:
            struct.add(None); continue
        sco, rio, cio = lo
        if (R, C) != (len(rio), len(cio)):
            struct.add(None); continue
        gaps_r = {b[0] - a[1] - 1 for a, b in zip(rio, rio[1:])} or {0}
        gaps_c = {b[0] - a[1] - 1 for a, b in zip(cio, cio[1:])} or {0}
        if len(gaps_r) != 1 or len(gaps_c) != 1:
            struct.add(None); continue
        struct.add((gaps_r.pop(), gaps_c.pop(), rio[0][0], H(go) - 1 - rio[-1][1], cio[0][0], W(go) - 1 - cio[-1][1]))
        same = same and sco == sci
        outc.add(sco)
    rules = []
    if len(struct) == 1 and None not in struct:
        if same: rules.append(('sep', 'same') + next(iter(struct)))
        elif len(outc) == 1: rules.append(('sep', next(iter(outc))) + next(iter(struct)))
    if all(sep_layout(p['output']) is None for p in train):
        if blocks: rules.append(('blocks',))
        if blocksT: rules.append(('blocksT',))
    return rules


def _out_panels(rule, R, C, g_out):
    if rule[0] == 'sep':
        ps = part_sep(g_out)
        return [p.g for p in ps] if ps else None
    nr, nc = (R, C) if rule[0] == 'blocks' else (C, R)
    ps = part_blocks(g_out, nr, nc)
    return [p.g for p in ps] if ps else None


def _build_panels(panels, nr, nc, sc, geom):
    tr_, tc, mt, mb, ml, mr = geom
    rows = [panels[a * nc:(a + 1) * nc] for a in range(nr)]
    hs = [{H(p) for p in row} for row in rows]
    ws = [{W(rows[a][b]) for a in range(nr)} for b in range(nc)]
    if any(len(s) != 1 for s in hs + ws): return None
    hs = [s.pop() for s in hs]; ws = [s.pop() for s in ws]
    Ht = mt + mb + sum(hs) + tr_ * (nr - 1); Wt = ml + mr + sum(ws) + tc * (nc - 1)
    if Ht > 30 or Wt > 30: return None
    out = [[sc] * Wt for _ in range(Ht)]
    y = mt
    for a in range(nr):
        x = ml
        for b in range(nc):
            paste(out, rows[a][b], y, x); x += ws[b] + tc
        y += hs[a] + tr_
    return out


def lifted_panelmap(kind, rule, ap):
    def F(g):
        lay = in_layout(kind, g)
        if lay is None: return None
        ps, R, C, sci = lay
        outs = [ap(p) for p in ps]
        if any(o is None for o in outs): return None
        if rule[0] == 'blocks':
            return _build_panels(outs, R, C, 0, (0, 0, 0, 0, 0, 0))
        if rule[0] == 'blocksT':
            return _build_panels(outs, C, R, 0, (0, 0, 0, 0, 0, 0))
        return _build_panels(outs, R, C, sci if rule[1] == 'same' else rule[1], rule[2:])
    return F


def try_panelmap(task, budget, emit, stats):
    train = task['train']
    for kind in ('sep', 'bgsep'):
        for rule in _out_layout(train, kind) or ():
            if budget.left() < 1.5: return
            meta = []; ok = True
            for j, p in enumerate(train):
                ps, R, C, _ = in_layout(kind, p['input'])
                po = _out_panels(rule, R, C, p['output'])
                if not po or len(po) != len(ps): ok = False; break
                for a, b in zip(ps, po):
                    meta.append((None, a, b, j))
            if not ok: continue
            tl = [in_layout(kind, t['input']) for t in task['test']]
            if any(x is None for x in tl): continue
            pairs = [(m[1], m[2]) for m in meta]
            if not _functional(pairs) or _held_out(meta) is None: continue
            res = lib_search(pairs, [p for x in tl for p in x[0]], budget, cap=3.0, maxp=4, stats=stats)
            res = loo_filter(meta, res, budget, None, stats, folds=2, occam=True)
            for name, cost, tp, ap in res:
                emit(f"lift-panelmap[{kind}->{rule[0]}]:{name}", 12 + cost, lifted_panelmap(kind, rule, ap))


# ------------------------------------------------------------------ SEARCH
def SEARCH(task):
    budget = Budget(TOTAL_BUDGET)
    DIAG.clear()
    found = []; seen = {}; stats = []
    train, test = task['train'], task['test']

    def emit(name, cost, F):
        """Verify the whole lifted program on every training pair, then predict the test inputs."""
        try:
            for p in train:
                if F(p['input']) != p['output']: return False
            preds = [F(t['input']) for t in test]
        except _Timeout:
            raise
        except Exception:
            return False
        if any(p is None for p in preds): return False
        k = str(preds)
        if k in seen:
            seen[k]['votes'] += 1            # another hypothesis agrees on the test prediction
            return 0.5
        seen[k] = {'program': name, 'cost': cost, 'preds': preds, 'votes': 1, 't': round(time.time() - budget.t0, 2)}
        found.append(seen[k])
        return True

    patched = _install_patch()
    try:
        with prof_timer(), wall_cap(TOTAL_BUDGET + 0.5):
            same = all(dims(p['input']) == dims(p['output']) for p in train)
            if same:
                try_inplace(task, budget.sub(11.0), emit, stats, INPLACE_SPECS)
                if not found:
                    try_layers(task, budget.sub(5.0), emit, stats)
                if not found:
                    try_objmap(task, budget.sub(3.0), emit, stats)
                if not found:
                    try_selin(task, budget.sub(3.0), emit, stats)
            else:
                try_panelmap(task, budget.sub(4.0), emit, stats)
                try_select(task, budget, emit, stats)
    except _Timeout:
        pass
    finally:
        _remove_patch(patched)
        _FORCED[0] = None
    found.sort(key=lambda r: (-r['votes'], r['cost']))
    SEARCH.stats = stats + [('first', min((r['t'] for r in found), default=None)), ('diag', dict(DIAG))]
    return [{'program': r['program'] + (f" (x{r['votes']})" if r['votes'] > 1 else ''), 'cost': r['cost'], 'preds': r['preds']}
            for r in found[:3]]
