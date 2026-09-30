"""Fable guidance v5 Q3: split the 68 'far cells' tasks (B0-failed design tasks in the four largest change-signature
groups: cells added away from existing objects) by the geometry that generates the new cells.
Training pairs only (test outputs are never read). A task gets every label whose test holds in ALL training pairs:

  reflection  the output, restricted to the bbox of its non-background cells (or the whole grid), is invariant under a
              flip / rotation / transpose that the input is not, and >= 90% of changed cells copy their mirror cell
  periodic    the output (whole grid or content bbox) has a translation period (row, column or diagonal) smaller than
              its extent, and the input is not periodic with that period
  ray/line    every 8-connected component of changed cells is a straight segment (row, column or diagonal) and every
              changed cell lies on a ray cast from an input object cell through background (8 directions)
  copy        every changed component (with colours) equals an input object up to translation / rotation / flip
  fill        every changed cell lies inside the bounding box of some input object group or an enclosed background area
First matching label in this order is the primary class; multi-labels are reported too.
usage: python3 far_split.py far68.json"""
import json, sys
from collections import Counter, deque

B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
N4 = ((0, 1), (1, 0), (0, -1), (-1, 0)); N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def bg_of(g):
    c = Counter(v for r in g for v in r)
    return 0 if 0 in c else c.most_common(1)[0][0]


def comps(cells, nb=N8):
    cells = set(cells); out = []
    while cells:
        s = cells.pop(); q = deque([s]); cc = [s]
        while q:
            a, b = q.popleft()
            for dy, dx in nb:
                p = (a + dy, b + dx)
                if p in cells: cells.remove(p); q.append(p); cc.append(p)
        out.append(cc)
    return out


def content_bbox(g, bg):
    pts = [(y, x) for y, r in enumerate(g) for x, v in enumerate(r) if v != bg]
    if not pts: return None
    ys = [p[0] for p in pts]; xs = [p[1] for p in pts]
    return min(ys), min(xs), max(ys), max(xs)


def sym_maps(y0, x0, y1, x1):
    maps = {'flip_h': lambda y, x: (y, x0 + x1 - x), 'flip_v': lambda y, x: (y0 + y1 - y, x),
            'rot180': lambda y, x: (y0 + y1 - y, x0 + x1 - x)}
    if y1 - y0 == x1 - x0:
        maps['transpose'] = lambda y, x: (y0 + (x - x0), x0 + (y - y0))
        maps['anti'] = lambda y, x: (y0 + (x1 - x), x0 + (y1 - y))
    return maps


def invariant(g, box, f):
    y0, x0, y1, x1 = box; n = ok = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            a, b = f(y, x)
            if not (0 <= a < len(g) and 0 <= b < len(g[0])): return 0.0
            n += 1; ok += g[y][x] == g[a][b]
    return ok / max(n, 1)


def is_reflection(a, b, D):
    bg = bg_of(a)
    boxes = [(0, 0, len(b) - 1, len(b[0]) - 1)]
    cb = content_bbox(b, bg)
    if cb: boxes.append(cb)
    for box in boxes:
        for name, f in sym_maps(*box).items():
            if invariant(b, box, f) < 0.98 or invariant(a, box, f) >= 0.98: continue
            inside = [p for p in D if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]]
            if len(inside) < 0.9 * len(D): continue
            copied = sum(1 for (y, x) in inside if (lambda q: a[q[0]][q[1]] == b[y][x] and a[q[0]][q[1]] != bg)(f(y, x)))
            if copied >= 0.9 * len(inside): return True
    return False


def periodic_ok(g, box, py, px):
    y0, x0, y1, x1 = box
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            yy, xx = y + py, x + px
            if y0 <= yy <= y1 and x0 <= xx <= x1 and g[y][x] != g[yy][xx]: return False
    return True


def is_periodic(a, b, D):
    bg = bg_of(a)
    boxes = [(0, 0, len(b) - 1, len(b[0]) - 1)]
    cb = content_bbox(b, bg)
    if cb: boxes.append(cb)
    for box in boxes:
        H, W = box[2] - box[0] + 1, box[3] - box[1] + 1
        cands = [(py, 0) for py in range(1, H // 2 + 1)] + [(0, px) for px in range(1, W // 2 + 1)] + \
                [(d, d) for d in range(1, min(H, W) // 2 + 1)] + [(d, -d) for d in range(1, min(H, W) // 2 + 1)]
        for py, px in cands:
            if periodic_ok(b, box, py, px) and not periodic_ok(a, box, py, px):
                if len(set(b[y][x] for y in range(box[0], box[2] + 1) for x in range(box[1], box[3] + 1))) > 1:
                    return True
    return False


def is_line(a, b, D):
    bg = bg_of(a); h, w = len(a), len(a[0])
    for cc in comps(D):
        ys = {p[0] for p in cc}; xs = {p[1] for p in cc}; d1 = {p[0] - p[1] for p in cc}; d2 = {p[0] + p[1] for p in cc}
        if not (len(ys) == 1 or len(xs) == 1 or len(d1) == 1 or len(d2) == 1): return False
    reach = set()
    for y in range(h):
        for x in range(w):
            if a[y][x] == bg: continue
            for dy, dx in N8:
                yy, xx = y + dy, x + dx
                while 0 <= yy < h and 0 <= xx < w and a[yy][xx] == bg:
                    reach.add((yy, xx)); yy += dy; xx += dx
    return set(D) <= reach


def norm(cells_col):
    ys = [p[0] for p, _ in cells_col]; xs = [p[1] for p, _ in cells_col]
    return frozenset(((y - min(ys), x - min(xs)), c) for (y, x), c in cells_col)


def variants(shape):
    pts = list(shape); out = set()
    for t in range(8):
        q = []
        for (y, x), c in pts:
            for _ in range(t % 4): y, x = x, -y
            if t >= 4: x = -x
            q.append(((y, x), c))
        out.add(norm(q))
    return out


def is_copy(a, b, D):
    bg = bg_of(a)
    objs = comps([(y, x) for y, r in enumerate(a) for x, v in enumerate(r) if v != bg])
    shapes = set()
    for o in objs:
        shapes |= variants(norm([(p, a[p[0]][p[1]]) for p in o]))
    for cc in comps(D):
        if len(cc) < 2: return False
        s = norm([(p, b[p[0]][p[1]]) for p in cc])
        if s not in shapes:
            # allow the copy to touch/extend an input object: component of changed + adjacent input cells
            return False
    return True


def is_fill(a, b, D):
    bg = bg_of(a); h, w = len(a), len(a[0])
    boxes = []
    for o in comps([(y, x) for y, r in enumerate(a) for x, v in enumerate(r) if v != bg]):
        ys = [p[0] for p in o]; xs = [p[1] for p in o]; boxes.append((min(ys), min(xs), max(ys), max(xs)))
    enclosed = set()
    for cc in comps([(y, x) for y, r in enumerate(a) for x, v in enumerate(r) if v == bg], N4):
        if not any(y in (0, h - 1) or x in (0, w - 1) for y, x in cc): enclosed |= set(cc)
    return all(p in enclosed or any(b0[0] <= p[0] <= b0[2] and b0[1] <= p[1] <= b0[3] for b0 in boxes) for p in D)


TESTS = [('reflection', is_reflection), ('periodic', is_periodic), ('ray/line', is_line), ('copy', is_copy), ('fill', is_fill)]


def main():
    ids = json.load(open(sys.argv[1]))['tasks']
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ev = json.load(open(B + 'arc-agi_evaluation_challenges.json'))
    prim = Counter(); multi = Counter(); rows = []
    for k in ids:
        t = tr.get(k) or ev[k]
        labels = []
        for name, fn in TESTS:
            ok = True
            for p in t['train']:
                a, b = p['input'], p['output']
                D = [(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]]
                if not D: continue
                try:
                    if not fn(a, b, D): ok = False; break
                except Exception:
                    ok = False; break
            if ok: labels.append(name)
        prim[labels[0] if labels else 'other'] += 1
        for l in labels: multi[l] += 1
        rows.append({'task': k, 'labels': labels})
    print(json.dumps({'n': len(ids), 'primary': prim, 'any_label': multi}, indent=1))
    json.dump(rows, open('far68_split.json', 'w'))


if __name__ == '__main__':
    main()
