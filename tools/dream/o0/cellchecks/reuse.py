"""Where else do Len's key x tile and fg x disperse definitions reproduce every training pair? Design population
(ARC-1 training minus N2, plus the 99 ARC-2), held-out excluded. Training pairs only. Then ONE harness check of the
key x tile definition on its own task (15696249, ARC-1, not N2, not held-out): expected outputs compared inside, never printed."""
import json, os, sys, re
sys.path.insert(0, '.'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import line_check as LC
from check3 import key_tile, disperse
held = set(json.load(open('/home/claude/work/public_repo/results/o0/t86_heldout.json')))
keys = [k for k in sorted(LC.tr) if k not in LC.N2] + sorted(LC.D99); keys = [k for k in keys if k not in held]
page = open('/tmp/claude-0/-home-claude/47726fdd-2a5c-5c69-a676-871abe4e1a48/scratchpad/phone/arc_review_mobile.html').read()
solved = set(json.loads(re.search(r'<script id="meta" type="application/json">(.*?)</script>', page, re.S).group(1))['solved'])
res = {}
for name, f in [('key|tile', key_tile), ('fg|disperse', disperse)]:
    fits = []
    for k in keys:
        T = LC.task(k)[0]['train']
        try:
            if all(f(q['input']) == q['output'] for q in T): fits.append(k)
        except Exception: pass
    res[name] = {'fits': fits, 'arc2': [k for k in fits if k in LC.D99], 'not_build_solved': [k for k in fits if k not in solved]}
    print(name, 'fits', len(fits), 'ARC-2', len(res[name]['arc2']), 'not solved by V32', len(res[name]['not_build_solved']), fits)
T, S = LC.task('15696249')
ok = all(key_tile(q['input']) == s for q, s in zip(T['test'], S))
res['harness_15696249_key_tile'] = 'exact' if ok else 'wrong'
print('harness check 15696249:', res['harness_15696249_key_tile'], '| in V32 solved:', '15696249' in solved, '| 66e6c45b in V32 solved:', '66e6c45b' in solved)
json.dump(res, open('/tmp/claude-0/-home-claude/47726fdd-2a5c-5c69-a676-871abe4e1a48/scratchpad/cellcheck/reuse.json', 'w'), indent=1)
