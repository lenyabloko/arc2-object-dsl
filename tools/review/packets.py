"""Packet queue for the review page (Fable review-page audit item 4, G-D / G-E; test T50).

Groups the failed design tasks by FAILURE SIGNATURE (what is missing), not by output operator, so one decision by the
reviewer covers a packet of tasks. Inputs: the page's embedded `signal` (per failed design task: same size, share of
changed cells on background, C_t, whether V29 / O0 names the changed set exactly), the page's `solved` list, the task
population of the page (tasks.json: training pairs only are read), and the LLM-cleared tasks (G51: D2 source tasks
whose family was exact at its one harness check, cycle 22 and cycle 23 proposal members).

Residual descriptor for same-size tasks with no exact name, from the training pairs only (Δ = changed cells):
  objects  < 10 % of Δ on background;  mixed  10-80 % on background
  fill   changed background cells lie in background regions not 4-connected to the border (enclosed)
  line   changed background cells form 8-connected pieces of >= 2 cells, each on one row, column or diagonal
  halo   changed background cells are 8-adjacent to a non-background input cell
  other  anything else with most changes on background (copies, continued patterns, shapes)
A class needs >= 80 % of a pair's changed background cells; a task takes the class of >= 2/3 of its pairs, else 'mixed'.
Order: |packet| x expected reuse; expected reuse is not measured before cycle A, so it is 1 for every packet (stated
on the page). Test outputs are never read.
usage: python3 packets.py <review.html> <tasks.json> <out.json> [--only <ids.txt>] [--keep-cleared]
  --only: restrict to these task ids (Len, Sep 30 20:40 EDT: "needs you" = the harder ARC-2 tasks, i.e. the design
          ARC-2 tasks V29 fails); --keep-cleared: keep LLM-cleared tasks and mark them (their one-off programs are not
          in the build and do not transfer, cycle 22)."""
import json, re, sys, collections, glob, os

html, tasksf, outf = sys.argv[1:4]
ONLY = set(open(sys.argv[sys.argv.index('--only') + 1]).read().split()) if '--only' in sys.argv else None
KEEP = '--keep-cleared' in sys.argv
s = open(html).read()


def obj(key):
    m = re.search(r'"%s":' % key, s); i = m.end()
    while s[i] == ' ': i += 1
    op = s[i]; cl = {'{': '}', '[': ']'}[op]; d = 0
    for j in range(i, len(s)):
        if s[j] == op: d += 1
        elif s[j] == cl:
            d -= 1
            if d == 0: return json.loads(s[i:j + 1])


SIG = obj('signal'); SOLVED = set(obj('solved'))
T = json.load(open(tasksf))
R = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
cleared = set()
for f in glob.glob(os.path.join(R, 'tools/dream/d2/families_v1/*_family.py')):
    cleared.add(os.path.basename(f)[:8])
cleared -= {'89565ca0', 'f560132c'}                      # cycle-22 harness misses
for f in ('results/cycle23/t42_opus.json', 'results/cycle23/t42_fable.json'):
    for r in json.load(open(os.path.join(R, f))):
        if r.get('role') == 'proposal' and r.get('exact'): cleared.add(r['task'])


def G(sx): return [list(map(int, r)) for r in sx.split('/')]


def descriptor(a, b):
    """Residual shape of one training pair (tolerant: a class needs >= 80 % of the changed background cells)."""
    H, W = len(a), len(a[0])
    cnt = collections.Counter(v for r in a for v in r); bg = cnt.most_common(1)[0][0]
    D = {(y, x) for y in range(H) for x in range(W) if a[y][x] != b[y][x]}
    if not D: return 'none'
    onbg = {p for p in D if a[p[0]][p[1]] == bg}
    if len(onbg) < 0.1 * len(D): return 'objects'
    if len(onbg) < 0.8 * len(D): return 'mixed'
    seen = set(); st = [(y, x) for y in range(H) for x in range(W) if (y in (0, H - 1) or x in (0, W - 1)) and a[y][x] == bg]
    seen.update(st)
    while st:
        y, x = st.pop()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (y + dy, x + dx)
            if 0 <= q[0] < H and 0 <= q[1] < W and q not in seen and a[q[0]][q[1]] == bg: seen.add(q); st.append(q)
    n = len(onbg)
    if sum(p not in seen for p in onbg) >= 0.8 * n: return 'fill'
    left = set(onbg); online = 0
    while left:
        st = [left.pop()]; comp = set(st)
        while st:
            y, x = st.pop()
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    q = (y + dy, x + dx)
                    if q in left: left.discard(q); comp.add(q); st.append(q)
        ys = {p[0] for p in comp}; xs = {p[1] for p in comp}; d1 = {p[0] - p[1] for p in comp}; d2 = {p[0] + p[1] for p in comp}
        if len(comp) >= 2 and (len(ys) == 1 or len(xs) == 1 or len(d1) == 1 or len(d2) == 1): online += len(comp)
    if online >= 0.8 * n: return 'line'
    adj = sum(any(0 <= p[0] + dy < H and 0 <= p[1] + dx < W and a[p[0] + dy][p[1] + dx] != bg
                  for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx) for p in onbg)
    if adj >= 0.8 * n: return 'halo'
    return 'other'


def size_rel(t):
    rel = set()
    for p in t['train']:
        a, b = p[0].split('/'), p[1].split('/')
        ha, wa, hb, wb = len(a), len(a[0]), len(b), len(b[0])
        r = 'smaller' if hb * wb < ha * wa else 'larger' if hb * wb > ha * wa else 'same_area'
        if r == 'smaller':
            sub = any(all(a[y + i][x:x + wb] == b[i] for i in range(hb)) for y in range(ha - hb + 1) for x in range(wa - wb + 1)) if hb <= ha and wb <= wa else False
            r = 'crop' if sub else 'panels' if (hb and wb and ha % hb == 0 and wa % wb == 0) else 'summary'
        rel.add(r)
    return rel.pop() if len(rel) == 1 else 'mixed'


def cname(c): return str(c[1]) if c else ''


rows = {}
excluded = {'solved': 0, 'llm_cleared': 0, 'not_in_page': 0}
for tid, x in SIG.items():
    if tid in SOLVED: excluded['solved'] += 1; continue
    if ONLY is not None and tid not in ONLY: continue
    if tid in cleared and not KEEP: excluded['llm_cleared'] += 1; continue
    if tid not in T: excluded['not_in_page'] += 1; continue
    t = T[tid]
    if not x.get('ss'):
        key = 'size:' + size_rel(t)
    elif x.get('ex'):
        key = 'action:' + cname(x.get('c29'))
    elif x.get('ex0'):
        key = 'o0'
    else:
        ds = collections.Counter(descriptor(G(p[0]), G(p[1])) for p in t['train']); ds.pop('none', None)
        top_d, c = ds.most_common(1)[0] if ds else ('mixed', 0)
        key = 'draw:' + (top_d if c >= (2 * sum(ds.values()) + 2) // 3 else 'mixed')
    rows[tid] = {'key': key, 'ct': x.get('ct'), 'bg': x.get('bg'), 'llm_one_off': tid in cleared}

by = collections.defaultdict(list)
for tid, r in rows.items(): by[r['key']].append(tid)
# small action packets merge into one
for k in [k for k in by if k.startswith('action:') and len(by[k]) < 3]:
    by['action:other'] += by.pop(k)

META = {
 'draw:line': ('Lines and rays drawn on the background', 'mechanism', 'What is drawn along each line: where it starts, which direction, where it stops (border, obstacle, a colour), how wide, which colour?'),
 'draw:halo': ('Rings or outlines around objects', 'mechanism', 'Which objects get a ring, how wide, which colour, and what happens where two rings meet?'),
 'draw:fill': ('Enclosed background regions filled', 'mechanism', 'Which enclosed regions get filled, and with which colour?'),
 'draw:other': ('New shapes on the background (copies, continued patterns)', 'mechanism', 'What is copied or continued, from where to where, and when does it stop?'),
 'draw:objects': ('Objects change; nothing in the vocabulary singles them out', 'concept', 'Which objects change (a concept), and into what (a mechanism)?'),
 'draw:mixed': ('Partly objects, partly background, or pairs disagree', 'split', 'Is this one rule? If so, what is drawn; if not, which tasks belong together?'),
 'o0': ('Named only by the new spatial roles (O₀)', 'mechanism', 'The new spatial roles pick out exactly the changed cells. What is drawn there?'),
 'size:crop': ('Output is a piece cut out of the input', 'mechanism', 'Which piece is cut out: what singles it out (a concept), and are its edges exact?'),
 'size:panels': ('Output is one panel-sized grid (input divides into panels)', 'mechanism', 'How are the panels combined or chosen: overlay, logic (and / or / xor), pick one?'),
 'size:summary': ('Output is a small summary of the input', 'mechanism', 'What is counted or summarised, and how is it laid out in the output?'),
 'size:larger': ('Output larger than the input', 'mechanism', 'How is the output built from the input: tile, scale, extend the canvas, draw around?'),
 'size:same_area': ('Output same area, different shape', 'mechanism', 'How is the output built from the input: transpose, rearrange, re-grid?'),
 'size:mixed': ('Output size varies across pairs', 'mechanism', 'How is the output size decided, and how is it filled?'),
 'action:other': ('Changed objects already named exactly (various names)', 'mechanism', 'The solver already selects exactly the changed objects. What is done to them?'),
}
packets = []
for k, ms in by.items():
    if k.startswith('action:') and k != 'action:other':
        nm = k.split(':', 1)[1]
        title, kind, ask = ('Changed objects already named exactly: ' + nm, 'mechanism', 'The solver already selects exactly the changed objects by "%s". What is done to them?' % nm)
    else:
        title, kind, ask = META.get(k, (k, 'mechanism', 'What is missing?'))
    names = collections.Counter(); roles = collections.Counter(); top = 0
    for t in ms:
        ct = rows[t]['ct']
        if ct and (ct.get('names') or ct.get('roles')):
            for n in ct.get('names', []): names[n] += 1
            for r in ct.get('roles', []): roles[r] += 1
        else: top += 1
    packets.append({'id': re.sub(r'[^a-z0-9]+', '_', k.lower()).strip('_'), 'key': k, 'title': title, 'kind': kind, 'ask': ask,
                    'n': len(ms), 'reuse': 1, 'score': len(ms), 'members': sorted(ms), 'llm_one_off': sorted(t for t in ms if rows[t]['llm_one_off']),
                    'ct': {'top_names': [n for n, _ in names.most_common(5)], 'top_roles': [r for r, _ in roles.most_common(4)], 'n_top': top}})
packets.sort(key=lambda p: (-p['score'], p['id']))
out = {'packets': packets, 'excluded': excluded, 'n_tasks': len(rows), 'n_cleared_list': len(cleared)}
json.dump(out, open(outf, 'w'), indent=0)
print(json.dumps({'n_tasks': len(rows), 'excluded': excluded, 'packets': [(p['id'], p['n'], p['ct']['n_top']) for p in packets]}))
