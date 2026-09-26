import json,collections,sys
for f in sys.argv[1:]:
  rows=[json.loads(l) for l in open(f)]
  n=len(rows)
  occ=sum(bool(r.get('occupied')) for r in rows); te=sum(bool(r.get('test_exact')) for r in rows)
  lo=sum(r.get('loo') is True for r in rows); to=sum(r.get('status')=='timeout' for r in rows)
  best=collections.Counter()
  order=['occupied','not_occupied','not_representable','unlabelled_node','extent_change']
  for r in rows:
    st=set(r.get('statuses',{}).values()) or {'timeout'}
    best[next((o for o in order if o in st), sorted(st)[0])]+=1
  print(f, dict(tasks=n, occupied=occ, test_exact=te, loo_pass=lo, timeouts=to)); print('  best status per task:', dict(best))
  fam=collections.Counter()
  for r in rows:
    if r.get('test_exact'):
      for g,l in r['rules']:
        for a in g: fam[a.split('=')[0]]+=1
  print('  attribute families used in solved rules:', dict(fam.most_common()))
  print('  solved:', [r['task'] for r in rows if r.get('test_exact')])
