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
       python3 harness.py <probe_dir> vcov <c32_results> <e99_jsonl> <out.json> [item names...]"""
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


if __name__ == "__main__":
    probe, mode = sys.argv[1], sys.argv[2]
    P = setup(probe)
    if mode == "check":
        print(json.dumps(check(P, load_items(set(sys.argv[3:]) or None)), indent=1))
    elif mode == "vcov":
        c32f, e99f, outf = sys.argv[3:6]
        print(json.dumps(vcov(P, load_items(set(sys.argv[6:]) or None), c32f, e99f, os.path.abspath(outf))))
