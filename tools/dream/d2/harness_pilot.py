"""Single harness test check (once per family version) for LLM-authored families; appends to the harness ledger."""
import json, importlib.util, time, sys, signal
B='/kaggle/input/arc-prize-2026-arc-agi-2/'
ev=json.load(open(B+'arc-agi_evaluation_challenges.json')); es=json.load(open(B+'arc-agi_evaluation_solutions.json'))
class TO(Exception): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
done={json.loads(l)['task'] for l in open('/home/claude/work/public_repo/results/cycle21/harness_ledger.jsonl.txt') if 'program' in l}
out=[]
for k in sys.argv[1:]:
    if k in done: print(k,'already checked; skipped'); continue
    r={'task':k,'program':None,'fits_train':False,'exact':False}
    try:
        spec=importlib.util.spec_from_file_location('F'+k, f'{k}_family.py'); F=importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
        for fam in F.FAMILIES:
            signal.alarm(120); progs=list(fam(ev[k]['train'])); signal.alarm(0)
            if not progs: continue
            name,cost,fn=progs[0]; t0=time.time()
            signal.alarm(120); preds=[fn(q['input']) for q in ev[k]['test']]; signal.alarm(0)
            r.update(program=name, fits_train=True, exact=all(preds[i]==es[k][i] for i in range(len(es[k]))), s=round(time.time()-t0,2))
            break
    except Exception as e:
        signal.alarm(0); r['error']=repr(e)[:100]
    r.update(check='single harness test check, version 1', time=time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()))
    out.append(r); print(r)
with open('/home/claude/work/public_repo/results/cycle21/harness_ledger.jsonl.txt','a') as f:
    for r in out: f.write(json.dumps(r)+'\n')
print('batch: fits',sum(r['fits_train'] for r in out),'exact',sum(r['exact'] for r in out),'of',len(out))
