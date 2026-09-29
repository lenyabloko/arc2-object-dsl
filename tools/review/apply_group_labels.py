"""Apply reviewer-facing display names to groups (group_labels.json); keys stay.  usage: apply_group_labels.py <review json> <labels.json>"""
import json, sys
p, q = sys.argv[1], sys.argv[2]
D = json.load(open(p)); L = json.load(open(q)); n = 0
for g in D['groups']:
    if g['key'] in L['by_key']:
        g['name'] = L['by_key'][g['key']]; n += 1
    elif g['kind'] == 'solved' and g.get('family') in L.get('solved_family', {}):
        g['name'] = 'solved · ' + L['solved_family'][g['family']] + ' [' + g['family'] + ']'; n += 1
json.dump(D, open(p, 'w')); print('renamed', n)
