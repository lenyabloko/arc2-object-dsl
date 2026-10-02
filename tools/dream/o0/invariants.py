"""Situation invariants for open-slot filling (Fable v16 G79 / v17 P3, G80; Oct 2 2026).

An invariant is a property that holds in EVERY training pair of a task (input -> output). It is induced from the
training pairs only, then used on the test input to accept or reject a candidate prediction (a rollout of a program
that already fits the training pairs). A candidate that fits every pair but breaks an invariant every pair obeys is a
forced simulation: the training pairs left that choice open and the program filled it against the situation.

Invariants (each induced only when it holds on all training pairs; the WHY of the situation it encodes in brackets):
  acts          every output differs from its input                                  [the situation acts]
  size          output size = input size, = k x input size (one k), = input size + d, or one constant size
                                                                                     [tiling: the unit repeats exactly]
  palette       output colours are input colours plus the colours new in training outputs
                                                                                     [no colour from nowhere]
  keeps_ink     same size; every non-background input cell keeps its colour            [figures persist]
  keeps_bg      same size; every background input cell keeps its colour                [only figures change]
  symmetric(s)  every output is invariant under the isometry s (lr, ud, tr, at, r180)  [symmetry completion]
  colours_kept  every input colour also appears in the output                          [no figure vanishes]
Only size relations that hold on all pairs are kept; a candidate passes 'size' if it satisfies any of them.
No task ids; deterministic; pure functions of the grids."""
from collections import Counter

ISOS = ('lr', 'ud', 'tr', 'at', 'r180')


def bg(g): return Counter(v for r in g for v in r).most_common(1)[0][0]


def dims(g): return (len(g), len(g[0])) if isinstance(g, list) and g and isinstance(g[0], list) and g[0] else None


def iso(g, s):
    if s == 'lr': return [r[::-1] for r in g]
    if s == 'ud': return g[::-1]
    if s == 'r180': return [r[::-1] for r in g[::-1]]
    if s == 'tr': return [list(c) for c in zip(*g)]
    if s == 'at': return [list(c) for c in zip(*[r[::-1] for r in g[::-1]])]


def colours(g): return {v for r in g for v in r}


def _size_rules(train):
    rules = []
    ins = [dims(p['input']) for p in train]; outs = [dims(p['output']) for p in train]
    if all(i == o for i, o in zip(ins, outs)): rules.append(('same',))
    ks = {(o[0] / i[0], o[1] / i[1]) for i, o in zip(ins, outs)}
    if len(ks) == 1:
        k = ks.pop()
        if k != (1.0, 1.0): rules.append(('scale', k))
    ds = {(o[0] - i[0], o[1] - i[1]) for i, o in zip(ins, outs)}
    if len(ds) == 1 and ds != {(0, 0)}: rules.append(('add', ds.pop()))
    if len(set(outs)) == 1: rules.append(('const', outs[0]))
    return rules


def _size_ok(rule, i, o):
    if rule[0] == 'same': return i == o
    if rule[0] == 'scale': return abs(o[0] - rule[1][0] * i[0]) < 1e-9 and abs(o[1] - rule[1][1] * i[1]) < 1e-9
    if rule[0] == 'add': return (o[0] - i[0], o[1] - i[1]) == rule[1]
    if rule[0] == 'const': return o == rule[1]
    return False


def induce(train):
    """the invariants that hold on every training pair"""
    inv = {}
    if all(p['input'] != p['output'] for p in train): inv['acts'] = True
    rules = _size_rules(train)
    if rules: inv['size'] = rules
    new = set()
    for p in train: new |= colours(p['output']) - colours(p['input'])
    inv['palette'] = sorted(new)
    same = all(dims(p['input']) == dims(p['output']) for p in train)
    if same:
        def keeps(p, ink):
            b = bg(p['input'])
            return all(a == c for ra, rc in zip(p['input'], p['output']) for a, c in zip(ra, rc) if (a != b) == ink)
        if all(keeps(p, True) for p in train): inv['keeps_ink'] = True
        if all(keeps(p, False) for p in train): inv['keeps_bg'] = True
    sym = [s for s in ISOS if all(dims(p['output']) and (s in ('lr', 'ud', 'r180') or len(p['output']) == len(p['output'][0]))
                                  and iso(p['output'], s) == p['output'] for p in train)]
    # a symmetry already present in every input explains nothing; keep only symmetries the outputs gain
    sym = [s for s in sym if not all(dims(p['input']) and (s in ('lr', 'ud', 'r180') or len(p['input']) == len(p['input'][0]))
                                     and iso(p['input'], s) == p['input'] for p in train)]
    if sym: inv['symmetric'] = sym
    if all(colours(p['input']) <= colours(p['output']) for p in train): inv['colours_kept'] = True
    return inv


def check(inv, x, y):
    """names of the invariants the candidate y (prediction for test input x) breaks; [] = accepted"""
    bad = []
    if not dims(y): return ['grid']
    if inv.get('acts') and y == x: bad.append('acts')
    if 'size' in inv and not any(_size_ok(r, dims(x), dims(y)) for r in inv['size']): bad.append('size')
    if not colours(y) <= colours(x) | set(inv.get('palette', [])): bad.append('palette')
    if dims(x) == dims(y):
        b = bg(x)
        if inv.get('keeps_ink') and any(a != c for ra, rc in zip(x, y) for a, c in zip(ra, rc) if a != b): bad.append('keeps_ink')
        if inv.get('keeps_bg') and any(a != c for ra, rc in zip(x, y) for a, c in zip(ra, rc) if a == b): bad.append('keeps_bg')
    for s in inv.get('symmetric', []):
        if (s in ('tr', 'at') and len(y) != len(y[0])) or iso(y, s) != y: bad.append('symmetric:' + s); break
    if inv.get('colours_kept') and not colours(x) <= colours(y): bad.append('colours_kept')
    return bad
