"""move.toward_anchor: every mover object travels straight toward the anchor it is paired with.

One parametrised primitive  attract(anchors, conn, pairing, mode, stop, unmatched, paint):
  anchors  : lines   (full rows/cols or frame sides of one non-bg colour)
             | static (components of colours that never change in training)
             | big    (per colour, the unique largest component of size >= 2)
             | all    (every component; used with the table pairing)
  conn     : mover segmentation, single-colour 4- or 8-connected components (non-anchor components)
  pairing  : same colour | any colour (nearest) | table (colour-compatibility pairs + allowed directions,
             both induced from the displacements observed in the training pairs)
  mode     : orth (only anchors whose row/col projection overlaps the mover; straight perpendicular motion)
             | king (step = sign vector toward the anchor's bbox, recomputed each step; 8 directions)
  stop     : touch8 / touch4 (stop when 8/4-adjacent to the anchor, obstacles ignored)
             | contact (stop when the next step hits any non-background cell; nearest movers settle first)
             | into (enter the anchor region and settle against its far side)
  unmatched: keep | erase   (movers with no reachable paired anchor)
  paint    : keep | rim     (moved mover drawn in the anchor's rim colour: the non-bg colour bordering it)
Every parameter is enumerated from a small generic domain or induced from the training pairs; programs are
verified on all training pairs before being yielded.
"""
import sys
sys.path.append('/home/claude/work/widen')
sys.path.append('/home/claude/work/latent')
from collections import Counter
from gdsl import H, W, bg_of, objects, static_colours
from fam_move_slide_until_contact import fits

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def sgn(v): return (v > 0) - (v < 0)


def bb(cells):
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


# ------------------------------------------------------------------ anchors
def line_anchors(g, bg):
    h, w = H(g), W(g); out = []
    for r in range(h):
        inner = set(g[r][1:w - 1])
        if w >= 4 and len(inner) == 1 and g[r][1] != bg:
            c = g[r][1]; out.append((c, [(r, x) for x in range(w) if g[r][x] == c]))
    for x in range(w):
        inner = {g[r][x] for r in range(1, h - 1)}
        if h >= 4 and len(inner) == 1 and g[1][x] != bg:
            c = g[1][x]; out.append((c, [(r, x) for r in range(h) if g[r][x] == c]))
    return out


def split(g, sel, conn, st):
    """-> (anchors [(colour, cells)], movers [(colour, cells)]) or None."""
    bg = bg_of(g)
    comps = [(g[ob[0][0]][ob[0][1]], ob) for ob in objects(g, bg, diag=conn == 8, by_colour=True)]
    if len(comps) > 80: return None
    if sel == 'lines':
        an = line_anchors(g, bg)
        if not an: return None
        ac = {p for _, cs in an for p in cs}
        mv = [(c, [p for p in cs if p not in ac]) for c, cs in comps]
        return an, [(c, cs) for c, cs in mv if cs]
    if sel == 'static':
        an = [(c, cs) for c, cs in comps if c in st]
        mv = [(c, cs) for c, cs in comps if c not in st]
        return an, mv
    if sel == 'big':
        an = []; mv = []
        byc = {}
        for c, cs in comps: byc.setdefault(c, []).append(cs)
        for c, L in byc.items():
            L = sorted(L, key=len, reverse=True)
            if len(L[0]) >= 2 and (len(L) == 1 or len(L[0]) > len(L[1])):
                an.append((c, L[0])); mv += [(c, cs) for cs in L[1:]]
            else:
                mv += [(c, cs) for cs in L]
        return an, mv
    if sel == 'all':
        return comps, comps
    return None


def rim_colour(g, cells, bg):
    s = set(cells); col = g[cells[0][0]][cells[0][1]]; cnt = Counter()
    for y, x in cells:
        for dy, dx in N4:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H(g) and 0 <= xx < W(g) and (yy, xx) not in s and g[yy][xx] not in (bg, col):
                cnt[g[yy][xx]] += 1
    return cnt.most_common(1)[0][0] if cnt else None


# ------------------------------------------------------------------ geometry
def rel(mb, ab):
    """Sign vector from mover bbox toward anchor bbox (0 on overlapping axes) and the Chebyshev gap."""
    r0, c0, r1, c1 = mb; a0, b0, a1, b1 = ab
    dy = 1 if a0 > r1 else -1 if a1 < r0 else 0
    dx = 1 if b0 > c1 else -1 if b1 < c0 else 0
    gy = a0 - r1 if dy > 0 else r0 - a1 if dy < 0 else 0
    gx = b0 - c1 if dx > 0 else c0 - b1 if dx < 0 else 0
    return dy, dx, max(gy, gx)


def adjacent(cells, aset, nb):
    return any((y + dy, x + dx) in aset for y, x in cells for dy, dx in nb)


def choose(mc, mcells, anchors, pairing, mode, table, dirs):
    mb = bb(mcells); best = None; ms = set(mcells)
    for k, (ac, acells, ab) in enumerate(anchors):
        if acells is mcells or ms & set(acells): continue
        if pairing == 'same' and ac != mc: continue
        if pairing == 'table' and ac not in table.get(mc, ()): continue
        dy, dx, gap = rel(mb, ab)
        if dy == 0 and dx == 0: continue
        if mode == 'orth' and dy and dx: continue
        if dirs is not None and (sgn(dy), sgn(dx)) not in dirs: continue
        if best is None or gap < best[0]: best = (gap, k)
        elif gap == best[0]: best = (gap, None)
    return None if best is None or best[1] is None else best[1]


# ------------------------------------------------------------------ simulation
def attract(g, P, st, table=None, dirs=None):
    sel, conn, pairing, mode, stop, unmatched, paint = P
    sp = split(g, sel, conn, st)
    if sp is None: return None
    an, mv = sp
    if not an or not mv: return None
    h, w = H(g), W(g); bg = bg_of(g)
    anchors = [(c, cs, bb(cs)) for c, cs in an]
    out = [r[:] for r in g]
    plan = []
    for mc, cells in mv:
        k = choose(mc, cells, anchors, pairing, mode, table, dirs)
        plan.append((mc, cells, k))
    if all(k is None for _, _, k in plan) and unmatched == 'keep': return None
    moving = [(mc, cells, k) for mc, cells, k in plan if k is not None or unmatched == 'erase']
    for mc, cells, k in moving:
        for y, x in cells: out[y][x] = bg
    # nearest movers settle first
    order = sorted([p for p in moving if p[2] is not None], key=lambda p: rel(bb(p[1]), anchors[p[2]][2])[2])
    for mc, cells, k in order:
        ac, acells, ab = anchors[k]; aset = set(acells)
        cols = [g[y][x] for y, x in cells]; cur = list(cells)
        dy0, dx0, _ = rel(bb(cur), ab)
        for _ in range(h + w):
            dy, dx, _g = rel(bb(cur), ab)
            if mode == 'orth' or stop == 'into': dy, dx = dy0, dx0
            if stop in ('touch8', 'touch4'):
                if adjacent(cur, aset, N8 if stop == 'touch8' else N4) or (dy == 0 and dx == 0): break
            nxt = [(y + dy, x + dx) for y, x in cur]
            if any(not (0 <= y < h and 0 <= x < w) for y, x in nxt): break
            if stop == 'contact':
                if any(out[y][x] != bg for y, x in nxt): break
            elif stop == 'into':
                if all(p in aset for p in cur) and not all(p in aset for p in nxt): break
            else:
                if any(p in aset for p in nxt): break
            cur = nxt
        if stop == 'into' and not all(p in aset for p in cur): return None
        rc = rim_colour(g, acells, bg) if paint == 'rim' else None
        if paint == 'rim' and rc is None: return None
        for (y, x), c in zip(cur, cols): out[y][x] = rc if rc is not None else c
    return out


# ------------------------------------------------------------------ induction of the table pairing
def induce_table(train, conn):
    """Colour pairs (mover, partner) and step directions observed: a component that reappears translated
    straight along one of 8 directions with a different component 8-adjacent ahead of it."""
    table = {}; dirs = set()
    for p in train:
        i, o = p['input'], p['output']; bg = bg_of(i); h, w = H(i), W(i)
        for ob in objects(i, bg, diag=conn == 8, by_colour=True):
            c = i[ob[0][0]][ob[0][1]]
            if all(o[y][x] == c for y, x in ob): continue
            hit = None
            for dy, dx in N8:
                for k in range(1, max(h, w)):
                    sh = [(y + dy * k, x + dx * k) for y, x in ob]
                    if any(not (0 <= y < h and 0 <= x < w) for y, x in sh): break
                    if all(o[y][x] == c for y, x in sh):
                        ahead = {(y + dy, x + dx) for y, x in sh} - set(sh)
                        pc = {o[y][x] for y, x in ahead if 0 <= y < h and 0 <= x < w and o[y][x] not in (bg,)}
                        if len(pc) == 1:
                            hit = ((dy, dx), next(iter(pc))); break
                if hit: break
            if not hit: continue
            dirs.add(hit[0]); table.setdefault(c, set()).add(hit[1])
    if not table: return None, None
    # symmetric compatibility
    sym = {}
    for a, bs in table.items():
        for b in bs: sym.setdefault(a, set()).add(b); sym.setdefault(b, set()).add(a)
    return sym, dirs


# ------------------------------------------------------------------ family
CONFIGS = []
for sel in ('lines', 'static', 'big'):
    for pairing in ('same', 'any'):
        for mode in ('orth', 'king'):
            for stop in ('touch8', 'touch4', 'contact', 'into'):
                if stop == 'into' and (pairing != 'same' or mode != 'orth'): continue
                if mode == 'king' and stop == 'touch4' and sel == 'lines': continue
                for paint in (('keep', 'rim') if stop == 'into' else ('keep',)):
                    CONFIGS.append((sel, pairing, mode, stop, paint))
for mode in ('orth', 'king'):
    CONFIGS.append(('all', 'table', mode, 'touch8', 'keep'))


def fam_move_toward_anchor(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if any((H(p['input']), W(p['input'])) != (H(p['output']), W(p['output'])) for p in train): return
    if all(p['input'] == p['output'] for p in train): return
    st = static_colours(train) - {bg_of(p['input']) for p in train}
    n = 0; seen_ok = set()
    for conn in (4, 8):
        tabs = {}
        for sel, pairing, mode, stop, paint in CONFIGS:
            if sel == 'static' and not st: continue
            if not all(split(p['input'], sel, conn, st) for p in train[:1]): continue
            table = dirs = None
            if pairing == 'table':
                if conn not in tabs: tabs[conn] = induce_table(train, conn)
                table, dirs = tabs[conn]
                if table is None: continue
            for unmatched in ('keep', 'erase'):
                P = (sel, conn, pairing, mode, stop, unmatched, paint)
                prog = (lambda g, P=P, table=table, dirs=dirs: attract(g, P, st, table, dirs))
                try:
                    r0 = prog(i0)
                except Exception:
                    r0 = None
                if r0 is None or r0 == i0: continue
                if not fits(train, prog): continue
                key = tuple(tuple(map(tuple, prog(p['input']))) for p in train)
                if key in seen_ok: continue
                seen_ok.add(key)
                name = 'toward-anchor[%s,%d,%s,%s,%s,%s%s]' % (sel, conn, pairing, mode, stop, unmatched,
                                                                  ',rim' if paint == 'rim' else '')
                yield (name, 4 + (pairing == 'table') + (paint == 'rim') + (unmatched == 'erase'), prog)
                n += 1
                if n >= 6: return


FAMILIES = (fam_move_toward_anchor,)
