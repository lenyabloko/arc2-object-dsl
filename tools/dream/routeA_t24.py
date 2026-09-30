"""Fable guidance v4, test T24: Route A (EL-lcs seeding) on the lattice's short programs.

For every design training task (ARC training without N2) whose first lattice attempt is a |P| <= 2 decision list
(one rule + default, no effects, no pixel refinement) and is correct on the test, recompute the target set X (the
individuals the rule labels) and ask whether Route A recovers a one-concept program:

    C_t  = lcs over x in X (all pairs) of msc_k(x)                 (EL, role depth k <= 2, G34)
    S0   = concept names N with C_t <= N, and existential chains  exists r.N / exists r.exists s.N  drawn from C_t
    pick = the most general candidate whose extension equals X in every training pair (Principle 3)

Individuals and concept names are the lattice's own (occupancy2.prepare). Roles between individuals are re-asserted
from the same geometry: touches (8-neighbour contact), inside (pixels inside the other's interior), contains,
aligned (bounding boxes share a row or a column), same_shape.  Counters: W_sub (instance checks) <= 5e4 per task.
margin' = E - L with E = sum_i [log2 C(N_i, d_i) + d_i log2 a], a = 9 for colour labels else 3, L = 12 bits for a
one-concept program plus 4 bits per role step.  Output: one JSON line per program; summary on stderr.
usage: python3 routeA_t24.py <probe_dir> [limit]"""
import json, math, os, signal, sys
from itertools import product

probe = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 0
os.environ["M1B_VOCAB"] = 'fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,G_dsl'
os.chdir(probe); sys.path[:0] = [probe]
import occupancy2 as P

B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
M = '/home/claude/work/public_repo/tools/m1b/'
K = 2; W_SUB_MAX = 50000; SUCC_CAP = 6
ROLES = ("touches", "inside", "contains", "aligned", "same_shape")


class TO(BaseException): pass


P.Timeout = TO
signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def roles_of(nodes):
    n = len(nodes)
    inner = [P.interior(x["pix"]) for x in nodes]
    boxes = [P.bbox(x["pix"]) for x in nodes]
    shapes = [P.norm_shape(x["pix"]) for x in nodes]
    owner = {p: i for i, x in enumerate(nodes) for p in x["pix"]}
    R = {r: [set() for _ in range(n)] for r in ROLES}
    for i, x in enumerate(nodes):
        for (a, b) in x["pix"]:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    j = owner.get((a + dy, b + dx))
                    if j is not None and j != i: R["touches"][i].add(j)
        for j in range(n):
            if j == i: continue
            if x["pix"] <= inner[j]: R["inside"][i].add(j); R["contains"][j].add(i)
            bi, bj = boxes[i], boxes[j]
            if not (bj[2] < bi[0] or bj[0] > bi[2]) or not (bj[3] < bi[1] or bj[1] > bi[3]): R["aligned"][i].add(j)
            if shapes[j] == shapes[i]: R["same_shape"][i].add(j)
    return R


def msc(i, at, R, k):
    """EL concept tree: (frozenset of names, {role: tuple of successor trees})."""
    if k == 0: return (frozenset(at[i]), {})
    return (frozenset(at[i]), {r: tuple(msc(j, at, R, k - 1) for j in sorted(R[r][i])) for r in ROLES if R[r][i]})


def size(c):
    return len(c[0]) + sum(size(s) for ss in c[1].values() for s in ss)


def lcs(c1, c2):
    names = c1[0] & c2[0]; roles = {}
    for r in set(c1[1]) & set(c2[1]):
        succ = {}
        for s1, s2 in product(c1[1][r], c2[1][r]):
            l = lcs(s1, s2)
            key = (l[0], tuple(sorted((rr, len(v)) for rr, v in l[1].items())))
            if key not in succ or size(l) > size(succ[key]): succ[key] = l
        best = sorted(succ.values(), key=lambda c: -size(c))[:SUCC_CAP]
        roles[r] = tuple(best)
    return (names, roles)


def candidates(c, depth=0, prefix=()):
    """concept descriptions N, exists r.N, exists r.exists s.N (and exists r.Top) read off C_t."""
    out = [(prefix, n) for n in sorted(c[0])]
    if depth < K:
        for r, succ in sorted(c[1].items()):
            out.append((prefix + (r,), None))                   # exists r.Top
            seen = set()
            for s in succ:
                for cand in candidates(s, depth + 1, prefix + (r,)):
                    if cand not in seen: seen.add(cand); out.append(cand)
    return out


class Budget(Exception): pass


def holds(i, chain, name, at, R, W):
    W[0] += 1
    if W[0] > W_SUB_MAX: raise Budget()
    if not chain: return name is None or name in at[i]
    return any(holds(j, chain[1:], name, at, R, W) for j in R[chain[0]][i])


def main():
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ts = json.load(open(B + 'arc-agi_training_solutions.json'))
    N2 = set(open(M + 'novel_N2.txt').read().split())
    keys = [k for k in sorted(tr) if k not in N2]
    if limit: keys = keys[:limit]
    n_prog = n_rec = n_margin = 0; by_gen = {"single": [0, 0], "pair": [0, 0], "default-only": [0, 0]}
    for k in keys:
        t = tr[k]
        if any((len(p["input"]), len(p["input"][0])) != (len(p["output"]), len(p["output"][0])) for p in t["train"]): continue
        try:
            signal.alarm(120); att, _, _ = P.solve_once(t); signal.alarm(0)
        except TO: continue
        except Exception: signal.alarm(0); continue
        if not att: continue
        a = att[0]; rb, re_, rp = (list(a["rules"]) + [None])[:3]
        if re_ or rp or P.nrules(a["rules"]) > 2: continue
        if not all(a["preds"][i] == ts[k][i] for i in range(len(ts[k]))): continue
        n_prog += 1
        gen = "default-only" if len(rb) == 1 else ("single" if len(rb[0][0]) == 1 else ("pair" if len(rb[0][0]) == 2 else "default-only"))
        by_gen[gen][0] += 1
        if gen == "default-only":
            print(json.dumps({"task": k, "gen": gen, "recovered": True, "note": "no concept needed"})); n_rec += 1; by_gen[gen][1] += 1; continue
        g, lab = rb[0]
        pairs = []
        for p in t["train"]:
            nodes, bg, at, src, others, oc = P.prepare(p["input"], a["abstraction"])
            labs = P.predict_labels(rb, at)
            X = {i for i, l in enumerate(labs) if l == lab}
            pairs.append((nodes, at, roles_of(nodes), X))
        C = None
        for nodes, at, R, X in pairs:
            for i in sorted(X):
                m = msc(i, at, R, K)
                C = m if C is None else lcs(C, m)
        # test inputs are available on Kaggle too: their individuals measure generality (Principle 3, G-boundary)
        tests = []
        for q in t["test"]:
            nodes_q, bg_q, at_q, _, _, _ = P.prepare(q["input"], a["abstraction"])
            tests.append((at_q, roles_of(nodes_q)))
        W = [0]; exact = []; tried = 0
        try:
            for chain, name in candidates(C):
                tried += 1
                if all({i for i in range(len(at)) if holds(i, chain, name, at, R, W)} == X for nodes, at, R, X in pairs):
                    gen_ext = sum(1 for at_q, R_q in tests for i in range(len(at_q)) if holds(i, chain, name, at_q, R_q, W))
                    exact.append((-gen_ext, len(chain), name is None, str(name), chain, name))
        except Budget:
            exact = exact or "BUDGET"
        pick = "BUDGET" if exact == "BUDGET" else (min(exact)[4:] if exact else None)
        rec = pick not in (None, "BUDGET")
        test_ok = None
        if rec and not pick[0] and pick[1] is not None:             # depth-0 pick: run it as a lattice rule
            rb2 = [((pick[1],), lab)] + ([rb[-1]] if len(rb) > 1 else [((), "keep")])
            try:
                test_ok = all(P.run_rules(q["input"], (rb2, None, None), a["abstraction"]) == ts[k][i] for i, q in enumerate(t["test"]))
            except Exception:
                test_ok = False
        E = 0.0
        a_act = 9 if str(lab).startswith(("color", "recolor", "paint")) or "=" in str(lab) else 3
        for nodes, at, R, X in pairs:
            E += math.log2(math.comb(len(nodes), len(X))) + len(X) * math.log2(a_act)
        L = 12 + (4 * len(pick[0]) if rec else 0)
        mg = E - L
        n_rec += rec; by_gen[gen][1] += rec; n_margin += rec and mg >= 4
        print(json.dumps({"task": k, "gen": gen, "lattice_rule": [list(g), str(lab)], "recovered": rec,
                          "pick": (list(pick[0]) + [pick[1]]) if rec else pick, "n_exact": (len(exact) if isinstance(exact, list) else None), "test_ok": test_ok, "margin": round(mg, 1),
                          "W_sub": W[0], "tried": tried, "C_t_names": sorted(C[0])[:12], "C_t_roles": sorted(C[1])}), flush=True)
    print(json.dumps({"programs": n_prog, "recovered": n_rec, "recovered_margin_ge_4": n_margin, "by_generator": by_gen}), file=sys.stderr)


if __name__ == "__main__":
    main()
