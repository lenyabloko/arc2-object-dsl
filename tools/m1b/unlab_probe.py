import json, collections, sys
from occupancy import *
T='/kaggle/input/arc-prize-2026-arc-agi-2/'
ch=json.load(open(T+'arc-agi_training_challenges.json'))
rows=[json.loads(l) for l in open('m1_train.jsonl')]
cnt=collections.Counter(); ex=collections.defaultdict(list)
for r in rows:
    st=r.get('statuses',{})
    if 'unlabelled_node' not in st.values() or r.get('occupied'): continue
    ab=next(a for a,s in st.items() if s=='unlabelled_node')
    kinds=set()
    try:
      for p in ch[r['task']]['train']:
        gi,go=p['input'],p['output']
        nodes,bg,at,src,others=prepare(gi,ab)
        for n,s,o in zip(nodes,src,others):
            if candidate_labels(n,s,gi,go,bg,o): continue
            pix=n['pix']; r0,c0,r1,c1=bbox(pix)
            now={q:go[q[0]][q[1]] for q in pix}
            box=[row[c0:c1+1] for row in go[r0:r1+1]]; inb=[row[c0:c1+1] for row in gi[r0:r1+1]]
            if len(set(now.values()))>1 and all(v!=bg for v in now.values()): kinds.add('partial_recolor')
            elif box in ([list(x) for x in zip(*inb[::-1])],[row[::-1] for row in inb],inb[::-1]): kinds.add('flip_rotate_in_place')
            elif any(v==bg for v in now.values()) and any(v!=bg for v in now.values()): kinds.add('partial_erase/shape_change')
            else: kinds.add('other')
    except Exception: continue
    for k in kinds: cnt[k]+=1; ex[k].append(r['task'])
print(cnt); print({k:v[:6] for k,v in ex.items()})
