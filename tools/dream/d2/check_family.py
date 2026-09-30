"""usage: python3 check_family.py <family_module.py> <task.json>
Runs every family in FAMILIES on the task's training pairs and reports, per program the family yields, whether it
reproduces each training output; then shows the shape of its predictions for the test inputs (no answers here)."""
import importlib.util, json, sys, traceback
spec = importlib.util.spec_from_file_location('F', sys.argv[1]); F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
t = json.load(open(sys.argv[2]))
for fam in F.FAMILIES:
    try:
        progs = list(fam(t['train']))
    except Exception:
        print(fam.__name__, 'raised:'); traceback.print_exc(); continue
    if not progs: print(fam.__name__, 'yields no program (precondition failed or no fit)'); continue
    for name, cost, fn in progs:
        fits = []
        for i, p in enumerate(t['train']):
            try: fits.append(fn(p['input']) == p['output'])
            except Exception as e: fits.append(f'error {e!r}')
        shapes = []
        for q in t['test']:
            try: o = fn(q['input']); shapes.append((len(o), len(o[0])) if o else None)
            except Exception as e: shapes.append(f'error {e!r}')
        print(fam.__name__, '|', name, '| cost', cost, '| train fits', fits, '| test output shapes', shapes)
