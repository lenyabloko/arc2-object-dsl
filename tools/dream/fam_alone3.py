"""OQ7 / G31: each abduced family alone on the DESIGN population = ARC training minus N2, plus the 99 ARC-2 public tasks
(half A + half B). N2 and the 21 sealed tasks are not evaluated. Output: one JSON line per (family, task) fire."""
import json, sys, importlib.util, signal
spec = importlib.util.spec_from_file_location('M', sys.argv[1]); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'; T = '/home/claude/work/public_repo/tools/m1b/'
n2 = set(open(T + 'novel_N2.txt').read().split()); n1 = set(open(T + 'novel_N1.txt').read().split())
d99 = set(open(T + 'dev_eval_nl.txt').read().replace(',', ' ').split()); A = set(open(T + 'deval_a.txt').read().replace(',', ' ').split())
class TO(Exception): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
for split in ('training', 'evaluation'):
    ch = json.load(open(B + f'arc-agi_{split}_challenges.json')); so = json.load(open(B + f'arc-agi_{split}_solutions.json'))
    for tid, t in sorted(ch.items()):
        if split == 'training' and tid in n2: continue
        if split == 'evaluation' and tid not in d99: continue
        row = 'ARC-2 public' if split == 'evaluation' else ('N1' if tid in n1 else 'ARC-1 training')
        for fam in M.FAMILIES:
            try:
                signal.alarm(10); progs = list(fam(t['train'])); signal.alarm(0)
            except TO: continue
            except Exception: signal.alarm(0); continue
            if not progs: continue
            name, _, fn = progs[0]
            try: ok = all(fn(q['input']) == o for q, o in zip(t['test'], so[tid]))
            except Exception: ok = False
            print(json.dumps({'family': fam.__name__, 'task': tid, 'row': row, 'half': ('A' if tid in A else 'B') if split == 'evaluation' else None, 'exact': ok, 'prog': name[:60]}), flush=True)
