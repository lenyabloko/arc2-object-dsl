"""Check Claude's one-off attempts (cycle 26, Oct 1 2026): which unsolved design tasks can Claude solve on its own?
Len (Oct 1): his time goes first to tasks Claude cannot solve. For each task, a subagent writes
tools/dream/o0/oneoff/<task>.py (FAMILIES, test-blind, from that task's training pairs only). This script takes the
first two distinct test predictions of programs that reproduce every training pair (Kaggle's two attempts) and makes
one harness check per task. N2 and sealed tasks are never touched (line_check.task guards them).
Output: results/o0/oneoff_ledger.jsonl.txt rows {task, fit, exact, programs, time} and a summary line.
usage: python3 oneoff_check.py <task id>..."""
import importlib.util, json, os, re, signal, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import line_check as LC

HERE = os.path.dirname(os.path.abspath(__file__))


def attempt(k):
    t = LC.task(k)
    if t is None: return None
    T, S = t
    p = os.path.join(HERE, 'oneoff', k + '.py')
    if not os.path.exists(p): return {'task': k, 'missing': True}
    try:
        spec = importlib.util.spec_from_file_location('O' + k, p); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
        signal.alarm(30); progs = [q for fam in M.FAMILIES for q in fam(T['train'])]; signal.alarm(0)
    except BaseException as e:
        signal.alarm(0); return {'task': k, 'fit': False, 'exact': False, 'error': repr(e)[:80]}
    preds, names = [], []
    for name, cost, fn in progs:
        try:
            signal.alarm(10)
            ok = all(fn(x['input']) == x['output'] for x in T['train'])
            pr = [fn(q['input']) for q in T['test']] if ok else None
            signal.alarm(0)
        except BaseException:
            signal.alarm(0); continue
        if ok and pr not in preds: preds.append(pr); names.append(name)
        if len(preds) == 2: break
    ex = any(all(pr[i] == S[i] for i in range(len(S))) for pr in preds)
    return {'task': k, 'fit': bool(preds), 'exact': ex, 'programs': names}


def main():
    ks = [a for a in sys.argv[1:] if re.fullmatch(r'[0-9a-f]{8}', a)]
    out = os.path.join(LC.REPO, 'results/o0/oneoff_ledger.jsonl.txt'); n = ex = fit = 0
    with open(out, 'a') as f:
        for k in ks:
            r = attempt(k)
            if r is None: continue
            r['time'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime()); f.write(json.dumps(r) + '\n'); print(json.dumps(r), flush=True)
            n += 1; ex += bool(r.get('exact')); fit += bool(r.get('fit'))
    print(json.dumps({'n': n, 'fit': fit, 'exact': ex}))


if __name__ == '__main__':
    main()
