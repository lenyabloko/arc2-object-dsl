"""T42 (leave-members-out): each group family on its held-out members (training fit first, then ONE test check) and a
single test check on its proposal members. Appends every test check to the harness ledger (once per family version)."""
import importlib.util, json, signal, time
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
tr = json.load(open(B + 'arc-agi_training_challenges.json')); so = json.load(open(B + 'arc-agi_training_solutions.json'))
LED = '/home/claude/work/public_repo/results/cycle21/harness_ledger.jsonl.txt'
done = {(d.get('family_file'), d['task']) for d in map(json.loads, open(LED)) if 'family_file' in d}
class TO(BaseException): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
plan = json.load(open('plan.json')); rows = []
for g, sp in sorted(plan.items()):
    ff = f'fable/{g}_family.py'
    s = importlib.util.spec_from_file_location(g, ff); F = importlib.util.module_from_spec(s); s.loader.exec_module(F)
    for role, ms in (('proposal', sp['proposal']), ('held_out', sp['held_out'])):
        for m in ms:
            t = tr[m]; r = {'group': g, 'task': m, 'role': role, 'family_file': ff}
            try:
                signal.alarm(60); progs = []
                for fam in F.FAMILIES:
                    for name, cost, fn in fam(t['train']):
                        if all(fn(p['input']) == p['output'] for p in t['train']): progs.append((name, fn))
                signal.alarm(0)
            except TO: progs = []; r['timeout'] = True
            except Exception as e: signal.alarm(0); progs = []; r['err'] = repr(e)[:60]
            r['fits_train'] = bool(progs); r['n_progs'] = len(progs)
            if progs and (ff, m) not in done:
                try:
                    signal.alarm(60)
                    att = [[fn(q['input']) for q in t['test']] for _, fn in progs[:2]]
                    signal.alarm(0)
                    r['exact'] = any(all(a[i] == so[m][i] for i in range(len(so[m]))) for a in att)
                except BaseException as e: signal.alarm(0); r['exact'] = False
                r['program'] = progs[0][0][:120]
                with open(LED, 'a') as f:
                    f.write(json.dumps({'task': m, 'program': r['program'], 'family_file': 'cycle23/' + ff, 'fits_train': True,
                                        'exact': r['exact'], 'role': role, 'check': 'single harness test check (pass@2), group family v1 (fable proposer)',
                                        'time': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())}) + '\n')
            rows.append(r); print(json.dumps(r), flush=True)
json.dump(rows, open('t42_results_fable.json', 'w'), indent=0)
P = [r for r in rows if r['role'] == 'proposal']; H = [r for r in rows if r['role'] == 'held_out']
print('proposal: fit', sum(r['fits_train'] for r in P), '/', len(P), 'exact', sum(r.get('exact', False) for r in P))
print('held-out: fit', sum(r['fits_train'] for r in H), '/', len(H), 'exact', sum(r.get('exact', False) for r in H))
