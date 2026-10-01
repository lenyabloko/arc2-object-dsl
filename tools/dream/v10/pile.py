"""Description lattice (Fable v10 / v10a), T54-T56 harness.

The five schema modules (schema_<s>.py: SCHEMA, MENU, nodes(), key(), draw(), family()) were written test-blind from
the parsed description records (results/o0/v10_records.json). This script:
  ground   T54: every node drawn with seeds 0..3; ok = all drawn, outputs differ from inputs, the node's family fitted
           on pairs 0-2 predicts pair 3 (synthetic tasks are evidence only of ok(D), G59)
  index    T55: for each of the 68 far-cells design tasks (results/cycle21/far68_manual_split.json), score every
           grounded node: schema compatible with the task's change signature + the node family fits the task's
           training pairs (training pairs only; no test outputs). Reports how many tasks have a fitting node among
           the top-3 proposals, and among all nodes (oracle).
  redundancy T56: does an existing family (priors2, concepts, lines) solve the node's synthetic task?
usage: python3 pile.py ground|index|redundancy [--limit N]"""
import importlib, json, os, re, signal, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MODS = ['schema_path', 'schema_link', 'schema_cycle', 'schema_center_periphery', 'schema_symmetry']
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'


class TO(Exception): pass


signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def load():
    out = []
    for m in MODS:
        M = importlib.import_module(m)
        for n in M.nodes(): out.append((M, n, M.key(n)))
    return out


def fit_first(fam, train, budget=3):
    try:
        signal.alarm(budget)
        for name, cost, fn in fam(train):
            if all(fn(p['input']) == p['output'] for p in train):
                signal.alarm(0); return name, fn
        signal.alarm(0)
    except Exception:
        signal.alarm(0)
    return None


def ground(nodes):
    res = {}
    for M, n, k in nodes:
        pairs = []
        for s in range(4):
            try: p = M.draw(n, s)
            except Exception: p = None
            if not p: break
            pairs.append({'input': p[0], 'output': p[1]})
        ok = len(pairs) == 4 and all(p['input'] != p['output'] for p in pairs)
        if ok:
            f = fit_first(M.family(n), pairs[:3])
            try: ok = bool(f) and f[1](pairs[3]['input']) == pairs[3]['output']
            except Exception: ok = False
        res[k] = {'schema': M.SCHEMA, 'ok': ok}
    return res


SIG2SCHEMA = {'ray/line': {'PATH'}, 'between': {'LINK', 'PATH'}, 'periodic': {'CYCLE'}, 'fill': {'CENTER-PERIPHERY', 'LINK'},
              'reflection': {'SYMMETRY'}, 'copy': {'CYCLE', 'SYMMETRY'}, 'other generator': {'PATH', 'CYCLE', 'CENTER-PERIPHERY'}}


def index(nodes, grounded):
    far = json.load(open(os.path.join(REPO, 'results/cycle21/far68_manual_split.json')))['labels']
    ch = json.load(open(B + 'arc-agi_training_challenges.json')); ch.update(json.load(open(B + 'arc-agi_evaluation_challenges.json')))
    rows = []
    for t, lab in sorted(far.items()):
        train = ch[t]['train']; fits = []
        for M, n, k in nodes:
            if not grounded.get(k, {}).get('ok'): continue
            f = fit_first(M.family(n), train, budget=2)
            if f: fits.append((M.SCHEMA in SIG2SCHEMA.get(lab, set()), -len(k), k, f[0]))
        fits.sort(key=lambda x: (not x[0], -x[1]))          # schema-compatible first, then more general (shorter key)
        top3 = fits[:3]
        rows.append({'task': t, 'label': lab, 'n_fit': len(fits), 'top3': [x[2] for x in top3],
                     'top3_compatible': any(x[0] for x in top3)})
        print(json.dumps(rows[-1]), flush=True)
    n_top3 = sum(1 for r in rows if r['top3']); n_any = sum(1 for r in rows if r['n_fit'])
    print(json.dumps({'T55_tasks_with_fitting_node_in_top3': n_top3, 'oracle_any_node_fits': n_any, 'n': len(rows)}))
    return rows


def main():
    mode = sys.argv[1]
    nodes = load()
    gpath = os.path.join(REPO, 'results/o0/v10_ground.json')
    if mode == 'ground':
        t0 = time.time(); g = ground(nodes)
        json.dump(g, open(gpath, 'w'))
        by = {}
        for v in g.values(): by.setdefault(v['schema'], [0, 0]); by[v['schema']][0] += 1; by[v['schema']][1] += v['ok']
        print(json.dumps({'nodes': len(g), 'ok': sum(v['ok'] for v in g.values()), 'by_schema': by, 'seconds': round(time.time() - t0, 1)}))
    elif mode == 'index':
        rows = index(nodes, json.load(open(gpath)))
        json.dump(rows, open(os.path.join(REPO, 'results/o0/v10_index_far68.json'), 'w'))


if __name__ == '__main__':
    main()
