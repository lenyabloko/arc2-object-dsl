"""usage: python3 check_group.py <family_module.py> <group.json>
Runs every family in FAMILIES separately on each member task's training pairs (the family is called once per task,
with that task's training pairs only) and reports, per member, the first program yielded and whether it reproduces
each training output. A group family must fit EVERY member."""
import importlib.util, json, sys, time, traceback
spec = importlib.util.spec_from_file_location('F', sys.argv[1]); F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
g = json.load(open(sys.argv[2]))
ok_all = True
for tid, t in g['members'].items():
    t0 = time.time(); line = None
    for fam in F.FAMILIES:
        try:
            progs = list(fam(t['train']))
        except Exception:
            line = f'{fam.__name__} raised: ' + traceback.format_exc().strip().splitlines()[-1]; continue
        for name, cost, fn in progs:
            fits = []
            for p in t['train']:
                try: fits.append(fn(p['input']) == p['output'])
                except Exception as e: fits.append(f'error {e!r}'[:60])
            line = f'{fam.__name__} | {name} | train fits {fits}'
            if all(f is True for f in fits): break
        if line and 'train fits' in line and 'False' not in line and 'error' not in line: break
    fit = bool(line) and 'train fits' in line and 'False' not in line and 'error' not in line
    ok_all &= fit
    print(tid, 'FIT' if fit else 'NO FIT', '|', line or 'no program yielded', f'| {time.time() - t0:.2f}s')
print('GROUP', 'ALL MEMBERS FIT' if ok_all else 'NOT ALL MEMBERS FIT')
