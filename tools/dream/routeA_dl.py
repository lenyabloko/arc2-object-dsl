"""Fable guidance v11 B2: Route A seeding (T24, tools/dream/routeA_t24.py) reading the materialised A-box; T60 prepared.

Same task selection, target sets, lcs, candidates and checks as routeA_t24.py (its functions are imported, so the
search code is literally the reference's). New:
  --abox python    roles from routeA_t24.roles_of, memberships from occupancy2.prepare (the reference behaviour)
  --abox datalog   one run of tools/datalog/engine.py on tools/datalog/routeA_rules.dl.txt per grid, before the search
                   (G64): role successor sets (touches, inside, contains, aligned, same_shape) and memberships has(I, N)
                   (recogniser names closed under the T58 T-box lattice subsumptions) are read from the fixpoint; the
                   candidate search is propositional over them. Engine calls are counted; a call while the search is
                   running raises (the count inside the search is reported and must be 0).
  --parity FILE    (datalog mode) also computes roles_of and the recogniser memberships for every grid Route A touches,
                   outside the search, and writes per-grid hashes (sha256 of canonical JSON), W_mat and seconds.
  --parity-all F   role / membership parity on every input grid (train and test inputs) of every design training task
                   under each of occupancy2's abstractions (beyond the grids Route A touches); --part K --parts P.
  --pick t60       T60 (v10a §4.2) generality pick by subsumption: among the exact concept names, walk up the class
                   hierarchy while the extension stays exact on every training pair; keep the last exact ancestors;
                   tie-break by depth (longest chain of direct superclasses to a root; smaller = more general), then
                   IRI. No exact name -> the T24 order over the exact role chains. --hierarchy asserted (lattice
                   axioms of results/o0/t58_tbox.ofn.txt) or elk (results/o0/t58_taxonomy.tsv[.txt], tools/owl/T58.java).
  --pick t71       G71 / T71 (Fable v12): the T60 walk over the hierarchy that now includes the G71 parents
                   (tools/owl/lattice_parents.json: name <= ShapeProperty | PositionProperty | ColourRole | ScaleProperty |
                   Relation <= image-schema tops); depth counts up to the tops; among the last exact ancestors of minimal
                   depth: most other exact names under the same G71 class, then higher phi_design (results/o0/
                   t71_phi_design.json, --phi), then IRI. An ELK taxonomy classified before G71 gets the mapping added.
  --vocab F        emitted lattice names and phi_design on the design inputs (inputs only); --part K --parts P.
  --lattice-cache DIR   reuse the lattice pass of routeA_v6.py (lattice_cache*.json: abstraction, first-stage rules,
                   extra stages, |P|, test agreement of attempt 1 = routeA_t24's own filter); without it the lattice
                   runs fresh as in routeA_t24. --verify-cache re-solves the selected programs and compares.
Training pairs only for learning; the test check is routeA_t24's (one per program, depth-0 picks); N2 excluded.
Per-program JSON lines on stdout (routeA_t24's schema; --pick t60 / t71 add a "t60" / "t71" field); summary on stderr.
usage: python3 routeA_dl.py <probe_dir> [--abox python|datalog] [--parity F] [--pick t24|t60|t71] [--hierarchy asserted|elk]
                            [--lattice-cache DIR] [--verify-cache] [--keys k1,k2] [--limit N]
       python3 routeA_dl.py <probe_dir> --write-rules      regenerate the T-box block of routeA_rules.dl.txt
"""
import argparse, hashlib, json, math, os, re, signal, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
DL = os.path.join(ROOT, 'tools', 'datalog')
RULES = os.path.join(DL, 'routeA_rules.dl.txt')
TBOX = os.path.join(ROOT, 'results', 'o0', 't58_tbox.ofn.txt')
PARENTS = os.path.join(ROOT, 'tools', 'owl', 'lattice_parents.json')
PHI = os.path.join(ROOT, 'results', 'o0', 't71_phi_design.json')
TAXONOMY = [os.path.join(ROOT, 'results', 'o0', 't58_taxonomy.tsv'), os.path.join(ROOT, 'results', 'o0', 't58_taxonomy.tsv.txt')]
LAT_NS = "https://github.com/lenyabloko/arc2-object-dsl/ontology/lattice#"
CAP, REL_CAP = 200000, 50000                               # G63

ap = argparse.ArgumentParser()
ap.add_argument("probe"); ap.add_argument("--abox", choices=("python", "datalog"), default="python")
ap.add_argument("--parity"); ap.add_argument("--pick", choices=("t24", "t60", "t71"), default="t24")
ap.add_argument("--hierarchy", choices=("asserted", "elk"), default="asserted"); ap.add_argument("--taxonomy")
ap.add_argument("--lattice-cache"); ap.add_argument("--verify-cache", action="store_true")
ap.add_argument("--keys"); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--write-rules", action="store_true")
ap.add_argument("--parity-all"); ap.add_argument("--part", type=int, default=0); ap.add_argument("--parts", type=int, default=1)
ap.add_argument("--vocab"); ap.add_argument("--phi")
A = ap.parse_args()
if A.parity_all: A.abox, A.parity = "datalog", A.parity_all
for k in ("parity", "lattice_cache", "taxonomy", "vocab", "phi"):
    if getattr(A, k): setattr(A, k, os.path.abspath(getattr(A, k)))

sys.argv = [sys.argv[0], A.probe]                          # routeA_t24 reads its probe from argv[1] at import
sys.path[:0] = [HERE, DL]
import routeA_t24 as RA                                     # noqa: E402  (chdir to the probe, imports occupancy2)
import engine                                               # noqa: E402
P = RA.P


# ------------------------------------------------------------------------------------------------ T-box (lattice section)
def lat_local(name):                                        # = tools/owl/t58_export.lat_local
    s = name.replace(">", "_gt_").replace("=", "_eq_").replace(":", "_")
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    if not re.match(r"[A-Za-z_]", s): s = "a_" + s
    return s


def tbox_lattice():
    """labels (local -> recogniser name) and the named-class subsumptions of the lattice section:
    [("sub", C, D)] for SubClassOf(C D), [("eq", C, D)] for EquivalentClasses(C D) (names, not IRIs)."""
    t = open(TBOX).read()
    lab = dict(re.findall(r'AnnotationAssertion\(rdfs:label lat:(\S+) "([^"]*)"\)', t))
    ann = re.compile(r'Annotation\(rdfs:comment "(?:[^"\\]|\\.)*"\)\s*')
    ax = []
    for line in t.splitlines():
        s = ann.sub('', line)
        m = re.fullmatch(r'(SubClassOf|EquivalentClasses)\(lat:(\w+) lat:(\w+)\)', s)
        if m: ax.append(("sub" if m[1] == "SubClassOf" else "eq", lab[m[2]], lab[m[3]]))
    return lab, ax


def membership_rules():
    out = []
    for kind, c, d in tbox_lattice()[1]:
        out.append('has(I, "%s") :- has(I, "%s").' % (d, c))
        if kind == "eq": out.append('has(I, "%s") :- has(I, "%s").' % (c, d))
    return out


def rule_text():
    """the rule file; its T-box block must equal the block generated from the T-box (G65-style consistency)"""
    text = open(RULES).read()
    block = text.split("% BEGIN tbox-subsumptions\n")[1].split("% END tbox-subsumptions")[0].strip().splitlines()
    if block != membership_rules():
        raise SystemExit("routeA_rules.dl.txt T-box block differs from results/o0/t58_tbox.ofn.txt; run --write-rules")
    return text


if A.write_rules:
    text = open(RULES).read()
    head, rest = text.split("% BEGIN tbox-subsumptions\n")
    tail = rest.split("% END tbox-subsumptions")[1]
    open(RULES, "w").write(head + "% BEGIN tbox-subsumptions\n" + "\n".join(membership_rules()) + "\n% END tbox-subsumptions" + tail)
    print("wrote %d membership rules" % len(membership_rules())); sys.exit(0)


# ------------------------------------------------------------------------------------------------ A-box per grid
class State:
    calls = 0; calls_in_search = 0; in_search = False


PROG = engine.Program(rule_text()) if A.abox == "datalog" else None
GRID_ROWS = []


def edb(grid, nodes, at0):
    """primitive facts only: grid size, cells with colour, individuals' cells, recogniser names (no role is input)"""
    H, W = len(grid), len(grid[0])
    return {"size": [(H, W)], "cell": [(y, x, grid[y][x]) for y in range(H) for x in range(W)],
            "pix": [(i, y, x) for i, n in enumerate(nodes) for (y, x) in n["pix"]],
            "name0": [(i, a) for i, s in enumerate(at0) for a in s]}


def materialise(facts):
    if State.in_search:                                     # G64: never inside program enumeration
        State.calls_in_search += 1
        raise AssertionError("engine called inside the candidate search")
    State.calls += 1
    return PROG.run(facts, cap=CAP, rel_cap=REL_CAP)


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def roles_json(R):
    return {r: sorted([i, j] for i, s in enumerate(R[r]) for j in s) for r in RA.ROLES}


def abox(grid, nodes, at0, key):
    """(at, R) for one grid: memberships and role successor sets"""
    if A.abox == "python":
        return at0, RA.roles_of(nodes)
    t0 = time.perf_counter()
    res = materialise(edb(grid, nodes, at0))
    n = len(nodes)
    at = [set() for _ in range(n)]
    for i, a in res.relations.get("has", []): at[i].add(a)
    R = {r: [set() for _ in range(n)] for r in RA.ROLES}
    for r in RA.ROLES:
        for i, j in res.relations.get(r, []): R[r][i].add(j)
    t1 = time.perf_counter()
    row = {"grid": key, "n_ind": n, "cells": len(grid) * len(grid[0]), "wmat": res.wmat, "engine_s": round(t1 - t0, 4),
           "skipped": sorted(res.skipped)}
    if A.parity:
        t2 = time.perf_counter(); Rp = RA.roles_of(nodes); t3 = time.perf_counter()
        hp, hd = digest(roles_json(Rp)), digest(roles_json(R))
        ap_, ad = [sorted(s) for s in at0], [sorted(s) for s in at]
        row.update(roles_of_s=round(t3 - t2, 4), roles_py=hp[:16], roles_dl=hd[:16], roles_eq=hp == hd,
                   at_py=digest(ap_)[:16], at_dl=digest(ad)[:16], at_eq=ap_ == ad,
                   inherited_new=sum(len(b - a) for a, b in zip(at0, at)),
                   per_role_eq={r: roles_json(Rp)[r] == roles_json(R)[r] for r in RA.ROLES},
                   n_role_facts={r: sum(len(s) for s in R[r]) for r in RA.ROLES})
    GRID_ROWS.append(row)
    return at, R


# ------------------------------------------------------------------------------------------------ class hierarchy (T60)
class Hierarchy:
    """class graph over compact class names ("lat:square_bbox"): direct superclasses, equivalents merged (union-find).
    asserted: every atomic SubClassOf / named EquivalentClasses of the T58 T-box (lattice section, G71 parents and
    tops, and the rest; Pair_* classes have only conjunctive definitions there and stay out). elk: every row of the ELK taxonomy (tools/owl/T58.java TSV: class, direct superclasses
    " | " between nodes and " = " inside a node, equivalents), all classes kept so chains through Pair_* (or any other)
    classes stay intact; owl:Thing is the top and is not a node. A recogniser name absent from the T-box is its own
    root. depth = longest chain of direct superclasses up to a root (a root has depth 0)."""
    def __init__(self, kind, path=None):
        lab, ax = tbox_lattice()
        self.kind, self.parent, self.uf, self.unsat = kind, {}, {}, []
        self.cls = {v: "lat:" + k for k, v in lab.items()}             # recogniser name -> class
        self.name = {"lat:" + k: v for k, v in lab.items() if not k.startswith("Pair_")}   # class -> recogniser name
        M = json.load(open(PARENTS)) if os.path.exists(PARENTS) else {"classes": {}, "names": {}, "schema_tops": {}}
        self.g71 = {"t58:" + c for c in M["classes"]}                 # G71 parent classes
        if kind == "asserted":
            self.source = os.path.relpath(TBOX, ROOT)
            ann = re.compile(r'Annotation\(rdfs:comment "(?:[^"\\]|\\.)*"\)\s*')
            for line in open(TBOX):                                   # every atomic SubClassOf / EquivalentClasses
                m = re.fullmatch(r'(SubClassOf|EquivalentClasses)\(([^\s()]+) ([^\s()]+)\)', ann.sub('', line.strip()))
                if not m: continue
                if m[1] == "EquivalentClasses": self.union(m[2], m[3])
                else: self.parent.setdefault(m[2], set()).add(m[3])
        else:
            path = path or next((p for p in TAXONOMY if os.path.exists(p)), None)
            if not path or not os.path.exists(path):
                raise SystemExit("no ELK taxonomy (results/o0/t58_taxonomy.tsv[.txt]); use --hierarchy asserted")
            self.source = os.path.relpath(path, ROOT)
            for n, line in enumerate(open(path, encoding="utf-8")):
                cols = line.rstrip("\r\n").split("\t")
                if n == 0 or len(cols) < 2 or not cols[0]: continue
                c = cols[0]
                if cols[1].startswith("owl:Nothing"): self.unsat.append(c); continue
                for node in filter(None, cols[1].split(" | ")):
                    ms = [m for m in node.split(" = ") if m != "owl:Thing"]
                    for m in ms: self.parent.setdefault(c, set()).add(m)
                    for m in ms[1:]: self.union(ms[0], m)
                for e in filter(None, (cols[2] if len(cols) > 2 else "").split(" | ")):
                    if e != "owl:Thing": self.union(c, e)
            if self.g71 and not (self.g71 & set(self.parent)):         # taxonomy classified before G71: add the mapping
                self.source += " + tools/owl/lattice_parents.json (taxonomy predates G71)"
                for nm, c in M["names"].items(): self.parent.setdefault(self.node(nm), set()).add("t58:" + c)
                for c, d in M["classes"].items():
                    for t in d["tops"]: self.parent.setdefault("t58:" + c, set()).add(M["schema_tops"][t])
        self._depth, self._anc, self._mem = {}, {}, None

    def node(self, name):
        return self.cls.get(name) or "lat:" + lat_local(name)

    def find(self, x):
        while self.uf.get(x, x) != x: x = self.uf[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.uf[max(ra, rb)] = min(ra, rb)

    def members(self, rep):
        if self._mem is None:
            self._mem = {}
            for k in set(self.parent) | set(self.uf) | {p for v in self.parent.values() for p in v}:
                self._mem.setdefault(self.find(k), set()).add(k)
        return sorted(self._mem.get(rep, set()) | {rep})

    def parents(self, rep):
        return {self.find(p) for m in self.members(rep) for p in self.parent.get(m, ())} - {rep}

    def ancestors(self, name):
        r = self.find(self.node(name))
        if r not in self._anc:
            out, todo = set(), list(self.parents(r))
            while todo:
                p = todo.pop()
                if p not in out: out.add(p); todo += list(self.parents(p))
            self._anc[r] = out
        return self._anc[r]

    def _d(self, r, stack=()):
        if r not in self._depth:
            if r in stack: raise ValueError("cycle in class hierarchy at " + r)
            ps = self.parents(r)
            self._depth[r] = 0 if not ps else 1 + max(self._d(p, stack + (r,)) for p in ps)
        return self._depth[r]

    def depth(self, name):
        return self._d(self.find(self.node(name)))

    def iri(self, name):
        return LAT_NS + self.node(name)[4:]


def t60_pick(exact, pairs, H, W):
    """v10a §4.2: exact = Route A's exact candidates (chain, name). From the exact concept names (the lcs's names whose
    extension equals the targets on every training pair) walk up the hierarchy while exact; keep the last exact
    ancestors (exact names with no exact strict ancestor); pick by (depth, IRI). Classes that are not recogniser names
    (Pair_*, non-lattice) are walked through but never picked. No exact name -> None (caller keeps the T24 order)."""
    names = sorted({nm for ch, nm in exact if not ch and nm is not None})
    if not names:
        return None, {"fallback": "no exact concept name: T24 order over role chains"}
    ext_ok = {n: True for n in names}
    walked = []
    for n in names:                                         # walk up from every exact name
        for a in sorted(H.ancestors(n)):
            for m in H.members(a):
                nm = H.name.get(m)
                if nm is None or nm in ext_ok: continue
                walked.append(nm)                           # instance checks on the materialised A-box (counted in W)
                ext_ok[nm] = all({i for i in range(len(at)) if RA.holds(i, (), nm, at, R, W)} == X for nodes, at, R, X in pairs)
    ex = sorted(n for n, ok in ext_ok.items() if ok)
    top = [n for n in ex if not any(H.find(H.node(m)) in H.ancestors(n) for m in ex)]   # last exact ancestors
    key = lambda n: (H.depth(n), H.iri(n))
    top.sort(key=key)
    return ((), top[0]), {"exact_names": names, "walked_up": walked, "exact_after_walk": ex, "last_exact": top,
                          "depth": {n: H.depth(n) for n in top}, "pick": top[0], "hierarchy": H.kind, "source": H.source,
                          "tie": len(top) > 1 and key(top[0])[0] == key(top[1])[0]}


def t71_pick(exact, pairs, H, W, phi):
    """G71 / T71: the T60 walk, then among the last exact ancestors of minimal depth: the one whose G71 parent class
    holds the most OTHER exact concept names of the task (distinct classes up to equivalence, all exact names of the
    walk, any depth below the parent class); then higher phi_design (design fire ratio, this abstraction); then IRI."""
    p, info = t60_pick(exact, pairs, H, W)
    if p is None: return p, info
    top = info["last_exact"]; dmin = min(H.depth(n) for n in top)
    D = [n for n in top if H.depth(n) == dmin]
    exn = {}
    for m in info["exact_after_walk"]: exn.setdefault(H.find(H.node(m)), m)
    g71 = {H.find(c) for c in H.g71}

    def sib(n):
        me = H.find(H.node(n)); best = (0, None)
        for c in sorted(g71 & H.ancestors(n)):
            k = sum(1 for r, m in exn.items() if r != me and c in H.ancestors(m))
            if k > best[0] or best[1] is None: best = (k, c)
        return best
    sc = {n: sib(n) for n in D}
    key = lambda n: (-sc[n][0], -phi.get(n, 0.0), H.iri(n))
    D.sort(key=key)
    why = "depth" if len(D) == 1 else ("sibling" if sc[D[0]][0] > sc[D[1]][0] else
                                      ("phi_design" if phi.get(D[0], 0.0) > phi.get(D[1], 0.0) else "IRI"))
    info.update(t60_pick_iri=info["pick"], pick=D[0], min_depth=dmin, decided_by=why,
                sibling_split=len({sc[n][0] for n in D}) > 1,
                sibling={n: [sc[n][0], sc[n][1]] for n in D}, phi_design={n: phi.get(n, 0.0) for n in D})
    return ((), D[0]), info


# ------------------------------------------------------------------------------------------------ lattice pass
def load_cache(d):
    c = {}
    for f in sorted(os.listdir(d)):
        if f.startswith('lattice_cache') and f.endswith('.json'): c.update(json.load(open(os.path.join(d, f))))
    return c


def lattice(k, t, ts, cache):
    """(rb, abstraction) of a qualifying first attempt (|P| <= 2, no effects / pixel stage, correct on test) or None"""
    if any((len(p["input"]), len(p["input"][0])) != (len(p["output"]), len(p["output"][0])) for p in t["train"]): return None
    if cache is not None:
        if k not in cache: raise SystemExit("lattice cache lacks " + k)
        r = cache[k]
        if not r or r.get("timeout") or r["extra"] or r["n"] > 2 or not r["ok"]: return None
        return [(tuple(g), l) for g, l in r["rb"]], r["ab"]
    try:
        signal.alarm(120); att, _, _ = P.solve_once(t); signal.alarm(0)
    except RA.TO: return None
    except Exception: signal.alarm(0); return None
    if not att: return None
    a = att[0]; rb, re_, rp = (list(a["rules"]) + [None])[:3]
    if re_ or rp or P.nrules(a["rules"]) > 2: return None
    if not all(a["preds"][i] == ts[k][i] for i in range(len(ts[k]))): return None
    return rb, a["abstraction"]


def verify_cache(tr, ts, keys, cache):
    for k in keys:
        want = lattice(k, tr[k], ts, cache)
        if want is None: continue
        got = lattice(k, tr[k], ts, None)
        same = got is not None and got[1] == want[1] and [(tuple(g), l) for g, l in got[0]] == want[0]
        print(json.dumps({"task": k, "cache_equals_fresh": same, "fresh": None if got is None else [got[1], [[list(g), l] for g, l in got[0]]]}), flush=True)


def parity_summary(rows):
    es = [r["engine_s"] for r in rows]; rs = [r["roles_of_s"] for r in rows]; ws = [r["wmat"] for r in rows]
    return {"grids": len(rows), "roles_equal": sum(r["roles_eq"] for r in rows), "at_equal": sum(r["at_eq"] for r in rows),
            "inherited_new_total": sum(r["inherited_new"] for r in rows),
            "role_mismatch": {r: sum(not x["per_role_eq"][r] for x in rows) for r in RA.ROLES},
            "engine_s_mean": round(sum(es) / max(1, len(es)), 4), "engine_s_max": max(es, default=0),
            "roles_of_s_mean": round(sum(rs) / max(1, len(rs)), 4), "roles_of_s_max": max(rs, default=0),
            "wmat_mean": round(sum(ws) / max(1, len(ws)), 1), "wmat_max": max(ws, default=0),
            "grids_with_skipped_relation": sum(bool(r["skipped"]) for r in rows),
            "mismatch_grids": [r["grid"] for r in rows if not (r["roles_eq"] and r["at_eq"])][:50]}


def vocab(tr, keys):
    """G71 / T71 inputs (design inputs only): every concept name occupancy2.prepare emits on any input grid (train and
    test inputs) of the design training tasks under each abstraction, with counts; and phi_design = per abstraction,
    the fraction of design training-input grids on which the name fires on some individual (routeA_v6's statistic,
    over all design tasks instead of a 150-task sample)."""
    emitted, grids, fire, skip = {}, {}, {}, 0
    for k in keys[A.part::A.parts]:
        ins = [(p["input"], True) for p in tr[k]["train"]] + [(q["input"], False) for q in tr[k]["test"]]
        for g, is_train in ins:
            for ab in P.ABSTRACTIONS:
                try:
                    signal.alarm(30); nodes, bg, at0, _, _, _ = P.prepare(g, ab); signal.alarm(0)
                except RA.TO: skip += 1; continue
                except Exception: signal.alarm(0); skip += 1; continue
                names = set().union(*at0) if at0 else set()
                for n in names: emitted[n] = emitted.get(n, 0) + 1
                if is_train:
                    grids[ab] = grids.get(ab, 0) + 1
                    for n in names: fire.setdefault(ab, {})[n] = fire.setdefault(ab, {}).get(n, 0) + 1
    json.dump({"part": A.part, "parts": A.parts, "grids": grids, "fire": fire, "emitted": emitted, "skipped": skip}, open(A.vocab, "w"))


def parity_all(tr, keys):
    """inputs only (no outputs, no solutions); grids occupancy2 cannot segment (> 64 nodes, errors, 30 s) are counted"""
    seg_skip = 0
    for k in keys[A.part::A.parts]:
        grids = [p["input"] for p in tr[k]["train"]] + [q["input"] for q in tr[k]["test"]]
        for gi, g in enumerate(grids):
            for ab in P.ABSTRACTIONS:
                try:
                    signal.alarm(30); nodes, bg, at0, _, _, _ = P.prepare(g, ab); signal.alarm(0)
                except RA.TO: seg_skip += 1; continue
                except Exception: signal.alarm(0); seg_skip += 1; continue
                abox(g, nodes, at0, "%s:%d:%s" % (k, gi, ab))
    S = dict(parity_summary(GRID_ROWS), segmentation_skipped=seg_skip, engine_calls=State.calls, part=A.part, parts=A.parts)
    json.dump({"summary": S, "rows": GRID_ROWS}, open(A.parity, "w"))
    print(json.dumps(S), file=sys.stderr)


# ------------------------------------------------------------------------------------------------ Route A
def main():
    tr = json.load(open(RA.B + 'arc-agi_training_challenges.json')); ts = json.load(open(RA.B + 'arc-agi_training_solutions.json'))
    N2 = set(open(RA.M + 'novel_N2.txt').read().split())
    keys = [k for k in sorted(tr) if k not in N2]
    if A.keys: keys = [k for k in keys if k in set(A.keys.split(","))]
    if A.limit: keys = keys[:A.limit]
    cache = load_cache(A.lattice_cache) if A.lattice_cache else None
    if A.verify_cache: return verify_cache(tr, ts, keys, cache)
    if A.parity_all: return parity_all(tr, keys)
    if A.vocab: return vocab(tr, keys)
    H = Hierarchy(A.hierarchy, A.taxonomy) if A.pick in ("t60", "t71") else None
    PHI_D = json.load(open(A.phi or PHI))["phi_design"] if A.pick == "t71" else None
    n_prog = n_rec = n_margin = 0; by_gen = {"single": [0, 0], "pair": [0, 0], "default-only": [0, 0]}
    t_start = time.time()
    for k in keys:
        t = tr[k]
        lt = lattice(k, t, ts, cache)
        if lt is None: continue
        rb, ab = lt
        n_prog += 1
        gen = "default-only" if len(rb) == 1 else ("single" if len(rb[0][0]) == 1 else ("pair" if len(rb[0][0]) == 2 else "default-only"))
        by_gen[gen][0] += 1
        if gen == "default-only":
            print(json.dumps({"task": k, "gen": gen, "recovered": True, "note": "no concept needed"})); n_rec += 1; by_gen[gen][1] += 1; continue
        g, lab = rb[0]
        pairs = []
        for pi, p in enumerate(t["train"]):                 # A-box of every training input: once, before the search
            nodes, bg, at0, src, others, oc = P.prepare(p["input"], ab)
            at, R = abox(p["input"], nodes, at0, "%s:train%d:%s" % (k, pi, ab))
            labs = P.predict_labels(rb, at)
            X = {i for i, l in enumerate(labs) if l == lab}
            pairs.append((nodes, at, R, X))
        C = None
        for nodes, at, R, X in pairs:
            for i in sorted(X):
                m = RA.msc(i, at, R, RA.K)
                C = m if C is None else RA.lcs(C, m)
        tests = []
        for qi, q in enumerate(t["test"]):                  # test inputs: generality measure only (as routeA_t24)
            nodes_q, bg_q, at_q0, _, _, _ = P.prepare(q["input"], ab)
            tests.append(abox(q["input"], nodes_q, at_q0, "%s:test%d:%s" % (k, qi, ab)))
        State.in_search = True                              # G64: propositional from here to the pick
        W = [0]; exact = []; tried = 0; t60 = None
        try:
            for chain, name in RA.candidates(C):
                tried += 1
                if all({i for i in range(len(at)) if RA.holds(i, chain, name, at, R, W)} == X for nodes, at, R, X in pairs):
                    gen_ext = sum(1 for at_q, R_q in tests for i in range(len(at_q)) if RA.holds(i, chain, name, at_q, R_q, W))
                    exact.append((-gen_ext, len(chain), name is None, str(name), chain, name))
        except RA.Budget:
            exact = exact or "BUDGET"
        pick = "BUDGET" if exact == "BUDGET" else (min(exact)[4:] if exact else None)
        if A.pick in ("t60", "t71") and isinstance(exact, list) and exact:
            try:
                p60, t60 = (t60_pick([e[4:] for e in exact], pairs, H, W) if A.pick == "t60" else
                            t71_pick([e[4:] for e in exact], pairs, H, W, PHI_D.get(ab, {})))
            except RA.Budget:
                p60, t60 = None, {"fallback": "BUDGET during the walk: T24 order"}
            t60["t24_pick"] = list(pick[0]) + [pick[1]]
            if p60 is not None: pick = p60
        State.in_search = False
        rec = pick not in (None, "BUDGET")
        test_ok = None
        if rec and not pick[0] and pick[1] is not None:     # depth-0 pick: run it as a lattice rule (routeA_t24's check)
            rb2 = [((pick[1],), lab)] + ([rb[-1]] if len(rb) > 1 else [((), "keep")])
            try:
                test_ok = all(P.run_rules(q["input"], (rb2, None, None), ab) == ts[k][i] for i, q in enumerate(t["test"]))
            except Exception:
                test_ok = False
        E = 0.0
        a_act = 9 if str(lab).startswith(("color", "recolor", "paint")) or "=" in str(lab) else 3
        for nodes, at, R, X in pairs:
            E += math.log2(math.comb(len(nodes), len(X))) + len(X) * math.log2(a_act)
        L = 12 + (4 * len(pick[0]) if rec else 0)
        mg = E - L
        n_rec += rec; by_gen[gen][1] += rec; n_margin += rec and mg >= 4
        line = {"task": k, "gen": gen, "lattice_rule": [list(g), str(lab)], "recovered": rec,
                "pick": (list(pick[0]) + [pick[1]]) if rec else pick, "n_exact": (len(exact) if isinstance(exact, list) else None), "test_ok": test_ok, "margin": round(mg, 1),
                "W_sub": W[0], "tried": tried, "C_t_names": sorted(C[0])[:12], "C_t_roles": sorted(C[1])}
        if A.pick in ("t60", "t71"): line[A.pick] = t60
        print(json.dumps(line), flush=True)
    summ = {"programs": n_prog, "recovered": n_rec, "recovered_margin_ge_4": n_margin, "by_generator": by_gen}
    print(json.dumps(summ), file=sys.stderr)
    if A.abox == "datalog":
        es = [r["engine_s"] for r in GRID_ROWS]; ws = [r["wmat"] for r in GRID_ROWS]
        S = {"mode": "datalog", "pick": A.pick, "grids": len(GRID_ROWS), "engine_calls": State.calls,
             "engine_calls_in_search": State.calls_in_search, "engine_s_mean": round(sum(es) / max(1, len(es)), 4),
             "engine_s_max": max(es, default=0), "engine_s_total": round(sum(es), 3), "wmat_max": max(ws, default=0),
             "wmat_mean": round(sum(ws) / max(1, len(ws)), 1), "grids_with_skipped_relation": sum(bool(r["skipped"]) for r in GRID_ROWS),
             "run_s": round(time.time() - t_start, 1), "t24_summary": summ}
        if A.parity:
            S.update({k: v for k, v in parity_summary(GRID_ROWS).items() if k not in S})
            json.dump({"summary": S, "rows": GRID_ROWS}, open(A.parity, "w"), indent=0)
        print(json.dumps(S), file=sys.stderr)


if __name__ == "__main__":
    main()
