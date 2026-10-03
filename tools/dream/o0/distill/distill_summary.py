"""T94 numbers for a distillation batch (Fable v23 C.7 / v23a item 3): readings / executable / fitting / exact at the
harness, frames and their R(S) (distinct tasks a frame fits), new rows, head verbs, the growth curve of distinct
frames against tasks processed, and the split by whether the build already solves the task.
usage: python3 distill_summary.py <batch.json>   -> results/o0/distill_b<batch>_summary.json"""
import collections, glob, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
B = json.load(open(sys.argv[1]))
rows = {}
for f in sorted(glob.glob(os.path.join(REPO, f"results/o0/distill_b{B['batch']}_g*.json"))):
    rows.update(json.load(open(f))['tasks'])
order = [t for t in B['tasks'] if t in rows]
failing = {e['task'] if isinstance(e, dict) else e for e in json.load(open(os.path.join(REPO, 'results/o0/overnight_order.json')))['order']}
L4 = json.load(open(os.path.join(HERE, 'l4_verbs.json')))

def head(verb):
    v = (verb or '').lower().strip()
    return v.split(' ')[0] if v else ''

R = [r for t in order for r in rows[t]['readings']]
out = {'batch': B['batch'], 'tasks': len(order), 'readings': len(R)}
out['executable_readings'] = sum(r['executable'] for r in R)
out['other_readings'] = sum(not r['executable'] for r in R)
out['l4_normalised'] = sum(bool(r.get('l4')) and r['executable'] for r in R)
out['fitting_readings'] = sum(bool(r.get('n_fits')) for r in R)
out['fitting_readings_all_slots_bound'] = sum(bool(r.get('n_fits')) and r.get('n_open', 0) == 0 for r in R)
out['tasks_with_a_fit'] = sum(rows[t]['n_fitting'] > 0 for t in order)
h = collections.Counter(re.split(r' \(', rows[t]['harness'])[0] for t in order)
out['harness'] = dict(h)
out['tasks_support_ge3'] = sum(rows[t]['max_support'] >= 3 for t in order)
out['exact_by_build'] = {'build_failing': sum(rows[t]['harness'].startswith('exact') and t in failing for t in order),
                         'build_solved_or_unknown': sum(rows[t]['harness'].startswith('exact') and t not in failing for t in order)}
out['batch_build_failing_tasks'] = sum(t in failing for t in order)
# frames and R(S)
frame_tasks = collections.defaultdict(set)
for t in order:
    for r in rows[t]['readings']:
        for fr in r.get('frames') or []: frame_tasks[fr].add(t)
out['frames_distinct'] = len(frame_tasks)
out['frames_R_ge2'] = {fr: len(ts) for fr, ts in sorted(frame_tasks.items(), key=lambda x: -len(x[1])) if len(ts) >= 2}
# heads: column of fitting readings; raw head verbs of non-executable readings
out['fitting_by_column'] = dict(collections.Counter(fr.split('(')[0] for fr in frame_tasks for _ in frame_tasks[fr]))
other_verbs = collections.Counter(head(r.get('verb')) for r in R if not r['executable'])
out['other_head_verbs_top'] = other_verbs.most_common(25)
out['other_head_verbs_distinct'] = len(other_verbs)
out['other_verbs_not_in_L4'] = sum(n for v, n in other_verbs.items() if v not in L4['verbs'] and v not in L4['columns'])
# task-level agreement of the non-executable head verb (G48: 3 of 5)
agree = 0
for t in order:
    c = collections.Counter(head(r.get('verb')) for r in rows[t]['readings'] if not r['executable'])
    if c and c.most_common(1)[0][1] >= 3: agree += 1
out['tasks_other_verb_3of5'] = agree
# new rows
nr = [n for r in R for n in r.get('new_rows', [])]
out['new_rows'] = len(nr); out['new_row_errors'] = sum(len(r.get('row_errors', [])) for r in R)
eq = sum(all(x == 'equal' for x in v) for r in R for v in (r.get('row_vs_changed') or {}).values())
out['new_rows_equal_to_changed_cells_on_every_pair'] = eq
# growth curve: distinct frames after every 25 tasks
seen = set(); curve = []
for i, t in enumerate(order, 1):
    for r in rows[t]['readings']:
        seen |= set(r.get('frames') or [])
    if i % 25 == 0 or i == len(order): curve.append([i, len(seen)])
out['growth_distinct_frames'] = curve
json.dump(out, open(os.path.join(REPO, f"results/o0/distill_b{B['batch']}_summary.json"), 'w'), indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('frames_R_ge2', 'other_head_verbs_top')}, indent=1))
print('frames R>=2:', len(out['frames_R_ge2'])); [print('  ', n, fr) for fr, n in list(out['frames_R_ge2'].items())[:25]]
print('other verbs top:', out['other_head_verbs_top'][:25])
