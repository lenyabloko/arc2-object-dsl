"""Fable v21 C.4: the fresh Len-blind held-out draw H for T90.
Seen-list = every task Len could have looked at on a surface we can account for:
  review page  - members of every group Len decided on (decisions with reviewer=len, feedback), every task id in his
                 decision / placement / cell / axis / task docs, every task shown in the profile matrix (cells.place)
                 and the need-you list (need2 block, need_ids.json)
  phone page   - his lines, the line expansions, the needs list, the one-off list (claude_solved) and its readings,
                 including the pre-strip copies (Oct 1-2)
  lines        - desktop expansions and the line_* prior docs
  always       - the 14 T86 tasks, dd2401ed, the 4 A/B tasks
H = build-failing design tasks (results/o0/t80b_population.json) not on the seen-list (N2 is outside design).
Fallback stratum H2 (only reported if |H| < 20): design tasks not seen, regardless of build status.
H's ids go to /home/claude/work/sealed/t90_H.json (cloud only, never shipped, never printed); the repo gets counts
and the sha256 of the sorted id list. Usage: python3 t90_draw.py"""
import glob, hashlib, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC
SP = '/tmp/claude-0/-home-claude/47726fdd-2a5c-5c69-a676-871abe4e1a48/scratchpad'
TID = re.compile(r'\b[0-9a-f]{8}\b')
ids = lambda s: set(TID.findall(s))
seen = {}
def add(src, ts):
    for t in ts: seen.setdefault(t, set()).add(src)

page = open(os.path.join(SP, 'sitpage/arc_group_review_full.html')).read()      # built page before the held-out strip
def blk(name):
    tag = '<script id="%s" type="application/json">' % name; a = page.index(tag) + len(tag); return json.loads(page[a:page.index('</script>', a)])
D = blk('data')
groups = {g['id']: [m[0] for m in g.get('members', [])] for g in D['groups'] + D.get('groups_v1', [])}
for f in glob.glob(os.path.join(SP, 'seen/decisions/*.json')) + glob.glob(os.path.join(SP, 'seen/feedback/*.json')):
    d = json.load(open(f)); doc = os.path.basename(f)[:-5]
    if 'feedback' not in f and d.get('reviewer') != 'len': continue
    add('review:doc', ids(json.dumps(d)))
    if doc in groups: add('review:group', groups[doc])
    if doc.startswith('T_'): add('review:task', [doc[2:]])
add('review:matrix', D.get('cells', {}).get('place', {}).keys())
add('review:need2', ids(json.dumps(blk('need2'))))
add('review:need_ids', json.load(open(os.path.join(SP, 'sitpage/need_ids.json'))))
for f in glob.glob(os.path.join(SP, 'seen/expansions/*.json')) + glob.glob(os.path.join(SP, 'seen/priors/line_*.json')):
    add('lines', [os.path.basename(f)[:-5].replace('line_', '')])
for f in glob.glob(os.path.join(SP, 'seen/phone/lines/*.json')): add('phone:lines', [os.path.basename(f)[:-5]])
for f in ['phone/needs_current.json', 'phone/needs_patch.json', 'phone/needs_patch2.json', 'phone/covered_new.json',
          'phone/oneoff_readings.json', 'phone/readings_doc.json', 'mdump/needs/current.json', 'mdump/needs/readings.json']:
    p = os.path.join(SP, f)
    if os.path.exists(p): add('phone:' + os.path.basename(f), ids(open(p).read()))
orig = os.path.join(SP, 'artifact-files/1cc38559-5ed8-44df-81bb-96fc9f60da71/index.html')   # phone page as it was Oct 1-2
m = re.search(r'<script id="meta" type="application/json">(.*?)</script>', open(orig).read(), re.S)
meta = json.loads(m.group(1))
add('phone:need', meta.get('need', {}).keys()); add('phone:oneoff', meta.get('claude_solved', []))
held = set(json.load(open(os.path.join(REPO, 'results/o0/t86_heldout.json'))))
add('always:t86', held); add('always:dd2401ed', ['dd2401ed']); add('always:ab', ['a8c38be5', 'e681b708', '9f8de559', 'f3e62deb'])

design = set(k for k in LC.tr if k not in LC.N2) | set(LC.D99)
fail = set(json.load(open(os.path.join(REPO, 'results/o0/t80b_population.json'))))
assert not (fail - design - held), 'build-failing population outside design'
H = sorted((fail & design) - set(seen) - held)
H2 = sorted(design - set(seen) - held - set(H))
sha = lambda L: hashlib.sha256('\n'.join(L).encode()).hexdigest()
json.dump({'H': H, 'H2_fallback': H2 if len(H) < 20 else [], 'drawn': '2026-10-02 (EDT)'},
          open('/home/claude/work/sealed/t90_H.json', 'w'))
by_src = {}
for t, s in seen.items():
    for x in s: by_src[x] = by_src.get(x, 0) + 1
out = {'seen_total': len(seen), 'seen_in_design': len(set(seen) & design), 'by_source': dict(sorted(by_src.items())),
       'build_failing_design': len(fail & design), 'H': len(H), 'H_arc2': sum(t in LC.D99 for t in H),
       'H_sha256': sha(H), 'H2_fallback': len(H2) if len(H) < 20 else None, 'H2_sha256': sha(H2) if len(H) < 20 else None,
       'sealed_at': 'cloud only: /home/claude/work/sealed/t90_H.json (ids hidden from Len and Fable)'}
json.dump(out, open(os.path.join(REPO, 'results/o0/t90_H_counts.json'), 'w'), indent=1)
json.dump(sorted(seen), open(os.path.join(REPO, 'results/o0/len_seen_list.json'), 'w'))
print(json.dumps(out, indent=1))

# ---- strata and the looser reading (reported to Fable; the strict reading above is the one C.4 asks for)
solved_build = set(D.get('solved', []))
loose_src = {'phone:oneoff', 'phone:oneoff_readings.json', 'phone:readings.json', 'phone:readings_doc.json',
             'phone:covered_new.json', 'phone:needs_patch.json', 'phone:current.json', 'phone:needs_current.json'}
seen_loose = {t for t, s in seen.items() if s - loose_src}
H_loose = sorted((fail & design) - seen_loose - held)
extra = {'H2_arc2': sum(t in LC.D99 for t in H2), 'H2_build_solved': sum(t in solved_build for t in H2),
         'H_loose_note': 'not counting the phone page one-off list and its readings (paginated, 40 per page) as seen',
         'H_loose': len(H_loose), 'H_loose_arc2': sum(t in LC.D99 for t in H_loose), 'H_loose_sha256': sha(H_loose)}
S = json.load(open('/home/claude/work/sealed/t90_H.json')); S['H_loose'] = H_loose
json.dump(S, open('/home/claude/work/sealed/t90_H.json', 'w'))
out.update(extra); json.dump(out, open(os.path.join(REPO, 'results/o0/t90_H_counts.json'), 'w'), indent=1)
print(json.dumps(extra, indent=1))
