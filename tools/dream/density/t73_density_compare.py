"""T73 density check (Fable v14 O5, Oct 2 2026): the slot-augmented binder (SLOTS=default) on ARC-GEN variants vs the
baseline T75 rows, on the same (task, variant, family) cells: the 266 ARC-1 tasks with a baseline fit, variants 0-9.
Design-side instrument only (G74). Output: results/o0/t73_density.json.  usage: python3 t73_density_compare.py"""
import glob, json, os
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
R = os.path.join(REPO, 'results/o0')


def load(pat):
    out = {}
    for p in sorted(glob.glob(os.path.join(R, pat))):
        for l in open(p):
            if l.strip():
                r = json.loads(l); out[(r['task'], r['v'], r['dir'], r['family'])] = r
    return out


def state(r): return 'nofit' if r is None else ('exact' if r['exact'] else 'wrong')


def main():
    after = load('t75_density_slots_default_*.jsonl.txt')
    tasks = set(json.load(open(os.path.join(R, 't75_fitted_tasks.json'))))
    before = {k: r for k, r in load('t75_density_[01].jsonl.txt').items() if k[1] < 10 and k[0] in tasks}
    keys = set(before) | set(after)
    out = {'tasks': len(tasks)}
    for d in ('priors3', 'priors4'):
        for grp in ('non_source', 'member'):
            kk = [k for k in keys if k[2] == d and ((before.get(k) or after.get(k))['member'] == (grp == 'member'))]
            tr = Counter((state(before.get(k)), state(after.get(k))) for k in kk)
            b = Counter(state(before.get(k)) for k in kk); a = Counter(state(after.get(k)) for k in kk)
            slots = Counter(after[k]['program'].split('|')[-1] for k in kk
                            if after.get(k) and '|' in after[k]['program'] and state(before.get(k)) != state(after.get(k)))
            out['%s_%s' % (d, grp)] = {'before': dict(b), 'after': dict(a), 'transitions': {'%s->%s' % t: n for t, n in tr.items() if t[0] != t[1]},
                                       'changed_by_slot': dict(slots)}
    json.dump(out, open(os.path.join(R, 't73_density.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
