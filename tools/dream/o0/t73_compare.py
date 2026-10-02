"""Fable v13/v14 T73 (Oct 2 2026): the same families with the slot-augmented action binder, before vs after.

Before: the latest row per family in results/o0/<dir>_ledger.jsonl.txt (the T65/T68 measurements).
After (policy default): results/o0/<dir>_slots_default_ledger.jsonl.txt (prior_check with SLOTS=default, one harness
check per family version per task).
After (policy mdl): derived, not run: on every task a base program fits, mdl keeps the base program (a slot value is a
charged parameter); on the other tasks mdl and default try the same programs in the same order, so the default
outcome is the mdl outcome there.
Non-source = design tasks that are not the family's members. Distinct tasks are counted over the 19 families of a dir.
new over V32: non-member design tasks in the V32 failure list. new over V35 (components): of those, tasks no existing
O0 ledger (priors2, priors3, priors4, lines, concepts, one-offs, mech) already solves exactly.
usage: python3 t73_compare.py <v32_fail.json> [dirs]"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
R = os.path.join(REPO, 'results/o0')


def latest(path, key='concept'):
    out = {}
    if not os.path.exists(path): return out
    for l in open(path):
        if l.strip():
            r = json.loads(l); out[r.get(key)] = r
    return out


def solved_components():
    s = set()
    for f in ('prior_ledger', 'priors3_ledger', 'priors4_ledger', 'concept_ledger', 'oneoff_ledger', 'mech_ledger', 'line_ledger'):
        for l in open(os.path.join(R, f + '.jsonl.txt')):
            if not l.strip(): continue
            r = json.loads(l)
            for k in ('members_exact', 'exact_other', 'pop_exact_other', 'held_exact_tasks', 'union_exact_other'):
                v = r.get(k)
                if isinstance(v, list): s |= set(v)
            if (r.get('own_exact') is True or r.get('exact') is True) and r.get('task'): s.add(r['task'])
    return s


def stats(rows):
    ex = set(); wr = set(); nex = nwr = mex = 0
    for r in rows.values():
        nex += len(r['exact_other']); nwr += len(r['wrong_other']); mex += len(r['members_exact'])
        ex |= set(r['exact_other']); wr |= set(r['wrong_other'])
    return {'non_source_fits': nex + nwr, 'non_source_exact': nex, 'non_source_wrong': nwr, 'members_exact': mex,
            'distinct_exact_tasks': len(ex), 'distinct_wrong_tasks': len(wr - ex)}, ex


def main():
    v32f = set(json.load(open(sys.argv[1])))
    comp = solved_components()
    out = {}
    for d in (sys.argv[2:] or ['priors3', 'priors4']):
        before = latest(os.path.join(R, '%s_ledger.jsonl.txt' % d))
        after = latest(os.path.join(R, '%s_slots_default_ledger.jsonl.txt' % d))
        fams = sorted(set(before) & set(after))
        b = {k: before[k] for k in fams}; a = {k: after[k] for k in fams}
        m = {}
        for k in fams:                                       # mdl derived
            B = set(b[k]['exact_other']) | set(b[k]['wrong_other']) | set(b[k]['members_exact']) | set(b[k]['members_wrong'])
            m[k] = {'exact_other': sorted(set(b[k]['exact_other']) | (set(a[k]['exact_other']) - B)),
                    'wrong_other': sorted(set(b[k]['wrong_other']) | (set(a[k]['wrong_other']) - B)),
                    'members_exact': sorted(set(b[k]['members_exact']) | (set(a[k]['members_exact']) - B))}
        res = {}
        for tag, rows in (('before', b), ('default', a), ('mdl', m)):
            s, ex = stats(rows)
            s['new_over_v32'] = sorted(ex & v32f)
            s['new_over_v35_components'] = sorted((ex & v32f) - comp) if tag != 'before' else []
            res[tag] = s
        _, exb = stats(b)
        for tag, rows in (('default', a), ('mdl', m)):
            _, ex = stats(rows)
            res[tag]['gained_exact_tasks'] = sorted(ex - exb); res[tag]['lost_exact_tasks'] = sorted(exb - ex)
            progs = {}
            for k in fams:
                for x in set(rows[k]['exact_other']) - set(b[k]['exact_other']): progs.setdefault(k, []).append(x)
            res[tag]['gained_by_family'] = progs
        out[d] = {'families': len(fams), **res}
    json.dump(out, open(os.path.join(R, 't73_result.json'), 'w'), indent=1)
    for d, r in out.items():
        print(d, r['families'])
        for tag in ('before', 'default', 'mdl'):
            s = r[tag]
            print('  %-8s fits %4d exact %4d wrong %4d members_exact %4d distinct_exact %4d new_v32 %2d new_v35c %2d %s' % (
                tag, s['non_source_fits'], s['non_source_exact'], s['non_source_wrong'], s['members_exact'], s['distinct_exact_tasks'],
                len(s['new_over_v32']), len(s['new_over_v35_components']),
                ('gained %d lost %d' % (len(s['gained_exact_tasks']), len(s['lost_exact_tasks']))) if tag != 'before' else ''))


if __name__ == '__main__':
    main()
