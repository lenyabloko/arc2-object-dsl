"""LLM-proposed concept families (Dream D2, Fable guidance v7; cycle 22).

Each llm_<source>.py holds one family written by a language-model proposer from ONE design task's training pairs and
test inputs (test-blind: no test output was read), named by an outside concept (optics:spotlight,
mechanics:pin_tumbler, topology:genus, ...).  A family induces its parameters from the training pairs of the task at
hand and yields a program only if it reproduces every training output; nothing task-specific is stored in code
(G30(b) lint: no coordinate, size or colour constants; colours by role or induced from training).

Stage rule (V30): the stage runs LAST and only fills attempt slots that every earlier stratum left empty, so it can
never displace an earlier attempt.  It runs under its own clock: each family (fit + prediction) gets FAM_S seconds (measured max 0.6 s per family and 1.5 s per stage over the 120
public eval tasks and 898 design training tasks, after the V30 speed fixes) and
the whole stage STAGE_S seconds, never more than the task's own remaining time minus RESERVE_S; when a cap fires the
stage stops that family (or itself) and returns what it has, so a slow family cannot time out a task that an earlier
stratum already answered.
"""
import glob, importlib, json, os, signal, time

FAM_S, STAGE_S, RESERVE_S = 8.0, 60.0, 3.0

_HERE = os.path.dirname(os.path.abspath(__file__))
_FAMS = None


class _Cap(BaseException):
    pass


def _raise(*_a):
    raise _Cap()


def families():
    global _FAMS
    if _FAMS is None:
        _FAMS = []
        for path in sorted(glob.glob(os.path.join(_HERE, 'llm_*.py'))):
            name = os.path.basename(path)[:-3]
            try:
                mod = importlib.import_module(name)
                _FAMS.extend((name[4:], f) for f in mod.FAMILIES)
            except Exception:
                continue
    return _FAMS


def _grid(r):
    if r is None: return None
    try:
        r = [[int(v) for v in row] for row in r]
    except Exception:
        return None
    if not r or not r[0] or len(r) > 30 or len(r[0]) > 30 or any(len(row) != len(r[0]) for row in r): return None
    if any(v < 0 or v > 9 for row in r for v in row): return None
    return r


def _capped(seconds, f, *args):
    """run f(*args) under a nested real-time cap; the outer timer (the task's alarm) is restored with the time spent
    subtracted.  The cap re-fires every 50 ms until f returns, so a swallowed exception cannot outlive it."""
    old_h = signal.getsignal(signal.SIGALRM)
    outer = signal.getitimer(signal.ITIMER_REAL)[0]
    t0 = time.time()
    signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, max(seconds, 0.01), 0.05)
    try:
        return f(*args)
    finally:
        while True:
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
                break
            except _Cap:
                pass
        signal.signal(signal.SIGALRM, old_h)
        if outer:
            signal.setitimer(signal.ITIMER_REAL, max(outer - (time.time() - t0), 0.001))


def _fit_and_predict(fam, task):
    out = []
    for name, cost, fn in fam(task["train"]):
        if not all(_grid(fn(p["input"])) == p["output"] for p in task["train"]): continue
        preds = [_grid(fn(q["input"])) for q in task["test"]]
        if any(p is None for p in preds): continue
        out.append((name, preds))
    return out


def search(task, taken=(), need=2):
    """programs from the LLM families that reproduce every training pair, in family order (source id) then yield
    order; predictions equal to one in `taken` are skipped; stops once `need` programs are found."""
    outer = signal.getitimer(signal.ITIMER_REAL)[0]
    budget = STAGE_S if not outer else min(STAGE_S, outer - RESERVE_S)
    if budget <= 0.5: return []
    t_end = time.time() + budget
    seen = set(taken); found = []
    for src, fam in families():
        if len(found) >= need: break
        left = t_end - time.time()
        if left <= 0.05: break
        try:
            progs = _capped(min(FAM_S, left), _fit_and_predict, fam, task)
        except _Cap:
            continue
        except Exception:
            continue
        for name, preds in progs:
            key = json.dumps(preds)
            if key in seen: continue
            seen.add(key)
            found.append({"abstraction": "llm", "specific": False, "mode": "llm", "rules": ([], []),
                          "program": name, "source": src, "preds": preds})
    return found
