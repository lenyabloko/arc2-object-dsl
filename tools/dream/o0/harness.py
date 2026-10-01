"""O0 admission harness (Fable v9 §3, G54/G55): individuals, fire ratio, determinism, subsumption, V_cov with O0.

An O0 item lives in tools/dream/o0/items/<name>.py and defines ITEM = {
    "name": "on_ray", "layer": 1, "iri": "qsr:on_ray", "definition": "...", "kind": "role" | "concept",
    "params": {"d": ["N", "S", ...], ...},          # finite declared domains; one extension per parameter setting
    "subsumes": ["aligned"],                           # items this one specialises (G20: extension subset)
    "fn": f }   with  f(grid, inds, bg, **params) -> role: {i: set(j)} | concept: set(i)
Individuals (built here, once per grid and abstraction): the lattice's objects (occupancy2.prepare) plus one
individual per background cell ({"pix": {(y, x)}, "color": bg, "kind": "cell"}), so roles can relate background
cells to objects (v9 Layer 1; V_cov: 126 of 137 uncovered failed tasks change background cells).
Design data only (ARC-1 training minus N2 and the 99); no test outputs are read.
usage: python3 harness.py <probe_dir> check <item names...>      fire ratio, determinism, subsumption per item
       python3 harness.py <probe_dir> vcov <c32_results> <e99_jsonl> <out.json> [item names...]
       python3 harness.py <probe_dir> vcov2 <c32_results> <e99_jsonl> <out.json> [item names...]   vcov + G45 N1⊓N2 and
           depth-2 chains ∃r1.∃r2.N / ∃r1.∃r2.⊤ by set computation (env VCOV2_BUDGET seconds per abstraction, default 60)"""
import glob, importlib.util, json, os, random, signal, sys

HERE = os.path.dirname(os.path.abspath(__file__))
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
M = os.path.join(HERE, '..', '..', 'm1b')


def setup(probe):
    os.environ.setdefault("M1B_VOCAB", 'fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,G_dsl')
    sys.path[:0] = [probe, os.path.join(HERE, '..')]
    cwd = os.getcwd(); os.chdir(probe)
    import occupancy2 as P
    os.chdir(cwd)
    return P


def load_items(names=None):
    items = []
    for f in sorted(glob.glob(os.path.join(HERE, 'items', '*.py'))):
        n = os.path.basename(f)[:-3]
        if names and n not in names: continue
        s = importlib.util.spec_from_file_location('o0_' + n, f); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        items.append(m.ITEM)
    return items


def individuals(P, grid, ab):
    nodes, bg, at, src, others, oc = P.prepare(grid, ab)
    inds = [{"pix": set(n["pix"]), "color": n.get("color"), "kind": "object"} for n in nodes]
    names = [set(a) for a in at]
    occ = set().union(*[x["pix"] for x in inds]) if inds else set()
    for y in range(len(grid)):
        for x in range(len(grid[0])):
            if (y, x) not in occ and grid[y][x] == bg:
                inds.append({"pix": {(y, x)}, "color": bg, "kind": "cell"}); names.append({"kind=cell"})
    return inds, names, bg


def settings(item):
    ps = item.get("params") or {}
    keys = sorted(ps)
    out = [{}]
    for k in keys:
        out = [dict(o, **{k: v}) for o in out for v in ps[k]]
    return out


def extension(item, grid, inds, bg, prm):
    r = item["fn"](grid, inds, bg, **prm)
    if item["kind"] == "role":
        return {(i, j) for i, js in r.items() for j in js}
    return set(r)


def design_grids(n=300, seed=0):
    tr = json.load(open(B + 'arc-agi_training_challenges.json'))
    N2 = set(open(os.path.join(M, 'novel_N2.txt')).read().split())
    keys = sorted(k for k in tr if k not in N2)
    rnd = random.Random(seed); rnd.shuffle(keys)
    return [tr[k]["train"][0]["input"] for k in keys[:n]]


def check(P, items, ab="nbccg"):
    grids = design_grids()
    pre = []
    for g in grids:
        try: pre.append((g, *individuals(P, g, ab)))
        except Exception: pass
    rep = {}
    for it in items:
        for prm in settings(it):
            key = it["name"] + (json.dumps(prm, sort_keys=True) if prm else "")
            fired = dens = 0; det_ok = True; err = 0
            for g, inds, names, bg in pre:
                try:
                    e1 = extension(it, g, inds, bg, prm); e2 = extension(it, g, inds, bg, prm)
                except Exception:
                    err += 1; continue
                det_ok &= (e1 == e2)
                fired += bool(e1)
                n = len(inds); dens += len(e1) / max(1, n * n if it["kind"] == "role" else n)
            rep[key] = {"phi_grid": round(fired / max(1, len(pre)), 3), "density": round(dens / max(1, len(pre)), 4),
                        "deterministic": det_ok, "errors": err,
                        "phi_ok": 0.01 <= fired / max(1, len(pre)) <= 0.5}
    # G20: declared subsumptions, extension(A) subset extension(B) on every sampled grid (default parameters)
    by = {it["name"]: it for it in items}
    for it in items:
        for parent in it.get("subsumes", []):
            if parent not in by: continue
            ok = True
            for g, inds, names, bg in pre:
                a = extension(it, g, inds, bg, settings(it)[0]); b = extension(by[parent], g, inds, bg, settings(by[parent])[0])
                if not a <= b: ok = False; break
            rep.setdefault("subsumption", {})[f"{it['name']} ⊑ {parent}"] = ok
    return rep


def vcov(P, items, c32f, e99f, outf, abstractions=None):
    """V_cov with O0: target individuals X = objects AND background cells that change; msc over the lattice names plus
    the O0 roles (every parameter setting is its own role name) and the base roles of routeA_t24."""
    import routeA_t24 as RA
    sys.argv = sys.argv[:1]
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ev = json.load(open(B + 'arc-agi_evaluation_challenges.json'))
    T = {}
    for l in open(c32f):
        d = json.loads(l)
        if d['task'] in tr and not d.get('exact'): T[d['task']] = tr[d['task']]
    for l in open(e99f):
        d = json.loads(l); f = d.get('final')
        if not (isinstance(f, list) and any(f)): T[d['task']] = ev[d['task']]
    roles = [(it, prm) for it in items if it["kind"] == "role" for prm in settings(it)]
    concepts = [(it, prm) for it in items if it["kind"] == "concept" for prm in settings(it)]
    rname = lambda it, prm: it["name"] + ("[" + ",".join(f"{k}={v}" for k, v in sorted(prm.items())) + "]" if prm else "")

    class TO(BaseException): pass
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
    rows = []
    for k in sorted(T):
        t = T[k]
        if any((len(p['input']), len(p['input'][0])) != (len(p['output']), len(p['output'][0])) for p in t['train']):
            continue
        best = {"task": k, "loose": False, "exact": False, "exact_proper": False}
        for ab in (abstractions or P.ABSTRACTIONS):
            try:
                signal.alarm(30)
                pairs = []
                for p in t['train']:
                    a, b = p['input'], p['output']
                    inds, names, bg = individuals(P, a, ab)
                    base = RA.roles_of([{"pix": x["pix"]} for x in inds]) if len(inds) <= 400 else {r: [set() for _ in inds] for r in RA.ROLES}
                    R = dict(base)
                    for it, prm in roles:
                        rel = it["fn"](a, inds, bg, **prm); nm = rname(it, prm)
                        R[nm] = [set(rel.get(i, ())) for i in range(len(inds))]
                    for it, prm in concepts:
                        ext = it["fn"](a, inds, bg, **prm); nm = rname(it, prm)
                        for i in ext: names[i].add(nm)
                    ch = {(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]}
                    X = {i for i, x in enumerate(inds) if x["pix"] & ch}
                    pairs.append((inds, names, R, X))
                signal.alarm(0)
            except TO: continue
            except Exception: signal.alarm(0); continue
            if any(not X for *_, X in pairs): continue
            RA.ROLES = tuple(sorted(pairs[0][2])); RA.K = 1
            C = None
            try:
                signal.alarm(30)
                for inds, names, R, X in pairs:
                    for i in sorted(X):
                        m = RA.msc(i, names, R, 1); C = m if C is None else RA.lcs(C, m)
                loose = bool(C and ((C[0] - {"kind=cell"}) or C[1]))
                best["loose"] |= loose
                if loose:
                    W = [0]
                    for chain, name in RA.candidates(C):
                        if all({i for i in range(len(nm)) if RA.holds(i, chain, name, nm, R, W)} == X for inds, nm, R, X in pairs):
                            best["exact"] = True
                            if any(len(X) < len(inds) for inds, nm, R, X in pairs): best["exact_proper"] = True; best["concept"] = [list(chain), name]
                            break
                signal.alarm(0)
            except (TO, RA.Budget): signal.alarm(0); continue
            except Exception: signal.alarm(0); continue
        rows.append(best)
    n = len(rows)
    S = {"same_size_failed": n, "V_cov_loose": round(sum(r["loose"] for r in rows) / max(n, 1), 3),
         "V_cov_exact": round(sum(r["exact"] for r in rows) / max(n, 1), 3),
         "V_cov_exact_proper": round(sum(r["exact_proper"] for r in rows) / max(n, 1), 3),
         "items": [it["name"] for it in items]}
    json.dump({"summary": S, "rows": rows}, open(outf, "w"), indent=0)
    return S


def _form_role(r):
    return r.split("[", 1)[0]


def _form_name(nm):
    return "⊤" if nm is None else (nm.split("=", 1)[0] + "=*" if "=" in nm else nm)


def _cname(c):
    """readable concept: ('d0', N) | ('d1', r, N) | ('conj', N1, N2) | ('chain', r1, r2, N); N None = ⊤"""
    nm = lambda n: "⊤" if n is None else n
    if c[0] == "d0": return c[1]
    if c[0] == "d1": return f"∃{c[1]}.{nm(c[2])}"
    if c[0] == "conj": return f"{c[1]} ⊓ {c[2]}"
    return f"∃{c[1]}.∃{c[2]}.{nm(c[3])}"


def _cform(c):
    if c[0] == "d0": return _form_name(c[1])
    if c[0] == "d1": return f"∃{_form_role(c[1])}.{_form_name(c[2])}"
    if c[0] == "conj": return " ⊓ ".join(sorted((_form_name(c[1]), _form_name(c[2]))))
    return f"∃{_form_role(c[1])}.∃{_form_role(c[2])}.{_form_name(c[3])}"


class _PairSets:
    """one training pair as bitsets over its individuals: name extensions, role predecessor maps (lazy), X."""
    def __init__(self, inds, names, R, X):
        self.n = len(inds); self.R = R; self.all = (1 << self.n) - 1
        self.X = sum(1 << i for i in X)
        self.ext = {}
        for i, ns in enumerate(names):
            for a in ns: self.ext[a] = self.ext.get(a, 0) | (1 << i)
        self._pred = {}; self.c1 = {}

    def pred(self, r):
        p = self._pred.get(r)
        if p is None:
            pm = {}
            for i, js in enumerate(self.R[r]):
                b = 1 << i
                for j in js: pm[j] = pm.get(j, 0) | b
            p = self._pred[r] = (sum(1 << j for j in pm), pm)
        return p

    def ex(self, r, D):
        """extension of ∃r.D for D given as a bitset: union of predecessors of D's members"""
        tm, pm = self.pred(r); Dm = D & tm; m = 0
        while Dm:
            lo = Dm & -Dm; m |= pm[lo.bit_length() - 1]; Dm ^= lo
        return m

    def name(self, N):
        return self.all if N is None else self.ext.get(N, 0)

    def d1(self, r, N):
        k = (r, N); m = self.c1.get(k)
        if m is None: m = self.c1[k] = self.ex(r, self.name(N))
        return m

    def succ(self, r, i):
        return sum(1 << j for j in self.R[r][i])


def _search2(pairs, roles, found, cap=400):
    """set-based exact search over depth-0 names, depth-1 ∃r.N / ∃r.⊤ (diagnostic: no lcs, no budget), G45 conjunctions
    N1 ⊓ N2 and depth-2 chains ∃r1.∃r2.N / ∃r1.∃r2.⊤. A candidate is pruned as soon as it fails to contain X in the
    first pair; only survivors are evaluated on the other pairs. Appends exact concepts to `found` (kept on timeout)."""
    S = [_PairSets(*p) for p in pairs]
    S0, rest = S[0], S[1:]
    kinds = {"d0": 0, "d1": 0, "conj": 0, "chain": 0}

    def add(c):
        kinds[c[0]] += 1
        if kinds[c[0]] <= cap: found.append(c)
    # depth 0 and G45 conjunctions: names on every x in X in every pair
    CN = sorted(N for N in S0.ext if all(not s.X & ~s.ext.get(N, 0) for s in S))
    for N in CN:
        if all(s.ext[N] == s.X for s in S): add(("d0", N))
    for a in range(len(CN)):
        for b in range(a + 1, len(CN)):
            if all(s.ext[CN[a]] & s.ext[CN[b]] == s.X for s in S): add(("conj", CN[a], CN[b]))
    # depth 1 in pair 0: every ∃r2.N (N any name of pair 0, or ⊤), grouped by extension
    names0 = sorted(S0.ext) + [None]
    groups = {}
    for r2 in roles:
        for N in names0:
            m = S0.d1(r2, N)
            if m: groups.setdefault(m, []).append((r2, N))
    for r, N in groups.get(S0.X, ()):
        if all(s.d1(r, N) == s.X for s in rest): add(("d1", r, N))
    # depth 2: ∃r1.D with D = ∃r2.N; prune on pair 0 (every x in X0 needs an r1-successor in D)
    xs0 = [i for i in range(S0.n) if S0.X >> i & 1]
    G = sorted(groups.items(), key=lambda g: g[0])
    for r1 in roles:
        if S0.X & ~S0.ex(r1, S0.all): continue
        sx = sorted((S0.succ(r1, i) for i in xs0), key=lambda m: bin(m).count("1"))
        for D, syn in G:
            ok = True
            for m in sx:
                if not m & D: ok = False; break
            if not ok or S0.ex(r1, D) != S0.X: continue
            for r2, N in syn:
                if all(s.ex(r1, s.d1(r2, N)) == s.X for s in rest): add(("chain", r1, r2, N))
    return kinds


def vcov2(P, items, c32f, e99f, outf, abstractions=None, budget=60):
    """vcov plus richer concepts. Same tasks, individuals, roles and X as vcov; the depth <= 1 reference is computed by
    the identical vcov code path (msc / lcs / candidates / holds, same 30 s alarms and W budget). Then, per
    abstraction and within `budget` seconds (signal.alarm), a set-based search adds (a) G45 conjunctions N1 ⊓ N2 and
    (b) depth-2 chains ∃r1.∃r2.N, ∃r1.∃r2.⊤ (no depth-2 msc trees). Variants: (i) depth<=1, (ii) +conj,
    (iii) +chains, (iv) both; 'depth1_set' is the set-based depth <= 1 search (diagnostic: no SUCC_CAP, no W budget)."""
    import time
    import routeA_t24 as RA
    sys.argv = sys.argv[:1]
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ev = json.load(open(B + 'arc-agi_evaluation_challenges.json'))
    T = {}
    for l in open(c32f):
        d = json.loads(l)
        if d['task'] in tr and not d.get('exact'): T[d['task']] = tr[d['task']]
    for l in open(e99f):
        d = json.loads(l); f = d.get('final')
        if not (isinstance(f, list) and any(f)): T[d['task']] = ev[d['task']]
    roles = [(it, prm) for it in items if it["kind"] == "role" for prm in settings(it)]
    concepts = [(it, prm) for it in items if it["kind"] == "concept" for prm in settings(it)]
    rname = lambda it, prm: it["name"] + ("[" + ",".join(f"{k}={v}" for k, v in sorted(prm.items())) + "]" if prm else "")

    class TO(BaseException): pass
    signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))
    rows = []; t_start = time.time()
    lim = int(os.environ.get("VCOV2_LIMIT", "0")) or None          # testing only: first N tasks
    for k in sorted(T)[:lim]:
        t = T[k]
        if any((len(p['input']), len(p['input'][0])) != (len(p['output']), len(p['output'][0])) for p in t['train']):
            continue
        best = {"task": k, "loose": False, "exact": False, "exact_proper": False}
        ext = {"d1set": [False, False], "conj": [False, False], "chain": [False, False]}
        found_all = []; to = {"build": 0, "ref": 0, "ext": 0}; t_task = time.time()
        for ab in (abstractions or P.ABSTRACTIONS):
            try:
                signal.alarm(30)
                pairs = []
                for p in t['train']:
                    a, b = p['input'], p['output']
                    inds, names, bg = individuals(P, a, ab)
                    base = RA.roles_of([{"pix": x["pix"]} for x in inds]) if len(inds) <= 400 else {r: [set() for _ in inds] for r in RA.ROLES}
                    R = dict(base)
                    for it, prm in roles:
                        rel = it["fn"](a, inds, bg, **prm); nm = rname(it, prm)
                        R[nm] = [set(rel.get(i, ())) for i in range(len(inds))]
                    for it, prm in concepts:
                        ex_ = it["fn"](a, inds, bg, **prm); nm = rname(it, prm)
                        for i in ex_: names[i].add(nm)
                    ch = {(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]}
                    X = {i for i, x in enumerate(inds) if x["pix"] & ch}
                    pairs.append((inds, names, R, X))
                signal.alarm(0)
            except TO: to["build"] += 1; continue
            except Exception: signal.alarm(0); continue
            if any(not X for *_, X in pairs): continue
            RA.ROLES = tuple(sorted(pairs[0][2])); RA.K = 1
            C = None
            # (i) depth <= 1 reference: identical to vcov
            try:
                signal.alarm(30)
                for inds, names, R, X in pairs:
                    for i in sorted(X):
                        m = RA.msc(i, names, R, 1); C = m if C is None else RA.lcs(C, m)
                loose = bool(C and ((C[0] - {"kind=cell"}) or C[1]))
                best["loose"] |= loose
                if loose:
                    W = [0]
                    for chain, name in RA.candidates(C):
                        if all({i for i in range(len(nm)) if RA.holds(i, chain, name, nm, R, W)} == X for inds, nm, R, X in pairs):
                            best["exact"] = True
                            if any(len(X) < len(inds) for inds, nm, R, X in pairs): best["exact_proper"] = True; best["concept"] = [list(chain), name]
                            break
                signal.alarm(0)
            except TO: signal.alarm(0); to["ref"] += 1
            except RA.Budget: signal.alarm(0)
            except Exception: signal.alarm(0)
            # (a) + (b): set-based search under its own budget
            proper = any(len(X) < len(inds) for inds, nm, R, X in pairs)
            found = []
            try:
                signal.alarm(budget)
                _search2(pairs, RA.ROLES, found)
                signal.alarm(0)
            except TO: to["ext"] += 1
            except Exception: signal.alarm(0)
            for c in found:
                key = "d1set" if c[0] in ("d0", "d1") else c[0]
                ext[key][0] = True; ext[key][1] |= proper
                found_all.append((ab, c, proper))
        row = dict(best)
        for key in ext: row[key + "_exact"], row[key + "_exact_proper"] = ext[key]
        ref_e, ref_p = best["exact"], best["exact_proper"]
        for v, keys in (("ii", ("conj",)), ("iii", ("chain",)), ("iv", ("conj", "chain"))):
            row[v + "_exact"] = ref_e or any(ext[q][0] for q in keys)
            row[v + "_exact_proper"] = ref_p or any(ext[q][1] for q in keys)
        new = [(ab, c, pr) for ab, c, pr in found_all if c[0] in ("conj", "chain")]
        row["new_forms_exact"] = sorted({_cform(c) for ab, c, pr in new}) if not ref_e else []
        row["new_forms_exact_proper"] = sorted({_cform(c) for ab, c, pr in new if pr}) if not ref_p else []
        rf = lambda c: _cform(c) if c[0] == "conj" else f"∃{_form_role(c[1])}.∃{_form_role(c[2])}.·"
        row["new_role_forms_exact"] = sorted({rf(c) for ab, c, pr in new}) if not ref_e else []
        row["new_role_forms_exact_proper"] = sorted({rf(c) for ab, c, pr in new if pr}) if not ref_p else []
        row["examples"] = [[ab, _cname(c)] for ab, c, pr in new[:8]]
        row["n_conj"] = sum(c[0] == "conj" for ab, c, pr in found_all)
        row["n_chain"] = sum(c[0] == "chain" for ab, c, pr in found_all)
        row["timeouts"] = to; row["sec"] = round(time.time() - t_task, 1)
        rows.append(row)
        print(json.dumps({q: row[q] for q in ("task", "exact", "exact_proper", "iv_exact", "iv_exact_proper", "timeouts", "sec")}), file=sys.stderr, flush=True)
    n = len(rows); fr = lambda q: round(sum(bool(r[q]) for r in rows) / max(n, 1), 3)
    cnt = lambda q: sum(bool(r[q]) for r in rows)
    from collections import Counter
    fe = Counter(f for r in rows for f in r["new_forms_exact"]); fp = Counter(f for r in rows for f in r["new_forms_exact_proper"])
    S = {"same_size_failed": n, "V_cov_loose": fr("loose"),
         "i_depth1": {"exact": fr("exact"), "exact_proper": fr("exact_proper"), "n_exact": cnt("exact"), "n_exact_proper": cnt("exact_proper")},
         "ii_conj": {"exact": fr("ii_exact"), "exact_proper": fr("ii_exact_proper"), "n_exact": cnt("ii_exact"), "n_exact_proper": cnt("ii_exact_proper")},
         "iii_chain2": {"exact": fr("iii_exact"), "exact_proper": fr("iii_exact_proper"), "n_exact": cnt("iii_exact"), "n_exact_proper": cnt("iii_exact_proper")},
         "iv_both": {"exact": fr("iv_exact"), "exact_proper": fr("iv_exact_proper"), "n_exact": cnt("iv_exact"), "n_exact_proper": cnt("iv_exact_proper")},
         "depth1_set_diag": {"exact": fr("d1set_exact"), "exact_proper": fr("d1set_exact_proper"), "n_exact": cnt("d1set_exact"), "n_exact_proper": cnt("d1set_exact_proper")},
         "conj_only": {"n_exact": cnt("conj_exact"), "n_exact_proper": cnt("conj_exact_proper")},
         "chain_only": {"n_exact": cnt("chain_exact"), "n_exact_proper": cnt("chain_exact_proper")},
         "timeouts": {"ext_abstractions": sum(r["timeouts"]["ext"] for r in rows), "ext_tasks": sum(bool(r["timeouts"]["ext"]) for r in rows),
                      "ext_tasks_not_covered_iv": sum(bool(r["timeouts"]["ext"]) and not r["iv_exact"] for r in rows),
                      "build_abstractions": sum(r["timeouts"]["build"] for r in rows), "ref_abstractions": sum(r["timeouts"]["ref"] for r in rows),
                      "ext_budget_s": budget},
         "new_tasks_exact": [r["task"] for r in rows if r["iv_exact"] and not r["exact"]],
         "new_tasks_exact_proper": [r["task"] for r in rows if r["iv_exact_proper"] and not r["exact_proper"]],
         "top_new_forms_exact": fe.most_common(10), "top_new_forms_exact_proper": fp.most_common(10),
         "top_new_role_forms_exact": Counter(f for r in rows for f in r["new_role_forms_exact"]).most_common(10),
         "top_new_role_forms_exact_proper": Counter(f for r in rows for f in r["new_role_forms_exact_proper"]).most_common(10),
         "items": [it["name"] for it in items], "n_roles": len(roles) + 5, "wall_s": round(time.time() - t_start)}
    json.dump({"summary": S, "rows": rows}, open(outf, "w"), indent=0, ensure_ascii=False)
    return S


if __name__ == "__main__":
    probe, mode = sys.argv[1], sys.argv[2]
    P = setup(probe)
    if mode == "check":
        print(json.dumps(check(P, load_items(set(sys.argv[3:]) or None)), indent=1))
    elif mode == "vcov":
        c32f, e99f, outf = sys.argv[3:6]
        print(json.dumps(vcov(P, load_items(set(sys.argv[6:]) or None), c32f, e99f, os.path.abspath(outf))))
    elif mode == "vcov2":
        c32f, e99f, outf = sys.argv[3:6]
        print(json.dumps(vcov2(P, load_items(set(sys.argv[6:]) or None), c32f, e99f, os.path.abspath(outf),
                               budget=int(os.environ.get("VCOV2_BUDGET", "60"))), ensure_ascii=False))
