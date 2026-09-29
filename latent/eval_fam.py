"""Evaluate a candidate G-DSL family module in isolation.
usage: python3 eval_fam.py fam_X.py [out.jsonl]
The module must define FAMILIES = (fam_a, fam_b, ...), each fam(train) yielding (name, cost, fn(grid)->grid).
Runs gdsl.search restricted to those families (plus the colour-map post-step and dihedral composition)
on the 1000 training tasks + dev-eval half A. Prints: exact solves, NEW solves (not solved by the current system),
and WRONG = tasks where a program fit all training pairs but the test prediction was wrong (over-firing)."""
import json,sys,re,signal,os,importlib.util
from multiprocessing import Pool
sys.path.insert(0,'/home/claude/work/widen'); import gdsl
B='/kaggle/input/arc-prize-2026-arc-agi-2/'
tr=json.load(open(B+'arc-agi_training_challenges.json'));trs=json.load(open(B+'arc-agi_training_solutions.json'))
ev=json.load(open(B+'arc-agi_evaluation_challenges.json'));evs=json.load(open(B+'arc-agi_evaluation_solutions.json'))
A=[x for x in re.split(r'[,\s]+',open('/home/claude/work/widen/deval_a.txt').read()) if x]
SOLVED=set(json.load(open('/home/claude/work/s0/review_groups.json'))['status'])
spec=importlib.util.spec_from_file_location('famx',os.path.abspath(sys.argv[1])); M=importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
gdsl.FAMILIES=tuple(M.FAMILIES)
class TO(Exception):pass
def one(k):
    ch,so=(tr,trs) if k in tr else (ev,evs)
    def h(*a): raise TO()
    signal.signal(signal.SIGALRM,h);signal.alarm(20)
    try:
        res=gdsl.search(ch[k],allow2=False)
        ok=bool(res) and all(any(r['preds'][i]==so[k][i] for r in res[:2]) for i in range(len(so[k])))
        return {'task':k,'occ':bool(res),'exact':ok,'prog':res[0]['program'] if res else None}
    except TO: return {'task':k,'occ':False,'exact':False,'timeout':True}
    except BaseException as e: return {'task':k,'occ':False,'exact':False,'err':repr(e)[:100]}
    finally: signal.alarm(0)
if __name__=='__main__':
    keys=sorted(tr)+A
    if len(sys.argv)>3: keys=[k for k in keys if k in set(sys.argv[3].split(','))]
    with Pool(2) as p: R=p.map(one,keys,chunksize=8)
    if len(sys.argv)>2: open(sys.argv[2],'w').write('\n'.join(json.dumps(r) for r in R))
    ex=[r for r in R if r['exact']]; wr=[r for r in R if r['occ'] and not r['exact']]
    print('exact',len(ex),'new',sorted(r['task'] for r in ex if r['task'] not in SOLVED),'halfA_exact',sum(r['task'] in A for r in ex))
    print('WRONG(over-fire)',len(wr),[(r['task'],r['prog']) for r in wr][:30])
    print('timeouts',sum(1 for r in R if r.get('timeout')),'errors',sum(1 for r in R if r.get('err')))
    from collections import Counter; print(Counter(re.split(r'[\[:(+]',r['prog'])[0] for r in ex).most_common(20))
