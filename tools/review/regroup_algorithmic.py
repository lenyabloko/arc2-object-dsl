"""Algorithmic regrouping of the review page data, in place, with stable group ids.

Principle (the original purpose of the grouping): a group is the set of tasks covered by ONE DSL primitive.
So group membership is computed, not reviewed:
  * a task that is solved by a group primitive (a module fam_<key> bound to mechanism group <key>) belongs to that
    group; tasks sitting in a solved-by-program-family group, a residual group or 'unplaced' move there;
  * extra primitive bindings (new primitives written for an existing group) are listed in BIND;
  * multi-group modules (one file implementing two groups) never move a task between two mechanism groups;
  * the medoid of a reviewed mechanism group never moves (reviewer rule: a group cannot lose its medoid);
    solved-by-program-family and residual groups dissolve freely (a new medoid is picked when needed);
  * groups that become empty are dropped (their ids are retired, never reused).
Every per-group field that depends on membership is recomputed (n, members, categories, Codex rows, counts, needs);
run patch_review_json.py, apply_op_domains.py and apply_solved_names.py afterwards (labels, mechanism rows, links).  Reviewer decisions (misfits, hints) are inputs for the next cycle, not applied here.

usage: python3 regroup_algorithmic.py <review_groups_mview.json> <S0 dir> <extra_solves.json>
  extra_solves.json: {"module": [task ids solved exactly]} for primitives not yet in the page data."""
import json, sys, math, collections, re
path, S0, EXTRA = sys.argv[1], sys.argv[2], sys.argv[3]
D = json.load(open(path))
tcc = json.load(open(f'{S0}/task_codex_classes.json')); tcr = json.load(open(f'{S0}/task_codex_rules.json'))
CS = json.load(open(f'{S0}/cat_strength.json'))
BIND = {'fill_bg_windows': 'fill.largest_empty'}                      # new primitive -> mechanism group key
MULTI = {'connect_aligned_pair', 'recolour_by_colour_map', 'combine_boolean_panels', 'transform_objects', 'recolour_objects'}
DNAME = D['prior_names']
G = {g['id']: g for g in D['groups']}
key2id = {g['key']: g['id'] for g in D['groups']}
mod2key = {g['key'].replace('.', '_'): g['key'] for g in D['groups'] if g['kind'] == 'mechanism'}
mod2key.update(BIND)
TP = {t: [dict(x) for x in v] for t, v in D.get('task_priors', {}).items()}
extra = json.load(open(EXTRA))
for m, ts in extra.items():
    for t in ts:
        if not any(x['module'] == m for x in TP.get(t, [])):
            TP.setdefault(t, []).append({'module': m, 'domain': 'group primitive', 'prog': m})
cur = {m[0]: g['id'] for g in D['groups'] for m in g['members']}
TL0 = {t: [x for x in labs if not x.startswith('mech:')] for g in D['groups'] for t, labs in (g.get('task_labels') or {}).items()}
V1 = {t: g['id'] for g in D.get('groups_v1', []) for t in D.get('members', {}).get(g['id'], [])}
medoids = {g['medoid'] for g in D['groups'] if g['kind'] == 'mechanism'}   # reviewed mechanism groups keep their medoid
moves = {}
for t, xs in TP.items():
    if t not in cur or t in medoids: continue
    src = G[cur[t]]
    cands = [(x['module'], mod2key[x['module']]) for x in xs if x['module'] in mod2key]
    if not cands: continue
    keys = {k for _, k in cands}
    if src['key'] in keys: continue
    if src['kind'] == 'mechanism':
        cands = [(m, k) for m, k in cands if m not in MULTI]              # only unambiguous primitives cross mechanism groups
        if not cands: continue
    m, k = max(cands, key=lambda c: (G[key2id[c[1]]]['n'], c[1]))
    moves[t] = (src['id'], key2id[k], m)
# ---- apply
place = D.get('placement', {})
for t, (a, b, m) in moves.items():
    ent = next(x for x in G[a]['members'] if x[0] == t)
    G[a]['members'].remove(ent); G[b]['members'].append(ent)
    place[t] = {'from': a, 'to': b, 'by': 'primitive', 'module': m}
    D['group_of'][t] = G[b]['key']
D['placement'] = place
pop = [m[0] for g in D['groups'] for m in g['members']]
N = len(pop)
cls_freq = collections.Counter(c for t in pop for c in set(tcc.get(t, [])))
rule_freq = collections.Counter(c for t in pop for c in set(tcr.get(t, [])))
cat_base = {c: sum(1 for t in pop if CS.get(t, {}).get(c, 0) >= 2) / N for c in next(iter(CS.values()))}
status = D.get('status', {}); comp = set(D.get('composed', []))
for m, ts in extra.items(): comp |= {t for t in ts if t not in status}
D['composed'] = sorted(comp)
ABS = D.get('abs', {})
touched = {a for a, _, _ in moves.values()} | {b for _, b, _ in moves.values()}
for gid in touched:
    g = G[gid]; ts = [m[0] for m in g['members']]; n = len(ts); g['n'] = n
    if not n: continue
    D['members'][gid] = ts
    dcount = collections.Counter(d for t in ts for d in {x['domain'] for x in TP.get(t, [])} if d in DNAME)
    cats = []
    for d in DNAME:
        cov = dcount[d] / n; gd = d in g.get('grounded', [])
        if cov >= 0.3 or gd:
            fams = collections.Counter(x['prog'].split('[')[0].split('(')[0] for t in ts for x in TP.get(t, []) if x['domain'] == d)
            cats.append({'axes': [], 'classes': [], 'id': 'p_' + d, 'cov': round(max(cov, 0.5 if gd else 0), 2), 'lift': round(max(cov, 0.5) * 4, 1),
                         'score': round(max(cov, 0.5 if gd else 0) * 2, 3), 'concepts': [[f, c] for f, c in fams.most_common(4)],
                         'evidence': 'solved by this prior on %d of %d members' % (dcount[d], n) + (' · grounded' if gd else '')})
    for c, base in cat_base.items():
        k = sum(1 for t in ts if CS.get(t, {}).get(c, 0) >= 2)
        if n and k / n >= 0.5 and base > 0:
            cats.append({'axes': [], 'classes': [], 'id': c, 'cov': round(k / n, 2), 'lift': round((k / n) / base, 1), 'score': round((k / n) * min(3, (k / n) / base), 3), 'concepts': []})
    g['cats'] = sorted(cats, key=lambda c: -c['score'])
    ccl = collections.Counter(c for t in ts for c in set(tcc.get(t, [])))
    g['codex_classes'] = [{'c': c, 'k': k, 'lift': round((k / n) / (cls_freq[c] / N), 1), 'kind': 'class', 'chain': []} for c, k in ccl.most_common()
                          if k >= max(2, math.ceil(0.4 * n)) and (k / n) / (cls_freq[c] / N) >= 1.8][:8] if n > 1 else []
    crl = collections.Counter(c for t in ts for c in set(tcr.get(t, [])))
    g['codex_rules'] = [{'c': c, 'k': k, 'lift': round((k / n) / (rule_freq[c] / N), 1)} for c, k in crl.most_common() if k >= max(1, math.ceil(0.3 * n))][:6]
    g['codex_rules_cov'] = sum(1 for t in ts if tcr.get(t))
    g['n_solved'] = sum(t in status for t in ts); g['n_comp'] = sum(t in comp for t in ts)
    g['priors'] = [[DNAME[d], c] for d, c in dcount.most_common()]
    g['task_labels'] = {t: TL0[t] for t in ts if TL0.get(t)}          # Codex / mechanism rows are re-added by patch_review_json.py
    def needs(t):
        if t in status or t in comp: return None
        a = ABS.get(t)
        if not a: return 'no reading yet'
        r = []
        if g['key'].endswith('.residual'): r.append('no generic mechanism found')
        c = a.get('confidence')
        if isinstance(c, (int, float)) and c < 0.6: r.append('uncertain reading (%.2f)' % c)
        if a.get('abstraction_level') in (1, '1'): r.append('could not abstract')
        return '; '.join(r) or None
    g['needs'] = {t: needs(t) for t in ts if needs(t)}; g['n_needs'] = len(g['needs'])
    if g.get('reasons'): g['reasons'] = {t: v for t, v in g['reasons'].items() if t in ts}
    g['v1'] = [list(x) for x in collections.Counter(V1.get(t) for t in ts if V1.get(t)).most_common()]
for g in D['groups']:                                            # a dissolving solved/residual group gets a new medoid
    ts = [m[0] for m in g['members']]
    if ts and g['medoid'] not in ts:
        g['medoid'] = sorted(ts, key=lambda t: (-((ABS.get(t) or {}).get('confidence') or 0), t))[0]
        ent = next(m for m in g['members'] if m[0] == g['medoid']); g['med_pairs'] = [[ent[1], ent[2]]]
        g['members'].sort(key=lambda m: m[0] != g['medoid'])
dropped = [g['id'] for g in D['groups'] if not g['members']]
D['groups'] = [g for g in D['groups'] if g['members']]
for gid in dropped: D['members'].pop(gid, None)
vm = D.get('view_meta', {}); vm['n_groups'] = len(D['groups']); vm['regroup'] = {'moves': len(moves), 'dropped': dropped}
json.dump(D, open(path, 'w'))
print('moves', len(moves), collections.Counter((G[a]['kind'], G[b]['kind']) for a, b, _ in moves.values()), 'dropped', dropped)
