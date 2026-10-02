"""Check prior-concept families mined from solution texts (cycle 27, Oct 1 2026; Len: shared prior concepts across
solution lines, WordNet/VerbNet-style normalisation). Each family tools/dream/o0/priors2/<concept>.py anti-unifies
the one-off programs of its member tasks. Measured on design data only (ARC-1 training minus N2, plus the 99), with
line_check.run (first program that reproduces every training pair; one harness test check per task and version):
members fit / exact; population fires, fit, exact, wrong; exact on non-members; new over V32 (non-member design tasks
V32 fails). Output: results/o0/prior_ledger.jsonl.txt.
usage: [PRIOR_DIR=priors3] python3 prior_check.py <v32_fail.json> <concept>..."""
import importlib.util, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import line_check as LC

HERE = os.path.dirname(os.path.abspath(__file__))
PDIR = os.environ.get('PRIOR_DIR', 'priors2')          # T65 (Fable v10b): PRIOR_DIR=priors3 measures the second pass
LEDGER = 'results/o0/prior_ledger.jsonl.txt' if PDIR == 'priors2' else 'results/o0/%s_ledger.jsonl.txt' % PDIR
SLOTS = os.environ.get('SLOTS')                        # T73 (Fable v14 O5): mdl | default -> slot-augmented binder (slots.py)
if SLOTS:
    LEDGER = 'results/o0/%s_slots_%s_ledger.jsonl.txt' % (PDIR, SLOTS)


def main():
    v32f = set(json.load(open(sys.argv[1])))
    keys = [x for x in sorted(LC.tr) if x not in LC.N2] + sorted(LC.D99)
    for c in sys.argv[2:]:
        t0 = time.time()
        p = os.path.join(HERE, PDIR, c + '.py')
        spec = importlib.util.spec_from_file_location('P_%s_%s' % (PDIR, c), p); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
        if SLOTS:
            import slots; M = slots.Augmented(M, SLOTS)
        mem = list(getattr(M, 'MEMBERS', []))
        fired = fit = 0; exact, wrong = [], []; slow = 0.0
        for x in keys:
            s = time.time(); r = LC.run(M, x, budget=8); slow = max(slow, time.time() - s)
            if not r: continue
            fired += bool(r.get('fired')); fit += bool(r.get('fit'))
            if r.get('fit'): (exact if r.get('exact') else wrong).append(x)
        row = {'concept': c, 'members': mem, 'members_exact': [x for x in exact if x in mem], 'members_wrong': [x for x in wrong if x in mem],
               'pop_n': len(keys), 'pop_fired': fired, 'pop_fit': fit, 'pop_exact': len(exact), 'pop_wrong': len(wrong),
               'exact_other': [x for x in exact if x not in mem], 'wrong_other': [x for x in wrong if x not in mem],
               'new_over_v32': [x for x in exact if x not in mem and x in v32f], 'max_s': round(slow, 2),
               'lines': sum(1 for _ in open(p)), 'seconds': round(time.time() - t0, 1), 'time': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())}
        with open(os.path.join(LC.REPO, LEDGER), 'a') as f: f.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
