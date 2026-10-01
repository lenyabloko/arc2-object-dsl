"""Harness for mechanism cards (Fable review-page audit item 2 / G57, T49; Fable v10 generator-first cards).

A mechanism card is authored on the review page (`priors` collection, card_type 'mechanism'). The supervisor implements
it literally from the card's fields (generator, stop condition, parameters, participants, preconditions), test-blind,
as a family module in tools/dream/o0/mech/<card id>.py with the D2 family interface:
    CARD = "<card id>"
    FAMILIES = [fam]      fam(train_pairs) -> iterable of (name, cost, fn), fn(grid) -> grid
The harness then measures, on the design population only (ARC-1 training minus N2, plus the 99 = half A + half B;
never N2, never the 21 sealed tasks):
    lint        the card has every required field; each parameter has a finite domain; the module has no
                coordinate / size / colour literals beyond 0-2 (G30 b)
    fires       tasks where the family yields a program (its preconditions hold), and where a program reproduces
                every training pair (training fit); density = share of the design population
    round trip  the card's own tasks: how many have every training pair reproduced
    solves      one harness test check per task with a training fit (first program only); split into the card's
                own tasks and the rest (non-source exact = design reuse; Reuse (R) proper is counted at cycle A)
Output: a JSON patch of h_* fields for the card document (written back with the ArtifactData tool) and a ledger row
in results/o0/mech_ledger.jsonl.txt.
usage: python3 mech_admit.py <card.json> <module.py> <patch_out.json> [--limit N] [--v29 <c32 results.jsonl> <e99_v29.jsonl>]
  --v29: count clean gains (exact on design tasks V29 fails); N2 rows of the c32 file are skipped unread."""
import ast, importlib.util, json, os, re, signal, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
REQ = ['name', 'generator', 'stop', 'params', 'participants', 'preconditions']


class TO(Exception): pass


signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def rd(f): return [x for x in re.split(r'[,\s]+', open(os.path.join(REPO, 'tools/m1b', f)).read()) if x]


def population():
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ts = json.load(open(B + 'arc-agi_training_solutions.json'))
    ev = json.load(open(B + 'arc-agi_evaluation_challenges.json')); es = json.load(open(B + 'arc-agi_evaluation_solutions.json'))
    N2 = set(rd('novel_N2.txt')); d99 = rd('deval_a.txt') + rd('deval_b.txt')
    P = {k: (tr[k], ts[k]) for k in sorted(tr) if k not in N2}
    P.update({k: (ev[k], es[k]) for k in d99})
    return P


def lint(card, src):
    msgs = []
    miss = [k for k in REQ if not str(card.get(k, '')).strip()]
    if miss: msgs.append('missing: ' + ', '.join(miss))
    if not re.search(r'(∈|\bin\b)\s*\{', str(card.get('params', ''))): msgs.append('no finite parameter domain written as "name ∈ {…}"')
    declared = {int(x) for x in re.findall(r'\b\d+\b', str(card.get('params', '')))}
    bad = sorted({n.value for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, int)
                  and not isinstance(n.value, bool) and abs(n.value) > 2 and n.value not in declared})
    if bad: msgs.append('integer literals > 2 in code that are not declared parameter values: ' + ', '.join(map(str, bad[:8])))
    return msgs


def main():
    cardf, modf, outf = sys.argv[1:4]
    limit = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else None
    v29_fail = None
    if '--v29' in sys.argv:
        i = sys.argv.index('--v29'); N2 = set(rd('novel_N2.txt')); v29_fail = set()
        for l in open(sys.argv[i + 1]):
            d = json.loads(l)
            if d.get('task') in N2: continue
            if not d.get('exact'): v29_fail.add(d['task'])
        for l in open(sys.argv[i + 2]):
            d = json.loads(l); f = d.get('final')
            if not (isinstance(f, list) and any(f)) or d.get('exact') is False: v29_fail.add(d['task'])
    card = json.load(open(cardf)); card = card.get('data', card)
    src = open(modf).read()
    spec = importlib.util.spec_from_file_location('M', modf); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
    own = set(re.findall(r'\b[0-9a-f]{8}\b', str(card.get('tasks', '')))) - set(card.get('test_seen') or [])
    P = population(); keys = sorted(P)[:limit] if limit else sorted(P)
    lint_msgs = lint(card, src)
    fired, fit, exact_own, exact_other, wrong, rt_ok, errors = [], [], [], [], [], [], 0
    t0 = time.time()
    for k in keys:
        task, sol = P[k]
        try:
            signal.alarm(20)
            progs = []
            for fam in M.FAMILIES:
                progs += list(fam(task['train']))
            signal.alarm(0)
        except TO:
            errors += 1; continue
        except Exception:
            signal.alarm(0); errors += 1; continue
        if not progs: continue
        fired.append(k)
        good = None
        for name, cost, fn in progs:
            try:
                signal.alarm(10)
                if all(fn(p['input']) == p['output'] for p in task['train']): good = (name, fn)
                signal.alarm(0)
            except Exception:
                signal.alarm(0)
            if good: break
        if not good: continue
        fit.append(k)
        if k in own: rt_ok.append(k)
        try:                                            # one harness test check per task, first fitting program
            signal.alarm(10); preds = [good[1](q['input']) for q in task['test']]; signal.alarm(0)
            ex = all(preds[i] == sol[i] for i in range(len(sol)))
        except Exception:
            signal.alarm(0); ex = False
        (exact_own if k in own else exact_other).append(k) if ex else wrong.append(k)
    n = len(keys)
    patch = {
        'h_status': ('checked' if not lint_msgs else 'lint issues') + ' (mechanism harness, ' + time.strftime('%b %d %H:%M UTC', time.gmtime()) + ')',
        'h_lint': 'ok' if not lint_msgs else '; '.join(lint_msgs),
        'h_phi': f'preconditions hold on {len(fired)} of {n} design tasks ({len(fired) / max(n, 1):.3f}); training fit on {len(fit)}',
        'h_roundtrip': f'{len(rt_ok)} of {len(own)} of the card\'s tasks reproduced' + (f' (not: {", ".join(sorted(own - set(rt_ok))[:6])})' if own - set(rt_ok) else ''),
        'h_solves': f'{len(exact_own) + len(exact_other)} exact ({len(exact_own)} own, {len(exact_other)} other), {len(wrong)} wrong'
                    + (f'; new over V29: {len([k for k in exact_own + exact_other if k in v29_fail])}' if v29_fail is not None else ''),
        'h_R': f'pending (cycle A); design reuse now: {len(exact_other)} non-source exact',
        'h_note': f'code {os.path.relpath(modf, REPO)}; {errors} errors/timeouts; {round(time.time() - t0)} s; test outputs used only for the one check per fitted task',
    }
    json.dump(patch, open(outf, 'w'), indent=1, ensure_ascii=False)
    os.makedirs(os.path.join(REPO, 'results/o0'), exist_ok=True)
    with open(os.path.join(REPO, 'results/o0/mech_ledger.jsonl.txt'), 'a') as f:
        f.write(json.dumps({'card': getattr(M, 'CARD', card.get('name')), 'n': n, 'fired': len(fired), 'fit': len(fit),
                            'exact_own': exact_own, 'exact_other': exact_other, 'wrong': wrong, 'roundtrip': [len(rt_ok), len(own)],
                            'lint': lint_msgs, 'time': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())}) + '\n')
    print(json.dumps(patch, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
