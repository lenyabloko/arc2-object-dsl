"""Operator -> prior-domain links of the mechanism ontology (op_domains.json): add prior categories to groups whose
majority operators map to a domain (idempotent).  usage: python3 apply_op_domains.py <review json> <op_domains.json>"""
import json, sys
p, q = sys.argv[1], sys.argv[2]
D = json.load(open(p)); OPD = json.load(open(q)); D['op_domains'] = OPD; PN = D['prior_names']; added = 0
for g in D['groups']:
    n = g['n']; acc = {}
    for r in g.get('mech_rows') or []:
        if r['kind'] != 'operator' or r['k'] / n < 0.5: continue
        op = r['c'].split(':', 1)[1]
        for d in OPD.get(op, []): acc.setdefault(d, []).append((op, r['k']))
    for d, ops in acc.items():
        cid = 'p_' + d; ex = [c for c in g['cats'] if c['id'] == cid]
        tag = 'operator ' + ', '.join(o for o, _ in ops)
        if ex:
            if 'operator' not in ex[0].get('evidence', ''): ex[0]['evidence'] = (ex[0].get('evidence', '') + ' · ' if ex[0].get('evidence') else '') + tag
            continue
        k = max(k for _, k in ops); cov = round(k / n, 2)
        g['cats'].append({'axes': [], 'classes': [], 'id': cid, 'cov': cov, 'lift': round(cov * 4, 1), 'score': round(cov * 1.5, 3),
                          'concepts': [['operator ' + o, kk] for o, kk in ops],
                          'evidence': 'via ' + tag + ' in %d of %d members (mechanism ontology: operator ⊑ %s)' % (k, n, PN[d])}); added += 1
    g['cats'].sort(key=lambda c: -c['score'])
json.dump(D, open(p, 'w')); print('op-domain category links added', added)
