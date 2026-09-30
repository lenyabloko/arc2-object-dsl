"""time ONE family module on given task ids (train pairs + test inputs only; no solutions are read).
usage: python3 famtime1.py <family_module.py> <task_id> [task_id ...]   -> per task: seconds, number of programs"""
import importlib.util, json, signal, sys, time
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
ch = {}
for s in ('training', 'evaluation'): ch.update(json.load(open(B + f'arc-agi_{s}_challenges.json')))
sp = importlib.util.spec_from_file_location('F', sys.argv[1]); F = importlib.util.module_from_spec(sp); sp.loader.exec_module(F)
class TO(BaseException): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
for k in sys.argv[2:]:
    t = ch[k]; t0 = time.time(); n = 'ok'
    try:
        signal.alarm(60); progs = []
        for fam in F.FAMILIES:
            for name, cost, fn in fam(t['train']):
                if all(fn(p['input']) == p['output'] for p in t['train']):
                    progs.append(name); [fn(q['input']) for q in t['test']]
        signal.alarm(0); n = len(progs)
    except TO: n = 'TIMEOUT(60s)'
    except Exception as e: signal.alarm(0); n = 'ERR ' + repr(e)[:60]
    print(k, round(time.time() - t0, 2), n, flush=True)
