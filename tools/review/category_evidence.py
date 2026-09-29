"""Evidence-based category membership (replaces the Codex-detector strengths, which over-fire).

A task carries a category only with verifiable evidence, strongest first:
  exact   a check on the grids of every training pair (e.g. palette: every output is a colour relabelling of its
          input; crop: every output is a sub-grid of its input);
  solver  the task is solved by a primitive whose module implements that kind of mechanism;
  reading the abstract reading's operators / roles / wording name it.
A group carries a category when at least half of its members (all of them for a singleton) carry it; a group
where only a minority carries it is still listed (marked 'minority', ranked last) if one of them has exact or solver
evidence, so the reviewer sees every candidate and can exclude it.
Prior-domain categories (p_*) are left as they are (they are already solver / grounding / operator evidence).

usage: python3 category_evidence.py <review_groups_mview.json> <S0 dir>"""
import json, sys, re, collections
path, S0 = sys.argv[1], sys.argv[2]
D = json.load(open(path)); T = json.load(open(f'{S0}/tasks.json'))
TP = D.get('task_priors', {}); ABS = D.get('abs', {}); ST = D.get('status', {})

def bg(g):
    return collections.Counter(v for r in g for v in r).most_common(1)[0][0]
def dims(g): return (len(g), len(g[0]))
def grid(x): return [[int(ch) for ch in row] for row in x.split('/')] if isinstance(x, str) else x
def pairs(t): return [(grid(a), grid(b)) for a, b in T[t]['train']]
def relabel(a, b):
    if dims(a) != dims(b): return None
    f = {}
    for ra, rb in zip(a, b):
        for x, y in zip(ra, rb):
            if f.setdefault(x, y) != y: return None
    return f
def subgrid(a, b):
    H, W = dims(a); h, w = dims(b)
    if h > H or w > W or h * w >= H * W: return False
    return any(all(a[y + i][x:x + w] == b[i] for i in range(h)) for y in range(H - h + 1) for x in range(W - w + 1))
def comps8(g, col):
    H, W = dims(g); seen = set(); out = []
    for y in range(H):
        for x in range(W):
            if g[y][x] != col or (y, x) in seen: continue
            st = [(y, x)]; seen.add((y, x)); c = [(y, x)]
            while st:
                a0, b0 = st.pop()
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        n = (a0 + dy, b0 + dx)
                        if 0 <= n[0] < H and 0 <= n[1] < W and n not in seen and g[n[0]][n[1]] == col: seen.add(n); c.append(n); st.append(n)
            out.append(c)
    return out
def shape_palette(P):
    """shapes of one colour are each recoloured uniformly with colours that appear elsewhere in the input (a palette);
    at least two different palette colours are used (erasing the palette itself is allowed)."""
    allc = set(); multi = False
    for a, b in P:
        if dims(a) != dims(b): return False
        B = bg(a)
        ch = {(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x] and b[y][x] != B}
        if not ch: return False
        src = {a[y][x] for y, x in ch}
        if len(src) != 1: return False
        m = src.pop(); new = set()
        for c in comps8(a, m):
            if not set(c) & ch: continue
            oc = {b[y][x] for y, x in c}
            if len(oc) != 1: return False
            o = oc.pop()
            if o == m: continue
            if o == B or not any(o in r for r in a): return False
            new.add(o)
        if not new: return False
        multi |= len(new) >= 2; allc |= new
    return multi or len(allc) >= 2
def full_line(g):
    c0 = bg(g)
    rows = any(len(set(r)) == 1 and r[0] != c0 for r in g)
    cols = any(len({g[y][x] for y in range(len(g))}) == 1 and g[0][x] != c0 for x in range(len(g[0])))
    return rows or cols

def exact(t):
    P = pairs(t); ev = {}
    same = all(dims(a) == dims(b) for a, b in P)
    if same:
        fs = [relabel(a, b) for a, b in P]
        if all(f is not None for f in fs) and any(any(k != v for k, v in f.items()) for f in fs):
            U = {}
            glob = all(U.setdefault(k, v) == v for f in fs for k, v in f.items())
            ev['palette'] = 'exact colour relabelling' + (' (one map for all pairs)' if glob else ' (map changes per pair)')
        if 'palette' not in ev and shape_palette(P): ev['palette'] = 'exact: shapes take their colours from an in-grid palette'
        fr = [sum(x != y for ra, rb in zip(a, b) for x, y in zip(ra, rb)) / (len(a) * len(a[0])) for a, b in P]
        if all(0 < f <= 0.2 for f in fr): ev['sparse'] = 'exact: at most %d%% of cells change' % round(100 * max(fr))
    if all(subgrid(a, b) for a, b in P): ev['crop'] = 'exact: every output is a sub-grid of its input'
    def mult(a, b):
        (H, W), (h, w) = dims(a), dims(b)
        return h % H == 0 and w % W == 0 and (h // H) * (w // W) >= 2
    if all(mult(a, b) for a, b in P): ev['scale'] = 'exact: output size is a multiple of the input size'
    if all(full_line(a) for a, _ in P): ev['partition'] = 'exact: every input has a full-length line of one colour'
    return ev

SOLVER = {  # module / program head -> categories
    'recolour_by_colour_map': ['palette', 'key'], 'colour-map': ['palette'], 'colours-by-frequency': ['palette', 'count'],
    'ray_diagonal_from_object': ['path', 'corner'], 'ray_orthogonal_directed': ['path'], 'ray_walker_turn_split': ['path'],
    'connect_aligned_pair': ['path'], 'lines': ['path'], 'connect-same-colour': ['path'], 'rays': ['path'],
    'move_by_vector': ['motion'], 'move_slide_until_contact': ['motion'], 'move_to_position': ['motion'], 'move_toward_anchor': ['motion'],
    'segment_pack_pieces': ['motion', 'cavity'], 'gravity-cells': ['motion'], 'object-gravity': ['motion'], 'slide': ['motion'],
    'move-to-anchor': ['motion'], 'to-position': ['motion'],
    'summarise_ranked_bars': ['count'], 'summarise_count_to_glyph': ['count'], 'summarise_panel_to_pixel': ['count', 'partition'],
    'summarise_concentric_rings': ['count'],
    'stamp_local_stencil': ['template', 'corner'], 'stamp_template_at_markers': ['template'], 'stamp_complete_partial_matches': ['template', 'repair'],
    'stamp_copy_to_congruent_target': ['template'], 'extend_repeat_stamp': ['template'], 'stencil': ['template', 'corner'],
    'extend_periodic_fill': ['repair'], 'symmetry-repair': ['repair'], 'symmetry-patch': ['repair'], 'symmetry-offset-repair': ['repair'],
    'symmetrize': ['repair'], 'fill-enclosed': ['cavity'], 'topo': ['cavity'], 'crop_fit_by_anchor': ['cavity', 'crop'],
    'crop_by_score': ['crop'], 'crop': ['crop'], 'transform_kronecker': ['scale', 'layout'], 'tile': ['scale'], 'upscale': ['scale'],
    'fractal': ['scale', 'layout'], 'combine_boolean_panels': ['partition'], 'panels': ['partition'],
}
READ = {  # category -> (operators, role words, text pattern)
    'palette': (set(), {'palette'}, r'palette|colou?r[ -]?map|relabel|swap colou?rs|colou?r permutation|colou?r substitution'),
    'key': ({'LEGEND', 'LOOKUP', 'DECODE'}, {'key', 'legend', 'glyph', 'palette'}, r'\blegend\b|\bkey\b'),
    'path': ({'RAY', 'PATH', 'CONNECT', 'DRAW'}, {'path', 'line', 'lines', 'ray'}, r'\bray|\bpath\b|polyline'),
    'motion': ({'MOVE', 'SHIFT', 'PACK', 'ALIGN', 'SLIDE', 'GRAVITY'}, {'movers', 'mover'}, r'gravity|slide|\bfall'),
    'count': ({'COUNT', 'MEASURE', 'RANK', 'SUMMARISE'}, set(), r'\bcount|frequenc|histogram'),
    'template': ({'STAMP', 'COPY', 'TEMPLATE', 'TEMPLATE_MATCH'}, {'template', 'templates', 'motif', 'exemplar'}, r'template|exemplar|stamp'),
    'repair': ({'COMPLETE', 'REPAIR', 'DENOISE', 'SYMMETRIZE'}, {'noise'}, r'symmetr|occlu|restore|repair|denois'),
    'cavity': ({'NEST', 'PACK', 'FIT'}, {'hole', 'holes', 'cavity', 'cup', 'cups', 'container'}, r'enclosed|cavity|\bhole|interior|fits? into'),
    'corner': (set(), {'corner', 'corners', 'cross', 'protrusion'}, r'corner|\bcross\b|protrusion'),
    'layout': ({'TILE', 'LAYOUT', 'ASSEMBLE', 'KRON', 'KRONECKER'}, {'lattice', 'slots', 'quadrants', 'tiles', 'panels'}, r'lattice|quadrant|\bslot'),
    'partition': ({'SEGMENT'}, {'separator', 'separators', 'panels', 'bands', 'lanes', 'walls'}, r'separator|\bpanel|\bband'),
    'crop': ({'CROP', 'EXTRACT'}, set(), r'\bcrop'),
    'scale': ({'SCALE', 'TILE', 'UPSCALE', 'KRON'}, set(), r'upscal|scale|\btile'),
    'shapemap': (set(), {'shape', 'shapes'}, r'shape (determines|decides|selects)|by shape'),
    'sparse': (set(), set(), r'(?!)'),
}
def solver(t):
    ev = collections.defaultdict(list)
    heads = [x['module'] for x in TP.get(t, [])]
    s = ST.get(t) or {}
    if s.get('program'): heads.append(re.split(r'[\[:(]', s['program'])[0])
    for h in heads:
        for c in SOLVER.get(h, []): ev[c].append(h)
    return {c: 'solver: ' + ', '.join(sorted(set(v))) for c, v in ev.items()}
def reading(t):
    a = ABS.get(t)
    if not a: return {}
    m = a.get('mechanism') or ''; ops = set(re.findall(r'\b([A-Z][A-Z_]{2,})\b', m))
    roles = {k.strip().lower() for k in (a.get('roles') or {})}; txt = (m + ' ' + ' '.join((a.get('roles') or {}).values()) + ' ' + (a.get('invariant') or '')).lower()
    ev = {}
    for c, (O, R, pat) in READ.items():
        why = []
        if ops & O: why.append('operator ' + '/'.join(sorted(ops & O)))
        if roles & R: why.append('role ' + '/'.join(sorted(roles & R)))
        if re.search(pat, txt): why.append('wording')
        if why: ev[c] = 'reading: ' + ', '.join(why)
    return ev

pop = [m[0] for g in D['groups'] for m in g['members']]
EV = {}
for t in pop:
    e = {}
    for src in (reading(t), solver(t), exact(t)):          # later sources override: exact > solver > reading
        e.update(src)
    EV[t] = e
CATS = [c['id'] for c in D['cats']['categories'] if not c['id'].startswith(('p_', 'r_prior')) and c['parents']]
base = {c: sum(1 for t in pop if c in EV[t]) / len(pop) for c in CATS}
rank = lambda s: 0 if s.startswith('exact') else 1 if s.startswith('solver') else 2
for g in D['groups']:
    ts = [m[0] for m in g['members']]; n = len(ts)
    keep = [c for c in g['cats'] if c['id'].startswith('p_')]
    for c in CATS:
        hit = [t for t in ts if c in EV[t]]
        strong_hits = [t for t in hit if rank(EV[t][c]) < 2]
        major = len(hit) >= (1 if n == 1 else n / 2)
        if not hit or not (major or strong_hits): continue          # minority groups are listed when a member has exact/solver evidence
        kinds = collections.Counter(EV[t][c].split(':')[0].split(' ')[0] for t in hit)
        cov = len(hit) / n; lift = round(cov / base[c], 1) if base[c] else 0
        strong = sum(1 for t in hit if rank(EV[t][c]) < 2)
        keep.append({'axes': [], 'classes': [], 'id': c, 'cov': round(cov, 2), 'lift': lift, 'minority': not major,
                     'score': round(cov * min(3, max(lift, 1)) * (1 + strong / n) * (1 if major else 0.25), 3), 'concepts': [],
                     'evidence': ('' if major else 'minority · ') + '%d of %d members: ' % (len(hit), n) + ', '.join('%s %d' % (k, v) for k, v in kinds.most_common())
                                 + ' · e.g. ' + EV[hit[0]][c]})
    g['cats'] = sorted(keep, key=lambda c: -c['score'])
D['task_cats'] = {t: e for t, e in EV.items() if e}
for c in D['cats']['categories']:
    if c['id'] in CATS:
        ts = [t for t in pop if c['id'] in EV[t]]
        c['n_any'] = len(ts); c['n_strong'] = sum(1 for t in ts if rank(EV[t][c['id']]) < 2)
        c['samples'] = [t for t in ts if EV[t][c['id']].startswith('exact')][:6] or ts[:6]
json.dump(D, open(path, 'w'))
cnt = collections.Counter(c['id'] for g in D['groups'] for c in g['cats'])
print({c: (cnt.get(c, 0), sum(1 for t in pop if c in EV[t]), sum(1 for t in pop if EV[t].get(c, '').startswith('exact'))) for c in CATS})
