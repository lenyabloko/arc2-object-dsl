import glob, importlib, sys, time, json, signal, inspect, hashlib
sys.path[:0] = ['/home/claude/work/codex', '/home/claude/work/stubs']
class TO(BaseException): pass
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
atoms = {}
for f in sorted(glob.glob('/home/claude/work/codex/detectors/*.py')):
    mod = 'detectors.' + f.split('/')[-1][:-3]
    m = importlib.import_module(mod)
    for name in dir(m):
        fn = getattr(m, name)
        if name.endswith('_evidence') and not name.startswith('_') and callable(fn) and getattr(fn, '__module__', '') == mod:
            try: npar = len([p for p in inspect.signature(fn).parameters.values() if p.default is inspect._empty])
            except Exception: npar = 1
            if npar == 1: atoms[f'{mod[10:]}.{name}'] = fn
part, nparts, limit = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
grids = json.load(open('population.json'))[:limit]
names = sorted(atoms)[part::nparts]
out = open(f'atoms_{part}.jsonl', 'w')
for n in names:
    fn = atoms[n]; ext = []; t0 = time.time(); errs = 0
    for gi, g in enumerate(grids):
        try:
            signal.setitimer(signal.ITIMER_REAL, 0.3)
            ev = fn(g)
            if ev:
                ext.append([gi, hashlib.sha1(json.dumps(ev, sort_keys=True, default=str).encode()).hexdigest()[:10]])
        except TO: errs += 1
        except Exception: errs += 1
        finally: signal.setitimer(signal.ITIMER_REAL, 0)
    out.write(json.dumps({"atom": n, "ext": ext, "ms": round((time.time() - t0) / max(1, len(grids)) * 1000, 2), "errs": errs}) + "\n"); out.flush()
