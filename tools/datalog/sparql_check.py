"""Standard-engine cross-check of engine.py: the rule file is translated mechanically (generic, from the engine's
rule AST) into SPARQL 1.1 CONSTRUCT queries and run by rdflib's SPARQL engine, iterated to a fixpoint per stratum
(same stratification as engine.py), then every derived relation is compared with engine.py on the same EDB.

Encoding: fact p(v0..vk) = IRI <urn:f:p/v0/../vk> with properties ex:p_0 v0 ... ex:p_k vk (typed literals; no
rdf:type triple, so rdflib's pattern ordering joins on shared variables instead of scanning a predicate's facts).
Translation of a body literal (in the engine's join order): positive atom -> triple patterns; negated atom ->
FILTER NOT EXISTS { ... }; comparison -> FILTER(...); 'V = e' with V unbound -> BIND(e AS ?V); abs -> ABS,
min/max -> IF. Head -> CONSTRUCT template with the fact IRI from BIND(IRI(CONCAT(...))). Rules with a head aggregate
are translated to a sub-SELECT with GROUP BY (MIN / MAX / COUNT(DISTINCT ...)) unless --agg-from-engine, in which
case aggregate relations are copied from engine.py and only the aggregate-free rules are checked.
Join order: rdflib's evalPart sorts a BGP's triples by the number of unbound terms (patterns holding a constant go
first), which makes rules with several constant-bearing atoms cross products. By default a BGP evaluator registered
through rdflib's official extension point (rdflib.plugins.sparql.CUSTOM_EVALS) orders the triples greedily (next =
fewest unbound variables given the bindings so far, ties to patterns sharing bound variables) and then calls
rdflib's own evalBGP. A BGP's solutions do not depend on triple order, so the SPARQL semantics are unchanged;
--rdflib-order keeps rdflib's order.
usage: python3 sparql_check.py [--n 100] [--extra 40 --max-cells 100] [--part K --parts P] [--agg-from-engine]
       python3 sparql_check.py --merge P [--n .. --extra ..]          -> results/o0/t59_sparql_check.json
"""
import argparse, json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine  # noqa: E402
import t59_parity as T  # noqa: E402
from rdflib import Graph, Literal, Namespace, URIRef  # noqa: E402
from rdflib.plugins.sparql import CUSTOM_EVALS, prepareQuery  # noqa: E402
from rdflib.plugins.sparql.evaluate import evalBGP  # noqa: E402
from rdflib.term import BNode, Variable  # noqa: E402

EX = Namespace("urn:p:")


def greedy_bgp(ctx, part):
    if part.name != "BGP": raise NotImplementedError
    isv = lambda x: isinstance(x, (Variable, BNode))
    rest, out = list(part.triples), []
    known = {x for t in rest for x in t if isv(x) and ctx[x] is not None}
    while rest:
        k = min(range(len(rest)), key=lambda i: (sum(isv(x) and x not in known for x in rest[i]),
                                                 -sum(isv(x) and x in known for x in rest[i]), i))
        t = rest.pop(k); out.append(t); known |= {x for x in t if isv(x)}
    return evalBGP(ctx, out)


def lit(v):
    return '"%s"' % v if isinstance(v, str) else str(v)


def sx(e):
    """engine expression -> SPARQL expression"""
    if e[0] == "v": return "?" + e[1]
    if e[0] == "c": return lit(e[1])
    if e[0] == "op": return "(%s %s %s)" % (sx(e[2]), e[1], sx(e[3]))
    if e[0] == "neg": return "(-%s)" % sx(e[1])
    a = [sx(x) for x in e[2]]
    if e[1] == "abs": return "ABS(%s)" % a[0]
    return "IF(%s %s %s, %s, %s)" % (a[0], "<" if e[1] == "min" else ">", a[1], a[0], a[1])


class Tr:
    def __init__(self): self.n = 0

    def fresh(self, p): self.n += 1; return "?%s%d" % (p, self.n)

    def atom(self, p, args):
        f = self.fresh("f"); parts = []
        for i, a in enumerate(args):
            parts.append("ex:%s_%d %s" % (p, i, self.fresh("w") if a[0] == "w" else ("?" + a[1] if a[0] == "v" else lit(a[1]))))
        return f + " " + " ; ".join(parts) + " ."

    def body(self, body):
        order, _ = engine.schedule(body, None)
        out, filters = [], []
        for k, mode in order:
            l = body[k]
            if l[0] == "atom" and not l[3]: out.append(self.atom(l[1], l[2]))
            elif l[0] == "atom": filters.append("FILTER NOT EXISTS { %s }" % self.atom(l[1], l[2]))
            elif isinstance(mode, tuple): out.append("BIND(%s AS ?%s)" % (sx(mode[2]), mode[1]))
            else: filters.append("FILTER(%s %s %s)" % (sx(l[2]), l[1], sx(l[3])))
        return "\n  ".join(out + filters)

    def rule(self, head, body):
        p, args = head
        hs, tmpl = [], []
        agg = [a for a in args if a[0] == "agg"]
        for i, a in enumerate(args):
            t = "?agg" if a[0] == "agg" else ("?" + a[1] if a[0] == "v" else lit(a[1]))
            hs.append("STR(%s)" % t); tmpl.append("ex:%s_%d %s" % (p, i, t))
        iri = 'BIND(IRI(CONCAT("urn:f:%s/", %s)) AS ?h)' % (p, ', "/", '.join(hs))
        where = self.body(body)
        if agg:
            fn, vs = agg[0][1], agg[0][2]
            gv = " ".join("?" + a[1] for a in args if a[0] == "v")
            if fn == "count":
                e = "?" + vs[0] if len(vs) == 1 else "CONCAT(%s)" % ', "|", '.join("STR(?%s)" % v for v in vs)
                ag = "(COUNT(DISTINCT %s) AS ?agg)" % e
            else: ag = "(%s(?%s) AS ?agg)" % (fn.upper(), vs[0])
            where = "{ SELECT %s %s WHERE {\n  %s } GROUP BY %s }" % (gv, ag, where, gv)
        return "PREFIX ex: <urn:p:>\nCONSTRUCT { ?h %s . } WHERE {\n  %s\n  %s }" % (" ; ".join(tmpl), where, iri)


def add_fact(g, p, t):
    f = URIRef("urn:f:%s/%s" % (p, "/".join(str(v) for v in t)))
    for i, v in enumerate(t): g.add((f, EX["%s_%d" % (p, i)], Literal(v)))


def read_rel(g, p, arity):
    out = set()
    for f in set(g.subjects(EX[p + "_0"], None)):
        out.add(tuple(g.value(f, EX["%s_%d" % (p, i)]).toPython() for i in range(arity)))
    return out


def check(prog, queries, edbf, agg_from_engine):
    res = prog.run(edbf)
    g = Graph()
    for p, ts in list(prog.facts.items()) + list(edbf.items()):
        for t in ts: add_fact(g, p, tuple(t))
    for comp, rs in prog.compiled:
        rec = any(r for _, r, _ in rs)
        for ri, _, _ in rs:
            head = prog.rules[ri][0]
            if agg_from_engine and any(a[0] == "agg" for a in head[1]):
                for t in res.relations[head[0]]: add_fact(g, head[0], t)
        while True:
            n0 = len(g)
            for ri, _, _ in rs:
                if queries[ri] is None: continue
                for tr in g.query(queries[ri]): g.add(tr)
            if not rec or len(g) == n0: break
    diff = {}
    for p in prog.idb:
        a = read_rel(g, p, prog.arity[p]); b = set(res.relations[p])
        if a != b: diff[p] = [len(a - b), len(b - a)]
    return diff, len(g), {r for r, c in res.by_rule.items() if c}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100, help="smallest design grids (by cell count)")
    ap.add_argument("--extra", type=int, default=0, help="more grids, evenly spaced over the larger grids")
    ap.add_argument("--max-cells", type=int, default=100); ap.add_argument("--agg-from-engine", action="store_true")
    ap.add_argument("--rdflib-order", action="store_true"); ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--parts", type=int, default=1); ap.add_argument("--merge", type=int, default=0)
    ap.add_argument("--out", default="t59_sparql_check.json")
    a = ap.parse_args()
    if not a.rdflib_order: CUSTOM_EVALS["greedy_bgp"] = greedy_bgp
    prog = engine.Program(open(os.path.join(HERE, "o0_rules.dl.txt")).read())
    tr = Tr()
    texts = [None if (a.agg_from_engine and any(x[0] == "agg" for x in h[1])) else tr.rule(h, b) for h, b in prog.rules]
    out = os.path.join(T.OUT, a.out)
    if a.merge:
        parts = [json.load(open(out.replace(".json", ".part%d.json" % k))) for k in range(a.merge)]
        rows = [r for q in parts for r in q["rows"]]; fired = set().union(*[set(q["fired"]) for q in parts])
        sec = sum(q["sec"] for q in parts)
    else:
        queries = [None if t is None else prepareQuery(t) for t in texts]
        P = T.Hn.setup(os.path.join(T.M1B, "v34"))
        grids, n2 = T.design_grids()
        grids.sort(key=lambda kg: (len(kg[1]) * len(kg[1][0]), kg[0]))
        ok = []
        for key, gr in grids:
            if len(gr) * len(gr[0]) > a.max_cells: break
            try: ok.append((key, gr, T.Hn.individuals(P, gr, "nbccg")))
            except Exception: continue
        pick = ok[:a.n]; big = ok[a.n:]
        if a.extra and big: pick += [big[(k * len(big)) // a.extra] for k in range(min(a.extra, len(big)))]
        rows, fired, t0 = [], set(), time.time()
        for key, gr, (inds, names, bg) in pick[a.part::a.parts]:
            t1 = time.time()
            diff, ntrip, fr = check(prog, queries, T.edb(gr, inds, bg), a.agg_from_engine); fired |= fr
            rows.append({"key": key, "cells": len(gr) * len(gr[0]), "n_ind": len(inds), "agree": not diff, "diff": diff,
                         "triples": ntrip, "sec": round(time.time() - t1, 2)})
            print(json.dumps(rows[-1]), file=sys.stderr, flush=True)
        sec = time.time() - t0
        if a.parts > 1:
            os.makedirs(T.OUT, exist_ok=True)
            json.dump({"rows": rows, "fired": sorted(fired), "sec": sec}, open(out.replace(".json", ".part%d.json" % a.part), "w"))
            sys.exit(0)
    S = {"grids": len(rows), "agree": sum(r["agree"] for r in rows), "rules_translated": sum(t is not None for t in texts),
         "rules_total": len(prog.rules), "rules_exercised": len(fired),
         "rules_not_exercised": sorted(set(engine.fmt_rule(h, b) for h, b in prog.rules) - fired),
         "aggregates": "engine" if a.agg_from_engine else "SPARQL GROUP BY",
         "bgp_order": "rdflib" if a.rdflib_order else "greedy (CUSTOM_EVALS)",
         "cells_max": max(r["cells"] for r in rows), "ind_max": max(r["n_ind"] for r in rows),
         "grids_over_9_cells": sum(r["cells"] > 9 for r in rows), "sec_total": round(sec, 1),
         "disagree_preds": sorted({p for r in rows for p in r["diff"]})}
    os.makedirs(T.OUT, exist_ok=True)
    json.dump({"summary": S, "rows": rows, "example_query": texts[[h[0] for h, b in prog.rules].index("allen")]},
              open(out, "w"), indent=0)
    print(json.dumps(S, indent=1))
