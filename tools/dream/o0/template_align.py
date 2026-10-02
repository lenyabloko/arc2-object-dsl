"""Fable v17 P2 (Oct 2 2026): template aligner. From a task's TRAINING PAIRS ONLY, induce the six-slot template
<WHO, WHAT, WHERE, HOW, UNTIL, WHY> in the closed vocabulary of template_vocab.json (WHY is left empty here: it is
what P3's invariants encode).

Per pair, every slot gets the candidate values whose definition holds on that pair (definitions below; objects are
8-connected single-colour components on the background). A value is kept only if it holds on every pair; among kept
values the one with the highest weight wins, relational values weighing 2 and object-level values 1 (Fable v17: a
fixed 2:1, not learned), ties broken by the vocabulary order. A slot with no kept value is OPEN.

WHAT (same-size pairs from the changed cells; size-changing pairs from the size relation):
  tile_scale (out = k x in, k integer > 1, or out made of copies of in), extract (out is a sub-grid of in, up to a
  recolour), summarise (other smaller outputs), recolour (>= 80 % of changed cells were ink and stay ink),
  delete (>= 80 % ink -> background), mirror_complete (out gains a symmetry in does not have), draw_line (added cells
  form straight 1-wide segments of length >= 2), fill (added cells are background enclosed in the input), move (an input
  object's shape appears elsewhere in the output and its old cells are cleared), copy_stamp (added components are
  translated copies of an input object's shape), decorate (added cells are 8-adjacent to input objects), complete_shape
  (added cells attach to input objects, otherwise)
WHO (participants = input objects that changed or touch / align with added cells): same_colour_pair*, exemplar*,
  frame_or_container*, separator*, odd_object*, marker, largest_object, smallest_object, all_objects, line_segment,
  whole_grid                                                                                      (* relational)
WHERE (relation of the changed cells to the participants): between*, inside*, adjacent*, on_line_of_sight*, aligned*,
  mirror_position*, at_marker*, toward*, in_place*, across_separator*, whole_output*, corner, centre
UNTIL (draw_line / move only): border (every added segment ends on the grid edge), obstacle (ends next to input ink),
  contact (a moved object ends touching another object); otherwise once
HOW: own_colour, other_object_colour, new_colour, background, same_shape (copies keep the shape)
No task ids; deterministic. usage: python3 template_align.py  (runs T83 against results/o0/t83_parsed.json)"""
import json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
VOC = json.load(open(os.path.join(HERE, 'template_vocab.json')))
REL = {'same_colour_pair', 'exemplar', 'frame_or_container', 'separator', 'odd_object', 'between', 'inside', 'adjacent',
       'on_line_of_sight', 'aligned', 'mirror_position', 'at_marker', 'toward', 'in_place', 'across_separator', 'whole_output'}
N8 = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]


def bg(g): return Counter(v for r in g for v in r).most_common(1)[0][0]


def objects(g, b):
    H, W = len(g), len(g[0]); seen = set(); out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == b or (r, c) in seen: continue
            col = g[r][c]; st = [(r, c)]; seen.add((r, c)); cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in N8:
                    n = (y + dy, x + dx)
                    if 0 <= n[0] < H and 0 <= n[1] < W and n not in seen and g[n[0]][n[1]] == col:
                        seen.add(n); st.append(n)
            out.append({'colour': col, 'cells': set(cells)})
    return out


def shape(cells):
    r0 = min(r for r, _ in cells); c0 = min(c for _, c in cells)
    return frozenset((r - r0, c - c0) for r, c in cells)


def comps(cells):
    cells = set(cells); out = []
    while cells:
        s = cells.pop(); st = [s]; c = {s}
        while st:
            y, x = st.pop()
            for dy, dx in N8:
                n = (y + dy, x + dx)
                if n in cells: cells.discard(n); c.add(n); st.append(n)
        out.append(c)
    return out


def straight(c):
    if len(c) < 2: return False
    rs = {r for r, _ in c}; cs = {k for _, k in c}
    if len(rs) == 1 or len(cs) == 1: return True
    return len({r - k for r, k in c}) == 1 or len({r + k for r, k in c}) == 1


def symmetric(g):
    s = set()
    if [r[::-1] for r in g] == g: s.add('lr')
    if g[::-1] == g: s.add('ud')
    if len(g) == len(g[0]) and [list(x) for x in zip(*g)] == g: s.add('tr')
    return s


def subgrid(o, i):
    H, W = len(i), len(i[0]); h, w = len(o), len(o[0])
    if h > H or w > W: return False
    for r in range(H - h + 1):
        for c in range(W - w + 1):
            m = {}
            ok = True
            for y in range(h):
                for x in range(w):
                    a, b = i[r + y][c + x], o[y][x]
                    if m.setdefault(a, b) != b: ok = False; break
                if not ok: break
            if ok: return True
    return False


def pair_candidates(p):
    i, o = p['input'], p['output']; b = bg(i)
    H, W = len(i), len(i[0]); h, w = len(o), len(o[0])
    cand = {k: set() for k in ('WHO', 'WHAT', 'WHERE', 'HOW', 'UNTIL')}
    objs = objects(i, b)
    multi = [ob for ob in comps({(r, c) for r in range(H) for c in range(W) if i[r][c] != b})
             if len({i[r][c] for r, c in ob}) > 1]
    sep = any(len(set(row)) == 1 and row[0] != b for row in i) or any(len({i[r][c] for r in range(H)}) == 1 and i[0][c] != b for c in range(W))
    if sep: cand['WHO'].add('separator')
    if (h, w) != (H, W):
        cand['WHERE'].add('whole_output'); cand['UNTIL'].add('once')
        if h % H == 0 and w % W == 0 and (h > H or w > W): cand['WHAT'].add('tile_scale'); cand['WHO'].add('whole_grid')
        elif h <= H and w <= W:
            if subgrid(o, i): cand['WHAT'].add('extract'); cand['WHO'].add('region')
            else: cand['WHAT'].add('summarise'); cand['WHO'].add('all_objects')
        return cand
    C = {(r, c) for r in range(H) for c in range(W) if i[r][c] != o[r][c]}
    if not C: return cand
    added = {x for x in C if i[x[0]][x[1]] == b}; removed = {x for x in C if o[x[0]][x[1]] == b}; rec = C - added - removed
    n = len(C)
    # WHAT
    if len(rec) >= 0.8 * n: cand['WHAT'].add('recolour')
    if len(removed) >= 0.8 * n: cand['WHAT'].add('delete')
    if symmetric(o) - symmetric(i): cand['WHAT'].add('mirror_complete')
    ac = comps(added)
    if added:
        if all(straight(c) for c in ac): cand['WHAT'].add('draw_line')
        reach = set(); st = [(r, c) for r in range(H) for c in range(W) if (r in (0, H - 1) or c in (0, W - 1)) and i[r][c] == b]
        reach |= set(st)
        while st:
            y, x = st.pop()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                m = (y + dy, x + dx)
                if 0 <= m[0] < H and 0 <= m[1] < W and m not in reach and i[m[0]][m[1]] == b: reach.add(m); st.append(m)
        if added and not (added & reach): cand['WHAT'].add('fill')
        shapes = {shape(ob['cells']) for ob in objs}
        if all(shape(c) in shapes for c in ac): cand['WHAT'].add('copy_stamp')
        ink = {x for ob in objs for x in ob['cells']}
        near = {(y + dy, x + dx) for y, x in ink for dy, dx in N8}
        if added <= near:
            cand['WHAT'].add('decorate' if all(len(c) <= 2 * max(1, len(ink)) for c in ac) else 'complete_shape')
            cand['WHAT'].add('complete_shape')
        if removed and added:
            oo = objects(o, b)
            if any(shape(a['cells']) == shape(x['cells']) and a['cells'] != x['cells'] for a in objs for x in oo): cand['WHAT'].add('move')
    # participants
    touched = [ob for ob in objs if ob['cells'] & C or any((y + dy, x + dx) in C for y, x in ob['cells'] for dy, dx in N8)]
    part = touched or objs
    if part:
        if len(part) == len(objs) and len(objs) > 1: cand['WHO'].add('all_objects')
        if all(len(ob['cells']) == 1 for ob in part): cand['WHO'].add('marker')
        sizes = [len(ob['cells']) for ob in objs]
        if len(part) == 1 and len(objs) > 1:
            s = len(part[0]['cells'])
            if s == max(sizes) and sizes.count(s) == 1: cand['WHO'].add('largest_object')
            if s == min(sizes) and sizes.count(s) == 1: cand['WHO'].add('smallest_object')
            cols = Counter(ob['colour'] for ob in objs)
            if cols[part[0]['colour']] == 1: cand['WHO'].add('odd_object')
        cc = Counter(ob['colour'] for ob in part)
        if len(part) >= 2 and all(v >= 2 for v in cc.values()): cand['WHO'].add('same_colour_pair')
        if all(straight(ob['cells']) for ob in part): cand['WHO'].add('line_segment')
    if multi and added and any(shape(c) in {shape(m) for m in multi} for c in ac): cand['WHO'].add('exemplar')
    boxes = [(min(r for r, _ in ob['cells']), min(c for _, c in ob['cells']), max(r for r, _ in ob['cells']), max(c for _, c in ob['cells'])) for ob in objs]
    def inside_any(x): return any(bx[0] < x[0] < bx[2] and bx[1] < x[1] < bx[3] for bx in boxes)
    if C and all(inside_any(x) for x in C): cand['WHO'].add('frame_or_container'); cand['WHERE'].add('inside')
    # WHERE
    if rec and not added and not removed: cand['WHERE'].add('in_place')
    ink = {x for ob in objs for x in ob['cells']}
    if added and all(any((y + dy, x + dx) in ink for dy, dx in N8) for c in ac for (y, x) in [min(c)]): cand['WHERE'].add('adjacent')
    if 'mirror_complete' in cand['WHAT']: cand['WHERE'].add('mirror_position')
    if added:
        rows = {r for ob in part for r, _ in ob['cells']}; cols = {c for ob in part for _, c in ob['cells']}
        if all(r in rows or c in cols for r, c in added): cand['WHERE'].add('on_line_of_sight'); cand['WHERE'].add('aligned')
        def between(x):
            for a in part:
                for z in part:
                    if a is z: continue
                    ra = {r for r, _ in a['cells']}; rz = {r for r, _ in z['cells']}
                    ca = {c for _, c in a['cells']}; cz = {c for _, c in z['cells']}
                    if x[0] in ra & rz and min(min(ca), min(cz)) < x[1] < max(max(ca), max(cz)): return True
                    if x[1] in ca & cz and min(min(ra), min(rz)) < x[0] < max(max(ra), max(rz)): return True
            return False
        if all(between(x) for x in added): cand['WHERE'].add('between')
        markers = [ob for ob in objs if len(ob['cells']) == 1]
        if markers and all(any(abs(y - m0) <= 2 and abs(x - m1) <= 2 for m in markers for (m0, m1) in m['cells']) for c in ac for (y, x) in c):
            cand['WHERE'].add('at_marker')
    if sep and C: cand['WHERE'].add('across_separator')
    # UNTIL
    if 'draw_line' in cand['WHAT'] and ac:
        def ends(c):
            return [x for x in c if sum((x[0] + dy, x[1] + dx) in c for dy, dx in N8) <= 1]
        if all(any(e[0] in (0, H - 1) or e[1] in (0, W - 1) for e in ends(c)) for c in ac): cand['UNTIL'].add('border')
        if all(any(any((e[0] + dy, e[1] + dx) in ink for dy, dx in N8) for e in ends(c)) for c in ac): cand['UNTIL'].add('obstacle')
    if 'move' in cand['WHAT']: cand['UNTIL'].add('contact')
    if not cand['UNTIL']: cand['UNTIL'].add('once')
    # HOW
    newc = {o[y][x] for y, x in C} - {v for r in i for v in r}
    if C and newc and all(o[y][x] in newc for y, x in C): cand['HOW'].add('new_colour')
    if removed and len(removed) == n: cand['HOW'].add('background')
    if added and part and all(o[y][x] in {ob['colour'] for ob in part} for y, x in added):
        if len({ob['colour'] for ob in part}) == 1: cand['HOW'].add('own_colour')
        else: cand['HOW'].add('other_object_colour')
    if rec and all(o[y][x] in {ob['colour'] for ob in objs} for y, x in rec): cand['HOW'].add('other_object_colour')
    if 'copy_stamp' in cand['WHAT']: cand['HOW'].add('same_shape')
    return cand


def align(train):
    per = [pair_candidates(p) for p in train]
    out = {}
    for slot in ('WHO', 'WHAT', 'WHERE', 'HOW', 'UNTIL'):
        kept = set.intersection(*[c[slot] for c in per]) if per else set()
        if not kept: out[slot] = 'OPEN'; continue
        order = list(VOC[slot])
        out[slot] = max(kept, key=lambda v: (2 if v in REL else 1, -order.index(v) if v in order else -99))
        out[slot + '_all'] = sorted(kept)
    out['WHY'] = ''
    return out


def main():
    sys.path.insert(0, HERE)
    import line_check as LC
    parsed = json.load(open(os.path.join(REPO, 'results/o0/t83_parsed.json')))
    rows = []
    for p in parsed:
        t = LC.task(p['card'])
        if t is None: continue
        a = align(t[0]['train'])                                       # training pairs only
        r = {'card': p['card'], 'parse_failure': p['parse_failure']}
        for s in ('WHO', 'WHAT', 'WHERE', 'UNTIL'):
            pv, av = p[s], a[s]
            r[s] = {'parsed': pv, 'aligned': av, 'kept': a.get(s + '_all', []),
                    'strict': pv == av, 'lenient': pv == 'unspecified' or pv == av, 'contained': pv == 'unspecified' or pv in a.get(s + '_all', [])}
        for mode in ('strict', 'lenient', 'contained'):
            r[mode] = (not p['parse_failure']) and all(r[s][mode] for s in ('WHO', 'WHAT', 'WHERE', 'UNTIL'))
        rows.append(r)
    summ = {'lines': len(rows), 'parsed': sum(not r['parse_failure'] for r in rows)}
    for mode in ('strict', 'lenient', 'contained'):
        summ['agree_all4_' + mode] = sum(r[mode] for r in rows)
        summ['agree_per_slot_' + mode] = {s: sum(r[s][mode] for r in rows if not r['parse_failure']) for s in ('WHO', 'WHAT', 'WHERE', 'UNTIL')}
    json.dump({'summary': summ, 'rows': rows}, open(os.path.join(REPO, 'results/o0/t83_result.json'), 'w'), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
