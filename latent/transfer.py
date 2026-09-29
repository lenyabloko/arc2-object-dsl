"""Cross-task transfer of Codex wake rules: which rule modes fit tasks other than the ones they were written for.
For every task (training + dev-eval half A only), every wake-rule module proposes bindings from the TRAIN pairs
(candidate_bindings), each binding is checked on all train pairs, and train-exact bindings are scored on test."""
import json,sys,os,glob,importlib,signal,time,re
sys.path[:0]=['/home/claude/work/codex','/home/claude/work/codex/extended_transformations']
B='/kaggle/input/arc-prize-2026-arc-agi-2/'
tr=json.load(open(B+'arc-agi_training_challenges.json'));trs=json.load(open(B+'arc-agi_training_solutions.json'))
ev=json.load(open(B+'arc-agi_evaluation_challenges.json'));evs=json.load(open(B+'arc-agi_evaluation_solutions.json'))
A=[x for x in re.split(r'[,\s]+',open('/home/claude/work/widen/deval_a.txt').read()) if x]
MODS=None
class TO(Exception):pass
def _h(*a): raise TO()
def mods():
    global MODS
    if MODS is None:
        MODS=[]
        for f in sorted(glob.glob('/home/claude/work/codex/wake/rules/*.py')):
            n=os.path.basename(f)[:-3]
            if n=='__init__':continue
            m=importlib.import_module('wake.rules.'+n)
            if hasattr(m,'candidate_bindings') and hasattr(m,'apply_rule'): MODS.append((n,m))
    return MODS
MODEKEYS=('object','mode','pattern_type','fill_type','type','tile_type','extract_type','recolor_type','move_type','placement_type','overlay_type','crop_type','operation')
def mode_of(b):
    for k in MODEKEYS:
        if k in b and isinstance(b[k],str): return k+'='+b[k]
    return ''
def one(k):
    ch,so=(tr,trs) if k in tr else (ev,evs)
    task=ch[k]; out=[]
    signal.signal(signal.SIGALRM,_h)
    for n,m in mods():
        t0=time.time()
        try:
            signal.setitimer(signal.ITIMER_REAL,4.0)
            bs=m.candidate_bindings({'train':task['train'],'test':[{'input':t['input']} for t in task['test']]}) or []
            hits=[]
            for b in bs:
                ok=True
                for p in task['train']:
                    try: y=m.apply_rule(p['input'],b)
                    except TO: raise
                    except Exception: y=None
                    if y!=p['output']: ok=False;break
                if ok:
                    preds=[]
                    for t in task['test']:
                        try: preds.append(m.apply_rule(t['input'],b))
                        except TO: raise
                        except Exception: preds.append(None)
                    hits.append({'mode':mode_of(b),'test_ok':all(preds[i]==so[k][i] for i in range(len(so[k]))),'binding':json.dumps(b,sort_keys=True,default=str)[:400]})
                    if len(hits)>=3: break
            signal.setitimer(signal.ITIMER_REAL,0)
            if hits: out.append({'rule':n,'hits':hits,'s':round(time.time()-t0,2)})
        except TO:
            out.append({'rule':n,'timeout':True})
        except BaseException as e:
            signal.setitimer(signal.ITIMER_REAL,0)
        finally: signal.setitimer(signal.ITIMER_REAL,0)
    return {'task':k,'fits':out}
if __name__=='__main__':
    from multiprocessing import Pool
    outp=sys.argv[1]; keys=sorted(tr)+A
    if len(sys.argv)>2: keys=keys[:int(sys.argv[2])]
    done=set()
    if os.path.exists(outp): done={json.loads(l)['task'] for l in open(outp)}
    keys=[k for k in keys if k not in done]
    with Pool(2,maxtasksperchild=20) as p, open(outp,'a') as f:
        for r in p.imap_unordered(one,keys):
            f.write(json.dumps(r)+'\n');f.flush()
