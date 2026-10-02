"""Stratified semi-naive Datalog evaluator (pure Python, single-threaded, no timeouts, deterministic).

Rule syntax (Souffle / Prolog-like; the rule file is data):
    % comment            // comment
    dirvec("N", -1, 0).                                   ground fact (constant table)
    ec(I, J) :- adj(I, J), !share(I, J), I != J.          Horn rule; '!' = stratified negation
    lo(I, "row", min(Y)) :- pix(I, Y, _).                 head aggregate: min(V) | max(V) | count(V, ...)
    nxt(D, Y, X, Y2, X2) :- dirvec(D, DY, DX), cell(Y, X, _), Y2 = Y + DY, X2 = X + DX, cell(Y2, X2, _).
Terms: Variables start upper-case or '_' ('_' alone = anonymous); integers (also negative); "strings"; lower-case
symbols are string constants. Built-ins: = != < <= > >= over integer expressions with + - * abs(e) min(a,b) max(a,b);
'V = expr' binds V when V is unbound and expr is bound. Atom arguments are plain terms (use '=' for arithmetic).
Aggregates group by the other head arguments; count(V1..Vk) counts distinct tuples, min/max over distinct values;
an empty group yields no fact.
Semantics: predicates are split into strongly connected components of the dependency graph; a negated or aggregated
body predicate must lie in a strictly lower component (else StratificationError). Components are evaluated in
topological order; recursive ones by semi-naive iteration (one rule variant per recursive body atom, that atom read
from the last delta and placed first in the join). Safety (every head / negated / compared variable bound by a
positive atom or an assignment) is checked at load time. Each rule body is compiled once into a Python function of
nested loops over hash indices (built lazily, maintained incrementally).
Work W_mat = number of distinct derived facts (EDB and constant facts excluded); counts are kept per rule (the rule
that first derived the fact) and per predicate.
Lazy views (G63): 'dc(I, J) ?- lo(I, "row", _), obj(J), I != J, !connected(I, J).' is never materialised and costs no
W_mat; Program.query(res, "dc", args) answers it from the materialised facts (args: tuple with None for free
positions). Its body may negate any materialised predicate (the fixpoint is complete when it is asked).
Per-relation cap: with rel_cap, a predicate whose stored facts exceed rel_cap is skipped for this run together with
its whole component (evaluation of that component stops, its facts are discarded and not counted in W_mat), and so
is every component or view that uses a skipped predicate. res.skipped logs predicate -> {size, reason}.

Usage:
    from engine import Program
    prog = Program(open("o0_rules.dl.txt").read())
    res = prog.run({"cell": [(0, 0, 3), ...], "pix": [...]}, cap=None, rel_cap=50000)   # cap: WorkCap if W_mat > cap
    res.relations["rcc8_EC"]   -> sorted list of tuples;  res.wmat;  res.by_rule (rule text -> facts);  res.by_pred
    prog.query(res, "rcc8_DC") -> sorted tuples (None if a predicate it uses was skipped)
"""
import re

AGG = ("min", "max", "count")
FUN = ("abs", "min", "max")
CMP = ("=", "!=", "<", "<=", ">", ">=")
_TOK = re.compile(r'\s+|%[^\n]*|//[^\n]*|(:-|\?-|!=|<=|>=|[(),.!=<>+*-])|(\d+)|("[^"]*")|([A-Za-z_][A-Za-z0-9_]*)|(\S)')


class DatalogError(Exception): pass
class StratificationError(DatalogError): pass
class WorkCap(DatalogError): pass


class _Skip(Exception): pass


# ------------------------------------------------------------------------------------------------ parser
def tokenize(text):
    out = []
    for m in _TOK.finditer(text):
        op, num, s, ident, bad = m.groups()
        if bad: raise DatalogError("bad character %r at %d" % (bad, m.start()))
        if op: out.append(("op", op))
        elif num: out.append(("num", int(num)))
        elif s: out.append(("str", s[1:-1]))
        elif ident: out.append(("id", ident))
    out.append(("eof", None))
    return out


class Parser:
    """clause := atom [(':-' | '?-') literal {',' literal}] '.'; terms: ('v', name) | ('c', value) | ('w',)."""
    def __init__(self, text):
        self.t = tokenize(text); self.i = 0; self.anon = 0

    def peek(self, k=0): return self.t[self.i + k]
    def next(self): tok = self.t[self.i]; self.i += 1; return tok

    def expect(self, val):
        tok = self.next()
        if tok[1] != val: raise DatalogError("expected %r, got %r (token %d)" % (val, tok[1], self.i))

    def clauses(self):
        out = []
        while self.peek()[0] != "eof":
            head = self.atom(head=True); body = []; kind = ":-"
            if self.peek()[1] in (":-", "?-"):
                kind = self.next()[1]; body.append(self.literal())
                while self.peek()[1] == ",": self.next(); body.append(self.literal())
            self.expect("."); out.append((head, body, kind))
        return out

    def term(self):
        k, v = self.next()
        if k == "num": return ("c", v)
        if k == "str": return ("c", v)
        if k == "op" and v == "-" and self.peek()[0] == "num": return ("c", -self.next()[1])
        if k == "id":
            if v == "_": self.anon += 1; return ("w",)
            return ("v", v) if (v[0].isupper() or v[0] == "_") else ("c", v)
        raise DatalogError("bad term %r" % (v,))

    def atom(self, head=False):
        k, name = self.next()
        if k != "id" or not name[0].islower(): raise DatalogError("bad predicate %r" % (name,))
        self.expect("("); args = []
        while True:
            if head and self.peek()[0] == "id" and self.peek()[1] in AGG and self.peek(1)[1] == "(":
                fn = self.next()[1]; self.next(); vs = [self.term()]
                while self.peek()[1] == ",": self.next(); vs.append(self.term())
                self.expect(")"); args.append(("agg", fn, [v[1] for v in vs]))
            else: args.append(self.term())
            if self.peek()[1] == ")": self.next(); return (name, args)
            self.expect(",")

    def literal(self):
        if self.peek()[1] == "!":
            self.next(); p, a = self.atom(); return ("atom", p, a, True)
        k, v = self.peek()
        if k == "id" and v[0].islower() and v not in FUN and self.peek(1)[1] == "(":
            p, a = self.atom(); return ("atom", p, a, False)
        lhs = self.expr(); op = self.next()[1]
        if op not in CMP: raise DatalogError("expected comparison, got %r" % (op,))
        return ("cmp", op, lhs, self.expr())

    def expr(self):
        e = self.prod()
        while self.peek()[1] in ("+", "-"): op = self.next()[1]; e = ("op", op, e, self.prod())
        return e

    def prod(self):
        e = self.unary()
        while self.peek()[1] == "*": self.next(); e = ("op", "*", e, self.unary())
        return e

    def unary(self):
        k, v = self.peek()
        if v == "-": self.next(); return ("neg", self.unary())
        if v == "(": self.next(); e = self.expr(); self.expect(")"); return e
        if k == "id" and v in FUN and self.peek(1)[1] == "(":
            self.next(); self.next(); args = [self.expr()]
            while self.peek()[1] == ",": self.next(); args.append(self.expr())
            self.expect(")"); return ("f", v, args)
        t = self.term()
        if t[0] == "w": raise DatalogError("'_' in expression")
        return t


def evars(e):
    if e[0] == "v": return {e[1]}
    if e[0] in ("c", "w"): return set()
    if e[0] == "op": return evars(e[2]) | evars(e[3])
    if e[0] == "neg": return evars(e[1])
    return set().union(*[evars(a) for a in e[2]])


def lvars(lit):
    if lit[0] == "atom": return {a[1] for a in lit[2] if a[0] == "v"}
    return evars(lit[2]) | evars(lit[3])


def fmt_term(a):
    if a[0] == "v": return a[1]
    if a[0] == "w": return "_"
    if a[0] == "agg": return "%s(%s)" % (a[1], ", ".join(a[2]))
    return '"%s"' % a[1] if isinstance(a[1], str) else str(a[1])


def fmt_expr(e):
    if e[0] in ("v", "c", "w"): return fmt_term(e)
    if e[0] == "op":
        a, b = fmt_expr(e[2]), fmt_expr(e[3])
        if e[2][0] == "op" and e[1] == "*" and e[2][1] != "*": a = "(" + a + ")"
        if e[3][0] == "op" and (e[1] != "+" or e[3][1] != "*"): b = "(" + b + ")"
        return "%s %s %s" % (a, e[1], b)
    if e[0] == "neg": return "-" + fmt_expr(e[1])
    return "%s(%s)" % (e[1], ", ".join(fmt_expr(a) for a in e[2]))


def fmt_lit(l):
    if l[0] == "atom": return ("!" if l[3] else "") + "%s(%s)" % (l[1], ", ".join(fmt_term(a) for a in l[2]))
    return "%s %s %s" % (fmt_expr(l[2]), l[1], fmt_expr(l[3]))


def fmt_rule(head, body):
    h = "%s(%s)" % (head[0], ", ".join(fmt_term(a) for a in head[1]))
    return h + (" :- " + ", ".join(fmt_lit(l) for l in body) if body else "") + "."


# ------------------------------------------------------------------------------------------------ compiler
def pyexpr(e):
    if e[0] == "v": return "v_" + e[1]
    if e[0] == "c": return repr(e[1])
    if e[0] == "op": return "(%s %s %s)" % (pyexpr(e[2]), e[1], pyexpr(e[3]))
    if e[0] == "neg": return "(-%s)" % pyexpr(e[1])
    return "%s(%s)" % (e[1], ", ".join(pyexpr(a) for a in e[2]))


def schedule(body, first):
    """Join order: the delta atom (index `first`) first, then positive atoms in written order; each negation or
    comparison is placed as soon as its variables are bound ('V = e' with V unbound becomes an assignment)."""
    order, bound = [], set()
    pend = list(range(len(body)))
    if first is not None:
        order.append((first, "scan")); bound |= lvars(body[first]); pend.remove(first)
    while pend:
        placed = False
        for k in pend:
            l = body[k]
            if l[0] == "atom" and l[3] and lvars(l) <= bound:
                order.append((k, "neg")); pend.remove(k); placed = True; break
            if l[0] == "cmp":
                if lvars(l) <= bound:
                    order.append((k, "test")); pend.remove(k); placed = True; break
                if l[1] == "=":
                    for a, b in ((l[2], l[3]), (l[3], l[2])):
                        if a[0] == "v" and a[1] not in bound and evars(b) <= bound:
                            order.append((k, ("assign", a[1], b))); bound.add(a[1]); pend.remove(k); placed = True; break
                    if placed: break
        if placed: continue
        pos = [k for k in pend if body[k][0] == "atom" and not body[k][3]]
        if not pos: raise DatalogError("unsafe rule: cannot bind %s" % ", ".join(fmt_lit(body[k]) for k in pend))
        order.append((pos[0], "join")); bound |= lvars(body[pos[0]]); pend.remove(pos[0])
    return order, bound


def compile_rule(head, body, first=None):
    """Python source of `def f(R, IX, DELTA)` returning the list of head tuples (or (group, value) pairs)."""
    order, bound = schedule(body, first)
    hv = set()
    for a in head[1]:
        if a[0] == "v": hv.add(a[1])
        elif a[0] == "agg": hv |= set(a[2])
        elif a[0] == "w": raise DatalogError("'_' in head: " + fmt_rule(head, body))
    if not hv <= bound: raise DatalogError("unsafe head variables %s in %s" % (hv - bound, fmt_rule(head, body)))
    pre, code, ind, bnd, n = [], [], 1, set(), [0]

    def fresh(p):
        n[0] += 1; return "%s%d" % (p, n[0])

    def emit(s): code.append("    " * ind + s)

    def key(args, poss):                     # index key: scalar for one position, else tuple
        ks = [pyexpr(args[p]) for p in poss]
        return ks[0] if len(ks) == 1 else "(" + ", ".join(ks) + ")"

    def fact(args):                          # full tuple for set membership
        return "(" + "".join(pyexpr(a) + ", " for a in args) + ")"

    for k, mode in order:
        lit = body[k]
        if lit[0] == "cmp":
            if isinstance(mode, tuple): emit("v_%s = %s" % (mode[1], pyexpr(mode[2]))); bnd.add(mode[1])
            else:
                op = "==" if lit[1] == "=" else lit[1]
                emit("if %s %s %s:" % (pyexpr(lit[2]), op, pyexpr(lit[3]))); ind += 1
            continue
        p, args = lit[1], lit[2]
        bpos = [i for i, a in enumerate(args) if a[0] == "c" or (a[0] == "v" and a[1] in bnd)]
        if mode == "neg":
            if len(bpos) == len(args): r = fresh("R"); pre.append("%s = R[%r]" % (r, p)); emit("if %s not in %s:" % (fact(args), r))
            elif not bpos: r = fresh("R"); pre.append("%s = R[%r]" % (r, p)); emit("if not %s:" % r)
            else: x = fresh("X"); pre.append("%s = IX(%r, %r)" % (x, p, tuple(bpos))); emit("if %s not in %s:" % (key(args, bpos), x))
            ind += 1; continue
        names, checks, new = [], [], set()
        for i, a in enumerate(args):
            if a[0] == "w": names.append("_")
            elif mode != "scan" and i in bpos: names.append("_")
            elif a[0] == "c": t = fresh("t"); names.append(t); checks.append("%s == %r" % (t, a[1]))
            elif a[1] in bnd or a[1] in new: t = fresh("t"); names.append(t); checks.append("%s == v_%s" % (t, a[1]))
            else: names.append("v_" + a[1]); new.add(a[1])
        unpack = "(" + ", ".join(names) + ("," if len(names) == 1 else "") + ")"
        if mode == "scan": emit("for %s in DELTA:" % unpack)
        elif not bpos: r = fresh("R"); pre.append("%s = R[%r]" % (r, p)); emit("for %s in %s:" % (unpack, r))
        elif len(bpos) == len(args) and not new: r = fresh("R"); pre.append("%s = R[%r]" % (r, p)); emit("if %s in %s:" % (fact(args), r))
        else: x = fresh("X"); pre.append("%s = IX(%r, %r)" % (x, p, tuple(bpos))); emit("for %s in %s.get(%s, ()):" % (unpack, x, key(args, bpos)))
        ind += 1; bnd |= new
        if checks: emit("if %s:" % " and ".join(checks)); ind += 1
    hs = [pyexpr(a) if a[0] != "agg" else None for a in head[1]]
    aggs = [a for a in head[1] if a[0] == "agg"]
    if aggs:
        a = aggs[0]; g = [h for h in hs if h is not None]
        val = "(" + ", ".join("v_" + v for v in a[2]) + ",)" if a[1] == "count" else "v_" + a[2][0]
        emit("OUT.append(((%s), %s))" % ("".join(x + ", " for x in g), val))
    else: emit("OUT.append((%s))" % "".join(x + ", " for x in hs))
    return "\n".join(["def f(R, IX, DELTA):", "    OUT = []"] + ["    " + s for s in pre] + code + ["    return OUT"])


# ------------------------------------------------------------------------------------------------ program
class Result:
    def __init__(self, relations, wmat, by_rule, by_pred, skipped, R, IX):
        self.relations, self.wmat, self.by_rule, self.by_pred = relations, wmat, by_rule, by_pred
        self.skipped, self._R, self._IX = skipped, R, IX


def subst(t, env):
    """replace variables bound in env (name -> value) by constants, in a term, expression or literal"""
    if t[0] == "v": return ("c", env[t[1]]) if t[1] in env else t
    if t[0] in ("c", "w"): return t
    if t[0] == "op": return ("op", t[1], subst(t[2], env), subst(t[3], env))
    if t[0] == "neg": return ("neg", subst(t[1], env))
    if t[0] == "f": return ("f", t[1], [subst(a, env) for a in t[2]])
    if t[0] == "atom": return ("atom", t[1], [subst(a, env) for a in t[2]], t[3])
    return ("cmp", t[1], subst(t[2], env), subst(t[3], env))


class Program:
    def __init__(self, text):
        self.facts, self.rules, self.views = {}, [], {}
        for head, body, kind in Parser(text).clauses():
            if kind == "?-":
                if any(a[0] == "agg" for a in head[1]) or head[0] in self.views: raise DatalogError("bad view " + head[0])
                self.views[head[0]] = (head, body); continue
            if not body:
                if any(a[0] != "c" for a in head[1]): raise DatalogError("non-ground fact " + fmt_rule(head, body))
                self.facts.setdefault(head[0], set()).add(tuple(a[1] for a in head[1]))
            else:
                if sum(a[0] == "agg" for a in head[1]) > 1: raise DatalogError("one aggregate per head: " + fmt_rule(head, body))
                self.rules.append((head, body))
        self.arity = {}
        for head, body in self.rules:
            for p, n in [(head[0], len(head[1]))] + [(l[1], len(l[2])) for l in body if l[0] == "atom"]:
                if self.arity.setdefault(p, n) != n: raise DatalogError("arity clash for %s" % p)
        self.idb = sorted({h[0] for h, b in self.rules})
        for v, (head, body) in self.views.items():
            if v in self.arity or v in self.facts: raise DatalogError("view %s is also stored" % v)
            for l in body:
                if l[0] == "atom" and l[1] in self.views: raise DatalogError("view %s uses view %s" % (v, l[1]))
            compile_rule(head, body)                     # safety check
        self._vcache = {}
        self.strata = self.stratify()
        self.compiled = []                       # per stratum: [(rule index, recursive?, [(first, fn)])]
        for comp in self.strata:
            cs = set(comp); rs = []
            for ri, (head, body) in enumerate(self.rules):
                if head[0] not in cs: continue
                rec = [k for k, l in enumerate(body) if l[0] == "atom" and not l[3] and l[1] in cs]
                variants = [(k, self._fn(head, body, k)) for k in rec] if rec else [(None, self._fn(head, body, None))]
                rs.append((ri, bool(rec), variants))
            self.compiled.append((comp, rs))

    def _fn(self, head, body, first):
        src = compile_rule(head, body, first); env = {}
        exec(compile(src, "<rule %s>" % fmt_rule(head, body), "exec"), env)
        return env["f"]

    def stratify(self):
        """SCCs of the predicate dependency graph (Tarjan, iterative), in topological order; strict edges
        (negation, aggregation) must cross components."""
        edges, strict = {}, []
        for head, body in self.rules:
            agg = any(a[0] == "agg" for a in head[1])
            for l in body:
                if l[0] != "atom": continue
                edges.setdefault(l[1], set()).add(head[0])
                if l[3] or agg: strict.append((l[1], head[0], fmt_rule(head, body)))
        nodes = sorted(set(edges) | set(self.idb) | {q for v in edges.values() for q in v})
        index, low, onst, st, comps, comp_of, cnt = {}, {}, set(), [], [], {}, [0]
        for root in nodes:
            if root in index: continue
            work = [(root, iter(sorted(edges.get(root, ()))))]
            index[root] = low[root] = cnt[0]; cnt[0] += 1; st.append(root); onst.add(root)
            while work:
                v, it = work[-1]; w = next(it, None)
                if w is not None:
                    if w not in index:
                        index[w] = low[w] = cnt[0]; cnt[0] += 1; st.append(w); onst.add(w)
                        work.append((w, iter(sorted(edges.get(w, ())))))
                    elif w in onst: low[v] = min(low[v], index[w])
                    continue
                work.pop()
                if work: low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    c = []
                    while True:
                        w = st.pop(); onst.discard(w); c.append(w)
                        if w == v: break
                    comps.append(sorted(c))
        comps.reverse()
        for i, c in enumerate(comps):
            for p in c: comp_of[p] = i
        for a, b, r in strict:
            if comp_of[a] == comp_of[b]: raise StratificationError("negation/aggregation through recursion: " + r)
        return [c for c in comps if any(p in self.idb for p in c)]

    def query(self, res, view, args=None):
        """answer a lazy view from res's materialised facts; None if the view uses a skipped predicate"""
        head, body = self.views[view]
        if any(l[0] == "atom" and l[1] in res.skipped for l in body): return None
        env = {}
        if args is not None:
            for a, v in zip(head[1], args):
                if v is None: continue
                if a[0] == "c" and a[1] != v: return []
                if a[0] == "v":
                    if a[1] in env and env[a[1]] != v: return []
                    env[a[1]] = v
        key = (view, tuple(sorted(env.items())))
        fn = self._vcache.get(key)
        if fn is None:
            h = (head[0], [subst(a, env) for a in head[1]])
            fn = self._vcache[key] = self._fn(h, [subst(l, env) for l in body], None)
            if len(self._vcache) > 4096: self._vcache.clear()
        R = res._R
        for l in body:
            if l[0] == "atom": R.setdefault(l[1], set())
        return sorted(set(fn(R, res._IX, None)))

    def run(self, edb, cap=None, rel_cap=None):
        R = {p: set() for p in self.arity}
        for p, ts in self.facts.items(): R.setdefault(p, set()).update(ts)
        for p, ts in edb.items(): R.setdefault(p, set()).update(tuple(t) for t in ts)
        for p in self.idb:
            if p in edb or p in self.facts: raise DatalogError("IDB predicate %s given as input" % p)
        idx = {}

        def IX(p, poss):
            d = idx.get((p, poss))
            if d is None:
                d = idx[(p, poss)] = {}
                if len(poss) == 1:
                    q = poss[0]
                    for t in R[p]: d.setdefault(t[q], []).append(t)
                else:
                    for t in R[p]: d.setdefault(tuple(t[q] for q in poss), []).append(t)
            return d

        def add(p, ts):
            s = R[p]; new = [t for t in ts if t not in s]
            if not new: return new
            new = list(dict.fromkeys(new)); s.update(new)
            for (q, poss), d in idx.items():
                if q != p: continue
                if len(poss) == 1:
                    i = poss[0]
                    for t in new: d.setdefault(t[i], []).append(t)
                else:
                    for t in new: d.setdefault(tuple(t[i] for i in poss), []).append(t)
            return new

        by_rule, wmat, skipped = [0] * len(self.rules), [0], {}

        def credit(ri, n):
            by_rule[ri] += n; wmat[0] += n
            p = self.rules[ri][0][0]
            if rel_cap is not None and len(R[p]) > rel_cap: raise _Skip(p)
            if cap is not None and wmat[0] > cap: raise WorkCap("W_mat > %d" % cap)

        def fire(ri, out):
            head = self.rules[ri][0]
            ai = [i for i, a in enumerate(head[1]) if a[0] == "agg"]
            if ai:
                fn, groups = head[1][ai[0]][1], {}
                for g, v in out: groups.setdefault(g, set()).add(v)
                out = []
                for g, vs in groups.items():
                    v = len(vs) if fn == "count" else (min(vs) if fn == "min" else max(vs))
                    out.append(g[:ai[0]] + (v,) + g[ai[0]:])
            return out

        for comp, rs in self.compiled:
            uses = {l[1] for ri, _, _ in rs for l in self.rules[ri][1] if l[0] == "atom"} - set(comp)
            bad = sorted(uses & set(skipped))
            if bad:
                for p in comp: skipped[p] = {"size": 0, "reason": "uses skipped " + ",".join(bad)}
                continue
            try:
                for ri, rec, variants in rs:                 # non-recursive rules: once
                    if rec: continue
                    new = add(self.rules[ri][0][0], fire(ri, variants[0][1](R, IX, None)))
                    credit(ri, len(new))
                if not any(rec for _, rec, _ in rs): continue
                delta = {p: list(R[p]) for p in comp}        # first recursive round reads everything derived so far
                while any(delta.values()):
                    found = []
                    for ri, rec, variants in rs:
                        if not rec: continue
                        body = self.rules[ri][1]
                        for k, fn in variants:
                            d = delta[body[k][1]]
                            if d: found.append((ri, fire(ri, fn(R, IX, d))))
                    nxt = {p: [] for p in comp}
                    for ri, out in found:
                        p = self.rules[ri][0][0]; new = add(p, out); credit(ri, len(new)); nxt[p].extend(new)
                    delta = nxt
            except _Skip as e:                               # per-relation cap: drop the whole component
                for p in comp:
                    skipped[p] = {"size": len(R[p]), "reason": "cap" if p == e.args[0] else "same component as " + e.args[0]}
                    R[p] = set()
                    for k in [k for k in idx if k[0] == p]: del idx[k]
                for ri, _, _ in rs: wmat[0] -= by_rule[ri]; by_rule[ri] = 0
        rel = {}
        for p in self.idb:
            if p in skipped: continue
            try: rel[p] = sorted(R[p])
            except TypeError: rel[p] = sorted(R[p], key=repr)
        by_pred = {}
        for ri, c in enumerate(by_rule): by_pred[self.rules[ri][0][0]] = by_pred.get(self.rules[ri][0][0], 0) + c
        return Result(rel, wmat[0], {fmt_rule(*self.rules[ri]): c for ri, c in enumerate(by_rule)}, by_pred,
                      skipped, R, IX)
