"""Evaluate a composition / family module with a transfer-aware report.
usage: python3 eval_fam2.py <module.py> [out.jsonl] [--families-only]
Splits reported: ARC-1-origin training (ids), N1 = design half of the 233 ARC-AGI-2-new training tasks (ids),
half A (ids), and N2 = validation half of the ARC-AGI-2-new training tasks (COUNTS ONLY, ids never printed).
Module must define FAMILIES (G-DSL interface) or SEARCH(task)->list[{'program','preds'}] (composition engines)."""
import json,sys,re,signal,os,importlib.util
from multiprocessing import Pool
sys.path.insert(0,'/home/claude/work/widen'); import gdsl
B='/kaggle/input/arc-prize-2026-arc-agi-2/'
tr=json.load(open(B+'arc-agi_training_challenges.json'));trs=json.load(open(B+'arc-agi_training_solutions.json'))
ev=json.load(open(B+'arc-agi_evaluation_challenges.json'));evs=json.load(open(B+'arc-agi_evaluation_solutions.json'))
rd=lambda f:[x for x in re.split(r'[,\s]+',open(f).read()) if x]
A=rd('/home/claude/work/widen/deval_a.txt'); N1=set(rd('/home/claude/work/latent/novel_N1.txt')); N2=set(rd('/home/claude/work/widen/novel_N2.txt'))
SOLVED=set(json.load(open('/home/claude/work/s0/review_groups.json'))['status'])
spec=importlib.util.spec_from_file_location('famx',os.path.abspath(sys.argv[1])); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
if hasattr(M,'FAMILIES'): gdsl.FAMILIES=tuple(M.FAMILIES)
TO_S=int(os.environ.get('EVAL_TIMEOUT','30'))
class TO(Exception):pass
def one(k):
    ch,so=(tr,trs) if k in tr else (ev,evs)
    def h(*a): raise TO()
    signal.signal(signal.SIGALRM,h);signal.alarm(TO_S)
    try:
        res=M.SEARCH(ch[k]) if hasattr(M,'SEARCH') else gdsl.search(ch[k],allow2=False)
        ok=bool(res) and all(any(r['preds'][i]==so[k][i] for r in res[:2]) for i in range(len(so[k])))
        return {'task':k,'occ':bool(res),'exact':ok,'prog':res[0]['program'] if res else None}
    except TO: return {'task':k,'occ':False,'exact':False,'timeout':True}
    except BaseException as e: return {'task':k,'occ':False,'exact':False,'err':repr(e)[:100]}
    finally: signal.alarm(0)
if __name__=='__main__':
    keys=sorted(tr)+A
    with Pool(2) as p: R=p.map(one,keys,chunksize=8)
    if len(sys.argv)>2 and not sys.argv[2].startswith('--'):
        open(sys.argv[2],'w').write('\n'.join(json.dumps(r) for r in R if r['task'] not in N2))
    def S(sel): 
        rr=[r for r in R if sel(r['task'])]; return len(rr),sum(r['exact'] for r in rr),sum(r['occ'] for r in rr),sum(r['occ'] and not r['exact'] for r in rr)
    arc1=lambda k:k in tr and k not in N1 and k not in N2
    for name,sel,show in [('ARC1-train',arc1,True),('N1',lambda k:k in N1,True),('halfA',lambda k:k in A,True),('N2 (counts only)',lambda k:k in N2,False)]:
        n,e,o,w=S(sel); line=f'{name}: n={n} exact={e} fit={o} wrong={w}'
        if show: line+=' new='+str(sorted(r['task'] for r in R if sel(r['task']) and r['exact'] and r['task'] not in SOLVED))
        print(line)
    print('timeouts',sum(1 for r in R if r.get('timeout')),'errors',sum(1 for r in R if r.get('err')))
