import json, importlib.util, signal, sys
B='/kaggle/input/arc-prize-2026-arc-agi-2/'; T='/home/claude/work/public_repo/tools/m1b/'
n2=set(open(T+'novel_N2.txt').read().split()); d99=set(open(T+'dev_eval_nl.txt').read().replace(',',' ').split())
class TO(BaseException): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
fams=[]
for k in sys.argv[1:]:
    spec=importlib.util.spec_from_file_location('F'+k, f'/home/claude/work/widen/probe_v30/llm_{k}.py'); F=importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
    fams += [(k,f) for f in F.FAMILIES]
out=[]
for split in ('training','evaluation'):
    ch=json.load(open(B+f'arc-agi_{split}_challenges.json')); so=json.load(open(B+f'arc-agi_{split}_solutions.json'))
    for tid,t in sorted(ch.items()):
        if split=='training' and tid in n2: continue
        if split=='evaluation' and tid not in d99: continue
        for src,fam in fams:
            try:
                signal.alarm(10); progs=list(fam(t['train'])); signal.alarm(0)
            except TO: continue
            except Exception: signal.alarm(0); continue
            if not progs: continue
            name,_,fn=progs[0]
            try:
                signal.alarm(10); ok=all(fn(q['input'])==o for q,o in zip(t['test'],so[tid])); signal.alarm(0)
            except TO: ok=False
            except Exception: signal.alarm(0); ok=False
            out.append({'family':fam.__name__,'source':src,'task':tid,'exact':ok})
            print(json.dumps(out[-1]),flush=True)
