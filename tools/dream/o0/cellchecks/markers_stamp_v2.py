"""Len's markers x stamp definition, revised 22:47 EDT Oct 2 (his words, G83):
  "one copy of the unit at every anchor depending only on the color of the marker mapped to the stamp by the legend"
  + "some markers got no stamp because they are used by exemplar to map the mark color to the stamp. Only the marks
     at left top corner of the exemplar indicate place for stamp"
Reading:
  markers   = single-cell objects; exemplars = the multi-cell objects (the legend shapes)
  anchor    = a marker. A marker touching an exemplar (8-neighbour) is a legend mark and gets no stamp, unless it sits at
              the exemplar's top-left corner (then it marks a stamp place)
  unit      = the stamp for each marker colour, the same in all examples (learned from the training outputs)
  placement = the stamp's top-left cell on the marker; cut off at the grid edge
  the rest of the input (exemplars, legend marks) is cleared
Training pairs first; if all reproduce, ONE harness check on the task's test inputs (compared inside, never printed)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import line_check as LC

def comps(g, bg=0):
    h, w = len(g), len(g[0]); seen = set(); out = []
    for y in range(h):
        for x in range(w):
            if g[y][x] == bg or (y, x) in seen: continue
            c = g[y][x]; st = [(y, x)]; seen.add((y, x)); cells = []
            while st:
                a, b = st.pop(); cells.append((a, b))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        n = (a + dy, b + dx)
                        if 0 <= n[0] < h and 0 <= n[1] < w and n not in seen and g[n[0]][n[1]] == c: seen.add(n); st.append(n)
            out.append((c, cells))
    return out

def anchors(g):
    cs = comps(g); ex = [cells for c, cells in cs if len(cells) > 1]
    res = []
    for c, cells in cs:
        if len(cells) != 1: continue
        y, x = cells[0]; legend = False; corner = False
        for e in ex:
            if any(abs(y - a) <= 1 and abs(x - b) <= 1 for a, b in e):
                legend = True
                if (y, x) == (min(a for a, _ in e), min(b for _, b in e)): corner = True
        if not legend or corner: res.append((y, x, c))
    return res

def learn(train, s):
    U = {}
    for q in train:
        g, o = q['input'], q['output']; h, w = len(o), len(o[0])
        for y, x, c in anchors(g):
            if y + s > h or x + s > w: continue
            P = tuple(tuple(o[y + i][x + j] for j in range(s)) for i in range(s))
            if U.setdefault(c, P) != P: return None
    return U

def apply(g, U, s):
    h, w = len(g), len(g[0]); o = [[0] * w for _ in range(h)]
    for y, x, c in anchors(g):
        if c not in U: return None
        for i in range(s):
            for j in range(s):
                if y + i < h and x + j < w and U[c][i][j] != 0: o[y + i][x + j] = U[c][i][j]
    return o

def fit(train):
    for s in range(1, 8):
        U = learn(train, s)
        if U and all(apply(q['input'], U, s) == q['output'] for q in train): return U, s
    return None, None

if __name__ == '__main__':
    k = sys.argv[1] if len(sys.argv) > 1 else 'dfadab01'
    T, S = LC.task(k)
    U, s = fit(T['train'])
    res = {'task': k, 'train_reproduced': U is not None, 'stamp_size': s}
    if U is not None:
        preds = [apply(q['input'], U, s) for q in T['test']]
        res['harness'] = 'exact' if all(p == e for p, e in zip(preds, S)) else ('empty' if any(p is None for p in preds) else 'wrong')
    else:
        # per-pair diagnosis with the best size (training pairs only)
        best = None
        for s2 in range(1, 8):
            U2 = learn(T['train'], s2)
            if U2: n = sum(apply(q['input'], U2, s2) == q['output'] for q in T['train']); best = max(best or (0, 0), (n, s2))
        res['best_pairs'] = best
    print(json.dumps(res))
    json.dump(res, open(os.path.join(HERE, '..', '..', '..', '..', 'results', 'o0', 'cellcheck_markers_stamp_v2_%s.json' % k), 'w'), indent=1)
