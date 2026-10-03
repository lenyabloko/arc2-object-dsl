"""Part-level reuse of distilled rows (G85 / G89, Fable v23 C.5 acceptance): a distilled row enters the shared
hierarchy only when fits on >= 2 non-source dev tasks need it. For every new row that a fitting reading used, the
same frame (column and the reading's other argument values; open slots stay open) is tried with that row on every
other dev task (393 = design - T86 14 - sealed). A hit = an exact training fit. 'needed' = the hit task has no
depth-1 fit without distilled rows (results/o0/v4_design_depth1.json) and no fitting reading of its own in the batch.
usage: python3 distill_reuse.py <batch.json> <shard> <nshards>  -> results/o0/distill_b<batch>_reuse_<shard>.json"""
import glob, json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); O0 = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(O0, '..', '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, O0)
import distill_check as DC
import overnight_check as OC, line_check as LC
import itertools

B = json.load(open(sys.argv[1])); shard, nsh = int(sys.argv[2]), int(sys.argv[3])
rows = {}
for f in sorted(glob.glob(os.path.join(REPO, f"results/o0/distill_b{B['batch']}_g*.json"))): rows.update(json.load(open(f))['tasks'])
# the (task, sample) readings that fitted with a new row, and their frames
items = []
for gi, grp in enumerate(B['groups']):
    for f in sorted(glob.glob(os.path.join(HERE, 'readings', f'g{gi:02d}_s*.json'))):
        s = int(re.search(r'_s(\d+)\.json$', f).group(1))
        for R in json.load(open(f)):
            t = R.get('task')
            if t not in rows: continue
            rec = next((r for r in rows[t]['readings'] if r['sample'] == s), None)
            if not rec or not rec.get('n_fits') or not rec.get('new_rows'): continue
            items.append((t, s, R))
items = items[shard::nsh]
dev = OC.dev_keys()
d1 = json.load(open(os.path.join(REPO, 'results/o0/v4_design_depth1.json'))).get('tasks', {})
own_fit = {t for t, v in rows.items() if v['n_fitting'] > 0}
trains = {k: LC.task(k)[0]['train'] for k in dev}
out = []; t0 = time.time()
for t, s, R in items:
    fr = R.get('frame') or {}
    if fr.get('form') not in ('map', 'seq') and fr.get('how') not in DC.COLS:
        col, _ = DC.norm_verb(fr.get('how') if fr.get('how') and fr.get('how') != 'other' else R.get('verb'))
        if col: fr = dict(fr, how=col)
    names, _ = DC.register_rows(t, s, R.get('new_rows'))
    spec, opens, _ = DC.spec_of(fr, names)
    if spec is None: continue
    hits = []; ti = time.time(); capped = False
    for k in dev:
        if k == t: continue
        if time.time() - ti > 150: capped = True; break               # per-item cap (reported)
        for vals in list(itertools.product(*[d for _, d in opens]))[:16] if opens else [()]:
            sp = spec
            for (p, _), v in zip(opens, vals): sp = DC.setp(sp, p, v)
            r = DC.timed(DC.fit_spec, 3, sp, trains[k])
            if r != 'timeout' and r[0]: hits.append(k); break
    out.append({'source': t, 'sample': s, 'rows': list(names.values()), 'frame': DC.frame_key(spec) if 'how' in spec or 'form' in spec else str(spec),
                'n_open': len(opens), 'capped': capped, 'hits': hits, 'needed': [k for k in hits if not d1.get(k) and k not in own_fit]})
    json.dump({'done': len(out), 'of': len(items), 'secs': round(time.time() - t0), 'items': out},
              open(os.path.join(REPO, f"results/o0/distill_b{B['batch']}_reuse_{shard}.json"), 'w'), indent=1)
print('shard', shard, 'items', len(out), 'with hits', sum(bool(o['hits']) for o in out), 'with needed', sum(bool(o['needed']) for o in out))
