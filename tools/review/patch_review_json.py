"""Patch the review page data IN PLACE (keeps group ids M001..M170 stable; do not rebuild with build_mview.py,
which renumbers groups when solve status changes).

usage: python3 patch_review_json.py <review_groups_mview.json> <S0 dir> <abs_all.json>
  1. task_labels: every Codex class / rule row of a group is carried by every member task that has it
     (row count "k/n tasks" == tasks carrying the label).
  2. mech_rows + mech: task labels: the mechanism ontology per group — operators parsed from each task's
     abstract reading, the roles its objects play, and the prior domains that solve it.
Then render: html = template.replace('__DATA__', json_text)."""
import json, re, sys, math, collections

path, S0, ABS = sys.argv[1], sys.argv[2], sys.argv[3]
D = json.load(open(path))
tcc = json.load(open(f'{S0}/task_codex_classes.json')); tcr = json.load(open(f'{S0}/task_codex_rules.json'))

# 1. Codex labels consistent with the row counts
for g in D['groups']:
    tl = g.get('task_labels') or {}
    for t in [m[0] for m in g['members']]:
        labs = list(tl.get(t, [])); have = set(labs)
        for r in g.get('codex_classes') or []:
            if r['c'] in tcc.get(t, []) and 'codex:' + r['c'] not in have: labs.append('codex:' + r['c']); have.add('codex:' + r['c'])
        for r in g.get('codex_rules') or []:
            if r['c'] in tcr.get(t, []) and 'rule:' + r['c'] not in have: labs.append('rule:' + r['c']); have.add('rule:' + r['c'])
        if labs: tl[t] = labs
    g['task_labels'] = tl

# 2. Mechanism ontology rows
A = {r['task']: r for r in json.load(open(ABS))}
for t, r in D.get('abs', {}).items(): A.setdefault(t, r)
ops_of = lambda m: set(re.findall(r'\b([A-Z][A-Z_]{2,})\b', m or ''))
tok = collections.Counter()
for r in A.values(): tok.update(ops_of(r.get('mechanism')))
VOC = {o for o, c in tok.items() if c >= 3 and o not in ('RDR', 'CA_', 'BG')}
def role_norm(k):
    k = k.strip().lower().replace(' ', '_')
    return k[:-1] if len(k) > 4 and k.endswith('s') and not k.endswith('ss') else k
PRI = {'topology', 'geometry', 'combinatorics', 'optics', 'mechanics', 'fluids', 'action', 'arithmetic'}
def labels(t):
    r = A.get(t); out = []
    if r:
        out += ['mech:op:' + o for o in sorted(ops_of(r.get('mechanism')) & VOC)]
        out += ['mech:role:' + role_norm(k) for k in sorted((r.get('roles') or {}).keys())]
    doms = {x.get('domain') for x in D.get('task_priors', {}).get(t, [])}
    out += ['mech:prior:' + d for d in sorted(doms & PRI)]
    return list(dict.fromkeys(out))
pop = [m[0] for g in D['groups'] for m in g['members']]
TL = {t: labels(t) for t in pop}
base = collections.Counter(l for t in pop for l in set(TL[t])); N = len(pop)
for g in D['groups']:
    ts = [m[0] for m in g['members']]; n = len(ts)
    cnt = collections.Counter(l for t in ts for l in TL[t])
    thr = 1 if n == 1 else max(2, math.ceil(0.34 * n))
    rows = []
    for l, k in cnt.items():
        if k < thr: continue
        kind = l.split(':')[1]
        rows.append({'c': l[5:], 'show': l.split(':', 2)[2].replace('_', ' '), 'k': k, 'lift': round((k / n) / (base[l] / N), 1),
                     'kind': {'op': 'operator', 'role': 'role', 'prior': 'prior'}[kind]})
    order = {'operator': 0, 'role': 1, 'prior': 2}
    rows.sort(key=lambda r: (order[r['kind']], -r['k'], r['c']))
    g['mech_rows'] = rows
    tl = g.get('task_labels') or {}
    keep = {'mech:' + r['c'] for r in rows}
    for t in ts:
        ml = [l for l in TL[t] if l in keep]
        old = [x for x in tl.get(t, []) if not x.startswith('mech:')]
        if ml or old: tl[t] = ml + old
    g['task_labels'] = tl
D['mech_vocab'] = sorted(VOC)
json.dump(D, open(path, 'w'))
print('patched', path)
