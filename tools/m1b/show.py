import json,sys
ch=json.load(open(sys.argv[1]))
def g2s(g): return [''.join('.' if v==0 else str(v) for v in row) for row in g]
for k in sys.argv[2].split(','):
  t=ch[k]; print('=== ',k)
  for i,p in enumerate(t['train']):
    a,b=g2s(p['input']),g2s(p['output'])
    print(f'-- train {i} in {len(a)}x{len(a[0])} | out {len(b)}x{len(b[0])}')
    for x in range(max(len(a),len(b))):
      print((a[x] if x<len(a) else ' '*len(a[0])),'  ',(b[x] if x<len(b) else ''))
  for i,p in enumerate(t['test']):
    a=g2s(p['input']); print(f'-- test {i} in {len(a)}x{len(a[0])}'); print('\n'.join(a))
