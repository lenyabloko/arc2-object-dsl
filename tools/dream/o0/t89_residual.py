"""Fable v20 B.3, T89 (diagnostic, nothing ships on it): residual after the best fit, on the 13 T86 tasks
(results/o0/t86_heldout.json minus dd2401ed, v20 A.4). Training pairs only; no test output is read.

For each task, every (column, row assignment, bound constants) the engine can form on the training pairs is applied
to every training input. score = output cells reproduced / output cells, summed over the pairs (a prediction of the
wrong size reproduces nothing). The identity (output = input) is the baseline. For the best candidate:
  residual cells, classified per pair:  extra    prediction ink where the output has background
                                        missing  output ink the prediction lacks
                                        colour   both ink, different colours
  placement  the missing cells are the extra cells moved (same shape up to a translation, on every pair)
  residual_fits_one_column   the pairs (prediction -> output) fit one situation exactly (a second step would close it)
usage: ENGINE=situation_engine_v1_frozen python3 t89_residual.py   (default ENGINE=situation_engine)"""
import importlib, itertools, json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC
SE = importlib.import_module(os.environ.get('ENGINE', 'situation_engine'))


def score(preds, train):
    tot = ok = 0
    for p, q in zip(preds, train):
        o = q['output']; n = len(o) * len(o[0]); tot += n
        if p is None or SE.dims(p) != SE.dims(o): continue
        ok += sum(p[y][x] == o[y][x] for y in range(len(o)) for x in range(len(o[0])))
    return ok / tot if tot else 0.0


def shape(cells):
    if not cells: return frozenset()
    y0 = min(y for y, _ in cells); x0 = min(x for _, x in cells)
    return frozenset((y - y0, x - x0) for y, x in cells)


def residual(preds, train):
    c = Counter(); placement = True; any_res = False
    for p, q in zip(preds, train):
        g, o = q['input'], q['output']
        if p is None or SE.dims(p) != SE.dims(o): c['size'] += 1; placement = False; continue
        b = SE.bgc(g)
        ex = {(y, x) for y in range(len(o)) for x in range(len(o[0])) if p[y][x] != o[y][x] and p[y][x] != b and o[y][x] == b}
        mi = {(y, x) for y in range(len(o)) for x in range(len(o[0])) if p[y][x] != o[y][x] and p[y][x] == b and o[y][x] != b}
        co = {(y, x) for y in range(len(o)) for x in range(len(o[0])) if p[y][x] != o[y][x] and p[y][x] != b and o[y][x] != b}
        c['extra'] += len(ex); c['missing'] += len(mi); c['colour'] += len(co)
        if ex or mi or co: any_res = True
        if not (ex and mi and shape(ex) == shape(mi)): placement = placement and not (ex or mi or co)
    return c, placement and any_res


def candidates(train):
    for how, C in SE.COLUMNS.items():
        names = [a for a, _ in C['args']]
        for vals in itertools.product(*[d for _, d in C['args']]):
            A = dict(zip(names, vals))
            try: Ks = C['bind'](train, A)
            except Exception: Ks = []
            for K in Ks[:40]:
                yield {'how': how, 'args': A, 'consts': K}


def main():
    held = [k for k in sorted(json.load(open(os.path.join(REPO, 'results/o0/t86_heldout.json')))) if k != 'dd2401ed']
    rows = []
    for k in held:
        T = LC.task(k)[0]['train']
        base = score([q['input'] for q in T], T)
        best = (base, None, [q['input'] for q in T])
        for S in candidates(T):
            preds = [SE.apply_raw(S, q['input']) for q in T]
            sc = score(preds, T)
            if sc > best[0] + 1e-9: best = (sc, S, preds)
        res, plac = residual(best[2], T)
        two = []
        if all(p is not None for p in best[2]):
            try: two = [SE.situation_key(S) for S in SE.fit([{'input': p, 'output': q['output']} for p, q in zip(best[2], T)])]
            except Exception: two = []
        tot = sum(v for kk, v in res.items() if kk != 'size')
        cls = 'size' if res.get('size') else ('placement' if plac else (max(('extra', 'missing', 'colour'), key=lambda z: res[z]) if tot else 'none'))
        rows.append({'task': k, 'identity_score': round(base, 3), 'best_score': round(best[0], 3),
                     'best': SE.situation_key(best[1]) if best[1] else 'identity', 'residual_cells': dict(res),
                     'class': cls, 'placement': plac, 'residual_fits_one_column': two[:3]})
        print(json.dumps(rows[-1]), flush=True)
    summ = {'n': len(rows), 'class': dict(Counter(r['class'] for r in rows)),
            'best_beats_identity': sum(r['best_score'] > r['identity_score'] for r in rows),
            'residual_closes_with_one_more_column': sum(bool(r['residual_fits_one_column']) for r in rows),
            'mean_best_score': round(sum(r['best_score'] for r in rows) / max(1, len(rows)), 3),
            'mean_identity_score': round(sum(r['identity_score'] for r in rows) / max(1, len(rows)), 3)}
    out = os.path.join(REPO, 'results/o0/t89_residual_%s.json' % ('v1' if 'v1' in SE.__name__ else 'v2'))
    json.dump({'engine': SE.__name__, 'summary': summ, 'rows': rows}, open(out, 'w'), indent=1)
    print(summ)


if __name__ == '__main__':
    main()
