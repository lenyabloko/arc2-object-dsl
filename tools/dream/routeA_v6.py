"""Fable guidance v6: Route A with G45 (two-name conjunctions as nested tests), the revised G5 low-evidence branch
(E_obj < 8 bits and most-general-exact pick), the phi_design tie-break, and the G34 fallback to k = 1 at 80 % of
W_sub.  Answers v6 Q1 (E_obj, E_cell, L, test agreement per concept program), T35 (the two T24 conjunction misses)
and Q2 (do lattice |P| = 3 programs become |P| = 2 or nested |P| = 3 programs under Route A).

Design training tasks only (ARC training without N2); test outputs are used only to report agreement of a pick that
was already made, as the harness does.  The lattice pass is cached in lattice_cache.json (rerun-safe).
usage: python3 routeA_v6.py <probe_dir> <workdir>"""
import json, math, os, signal, sys
from itertools import combinations

probe, work = sys.argv[1], sys.argv[2]
os.environ["M1B_VOCAB"] = 'fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,G_dsl'
os.chdir(probe); sys.path[:0] = [probe, os.path.dirname(os.path.abspath(__file__))]
import occupancy2 as P
from routeA_t24 import roles_of, msc, lcs, candidates, holds, Budget, K as K2
import routeA_t24 as RA

B = '/kaggle/input/arc-prize-2026-arc-agi-2/'; M = '/home/claude/work/public_repo/tools/m1b/'
W_CAP = 50000; W_FALLBACK = int(0.8 * W_CAP)


class TO(BaseException): pass


P.Timeout = TO
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def lattice_pass(tr, ts, keys, shard=None):
    if shard:
        i, n = map(int, shard.split('/')); keys = keys[i::n]; path = os.path.join(work, f'lattice_cache_{i}.json')
    else:
        path = os.path.join(work, 'lattice_cache.json')
        cache = {}
        for f in sorted(os.listdir(work)):
            if f.startswith('lattice_cache_') and f.endswith('.json'): cache.update(json.load(open(os.path.join(work, f))))
        if os.path.exists(path): cache.update(json.load(open(path)))
        if all(k in cache for k in keys): return cache
    cache = json.load(open(path)) if (shard and os.path.exists(path)) else (cache if not shard else {})
    for n, k in enumerate(keys):
        if k in cache: continue
        t = tr[k]; rec = None
        if all((len(p["input"]), len(p["input"][0])) == (len(p["output"]), len(p["output"][0])) for p in t["train"]):
            try:
                signal.alarm(120); att, _, _ = P.solve_once(t); signal.alarm(0)
                if att:
                    a = att[0]; rules = list(a["rules"]) + [None] * (3 - len(a["rules"]))
                    rec = {"ab": a["abstraction"], "rb": [[list(g), l] for g, l in rules[0]], "extra": bool(rules[1] or rules[2]),
                           "n": P.nrules(a["rules"]), "ok": all(a["preds"][i] == ts[k][i] for i in range(len(ts[k])))}
            except TO: rec = {"timeout": True}
            except Exception: signal.alarm(0)
        cache[k] = rec
        if n % 25 == 0: json.dump(cache, open(path, 'w'))
    json.dump(cache, open(path, 'w'))
    return cache


def phi_design(tr, keys, abstractions, sample=150):
    """grid-level design fire ratio of every attribute name, per abstraction (ordering statistic only)."""
    path = os.path.join(work, 'phi_design.json')
    if os.path.exists(path): return json.load(open(path))
    phi = {}
    step = max(1, len(keys) // sample)
    for ab in abstractions:
        cnt = {}; grids = 0
        for k in keys[::step]:
            for p in tr[k]["train"]:
                try: _, _, at, _, _, _ = P.prepare(p["input"], ab)
                except Exception: continue
                grids += 1
                for name in set().union(*at) if at else set(): cnt[name] = cnt.get(name, 0) + 1
        phi[ab] = {n: c / max(grids, 1) for n, c in cnt.items()}
    json.dump(phi, open(path, 'w'))
    return phi


def ext_of(chain, name, at, R, W):
    return {i for i in range(len(at)) if holds(i, chain, name, at, R, W)}


def route_a(pairs, tests, phi_ab, k_depth):
    RA.K = k_depth
    C = None
    for nodes, at, R, X in pairs:
        for i in sorted(X):
            m = msc(i, at, R, k_depth)
            C = m if C is None else lcs(C, m)
    W = [0]; exact = []; cands = candidates(C)
    for chain, name in cands:
        if all(ext_of(chain, name, at, R, W) == X for nodes, at, R, X in pairs):
            gen_ext = sum(len(ext_of(chain, name, at_q, R_q, W)) for at_q, R_q in tests)
            # most general exact: widest extension on the test inputs, then higher phi_design, shorter chain, IRI
            exact.append((-gen_ext, -phi_ab.get(str(name), 0.0), len(chain), str(name), ("single", ((chain, name),))))
        if W[0] > W_FALLBACK: raise Budget()
    if exact: return C, min(exact)[4], len(exact), W[0]
    # G45: two names, exact only jointly -> nested atomic tests (|P| = 3, slot 2)
    # G45 over depth-0 names of C_t: extensions precomputed once per name and pair (no role chains), so the pair
    # search costs set intersections, not instance checks
    names = [((), n) for n in sorted(C[0])]
    E = {c: [ext_of(*c, at, R, W) for nodes, at, R, X in pairs] for c in names}
    Eq = {c: [ext_of(*c, at_q, R_q, W) for at_q, R_q in tests] for c in names}
    joint = []
    for c1, c2 in combinations(names, 2):
        if all((E[c1][j] & E[c2][j]) == pairs[j][3] for j in range(len(pairs))):
            gen_ext = sum(len(a & b) for a, b in zip(Eq[c1], Eq[c2]))
            joint.append((-gen_ext, -(phi_ab.get(str(c1[1]), 0) + phi_ab.get(str(c2[1]), 0)), str(c1[1]) + '&' + str(c2[1]), ("pair", (c1, c2))))
    if joint: return C, min(joint)[3], len(joint), W[0]
    return C, None, 0, W[0]


def predict(q_in, ab, pick, lab, default):
    nodes, bg, at, src, others, oc = P.prepare(q_in, ab)
    R = roles_of(nodes); W = [0]
    sel = set(range(len(nodes)))
    for chain, name in pick[1]:
        sel &= ext_of(chain, name, at, R, W)
    labels = [lab if i in sel else default for i in range(len(nodes))]
    return P.apply_labels(q_in, nodes, src, labels, bg, others)


def main():
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ts = json.load(open(B + 'arc-agi_training_solutions.json'))
    N2 = set(open(M + 'novel_N2.txt').read().split())
    keys = [k for k in sorted(tr) if k not in N2]
    if os.environ.get("SHARD"):
        lattice_pass(tr, ts, keys, os.environ["SHARD"]); return
    cache = lattice_pass(tr, ts, keys)
    phi = phi_design(tr, keys, P.ABSTRACTIONS)
    rows = []
    only = set(os.environ.get("ONLY", "").split(",")) - {""}
    for k in keys:
        if only and k not in only: continue
        c = cache.get(k)
        if not c or c.get("timeout") or c["extra"] or not c["ok"] or c["n"] > 3: continue
        rb = [(tuple(g), l) for g, l in c["rb"]]
        default = rb[-1][1] if not rb[-1][0] else "keep"
        nondef = [(g, l) for g, l in rb if g]
        if not nondef: rows.append({"task": k, "n": c["n"], "kind": "default-only"}); continue
        labs = {l for _, l in nondef}
        if len(labs) != 1: rows.append({"task": k, "n": c["n"], "kind": "two actions (stays |P|=3)"}); continue
        lab = labs.pop(); t = tr[k]; ab = c["ab"]
        pairs = []
        for p in t["train"]:
            nodes, bg, at, src, others, oc = P.prepare(p["input"], ab)
            X = {i for i, l in enumerate(P.predict_labels(rb, at)) if l == lab}
            pairs.append((nodes, at, roles_of(nodes), X))
        tests = []
        for q in t["test"]:
            nq, _, atq, _, _, _ = P.prepare(q["input"], ab); tests.append((atq, roles_of(nq)))
        kd = K2
        try:
            C, pick, n_exact, W = route_a(pairs, tests, phi.get(ab, {}), kd)
        except Budget:
            kd = 1
            try: C, pick, n_exact, W = route_a(pairs, tests, phi.get(ab, {}), 1)
            except Budget: C, pick, n_exact, W = None, "BUDGET", 0, W_CAP
        a_act = 9 if ("recolor" in str(lab) or "=" in str(lab)) else 3
        E_obj = sum(math.log2(math.comb(len(nodes), len(X))) + len(X) * math.log2(a_act) for nodes, at, R, X in pairs)
        E_cell = 0.0
        for p in t["train"]:
            a_, b_ = p["input"], p["output"]
            d = sum(a_[y][x] != b_[y][x] for y in range(len(a_)) for x in range(len(a_[0])))
            E_cell += math.log2(math.comb(len(a_) * len(a_[0]), d)) + d * math.log2(9)
        row = {"task": k, "n": c["n"], "lattice": [[list(g), l] for g, l in nondef], "k": kd, "W_sub": W, "n_exact": n_exact,
               "E_obj": round(E_obj, 1), "E_cell": round(E_cell, 1)}
        if pick in (None, "BUDGET"):
            row.update(kind="FAIL" if pick is None else "BUDGET", C_t=sorted(C[0])[:10] if C else None)
        else:
            nodes_in_pick = sum(len(ch) + 1 for ch, _ in pick[1])
            P_size = 2 if pick[0] == "single" else 3
            L = 12 + 11 * (P_size - 2) + 4 * sum(len(ch) for ch, _ in pick[1])
            try:
                agree = all(predict(q["input"], ab, pick, lab, default) == ts[k][i] for i, q in enumerate(t["test"]))
            except Exception:
                agree = None
            row.update(kind=pick[0], P=P_size, L=L, margin=round(E_obj - L, 1), pick=[[list(ch), nm] for ch, nm in pick[1]],
                       low_evidence_branch=(E_obj < 8), test_agree=agree)
        rows.append(row); print(json.dumps(row), flush=True)
    json.dump(rows, open(os.path.join(work, 'routeA_v6.json'), 'w'), indent=0)


if __name__ == "__main__":
    main()
