"""Situation categories (decision CATEGORIES-ARE-SITUATIONS, Len 13:45 EDT Oct 2; Fable v17/v17a; G82).

A category is a situation: the six-slot template <WHO, WHAT, WHERE, HOW, UNTIL, WHY> in the closed vocabulary of
template_vocab.json, with its open role marked and a mandatory WHY (the invariant). The four seed situations are
v17's. Membership is alignment (P2, template_align.py), never a vote:
  aligned: roles bound k of 5   the situation's WHAT holds on every training pair, its invariant holds on every
                                training pair, and k of WHO/WHAT/WHERE/HOW/UNTIL have a value kept across all pairs
  invariant failed              the WHAT holds on every pair but the invariant fails on at least one
  not attempted                 the situation's WHAT does not hold on every pair
Training pairs only (design tasks; test outputs are never read). Output: results/o0/situation_membership.json.
usage: python3 situations.py"""
import json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import template_align as TA

SITUATIONS = [
    {"id": "S_tiling", "name": "tiling / output size",
     "template": {"WHO": "whole_grid", "WHAT": "tile_scale", "WHERE": "whole_output", "HOW": "same_shape", "UNTIL": "count",
                  "WHY": "the unit repeats exactly: every block of the output is the unit, a recoloured unit, or empty"},
     "open": "output size (= unit x count, the count read from the test input)", "invariant": "tile_blocks"},
    {"id": "S_stamping", "name": "stamping / anchor",
     "template": {"WHO": "marker", "WHAT": "copy_stamp", "WHERE": "at_marker", "HOW": "same_shape", "UNTIL": "once",
                  "WHY": "one stamp per marker, at the same offset from each marker"},
     "open": "anchor (every marker of the test input, with the learned offset)", "invariant": "one_per_marker"},
    {"id": "S_projection", "name": "projection / extent",
     "template": {"WHO": "marker", "WHAT": "draw_line", "WHERE": "on_line_of_sight", "HOW": "own_colour", "UNTIL": "obstacle",
                  "WHY": "the line continues until it meets something: an object or the border"},
     "open": "extent (to the test input's obstacle, not the training length)", "invariant": "ends_at_stop"},
    {"id": "S_symmetry", "name": "symmetry / fill",
     "template": {"WHO": "all_objects", "WHAT": "mirror_complete", "WHERE": "mirror_position", "HOW": "own_colour", "UNTIL": "once",
                  "WHY": "distance to the axis is preserved: the output is symmetric about the detected axis"},
     "open": "fill (the reflection across the axis detected on the test input)", "invariant": "output_symmetric"},
]


def _bg(g): return Counter(v for r in g for v in r).most_common(1)[0][0]


def inv_tile_blocks(p):
    i, o = p['input'], p['output']; H, W = len(i), len(i[0]); h, w = len(o), len(o[0])
    if h % H or w % W or (h == H and w == W): return False
    b = _bg(i); mask = [[v != b for v in r] for r in i]; bo = _bg(o)
    full = [[True] * W for _ in range(H)]; empty = [[False] * W for _ in range(H)]
    inv = [[not v for v in r] for r in mask]
    for R in range(0, h, H):
        for C in range(0, w, W):
            m = [[o[R + y][C + x] != bo for x in range(W)] for y in range(H)]
            if m not in (mask, full, empty, inv): return False
    return True


def inv_one_per_marker(p, cand):
    i, o = p['input'], p['output']; b = _bg(i)
    objs = TA.objects(i, b)
    added = {(r, c) for r in range(len(i)) for c in range(len(i[0])) if i[r][c] == b and o[r][c] != b}
    ac = TA.comps(added)
    small = [ob for ob in objs if len(ob['cells']) <= 2]
    cols = Counter(ob['colour'] for ob in objs)
    rare = [ob for ob in objs if cols[ob['colour']] == min(cols.values())] if cols else []
    return bool(ac) and (len(ac) == len(small) or len(ac) == len(rare))


def inv_ends_at_stop(p, cand): return bool(cand['UNTIL'] & {'border', 'obstacle'})


def inv_output_symmetric(p, cand): return bool(TA.symmetric(p['output']))


def membership(train):
    per = [TA.pair_candidates(p) for p in train]
    kept = {s: set.intersection(*[c[s] for c in per]) for s in ('WHO', 'WHAT', 'WHERE', 'HOW', 'UNTIL')}
    k = sum(1 for s in kept if kept[s])
    out = {}
    for S in SITUATIONS:
        if S['template']['WHAT'] not in kept['WHAT']: out[S['id']] = 'not attempted'; continue
        ok = True
        for p, c in zip(train, per):
            f = S['invariant']
            r = inv_tile_blocks(p) if f == 'tile_blocks' else inv_one_per_marker(p, c) if f == 'one_per_marker' else \
                inv_ends_at_stop(p, c) if f == 'ends_at_stop' else inv_output_symmetric(p, c)
            if not r: ok = False; break
        out[S['id']] = ('aligned: roles bound %d of 5' % k) if ok else 'invariant failed'
    return out


def main():
    import line_check as LC
    keys = [x for x in sorted(LC.tr) if x not in LC.N2] + sorted(LC.D99)
    mem = {}
    for t in keys:
        T = LC.task(t)
        if T is None: continue
        m = membership(T[0]['train'])                                  # training pairs only
        m = {s: v for s, v in m.items() if v != 'not attempted'}
        if m: mem[t] = m
    cnt = {S['id']: Counter(v.split(':')[0] for t in mem for s, v in mem[t].items() if s == S['id']) for S in SITUATIONS}
    json.dump({'situations': SITUATIONS, 'membership': mem, 'counts': {k: dict(v) for k, v in cnt.items()}},
              open(os.path.join(REPO, 'results/o0/situation_membership.json'), 'w'), indent=1)
    print(json.dumps({k: dict(v) for k, v in cnt.items()}))


if __name__ == '__main__':
    main()
