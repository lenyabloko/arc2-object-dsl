"""Same logic as predict_m1.py (identical predictions/digest) plus per-task wall times."""
import hashlib, json, os, signal, sys, time
PLACEHOLDER=[[0]]
class TaskTimeout(BaseException): pass
cand,probe_dir,vocab,chf,out,secs=sys.argv[1:7]; secs=int(secs)
os.environ["M1B_VOCAB"]=vocab; sys.path[:0]=[probe_dir,cand]
import occupancy2 as probe
probe.Timeout=TaskTimeout
ch=json.load(open(chf)); signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TaskTimeout()))
sub={}; times={}
for k in sorted(ch):
    task=ch[k]; slots=[{"attempt_1":PLACEHOLDER,"attempt_2":PLACEHOLDER} for _ in task["test"]]; t0=time.time(); to=False
    try:
        signal.alarm(secs); attempts,_,_=probe.solve(task)
        for rank,a in enumerate(attempts[:2]):
            for i,g in enumerate(a["preds"]):
                if g and all(isinstance(r,list) and r for r in g): slots[i]["attempt_1" if rank==0 else "attempt_2"]=g
    except TaskTimeout: to=True
    except Exception: pass
    finally: signal.alarm(0)
    sub[k]=slots; times[k]=(round(time.time()-t0,2),to)
blob=json.dumps(sub,sort_keys=True).encode(); open(out,"w").write(json.dumps(sub))
json.dump(times,open(out+'.times.json','w'))
ts=sorted(v[0] for v in times.values())
print(json.dumps({"tasks":len(sub),"digest":hashlib.sha256(blob).hexdigest(),"max_s":ts[-1],"p90_s":ts[int(.9*len(ts))],"total_s":round(sum(ts)),"timeouts":sum(v[1] for v in times.values())}))
