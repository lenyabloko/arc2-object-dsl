"""Remove the held-out tasks (N2) from the review page's embedded data and its tasks.json (protocol fix, Sep 30 2026).

The page had carried all 102 N2 tasks since before the held-out protocol, with per-task solve status and programs for
some of them. This strips every N2 id: dict keys, list elements (ids, or lists whose first element is an id) and ids
embedded in text; then repairs the groups (members, size, solved count, medoid and its example pairs). Ids are never
printed; the script reports counts only.
usage: python3 strip_heldout.py <page.html> <tasks.json> <page_out.html> <tasks_out.json>"""
import json, re, sys, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
N2 = set(x for x in re.split(r'[,\s]+', open(os.path.join(REPO, 'tools/m1b/novel_N2.txt')).read()) if x)
if os.environ.get('HELDOUT_JSON'):                    # e.g. results/o0/t86_heldout.json (the 14 T86 tasks, Oct 2)
    N2 = set(json.load(open(os.path.join(REPO, os.environ['HELDOUT_JSON']))))
pat = re.compile(r'\b(' + '|'.join(sorted(N2)) + r')\b')
removed = {'keys': 0, 'items': 0, 'text': 0}


def strip(v):
    if isinstance(v, dict):
        out = {}
        for k, x in v.items():
            if k in N2: removed['keys'] += 1; continue
            out[k] = strip(x)
        return out
    if isinstance(v, list):
        out = []
        for x in v:
            if isinstance(x, str) and x in N2: removed['items'] += 1; continue
            if isinstance(x, list) and x and isinstance(x[0], str) and x[0] in N2: removed['items'] += 1; continue
            out.append(strip(x))
        return out
    if isinstance(v, str) and pat.search(v):
        removed['text'] += 1; return pat.sub('[withheld]', v)
    return v


def main():
    page, tasksf, page_out, tasks_out = sys.argv[1:5]
    s = open(page).read()
    tag = '<script id="data" type="application/json">'
    i = s.find(tag) + len(tag); j = s.find('</script>', i)
    D = json.loads(s[i:j]); T = json.load(open(tasksf))
    orig = {g['id']: g for g in D['groups']}
    T2 = strip({k: v for k, v in T.items() if k not in N2})
    D2 = strip(D)
    solved = set(D2['solved'])
    for key in ('groups', 'groups_v1'):
        keep = []
        for g in D2.get(key, []):
            ids = [m[0] if isinstance(m, list) else m for m in g.get('members', [])]
            for t in ([g.get('medoid')] + list(D2.get('members', {}).get(g['id'], []))):
                if t and t not in N2 and t != '[withheld]' and t not in ids: ids.append(t)
            if not ids: continue
            if 'n' in g:
                lost = g['n'] - len(ids) if isinstance(g.get('n'), int) else 0
                g['n'] = len(ids)
                if 'n_heldout' in g and lost > 0: g['n_heldout'] = (g.get('n_heldout') or 0) + lost
            if 'n_solved' in g: g['n_solved'] = sum(1 for t in ids if t in solved)
            if g.get('medoid') in (None, '[withheld]') or g.get('medoid') in N2 or g.get('medoid') not in ids:
                nm = ids[0]; g['medoid'] = nm
                if nm in T2:
                    g['med_split'] = T2[nm]['split']; g['med_pairs'] = T2[nm]['train'][:3]
            keep.append(g)
        D2[key] = keep
    D2['N'] = D['N'] - len(N2 & set(T)); D2['heldout_excluded'] = D.get('heldout_excluded', 0) + len(N2 & set(T))
    if 'view_meta' in D2 and isinstance(D2['view_meta'], dict) and 'n_solved' in D2['view_meta']: D2['view_meta']['n_solved'] = len(solved)
    blob = json.dumps(D2, separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/')
    s2 = s[:i] + blob + s[j:]
    # the need-you block: drop held-out keys (Oct 2: one T86 task was on the need-you list)
    t2 = '<script id="need2" type="application/json">'
    if t2 in s2:
        i2 = s2.find(t2) + len(t2); j2 = s2.find('</script>', i2)
        try:
            N = json.loads(s2[i2:j2]); n0 = len(N.get('need', {}))
            N['need'] = {k: v for k, v in N.get('need', {}).items() if k not in N2}
            N['solved_b'] = [t for t in N.get('solved_b', []) if t not in N2]
            removed['need'] = n0 - len(N['need'])
            s2 = s2[:i2] + json.dumps(N, separators=(',', ':')).replace('</', '<\\/') + s2[j2:]
        except ValueError: pass
    # every other inline JSON block (packets, ...): the same strip
    for m in list(re.finditer(r'<script id="([\w-]+)" type="application/json">', s2)):
        if m.group(1) in ('data', 'need2'): continue
        i3 = s2.find(m.group(0)) + len(m.group(0)); j3 = s2.find('</script>', i3)
        try: B = json.loads(s2[i3:j3])
        except ValueError: continue
        if not pat.search(s2[i3:j3]): continue
        s2 = s2[:i3] + json.dumps(strip(B), separators=(',', ':'), ensure_ascii=False).replace('</', '<\\/') + s2[j3:]
    # any other inline JSON blocks (packets, need2) and the script itself: only scrub text, never N2-bearing structures
    left_page = len(pat.findall(s2)); left_tasks = len(pat.findall(json.dumps(T2)))
    open(page_out, 'w').write(s2); json.dump(T2, open(tasks_out, 'w'), separators=(',', ':'))
    print(json.dumps({'removed': removed, 'groups': len(D2['groups']), 'groups_v1': len(D2.get('groups_v1', [])), 'tasks': len(T2),
                      'N': D2['N'], 'solved': len(solved), 'n2_ids_left_in_page': left_page, 'n2_ids_left_in_tasks': left_tasks}))


if __name__ == '__main__':
    main()
