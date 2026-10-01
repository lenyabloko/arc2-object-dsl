"""Mechanism card halo_ring (worked example by Claude, Sep 30; review page card 'halo_ring').
Implemented literally from the card:
  generator      paint every background cell within distance w of a selected object, in colour c
  stop           at distance w; never paints over non-background cells
  params         w ∈ {1, 2, 3} · metric ∈ {chebyshev, manhattan} · selected ∈ {all objects, objects of one colour}
                 · c ∈ {one colour, the nearest object's own colour}   (colours induced from the training pairs)
  participants   objects = non-background cells; background = the most common colour of the input
  preconditions  same size; every changed cell was background; non-background cells unchanged
  conflicts      where rings meet, the nearest object wins; ties go to the object met first in reading order"""
from collections import Counter, deque

CARD = 'halo_ring'


def _bg(g): return Counter(v for r in g for v in r).most_common(1)[0][0]


def _ring(g, w, metric, sel, colour):
    H, W = len(g), len(g[0]); bg = _bg(g)
    src = [(y, x) for y in range(H) for x in range(W) if g[y][x] != bg and (sel is None or g[y][x] == sel)]
    dist = {p: 0 for p in src}; owner = {p: g[p[0]][p[1]] for p in src}; q = deque(src)
    steps = [(1, 0), (-1, 0), (0, 1), (0, -1)] + ([(1, 1), (1, -1), (-1, 1), (-1, -1)] if metric == 'chebyshev' else [])
    while q:
        y, x = q.popleft(); d = dist[(y, x)]
        if d >= w: continue
        for dy, dx in steps:
            n = (y + dy, x + dx)
            if 0 <= n[0] < H and 0 <= n[1] < W and n not in dist:
                dist[n] = d + 1; owner[n] = owner[(y, x)]; q.append(n)
    out = [r[:] for r in g]
    for (y, x), d in dist.items():
        if d >= 1 and g[y][x] == bg: out[y][x] = owner[(y, x)] if colour is None else colour
    return out


def fam(train):
    for p in train:                                  # preconditions
        a, b = p['input'], p['output']
        if len(a) != len(b) or len(a[0]) != len(b[0]): return
        bg = _bg(a)
        if any(a[y][x] != b[y][x] and a[y][x] != bg for y in range(len(a)) for x in range(len(a[0]))): return
        if all(a[y][x] == b[y][x] for y in range(len(a)) for x in range(len(a[0]))): return
    ch = {b2[y][x] for p in train for a2, b2 in [(p['input'], p['output'])] for y in range(len(a2)) for x in range(len(a2[0])) if a2[y][x] != b2[y][x]}
    colours = [None] + ([next(iter(ch))] if len(ch) == 1 else [])
    present = set.intersection(*[{v for r in p['input'] for v in r} - {_bg(p['input'])} for p in train])
    sels = [None] + sorted(present)
    for w in (1, 2, 3):
        for metric in ('chebyshev', 'manhattan'):
            for sel in sels:
                for c in colours:
                    name = f'halo_ring[w={w},{metric},sel={"all" if sel is None else "colour"},c={"own" if c is None else "induced"}]'
                    yield name, w + (sel is not None) + (c is not None), (lambda g, w=w, m=metric, s=sel, c=c: _ring(g, w, m, s, c))


FAMILIES = [fam]
