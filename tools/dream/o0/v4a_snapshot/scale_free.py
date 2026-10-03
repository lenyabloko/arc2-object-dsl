"""Engine v4: the scale-free situation schema (Fable v21 B.1 / C.1, v21a B; Len, Oct 2 23:00 EDT: "a scale free schema
that repeats for each sub-node").

Grammar:  S ::= HOW(arg*) ;  arg ::= row | const | S'@scale ;  scale in grid > panel > object > part
Depth <= 2, one recursion per situation, only in a slot that takes cells: the column's input (the grid it acts on).

Two nested forms, both a depth-1 situation S' filling the input slot one scale down (or at the same scale):
  seq   HOW(input := S'@grid)    the column acts on S'(X) instead of X                     (T89: a second step)
  map   paste(input := S'@s)     s in {panel, object, part}: S' is applied to every sub-node of X at scale s (the
                                 sub-grid in the node's box) and the results are pasted back in place; cells outside
                                 every node box never change (the parent's WHY). A node where S' does not apply (a row
                                 absent, WHY failing) is left as it is.
WHY at every level (v21a B.2, G86): S' must satisfy its own WHY on its sub-problem (apply_raw returns None otherwise)
and the parent's WHY is checked on the parent's result. Scale typing (v21a B.3): a child's scale is never above its
parent slot's scale (the input slot is at grid scale; every child scale qualifies, none is above).
Binding: map children are bound on the changed sub-problems of the training pairs and accepted only if the pasted result
reproduces every training output; seq children are the depth-1 candidates (bound on the training pairs as if alone) that
make progress (more output cells right than the identity, not already exact), in top-down order (v21a B.1: R of the
child's key over design first, i.e. specialisations of admitted elements before fresh ones; then progress), at most
K_INNER of them; the outer column is then fitted exactly on (S'(x), y).
Order of fitted situations (prediction order): depth 1 before depth 2 (G2: a depth-2 program pays two atoms), then
R(child) + R(parent) descending, then the canonical key. Canonical key (v21a B.4): arguments sorted.
Training pairs only; nothing here reads a test output.
usage: python3 scale_free.py fit <task id>...      (prints the fitted situations, depth 1 and depth 2)"""
import itertools, json, os, signal, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import situation_engine as SE

SCALES = ('panel', 'object', 'part')
K_INNER = 8
MAX_K = 40
R_PATH = os.path.join(REPO, 'results/o0/v4_R_depth1.json')
try: R = json.load(open(R_PATH))['R']                 # R(key) over design at depth 1 (admitted = R >= 1)
except Exception: R = {}


# ------------------------------------------------------------------ sub-nodes
def boxes(g, scale):
    b = SE.bgc(g)
    if scale == 'panel':
        P = SE.r_panels(g, b); return list(P[1]) if P else []
    if scale == 'object': cs = SE.multis(g, b)                                  # 8-connected, colours ignored
    elif scale == 'part': cs = [o['cells'] for o in SE.objects(g, b)]           # single-colour components
    else: return []
    out = sorted({SE.bbox(c) for c in cs if len(c) > 1})
    return out


def paste_apply(S1, g, scale):
    """apply S1 to every sub-node box of g at the scale and paste the results back; None if no node changes, if two
    nodes disagree on a cell, or if a node result changes size"""
    bx = boxes(g, scale)
    if not bx: return None
    out = SE.copy(g); painted = {}; changed = False
    for box in bx:
        sub = SE.crop(g, box); r = SE.apply_raw(S1, sub)
        if r is None: continue
        if SE.dims(r) != SE.dims(sub): return None
        y0, x0 = box[0], box[1]
        for y in range(len(sub)):
            for x in range(len(sub[0])):
                if r[y][x] != sub[y][x]:
                    if painted.setdefault((y0 + y, x0 + x), r[y][x]) != r[y][x]: return None
                    out[y0 + y][x0 + x] = r[y][x]; changed = True
    return out if changed else None


# ------------------------------------------------------------------ nested situations
def key(S):
    if S.get('form') == 'map': return 'paste(input:=%s@%s)' % (SE.situation_key(S['sub']), S['scale'])
    if S.get('form') == 'seq': return '%s[input:=%s@grid]' % (SE.situation_key(S['outer']), SE.situation_key(S['sub']))
    return SE.situation_key(S)


def depth(S): return 2 if S.get('form') in ('map', 'seq') else 1


def apply_raw(S, g):
    try:
        if S.get('form') == 'map': return paste_apply(S['sub'], g, S['scale'])
        if S.get('form') == 'seq':
            x = SE.apply_raw(S['sub'], g)
            return None if x is None else SE.apply_raw(S['outer'], x)
        return SE.apply_raw(S, g)
    except RecursionError: return None


def apply(S, g):
    out = apply_raw(S, g)
    return out if out is not None and out != g else None


def candidates(train, columns=None):
    """every (column, row assignment, bound constants) on these pairs, the first MAX_K constants per assignment"""
    for how, C in SE.COLUMNS.items():
        if columns and how not in columns: continue
        names = [a for a, _ in C['args']]
        for vals in itertools.product(*[d for _, d in C['args']]):
            A = dict(zip(names, vals))
            try: Ks = C['bind'](train, A)
            except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError, RecursionError): Ks = []
            if how in SE.REPEATABLE: Ks = Ks + [dict(K, repeat=1) for K in Ks]
            for K in Ks[:MAX_K]:
                yield {'how': how, 'args': A, 'consts': K}


def fit_map(train, scale, limit=3):
    if not SE.same_dims(train): return []
    subs = []
    for p in train:
        g, o = p['input'], p['output']; bx = boxes(g, scale)
        if not bx: return []
        inside = set()
        for y0, x0, y1, x1 in bx: inside |= {(y, x) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)}
        if any(g[y][x] != o[y][x] for y in range(len(g)) for x in range(len(g[0])) if (y, x) not in inside): return []
        subs += [{'input': SE.crop(g, b), 'output': SE.crop(o, b)} for b in bx]
    changed = [q for q in subs if q['input'] != q['output']]
    if not changed: return []
    out = []; seen = set()
    for S1 in candidates(changed):
        k1 = SE.situation_key(S1)
        if k1 in seen: continue
        if all(paste_apply(S1, p['input'], scale) == p['output'] for p in train):
            seen.add(k1); out.append({'form': 'map', 'scale': scale, 'sub': S1})
            if len(out) >= limit: break
    return out


def score(preds, train):
    tot = ok = 0
    for p, q in zip(preds, train):
        o = q['output']; n = len(o) * len(o[0]); tot += n
        if p is None or SE.dims(p) != SE.dims(o): continue
        ok += sum(p[y][x] == o[y][x] for y in range(len(o)) for x in range(len(o[0])))
    return ok / tot if tot else 0.0


def fit_seq(train, limit=3):
    base = score([q['input'] for q in train], train)
    inner = []; seen = set()
    for S1 in candidates(train):
        k1 = SE.situation_key(S1)
        preds = [SE.apply_raw(S1, q['input']) for q in train]
        if any(p is None for p in preds) or all(p == q['input'] for p, q in zip(preds, train)): continue
        if all(p == q['output'] for p, q in zip(preds, train)): continue          # already depth 1
        sc = score(preds, train)
        same = all(SE.dims(p) == SE.dims(q['output']) for p, q in zip(preds, train))
        if same and sc <= base: continue                                         # no progress
        sig = json.dumps(preds)
        if sig in seen: continue
        seen.add(sig); inner.append((-R.get(k1, 0), -sc, k1, S1, preds))
    inner.sort(key=lambda t: t[:3])
    out = []
    for _, _, k1, S1, preds in inner[:K_INNER]:
        for S2 in SE.fit([{'input': p, 'output': q['output']} for p, q in zip(preds, train)]):
            out.append({'form': 'seq', 'sub': S1, 'outer': S2})
            if len(out) >= limit: return out
    return out


def order_key(S):
    if S.get('form') == 'map': r = R.get(SE.situation_key(S['sub']), 0)
    elif S.get('form') == 'seq': r = R.get(SE.situation_key(S['sub']), 0) + R.get(SE.situation_key(S['outer']), 0)
    else: r = R.get(SE.situation_key(S), 0)
    return (depth(S), -r, key(S))


def fit_guarded(train, max_depth=2, budget=None):
    """fit() with G5 (B.4): drop programs below MU2; programs below MU1 go after every program that clears it"""
    F = fit(train, max_depth=max_depth, budget=budget); E = evidence(train)
    m = [(S, margin(S, train, E)) for S in F]
    return [S for S, x in m if x >= MU1] + [S for S, x in m if MU2 <= x < MU1]


def fit(train, max_depth=2, budget=None):
    """depth-1 fits (situation_engine.fit), then depth-2 (map at panel / object / part, seq at grid) when max_depth = 2;
    all of them, in prediction order. Depth-2 search runs whether or not depth 1 fitted (the design counts report
    both); prediction uses depth 1 first."""
    t0 = time.time()
    out = list(SE.fit(train))
    if max_depth >= 2:
        for sc in SCALES:
            if budget and time.time() - t0 > budget: break
            out += fit_map(train, sc)
        if not budget or time.time() - t0 <= budget: out += fit_seq(train)
    return sorted(out, key=order_key)


# ------------------------------------------------------------------ B.4: G2 code length and the G5 chance-fit margin
# Fixed before the second control run (Oct 3 00:25 EDT), from claude/meta_learning_bounds_guards.md Q2.2 and the
# routeA_t24 precedent; no parameter is chosen from the control's results.
#   individuals of a same-size pair: the input's objects (8-connected single-colour components) plus the change sites
#   (8-connected components of the changed cells); d_i = change sites, a = 9 (the colour a site takes).
#   size-changing pair: every output object is a produced individual, N_i = d_i = output objects, a = 9.
#   E = sum_i [log2 C(N_i, d_i) + d_i log2 a];   L(P) = 12 bits per atom (column) + 4 bits per row-valued argument (G2)
#   |H_<=(P)| = the number of situations the fitter enumerates at depth <= depth(P) (counted variant of the theorem)
#   margin' = E - log2 |H_<=(P)|.  G5: slot 1 needs margin' >= MU1 = 4, slot 2 margin' >= MU2 = 0; below MU2 a
#   program is not proposed. Depth-1 programs are under the same rule (they always were in G5).
import math
MU1, MU2 = 4.0, 0.0


def evidence(train):
    E = 0.0
    for p in train:
        g, o = p['input'], p['output']; b = SE.bgc(g)
        if SE.dims(g) == SE.dims(o):
            ch = {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] != o[y][x]}
            d = len(SE.comps(ch)) if ch else 0
            n = len(SE.objects(g, b)) + d
        else:
            n = d = len(SE.objects(o, SE.bgc(o)))
        if d: E += math.log2(math.comb(n, d)) + d * math.log2(9)
    return E


def n_depth1():
    return sum(math.prod(len(dm) for _, dm in C['args']) for C in SE.COLUMNS.values())


def code_len(S):
    atoms = [S['sub'], S['outer']] if S.get('form') == 'seq' else ([S['sub']] if S.get('form') == 'map' else [S])
    return sum(12 + 4 * sum(v in SE.ROWS for v in T['args'].values()) for T in atoms)


def margin(S, train, E=None):
    E = evidence(train) if E is None else E
    n1 = n_depth1(); H = n1 if depth(S) == 1 else n1 + K_INNER * n1 + len(SCALES) * n1
    return E - math.log2(H)


# ------------------------------------------------------------------ parts (B.3)
SOURCE = {'row:marks': 'dfadab01', 'arg:place=topleft': 'dfadab01', 'arg:rest=cleared': 'dfadab01'}   # Len's parts


def parts(S):
    """the parts a fitted situation uses: column, rows, constant kinds, argument values, sub-situation, scale"""
    P = set()
    def flat(T):
        P.add('column:' + T['how'])
        for k, v in T['args'].items():
            if v in SE.ROWS: P.add('row:' + v)
            elif v == 'train': P.add('const:%s.%s' % (T['how'], k))
            else: P.add('arg:%s=%s' % (k, v))
        if T['consts'].get('repeat'): P.add('arg:repeat')
    if S.get('form') == 'map': flat(S['sub']); P.add('scale:' + S['scale']); P.add('sub:' + SE.situation_key(S['sub']))
    elif S.get('form') == 'seq': flat(S['sub']); flat(S['outer']); P.add('scale:grid'); P.add('sub:' + SE.situation_key(S['sub']))
    else: flat(S)
    return P


if __name__ == '__main__':
    import line_check as LC
    if sys.argv[1] == 'fit':
        for k in sys.argv[2:]:
            t = LC.task(k)
            if t is None: print(k, 'not readable'); continue
            s = time.time(); F = fit(t[0]['train'])
            print(k, round(time.time() - s, 1), 's', [key(S) for S in F])
