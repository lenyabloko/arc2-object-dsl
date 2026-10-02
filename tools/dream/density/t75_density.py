"""Fable v14 O2 / T75: ARC-GEN density run (design-side instrument only, G74).

Variants: for every ARC-1 task with an ARC-GEN V1 generator (google/ARC-GEN, commit recorded in the output), V
variants of 4 example pairs each (3 train + 1 test), seeded and replayable: random.seed(hash(task, v, k)). The V2
(ARC-AGI-2) generators are never imported (they may cover held-out or sealed tasks); ids in tools/m1b/novel_N2.txt are
skipped as a guard. Families: the 19 second-pass prior families (tools/dream/o0/priors3) and the 19 roles-only ones
(priors4). For each (variant, family): first program that reproduces the 3 train pairs, its prediction on the test pair.
Recorded rows: every fit, with member (the variant's task is one of the family's sources), exact, residual cells.
Output: results/o0/t75_density_<part>.jsonl.txt and a summary on stdout. Synthetic data never counts as evidence.
usage: python3 t75_density.py <variants> <part> <parts>"""
import hashlib, importlib.util, json, os, random, re, signal, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GEN = '/home/claude/work/corpora/ARC-GEN'
sys.path.insert(0, GEN); sys.path.insert(0, os.path.join(REPO, 'tools/dream/o0'))
os.chdir(GEN)


class TO(Exception): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def v1_ids():
    src = open(os.path.join(GEN, 'task_list.py')).read()
    v1 = src.split('# V1 Tasks')[1].split('# V2 Tasks')[0]
    return sorted(set(re.findall(r'from tasks import task_([0-9a-f]{8})', v1)))


def families():
    out = []
    for d in ('priors3', 'priors4'):
        for f in sorted(os.listdir(os.path.join(REPO, 'tools/dream/o0', d))):
            if not f.endswith('.py'): continue
            s = importlib.util.spec_from_file_location('%s_%s' % (d, f[:-3]), os.path.join(REPO, 'tools/dream/o0', d, f))
            M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
            if os.environ.get('SLOTS'):                       # T73 density check: slot-augmented binder
                import slots; M = slots.Augmented(M, os.environ['SLOTS'])
            out.append((d, f[:-3], M, set(getattr(M, 'MEMBERS', []))))
    return out


def seed(t, v, k): return int(hashlib.sha256(('%s:%d:%d' % (t, v, k)).encode()).hexdigest()[:12], 16)


def variant(mod, t, v):
    pairs = []
    for k in range(4):
        random.seed(seed(t, v, k))
        try:
            signal.alarm(10); ex = mod.generate(); signal.alarm(0)
        except BaseException:
            signal.alarm(0); return None
        pairs.append({'input': ex['input'], 'output': ex['output']})
    return {'train': pairs[:3], 'test': pairs[3:]}


def first_fit(M, T, budget=8):
    try:
        signal.alarm(budget); progs = [p for fam in M.FAMILIES for p in fam(T['train'])]; signal.alarm(0)
    except BaseException:
        signal.alarm(0); return None
    for name, cost, fn in progs:
        try:
            signal.alarm(5); ok = all(fn(p['input']) == p['output'] for p in T['train']); signal.alarm(0)
        except BaseException:
            signal.alarm(0); ok = False
        if ok:
            try:
                signal.alarm(5); pr = fn(T['test'][0]['input']); signal.alarm(0)
            except BaseException:
                signal.alarm(0); pr = None
            exp = T['test'][0]['output']
            res = None
            if isinstance(pr, list) and pr and len(pr) == len(exp) and len(pr[0]) == len(exp[0]):
                res = sum(a != b for ra, rb in zip(pr, exp) for a, b in zip(ra, rb))
            return {'program': name, 'exact': pr == exp, 'residual_cells': res}
    return None


def main():
    V, part, parts = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    n2 = set(x for x in re.split(r'[,\s]+', open(os.path.join(REPO, 'tools/m1b/novel_N2.txt')).read()) if x)
    ids = [t for t in v1_ids() if t not in n2]
    if os.environ.get('DENSITY_TASKS'):                   # T73 density check: a subset (json list of ARC-1 ids)
        keep = set(json.load(open(os.environ['DENSITY_TASKS']))); ids = [t for t in ids if t in keep]
    ids = ids[part::parts]
    fams = families()
    commit = os.popen('git -C %s rev-parse HEAD' % GEN).read().strip()
    tag = ('slots_%s_' % os.environ['SLOTS']) if os.environ.get('SLOTS') else ''
    path = os.path.join(REPO, 'results/o0/t75_density_%s%d.jsonl.txt' % (tag, part))
    done = []                                   # resume: keep rows of fully finished tasks, redo the last one
    if os.path.exists(path):
        rows = [json.loads(l) for l in open(path) if l.strip()]
        order = []
        for r in rows:
            if r['task'] not in order: order.append(r['task'])
        if order:
            keep = set(order[:-1]); done = [t for t in ids if t in keep or ids.index(t) < ids.index(order[-1])]
            with open(path, 'w') as f:
                for r in rows:
                    if r['task'] in done: f.write(json.dumps(r) + '\n')
    ids = [t for t in ids if t not in set(done)]
    out = open(path, 'a')
    t0 = time.time(); nvar = nfit = 0
    for i, t in enumerate(ids):
        mod = importlib.import_module('tasks.task_' + t)
        for v in range(V):
            T = variant(mod, t, v)
            if T is None: continue
            nvar += 1
            for d, name, M, mem in fams:
                r = first_fit(M, T)
                if r:
                    nfit += 1
                    out.write(json.dumps(dict(task=t, v=v, dir=d, family=name, member=t in mem, **r)) + '\n')
        out.flush()
        if i % 10 == 0:
            print(json.dumps({'done': i, 'of': len(ids), 'variants': nvar, 'fits': nfit, 's': round(time.time() - t0)}), flush=True)
    print(json.dumps({'part': part, 'tasks': len(ids), 'variants': nvar, 'fits': nfit, 'commit': commit, 's': round(time.time() - t0)}), flush=True)


if __name__ == '__main__':
    main()
