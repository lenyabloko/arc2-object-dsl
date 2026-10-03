"""Rows as definitions (Fable v21 A.7 / C.2): a reviewer refinement is a Datalog definition over base relations,
evaluated by tools/datalog/engine.py, never a hand-written Python row.

Base relations built from a grid g with background b (task-free, deterministic):
  cell(Y, X, C)   every non-background cell and its colour
  obj(O, Y, X)    (Y, X) belongs to single-colour 8-connected component O (O = index in reading order)
  off(DY, DX)     the 8 neighbour offsets (constant facts)
A definition file defs/<row>.dl.txt names its output predicate in a '% output: name(Y, X)' header line; the row's value
on g is the set of (Y, X) the predicate derives (None if empty), the same type as a cell-set row of the engine.
usage: from defrows import DEF_ROWS; DEF_ROWS['marks'](g, b)"""
import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'datalog')))
from engine import Program

OFF = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)]


def components(g, b):
    H, W = len(g), len(g[0]); seen = set(); out = []
    for y in range(H):
        for x in range(W):
            if g[y][x] == b or (y, x) in seen: continue
            c = g[y][x]; st = [(y, x)]; seen.add((y, x)); cells = []
            while st:
                p = st.pop(); cells.append(p)
                for dy, dx in OFF:
                    q = (p[0] + dy, p[1] + dx)
                    if 0 <= q[0] < H and 0 <= q[1] < W and q not in seen and g[q[0]][q[1]] == c: seen.add(q); st.append(q)
            out.append(cells)
    return out


def edb(g, b):
    H, W = len(g), len(g[0])
    return {'cell': [(y, x, g[y][x]) for y in range(H) for x in range(W) if g[y][x] != b],
            'obj': [(i, y, x) for i, cs in enumerate(components(g, b)) for y, x in cs],
            'off': OFF}


def load(path):
    text = open(path).read()
    out = re.search(r'%\s*output:\s*([a-z_][a-z0-9_]*)\(', text).group(1)
    prog = Program(text)
    def row(g, b):
        res = prog.run(edb(g, b))
        s = {(t[0], t[1]) for t in res.relations.get(out, [])}
        return s or None
    row.__doc__ = 'definition row from ' + os.path.basename(path); row.source = text
    return row


DEF_ROWS = {os.path.basename(p)[:-7]: load(p) for p in sorted(glob.glob(os.path.join(HERE, 'defs', '*.dl.txt')))}
