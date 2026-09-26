import json,sys
A=set(open('deval_a.txt').read().replace(',','\n').split()); B=set(open('deval_b.txt').read().replace(',','\n').split())
def load(tag):
  tr={json.loads(l)['task']:json.loads(l) for l in open(f'm1b/{tag}_train.jsonl')}
  dv={json.loads(l)['task']:json.loads(l) for l in open(f'm1b/{tag}_deval.jsonl')}
  return tr,dv
def stats(tr,dv):
  s=lambda rows,keys=None:{k for k,r in rows.items() if r.get('test_exact') and (keys is None or k in keys)}
  return dict(T=s(tr),EA=s(dv,A),EB=s(dv,B),occ={k for k,r in tr.items() if r.get('occupied')})
base,new=sys.argv[1],sys.argv[2]
b,n=stats(*load(base)),stats(*load(new))
btr,_=load(base); ntr,_=load(new)
reg=(b['T']-n['T'])|(b['EA']-n['EA'])
mdl=[k for k in b['T']&n['T'] if ntr[k].get('n_rules',len(ntr[k].get('rules',[])))>btr[k].get('n_rules',len(btr[k].get('rules',[])))]
gain=len(n['T'])-len(b['T']); gainA=len(n['EA'])-len(b['EA']); occg=len(n['occ'])-len(b['occ'])
admit= not reg and not mdl and (gain>=1 or gainA>=1 or occg>=3)
print(json.dumps(dict(base=base,new=new,T=len(n['T']),dT=gain,EA=len(n['EA']),dEA=gainA,dOcc=occg,EB=len(n['EB']),
  regressions=sorted(reg),mdl_growth=sorted(mdl),new_solves=sorted(n['T']-b['T']),admit=admit)))
