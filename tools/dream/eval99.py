"""Full solve (Kaggle attempt ordering) on the 99 ARC-2 public design tasks (half A + half B, OQ7), one probe.
usage: python3 eval99.py <probe_dir> > out.jsonl"""
import json, os, sys, signal
probe = sys.argv[1]
os.environ["M1B_VOCAB"] = 'fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,G_dsl'
os.chdir(probe); sys.path[:0] = [probe]
import occupancy2 as P
class TO(BaseException): pass
P.Timeout = TO; signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
ch = json.load(open(B + 'arc-agi_evaluation_challenges.json')); so = json.load(open(B + 'arc-agi_evaluation_solutions.json'))
ids = open('/home/claude/work/public_repo/tools/m1b/dev_eval_nl.txt').read().replace(',', ' ').split()
A = set(open('/home/claude/work/public_repo/tools/m1b/deval_a.txt').read().replace(',', ' ').split())
def size(a):
    if a.get('abstraction') != 'gdsl': return P.nrules(a['rules'])
    prog = a.get('program') or ''
    if prog.startswith('nearmiss:'): return 99
    if '->' in prog:
        st = prog.split('objmap[')[1:] if prog.count('objmap[') >= 2 else [prog]
        return sum(s.count('->') + (0 if 'else ->' in s else 1) for s in st) + len(st) - 1
    return 1 + (1 + prog.count(' ; ')) + prog.count('+')
for k in sorted(ids):
    t = ch[k]; sol = so[k]; out = {'task': k, 'half': 'A' if k in A else 'B'}
    try:
        signal.alarm(300); att, _, found = P.solve(t); signal.alarm(0)
        out['final'] = [all(a['preds'][i] == sol[i] for i in range(len(sol))) for a in att[:2]]
        out['kinds'] = [a.get('abstraction') for a in att[:2]]
        out['size'] = [size(a) for a in att[:2]]
        out['prog'] = [(a.get('program') or '')[:80] for a in att[:2]]
    except TO: out['final'] = 'timeout'
    except Exception as e: out['final'] = 'error'; out['err'] = repr(e)[:120]
    print(json.dumps(out), flush=True)
