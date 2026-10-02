"""T59 (Fable v10a, re-run under v11 G63): engine parity between the Datalog fixpoint (o0_rules.dl.txt via engine.py)
and the Dream-side O0 materialisation (tools/dream/o0/items/*.py through harness.py), per design grid.

Design grids: inputs (train and test) of the design tasks = training challenges minus novel_N2, plus the evaluation
tasks in deval_a / deval_b. Individuals: harness.individuals(P, grid, 'nbccg') with probe tools/m1b/v34. For every
grid, both sides produce {item + json(params): sorted [[i, j], ...]} for every item and parameter setting; canonical
JSON -> sha256; equal / not, W_mat, seconds per side.
v11 G63: (1) rcc8_DC is the lazy view of the rule file, answered by engine.Program.query (not stored, no W_mat);
(2) dir_rel and allen are stored for object-object pairs and for cell-object pairs whose cell is in the change set
delta; delta of a training input = cells whose colour differs from its training output (same shape), empty for a
test input and for a size-changing training pair; the Python extension is filtered the same way; (3) a relation
whose stored facts exceed REL_CAP on a grid is skipped there (with everything that uses it) on both sides and logged.
Training outputs are read for delta only; test outputs and *_solutions.json are never read.
v12 G70 (default, --delta g70): Delta on a test input = the training Delta's role pattern evaluated on the test input,
when the task is same-size and Route A finds one: targets = the individuals (objects and background cells) meeting the
training change set, msc / lcs / candidates / holds of routeA_t24 (k = 1, W_sub <= 5e4, 30 s) over the lattice names
plus routeA_t24's base roles and every O0 role setting (unrestricted, Python items), exact on every training pair,
picked in routeA_t24's order (widest extension on the test inputs, shorter chain, name); Delta_test = the cells of the
individuals the pattern selects on that test input. Otherwise (size-changing task, no exact pattern, budget / time,
or an empty selection on that test input) Delta = cells inside any object's bbox plus the one-cell border ring
(also for the inputs of size-changing training pairs). Never raw positions, never empty; branch logged per task.
T70: the same Route A run again with the Delta-restricted relations read from the Datalog fixpoint (dir_rel / allen
first arguments: objects and Delta cells) on training and test inputs; the task's slot-1 program (Route A's pick)
is compared with the unrestricted one.
usage additions: --delta g70|v11 (v11 = B1 behaviour: test / size-changing Delta empty); --tasks k1,k2 (smoke runs).
usage: python3 t59_parity.py [--part K --parts P]                  one part -> results/o0/t59_parity.partK.json
       python3 t59_parity.py --limit N [--part K --parts P]        smoke run -> results/o0/t59_parity.limit.json
       python3 t59_parity.py --merge P                             parts -> results/o0/t59_parity.json + summary
"""
import argparse, hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
O0 = os.path.join(ROOT, 'tools', 'dream', 'o0')
M1B = os.path.join(ROOT, 'tools', 'm1b')
OUT = os.path.join(ROOT, 'results', 'o0')
sys.path[:0] = [HERE, O0]
import engine  # noqa: E402
import harness as Hn  # noqa: E402
import signal  # noqa: E402
BASE_ROLES = ("touches", "inside", "contains", "aligned", "same_shape")
RA = None                                                  # routeA_t24, imported in run_g70 (needs the probe in argv)

CAP = 200000                                               # G63 cap on derived facts per grid
REL_CAP = 50000                                            # G63 (v11) cap on stored facts per relation and grid
RESTRICTED = ("allen", "dir_rel")                          # first argument: objects and change-set cells only


def design_grids():
    tr = json.load(open(Hn.B + 'arc-agi_training_challenges.json'))
    ev = json.load(open(Hn.B + 'arc-agi_evaluation_challenges.json'))
    n2 = set(open(os.path.join(M1B, 'novel_N2.txt')).read().split())
    dv = []
    for f in ('deval_a.txt', 'deval_b.txt'):
        dv += [k for k in re.split(r'[,\s]+', open(os.path.join(M1B, f)).read()) if k]
    tasks = [(k, tr[k]) for k in sorted(tr) if k not in n2] + [(k, ev[k]) for k in sorted(set(dv)) if k not in n2]
    out = []
    for k, t in tasks:
        for i, p in enumerate(t['train']):
            a, b = p['input'], p['output']
            if (len(a), len(a[0])) == (len(b), len(b[0])):
                d = [(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]]
                out.append(("%s:%d" % (k, i), a, d, "train"))
            else: out.append(("%s:%d" % (k, i), a, [], "train_size_change"))
        for i, p in enumerate(t['test']):
            out.append(("%s:%d" % (k, len(t['train']) + i), p['input'], [], "test"))
    return out, n2


def edb(grid, inds, bg, delta=()):
    """primitive facts only: grid size, cells with colour, background colour, individuals' kind and cells, change set"""
    H, W = len(grid), len(grid[0])
    return {"size": [(H, W)], "cell": [(y, x, grid[y][x]) for y in range(H) for x in range(W)], "bg": [(bg,)],
            "ind": [(i, x["kind"]) for i, x in enumerate(inds)],
            "pix": [(i, y, x) for i, ind in enumerate(inds) for (y, x) in ind["pix"]],
            "delta": [tuple(c) for c in delta]}


def skey(it, prm):
    return it["name"] + (json.dumps(prm, sort_keys=True) if prm else "")


def py_side(items, grid, inds, bg, delta=()):
    """Python items; allen / dir_rel filtered to first arguments that are objects or change-set cells"""
    ds = set(map(tuple, delta))
    keep = {i for i, x in enumerate(inds) if x["kind"] == "object" or (x["kind"] == "cell" and x["pix"] <= ds)}
    ext, err = {}, {}
    for it in items:
        for prm in Hn.settings(it):
            try:
                e = Hn.extension(it, grid, inds, bg, prm)
                if it["name"] in RESTRICTED: e = {(i, j) for i, j in e if i in keep}
                ext[skey(it, prm)] = sorted([int(i), int(j)] for i, j in e)
            except Exception as e: err[skey(it, prm)] = repr(e)[:200]
    return ext, err


def dl_side(items, res, prog=None):
    """stored relations; lazy views (rcc8_DC) answered by prog.query; skipped relations are left out"""
    ext = {}
    for it in items:
        if it["name"] in res.skipped: continue
        if prog is not None and it["name"] in prog.views:
            rel = prog.query(res, it["name"])
            if rel is None: continue
        else: rel = res.relations.get(it["name"], [])
        keys = sorted(it.get("params") or {})
        by = {}
        for t in rel: by.setdefault(tuple(t[2:]), []).append([t[0], t[1]])
        for prm in Hn.settings(it):
            ext[skey(it, prm)] = sorted(by.get(tuple(prm[k] for k in keys), []))
    return ext


def digest(ext):
    return hashlib.sha256(json.dumps(ext, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(part, parts, limit):
    P = Hn.setup(os.path.join(M1B, 'v34'))
    items = Hn.load_items()
    prog = engine.Program(open(os.path.join(HERE, 'o0_rules.dl.txt')).read())
    grids, n2 = design_grids()
    grids = grids[part::parts][:limit] if limit else grids[part::parts]
    rows = []
    for n, (key, g, delta, dsrc) in enumerate(grids):
        assert key.split(":")[0] not in n2
        row = {"key": key, "H": len(g), "W": len(g[0]), "delta_src": dsrc, "n_delta": len(delta)}
        try: inds, names, bg = Hn.individuals(P, g, 'nbccg')
        except Exception as e:
            row["skip"] = repr(e)[:80]; rows.append(row); continue
        row["n_ind"] = len(inds); row["n_obj"] = sum(x["kind"] == "object" for x in inds)
        t0 = time.time(); pe, perr = py_side(items, g, inds, bg, delta); t1 = time.time()
        try:
            res = prog.run(edb(g, inds, bg, delta), rel_cap=REL_CAP); t2 = time.time()
            de = dl_side(items, res, prog); derr = None
        except Exception as e:
            res, de, derr, t2 = None, {}, repr(e)[:200], time.time()
        t3 = time.time()
        if res is not None and res.skipped:             # skipped on the Datalog side -> skipped on both sides
            row["skipped"] = res.skipped
            for k in [k for k in pe if k.split("{")[0] in res.skipped or k not in de]: del pe[k]
        row.update(py_s=round(t1 - t0, 4), dl_s=round(t2 - t1, 4), dc_s=round(t3 - t2, 4),
                   n_ext=sum(len(v) for v in pe.values()))
        if perr: row["py_err"] = perr
        if derr: row["dl_err"] = derr
        row["eq"] = (not perr and not derr and digest(pe) == digest(de))
        row["mismatch"] = sorted({k.split("{")[0] for k in set(pe) | set(de) if pe.get(k) != de.get(k)})
        if not row["eq"] and res is not None:
            row["diff"] = {k: [len(set(map(tuple, pe.get(k, []))) - set(map(tuple, de.get(k, [])))),
                               len(set(map(tuple, de.get(k, []))) - set(map(tuple, pe.get(k, []))))]
                           for k in set(pe) | set(de) if pe.get(k) != de.get(k)}
        if res is not None:
            row["wmat"] = res.wmat
            row["top_rule"] = max(res.by_rule.items(), key=lambda kv: kv[1])
            row["top_pred"] = sorted(res.by_pred.items(), key=lambda kv: -kv[1])[:5]
            row["rel_max"] = row["top_pred"][0] if row["top_pred"] else None
        rows.append(row)
        if n % 50 == 0:
            print(json.dumps({q: row.get(q) for q in ("key", "eq", "wmat", "py_s", "dl_s", "mismatch")}), file=sys.stderr, flush=True)
    return rows


# ------------------------------------------------------------------------------------------------ v12 G70 / T70
def rname(it, prm):                                        # = harness.vcov role naming
    return it["name"] + ("[" + ",".join(f"{k}={v}" for k, v in sorted(prm.items())) + "]" if prm else "")


def bbox_border(grid, inds):
    """cells inside any object's bbox plus the one-cell border ring of the grid"""
    H, W = len(grid), len(grid[0]); out = set()
    for x in inds:
        if x["kind"] != "object": continue
        ys = [q[0] for q in x["pix"]]; xs = [q[1] for q in x["pix"]]
        out |= {(y, c) for y in range(min(ys), max(ys) + 1) for c in range(min(xs), max(xs) + 1)}
    out |= {(y, c) for y in range(H) for c in range(W) if y in (0, H - 1) or c in (0, W - 1)}
    return sorted(out)


def role_abox(inds, names, ext_by_role):
    """(names, R): base roles of routeA_t24 (roles_of; empty above 400 individuals, as harness.vcov) + O0 role settings"""
    RA.ROLES = BASE_ROLES
    R = dict(RA.roles_of([{"pix": x["pix"]} for x in inds]) if len(inds) <= 400 else {r: [set() for _ in inds] for r in BASE_ROLES})
    for nm, pairs in ext_by_role.items():
        R[nm] = [set() for _ in inds]
        for i, j in pairs: R[nm][i].add(j)
    return names, R


def route_a_cells(pairs, tests):
    """routeA_t24's search over (names, R, X) training pairs, k = 1 (harness.vcov's setting for the O0 roles); returns
    (pick, info). pick = (chain, name) in routeA_t24's order or None."""
    RA.ROLES = tuple(sorted(pairs[0][1])); RA.K = 1
    if not any(X for _, _, X in pairs): return None, {"why": "no_targets"}
    W = [0]; exact = []; info = {}
    try:
        signal.alarm(30)
        C = None
        for names, R, X in pairs:
            for i in sorted(X):
                m = RA.msc(i, names, R, 1); C = m if C is None else RA.lcs(C, m)
        for chain, name in RA.candidates(C):
            if all({i for i in range(len(nm)) if RA.holds(i, chain, name, nm, R, W)} == X for nm, R, X in pairs):
                gen = sum(1 for nm_q, R_q in tests for i in range(len(nm_q)) if RA.holds(i, chain, name, nm_q, R_q, W))
                exact.append((-gen, len(chain), name is None, str(name), chain, name))
        signal.alarm(0)
    except RA.Budget:
        signal.alarm(0); info["budget"] = True
    except RA.TO:
        info["timeout"] = True
    finally:
        signal.alarm(0)
    info.update(W_sub=W[0], n_exact=len(exact))
    if not exact:
        info["why"] = "timeout" if info.get("timeout") else ("budget" if info.get("budget") else "no_exact")
        return None, info
    p = min(exact)
    return (tuple(p[4]), p[5]), info


def ext_sel(pick, names, R):
    W = [-10 ** 9]                                          # evaluation of a chosen pattern: not a search, no budget
    return [i for i in range(len(names)) if RA.holds(i, pick[0], pick[1], names, R, W)]


def run_g70(part, parts, limit, only=None):
    global RA
    P = Hn.setup(os.path.join(M1B, 'v34'))
    argv = sys.argv; sys.argv = [argv[0], os.path.join(M1B, 'v34')]
    sys.path.insert(0, os.path.join(ROOT, 'tools', 'dream'))
    import routeA_t24 as _RA                               # noqa: E402  (sets SIGALRM -> TO, chdir to the probe)
    RA = _RA; sys.argv = argv
    items = Hn.load_items()
    prog = engine.Program(open(os.path.join(HERE, 'o0_rules.dl.txt')).read())
    tr = json.load(open(Hn.B + 'arc-agi_training_challenges.json'))
    ev = json.load(open(Hn.B + 'arc-agi_evaluation_challenges.json'))
    n2 = set(open(os.path.join(M1B, 'novel_N2.txt')).read().split())
    dv = []
    for f in ('deval_a.txt', 'deval_b.txt'):
        dv += [k for k in re.split(r'[,\s]+', open(os.path.join(M1B, f)).read()) if k]
    tasks = [(k, tr[k]) for k in sorted(tr) if k not in n2] + [(k, ev[k]) for k in sorted(set(dv)) if k not in n2]
    if only: tasks = [t for t in tasks if t[0] in only]
    tasks = tasks[part::parts][:limit] if limit else tasks[part::parts]
    roles = [(it, prm) for it in items if it["kind"] == "role" for prm in Hn.settings(it)]
    rows, trows = [], []
    for n, (key, t) in enumerate(tasks):
        assert key not in n2
        same = all((len(p['input']), len(p['input'][0])) == (len(p['output']), len(p['output'][0])) for p in t['train'])
        G = []                                              # per input grid: [name, grid, kind, inds, names, bg, full ext]
        seg_fail = False
        for i, p in enumerate(t['train'] + t['test']):
            kind = "train" if i < len(t['train']) else "test"
            try: inds, names, bg = Hn.individuals(P, p['input'], 'nbccg')
            except Exception: G.append(("%s:%d" % (key, i), p['input'], kind, None, None, None, None)); seg_fail |= kind == "test" or same; continue
            t0 = time.time(); full = {}
            for it in items:
                for prm in Hn.settings(it):
                    try: full[skey(it, prm)] = Hn.extension(it, p['input'], inds, bg, prm)
                    except Exception as e: full[skey(it, prm)] = e
            G.append(("%s:%d" % (key, i), p['input'], kind, inds, names, bg, full, time.time() - t0))
        trow = {"task": key, "same_size": same}
        # ---- training Delta (observed change set) and the G70 test Delta
        deltas = {}
        for i, p in enumerate(t['train']):
            a, b = p['input'], p['output']
            if same: deltas[i] = [(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]]
            elif G[i][3] is not None: deltas[i] = bbox_border(a, G[i][3])
        tests = [j for j in range(len(t['train']), len(G))]
        pickU, infoU = None, {"why": "size_change"} if not same else {"why": "segmentation"}
        if same and not seg_fail and all(G[i][3] is not None for i in range(len(G))):
            def abox_u(g):
                return role_abox(g[3], g[4], {rname(it, prm): g[6][skey(it, prm)] for it, prm in roles
                                              if not isinstance(g[6][skey(it, prm)], Exception)})
            pr = []
            for i in range(len(t['train'])):
                nm, R = abox_u(G[i]); ch = set(deltas[i])
                pr.append((nm, R, {k for k, x in enumerate(G[i][3]) if x["pix"] & ch}))
            ts_ = [abox_u(G[j]) for j in tests]
            pickU, infoU = route_a_cells(pr, ts_)
            for j, (nm, R) in zip(tests, ts_):
                if pickU is None: continue
                sel = ext_sel(pickU, nm, R)
                cells = sorted(set().union(*[G[j][3][k]["pix"] for k in sel])) if sel else []
                if cells: deltas[j] = cells
        branch = {}
        for j in tests:
            if j in deltas: branch[j] = "role_pattern"
            elif G[j][3] is not None:
                deltas[j] = bbox_border(G[j][1], G[j][3])
                branch[j] = "bbox_border:" + ("pattern_selects_nothing" if pickU is not None else infoU.get("why", "?"))
            else: branch[j] = "skip:test_input_not_segmented"
        bs = set(branch.values())
        trow.update(branch=("role_pattern" if bs == {"role_pattern"} else (sorted(bs)[0] if len(bs) == 1 else "mixed")),
                    branch_per_test=[branch.get(j) for j in tests],
                    pattern=None if pickU is None else [list(pickU[0]), pickU[1]], route_a_unrestricted=infoU,
                    n_delta_test=[len(deltas.get(j, [])) for j in tests])
        # ---- T59 parity per grid with these Deltas (both sides apply the same Delta)
        dl_ext = {}
        for i, g in enumerate(G):
            name, grid, kind = g[0], g[1], g[2]
            delta = deltas.get(i, [])
            row = {"key": name, "H": len(grid), "W": len(grid[0]), "delta_src": kind if (kind == "test" or same) else "train_size_change",
                   "n_delta": len(delta), "delta_branch": branch.get(i, "observed" if (kind == "train" and same) else "bbox_border")}
            if g[3] is None: row["skip"] = "segmentation"; rows.append(row); continue
            inds, names, bg, full = g[3], g[4], g[5], g[6]
            ds = set(map(tuple, delta))
            keep = {k for k, x in enumerate(inds) if x["kind"] == "object" or (x["kind"] == "cell" and x["pix"] <= ds)}
            pe, perr = {}, {}
            for it in items:
                for prm in Hn.settings(it):
                    e = full[skey(it, prm)]
                    if isinstance(e, Exception): perr[skey(it, prm)] = repr(e)[:200]; continue
                    if it["name"] in RESTRICTED: e = {(a, b) for a, b in e if a in keep}
                    pe[skey(it, prm)] = sorted([int(a), int(b)] for a, b in e)
            t1 = time.time()
            try:
                res = prog.run(edb(grid, inds, bg, delta), rel_cap=REL_CAP); t2 = time.time()
                de = dl_side(items, res, prog); derr = None
            except Exception as e:
                res, de, derr, t2 = None, {}, repr(e)[:200], time.time()
            t3 = time.time()
            if res is not None and res.skipped:
                row["skipped"] = res.skipped
                for k in [k for k in pe if k.split("{")[0] in res.skipped or k not in de]: del pe[k]
            row.update(py_s=round(g[7], 4), dl_s=round(t2 - t1, 4), dc_s=round(t3 - t2, 4), n_ind=len(inds),
                       n_obj=sum(x["kind"] == "object" for x in inds), n_ext=sum(len(v) for v in pe.values()))
            if perr: row["py_err"] = perr
            if derr: row["dl_err"] = derr
            row["eq"] = (not perr and not derr and digest(pe) == digest(de))
            row["mismatch"] = sorted({k.split("{")[0] for k in set(pe) | set(de) if pe.get(k) != de.get(k)})
            if res is not None:
                row["wmat"] = res.wmat
                row["top_rule"] = max(res.by_rule.items(), key=lambda kv: kv[1])
                row["top_pred"] = sorted(res.by_pred.items(), key=lambda kv: -kv[1])[:5]
                row["rel_max"] = row["top_pred"][0] if row["top_pred"] else None
            rows.append(row); dl_ext[i] = de
        # ---- T70: Route A's slot-1 program with the Delta-restricted relations (Datalog fixpoint) vs unrestricted
        if same and pickU is not None or (same and infoU.get("why") in ("no_exact", "budget", "timeout")):
            if all(i in dl_ext for i in range(len(G))):
                def abox_r(i):
                    g = G[i]; de = dl_ext[i]
                    return role_abox(g[3], g[4], {rname(it, prm): [tuple(x) for x in de.get(skey(it, prm), [])] for it, prm in roles})
                pr = []
                for i in range(len(t['train'])):
                    nm, R = abox_r(i); ch = set(deltas[i])
                    pr.append((nm, R, {k for k, x in enumerate(G[i][3]) if x["pix"] & ch}))
                pickR, infoR = route_a_cells(pr, [abox_r(j) for j in tests])
                trow.update(route_a_restricted=infoR, pattern_restricted=None if pickR is None else [list(pickR[0]), pickR[1]],
                            slot1_changed=(pickR != pickU))

                def abox_b(i):                             # control: bbox u border restriction on every input (no
                    g = G[i]; ds = set(bbox_border(g[1], g[3]))   # training change set in the restriction); Python
                    keep = {k for k, x in enumerate(g[3]) if x["kind"] == "object" or x["pix"] <= ds}   # side = Datalog
                    ext = {}                                       # side by T59 parity
                    for it, prm in roles:
                        e = g[6][skey(it, prm)]
                        if isinstance(e, Exception): continue
                        ext[rname(it, prm)] = {(a, b) for a, b in e if a in keep} if it["name"] in RESTRICTED else e
                    return role_abox(g[3], g[4], ext)
                pr = []
                for i in range(len(t['train'])):
                    nm, R = abox_b(i); ch = set(deltas[i])
                    pr.append((nm, R, {k for k, x in enumerate(G[i][3]) if x["pix"] & ch}))
                pickB, infoB = route_a_cells(pr, [abox_b(j) for j in tests])
                trow.update(pattern_bbox_all=None if pickB is None else [list(pickB[0]), pickB[1]],
                            slot1_changed_bbox_all=(pickB != pickU))
        trows.append(trow)
        if n % 25 == 0:
            print(json.dumps({q: trow.get(q) for q in ("task", "branch", "pattern", "slot1_changed")}), file=sys.stderr, flush=True)
    return rows, trows


def t70_summary(trows):
    from collections import Counter
    br = Counter(r["branch"] for r in trows)
    cmp = [r for r in trows if "slot1_changed" in r]
    return {"tasks": len(trows), "same_size_tasks": sum(r["same_size"] for r in trows), "branch": dict(br),
            "test_inputs_per_branch": dict(Counter(b for r in trows for b in r["branch_per_test"] if b)),
            "route_a_unrestricted_outcome": dict(Counter(("program" if r["pattern"] else r["route_a_unrestricted"].get("why")) for r in trows if r["same_size"])),
            "t70_compared_tasks": len(cmp), "t70_slot1_changed": sum(r["slot1_changed"] for r in cmp),
            "t70_changed_detail": [{k: r.get(k) for k in ("task", "pattern", "pattern_restricted")} for r in cmp if r["slot1_changed"]][:40],
            "t70_both_program": sum(1 for r in cmp if r["pattern"] and r["pattern_restricted"]),
            "t70_changed_by_branch": dict(Counter(r["branch"] for r in cmp if r["slot1_changed"])),
            "t70_changed_kind": dict(Counter(("none->program" if not r["pattern"] else ("program->none" if not r["pattern_restricted"] else "program->other"))
                                             for r in cmp if r["slot1_changed"])),
            "t70_changed_restricted_role": dict(Counter((r["pattern_restricted"][0][0].split("[")[0] if r["pattern_restricted"] and r["pattern_restricted"][0] else "-")
                                                        for r in cmp if r["slot1_changed"])),
            "control_bbox_all_changed": sum(bool(r.get("slot1_changed_bbox_all")) for r in cmp),
            "control_bbox_all_changed_detail": [{k: r.get(k) for k in ("task", "pattern", "pattern_bbox_all")} for r in cmp if r.get("slot1_changed_bbox_all")][:40],
            "n_delta_test_mean": round(sum(sum(r["n_delta_test"]) for r in trows) / max(1, sum(len(r["n_delta_test"]) for r in trows)), 1)}


def rule_stats():
    """G62 shape of the rule file: relational body atoms (negated included) and distinct variables per rule"""
    prog = engine.Program(open(os.path.join(HERE, 'o0_rules.dl.txt')).read())
    st = []
    for h, b in prog.rules:
        vs = {a[1] for a in h[1] if a[0] == "v"} | {v for a in h[1] if a[0] == "agg" for v in a[2]}
        for l in b: vs |= engine.lvars(l)
        st.append((sum(l[0] == "atom" for l in b), len(vs)))
    return {"rules": len(st), "views": sorted(prog.views), "facts": sum(len(v) for v in prog.facts.values()), "strata": len(prog.strata),
            "recursive_strata": sum(any(r for _, r, _ in rs) for _, rs in prog.compiled),
            "atoms_le4": sum(a <= 4 for a, v in st), "vars_le4": sum(v <= 4 for a, v in st),
            "both_le4": sum(a <= 4 and v <= 4 for a, v in st), "max_atoms": max(a for a, v in st),
            "max_vars": max(v for a, v in st)}


def summarise(rows, n2):
    done = [r for r in rows if "skip" not in r]
    eq = sum(r["eq"] for r in done)
    per_item, ex = {}, {}
    for r in done:
        for it in r["mismatch"]:
            per_item[it] = per_item.get(it, 0) + 1
            if len(ex.setdefault(it, [])) < 5 and r["key"].split(":")[0] not in n2: ex[it].append(r["key"])
    w = [r["wmat"] for r in done if "wmat" in r]
    dl = [r["dl_s"] for r in done]; py = [r["py_s"] for r in done]; dc = [r.get("dc_s", 0) for r in done]
    sk = {}
    for r in done:
        for p, v in r.get("skipped", {}).items(): sk.setdefault(p, []).append([r["key"], v["size"], v["reason"]])
    from collections import Counter
    wmax = max(done, key=lambda r: r.get("wmat", 0)) if done else {}
    rule_tot = {}
    for r in done:
        for p, c in r.get("top_pred", []): rule_tot[p] = rule_tot.get(p, 0) + c
    return {"grids_total": len(rows), "grids_skipped_segmentation": len(rows) - len(done), "grids_compared": len(done),
            "grids_hash_equal": eq, "parity_pct": round(100.0 * eq / max(1, len(done)), 3),
            "items_with_mismatch": per_item, "mismatch_examples": ex,
            "wmat_max": max(w) if w else 0, "wmat_mean": round(sum(w) / max(1, len(w)), 1),
            "wmat_max_grid": wmax.get("key"), "wmat_max_top_rule": wmax.get("top_rule"), "wmat_max_top_preds": wmax.get("top_pred"),
            "grids_over_cap": sum(x > CAP for x in w), "cap": CAP, "rel_cap": REL_CAP,
            "grids_with_skipped_relation": sum(bool(r.get("skipped")) for r in done),
            "skipped_over_rel_cap": {p: {"grids": len(v), "log": [x for x in v if x[2] == "cap"][:20]}
                                     for p, v in sorted(sk.items()) if any(x[2] == "cap" for x in v)},
            "skipped_dependent": {p: len(v) for p, v in sorted(sk.items()) if not any(x[2] == "cap" for x in v)},
            "rel_max": max((r["rel_max"] for r in done if r.get("rel_max")), key=lambda pc: pc[1], default=None),
            "delta_src": dict(Counter(r["delta_src"] for r in done)),
            "dc_lazy_s_max": max(dc, default=0), "dc_lazy_s_mean": round(sum(dc) / max(1, len(dc)), 4),
            "ext_max": max((r["n_ext"] for r in done), default=0),
            "ext_mean": round(sum(r["n_ext"] for r in done) / max(1, len(done)), 1),
            "dl_s_max": max(dl, default=0), "dl_s_mean": round(sum(dl) / max(1, len(dl)), 4),
            "py_s_max": max(py, default=0), "py_s_mean": round(sum(py) / max(1, len(py)), 4),
            "pred_totals_from_grid_top5": sorted(rule_tot.items(), key=lambda kv: -kv[1])[:10],
            "py_errors": sum(bool(r.get("py_err")) for r in done), "dl_errors": sum(bool(r.get("dl_err")) for r in done),
            "rule_file": rule_stats()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--parts", type=int, default=1); ap.add_argument("--merge", type=int, default=0)
    ap.add_argument("--delta", choices=("g70", "v11"), default="g70"); ap.add_argument("--tasks")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    n2 = set(open(os.path.join(M1B, 'novel_N2.txt')).read().split())
    if a.delta == "g70":
        tag = "t59_parity_g70"
        if a.merge:
            rows, trows = [], []
            for k in range(a.merge):
                d = json.load(open(os.path.join(OUT, "%s.part%d.json" % (tag, k)))); rows += d["rows"]; trows += d["t70"]
        else:
            rows, trows = run_g70(a.part, a.parts, a.limit, set(a.tasks.split(",")) if a.tasks else None)
            if a.parts > 1 and not a.limit and not a.tasks:
                json.dump({"rows": rows, "t70": trows}, open(os.path.join(OUT, "%s.part%d.json" % (tag, a.part)), "w"))
                print(json.dumps(dict(summarise(rows, n2), t70=t70_summary(trows)), indent=1)); sys.exit(0)
        S = dict(summarise(rows, n2), t70=t70_summary(trows), delta_rule="v12 G70")
        for r in rows:
            r.pop("diff", None) if r.get("eq") else None
        out = os.path.join(OUT, tag + (".limit.json" if (a.limit or a.tasks) else ".json"))
        json.dump({"summary": S, "rows": rows, "t70": trows}, open(out, "w"), indent=0)
        print(json.dumps(S, indent=1)); sys.exit(0)
    if a.merge:
        rows = []
        for k in range(a.merge): rows += json.load(open(os.path.join(OUT, "t59_parity.part%d.json" % k)))["rows"]
    else:
        rows = run(a.part, a.parts, a.limit)
        if a.parts > 1 and not a.limit:
            json.dump({"rows": rows}, open(os.path.join(OUT, "t59_parity.part%d.json" % a.part), "w"))
            print(json.dumps(summarise(rows, n2), indent=1)); sys.exit(0)
    S = summarise(rows, n2)
    for r in rows:
        r.pop("diff", None) if r.get("eq") else None
    json.dump({"summary": S, "rows": rows}, open(os.path.join(OUT, "t59_parity.limit.json" if a.limit else "t59_parity.json"), "w"), indent=0)   # smoke runs never overwrite the full result
    print(json.dumps(S, indent=1))
