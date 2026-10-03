"""Check Len's submitted cell definitions (Oct 3 UTC) on the training pairs of the tasks he placed in each cell.
Engine v2 frozen (4b4a22370d20) where the definition maps onto an engine column; otherwise a direct reading of his
words (G83), stated in the output. Training pairs only; no test output is read."""
import json, sys, itertools
sys.path.insert(0, '/home/claude/work/public_repo/tools/dream/o0')
import line_check as LC
import situation_engine_v2_frozen as SE

def train(k): return LC.task(k)[0]['train']
def ok(f, T): 
    res = []
    for q in T:
        try: p = f(q['input'])
        except Exception as e: p = None
        res.append(p == q['output'])
    return res

out = {}
# 1. markers x extend: source markers, colour own, stop border or obstacle (his WHY: until it collides with other objects or the grid edge)
ext = ['0f63c0b9', '142ca369', '1bfc4729', '21f83797', '29c11459', '5c0a986e', '623ea044', '6e19193c']
C = SE.COLUMNS['extend']
for k in ext:
    T = train(k); best = None
    for stop in ['obstacle', 'border']:
        A = {'stop': stop, 'source': 'markers', 'colour': 'own'}
        try: Ks = C['bind'](T, A)
        except Exception: Ks = []
        for K in Ks[:40]:
            S = {'how': 'extend', 'args': A, 'consts': K}
            r = ok(lambda g: SE.apply_raw(S, g), T)
            if best is None or sum(r) > sum(best[1]): best = (stop, r)
    out['markers|extend', k] = {'pairs_reproduced': '%d/%d' % (sum(best[1]), len(T)) if best else '0/%d (nothing to bind)' % len(T),
                                 'stop': best[0] if best else None}

# 2. key x tile (his words): the whole input is the tile; output = input-size x input-size blocks; the tile is copied only
#    into the block row (or column) marked by the input's one-colour line; other blocks background; own colours.
def key_tile(g):
    h, w = len(g), len(g[0]); bg = 0
    rows = [y for y in range(h) if len(set(g[y])) == 1]
    cols = [x for x in range(w) if len({g[y][x] for y in range(h)}) == 1]
    o = [[bg] * (w * w) for _ in range(h * h)]
    if len(rows) == 1 and not cols: blocks = [(rows[0], j) for j in range(w)]
    elif len(cols) == 1 and not rows: blocks = [(i, cols[0]) for i in range(h)]
    else: return None
    for bi, bj in blocks:
        for y in range(h):
            for x in range(w): o[bi * h + y][bj * w + x] = g[y][x]
    return o
T = train('15696249'); r = ok(key_tile, T)
out['key|tile', '15696249'] = {'pairs_reproduced': '%d/%d' % (sum(r), len(T)), 'reading': 'direct reading of the definition'}

# 3. fg x disperse (no WHY; how = in all 4 directions): each foreground cell moves away from the centre of the
#    foreground, diagonally, until the grid edge.
def disperse(g):
    h, w = len(g), len(g[0]); bg = SE.bgc(g)
    cells = [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg]
    if not cells: return None
    cy = sum(y for y, _ in cells) / len(cells); cx = sum(x for _, x in cells) / len(cells)
    o = [[bg] * w for _ in range(h)]
    for y, x in cells:
        dy = (y > cy) - (y < cy); dx = (x > cx) - (x < cx)
        yy, xx = y, x
        while 0 <= yy + dy < h and 0 <= xx + dx < w and (dy or dx): yy += dy; xx += dx
        o[yy][xx] = g[y][x]
    return o
T = train('66e6c45b'); r = ok(disperse, T)
out['fg|disperse', '66e6c45b'] = {'pairs_reproduced': '%d/%d' % (sum(r), len(T)), 'reading': 'direct reading: each cell moves outward, diagonally, to the edge'}
solved = set(json.load(open('/home/claude/work/public_repo/tools/review/../../results/o0/c2_column_fit.json')).get('x', [])) if False else None
for k, v in out.items(): print(k, v)
json.dump({'%s %s' % k: v for k, v in out.items()}, open('/tmp/claude-0/-home-claude/47726fdd-2a5c-5c69-a676-871abe4e1a48/scratchpad/cellcheck/check3.json', 'w'), indent=1)
