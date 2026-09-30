import json, sys
from collections import Counter
sys.path.insert(0,'.')
from role_reuse import bg_of, objects_m8, N8, B, M, RES
tr=json.load(open(B+'arc-agi_training_challenges.json')); ev=json.load(open(B+'arc-agi_evaluation_challenges.json'))
N2=set(open(M+'novel_N2.txt').read().split()); A=set(open(M+'deval_a.txt').read().replace(',',' ').split())
R={r['task']:r for r in map(json.loads,open(RES))}
PT=json.load(open('role_reuse_tasks.json'))
design={k:tr[k] for k in tr if k not in N2}; design.update({k:ev[k] for k in A})
sig=Counter(); sig_seed=Counter(); shape=Counter()
for k,t in design.items():
    if R[k]['exact']: continue
    pairs=[(p['input'],p['output']) for p in t['train']]
    if any((len(a),len(a[0]))!=(len(b),len(b[0])) for a,b in pairs):
        ia=[(len(a),len(a[0])) for a,_ in pairs]; ob=[(len(b),len(b[0])) for _,b in pairs]
        rel='smaller' if all(o[0]*o[1]<i[0]*i[1] for i,o in zip(ia,ob)) else ('larger' if all(o[0]*o[1]>i[0]*i[1] for i,o in zip(ia,ob)) else 'mixed')
        shape[rel]+=1; continue
    kinds=set(); newc=False; fr=[]; adj=[]
    for a,b in pairs:
        bg=bg_of(a); h,w=len(a),len(a[0])
        D=[(y,x) for y in range(h) for x in range(w) if a[y][x]!=b[y][x]]
        if not D: continue
        for y,x in D:
            kinds.add('add' if a[y][x]==bg else ('erase' if b[y][x]==bg else 'recolour'))
        newc |= bool({v for r in b for v in r}-{v for r in a for v in r})
        fr.append(len(D)/(h*w))
        adj.append(sum(any(0<=y+dy<h and 0<=x+dx<w and a[y+dy][x+dx]!=bg for dy,dx in N8) for y,x in D)/len(D))
    kind='+'.join(sorted(kinds)); f=max(fr) if fr else 0
    fb='<5%' if f<.05 else ('5-20%' if f<.2 else '>20%')
    ad=min(adj) if adj else 0; ab='all-adjacent' if ad==1 else ('mostly-adjacent' if ad>=.5 else 'far')
    s=(kind,'newcolour' if newc else 'samecolours',fb,ab)
    sig[s]+=1
    if PT.get(k,{}).get('hits'): sig_seed[s]+=1
print('different-shape failed:',dict(shape),'total',sum(shape.values()))
print('same-shape failed:',sum(sig.values()),'groups',len(sig),'singletons',sum(1 for v in sig.values() if v==1),'groups>=5',sum(1 for v in sig.values() if v>=5),'tasks in groups>=5',sum(v for v in sig.values() if v>=5))
for s,n in sig.most_common(15): print(n, sig_seed[s], s)
