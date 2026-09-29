"""Plain mechanism names for solved-by-program-family groups + same-mechanism links (solved_names.json).
usage: python3 apply_solved_names.py <review json> <solved_names.json>"""
import json, sys
p, q = sys.argv[1], sys.argv[2]
D = json.load(open(p)); S = json.load(open(q)); byfam = {}
for g in D['groups']:
    if g['kind'] != 'solved': continue
    f = g.get('family') or (g['name'][len('solved · '):] if g['name'].startswith('solved · ') else g['key'].split('.', 1)[-1])
    g['family'] = f; byfam[f] = g['id']
    if f in S['names']: g['name'] = 'solved · ' + S['names'][f] + ' [' + f + ']'
for g in D['groups']: g.pop('same_as', None)
for cl in S['same_mechanism']:
    ids = [byfam[f] for f in cl if f in byfam]
    for g in D['groups']:
        if g['id'] in ids and len(ids) > 1: g['same_as'] = [i for i in ids if i != g['id']]
for a, b in S.get('same_mechanism_groups', []):          # explicit mechanism-group pairs
    for g in D['groups']:
        if g['id'] == a: g.setdefault('same_as', []).append(b)
        if g['id'] == b: g.setdefault('same_as', []).append(a)
json.dump(D, open(p, 'w')); print('solved groups named', len(byfam))
