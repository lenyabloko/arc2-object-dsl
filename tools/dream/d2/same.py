"""test-blind equivalence check of two family versions: same programs and same predictions on train + test inputs
of the given tasks (no solutions read). usage: same.py old.py new.py task_ids..."""
import importlib.util, json, sys, time, signal
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
ch = {}
for s in ('training', 'evaluation'): ch.update(json.load(open(B + f'arc-agi_{s}_challenges.json')))
def load(p, n):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m
A, Bm = load(sys.argv[1], 'A'), load(sys.argv[2], 'B')
class TO(BaseException): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
def run(m, t):
    out = []
    for fam in m.FAMILIES:
        for name, cost, fn in fam(t['train']):
            out.append((name, [fn(p['input']) for p in t['train']], [fn(q['input']) for q in t['test']]))
    return out
for k in sys.argv[3:]:
    t = ch[k]; r = {}
    for lab, m in (('old', A), ('new', Bm)):
        t0 = time.time()
        try: signal.alarm(120); r[lab] = run(m, t); signal.alarm(0)
        except TO: r[lab] = 'TIMEOUT'
        except Exception as e: signal.alarm(0); r[lab] = 'ERR ' + repr(e)[:60]
        r[lab + '_s'] = round(time.time() - t0, 2)
    print(k, 'SAME' if r['old'] == r['new'] else 'DIFF', r['old_s'], r['new_s'], (len(r['new']) if isinstance(r['new'], list) else r['new']))
