"""Fable v14 O3 (DSL level): Stitch corpus from Hodel's arc-dsl solvers (michaelhodel/arc-dsl, commit recorded).
Each solve_<task>(I) is a straight-line program `xk = f(args)`; it is turned into ONE expression by inlining every
intermediate variable (shared subterms are duplicated, which Stitch handles), with DSL primitives and constants kept as
symbols and the input as I. ARC-1 training tasks only (no held-out ids). Output: results/o0/stitch_arcdsl_corpus.json
(+ _index.json with the task id per program).
usage: python3 arcdsl_corpus.py"""
import ast, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = '/home/claude/work/corpora/arc-dsl/solvers.py'


def sexp(n, env):
    if isinstance(n, ast.Name): return env.get(n.id, n.id)
    if isinstance(n, ast.Constant): return 'k_%s' % n.value
    if isinstance(n, ast.Call):
        f = sexp(n.func, env); args = [sexp(a, env) for a in n.args]
        return '(%s %s)' % (f, ' '.join(args)) if args else '(%s)' % f
    if isinstance(n, ast.Tuple): return '(tuple %s)' % ' '.join(sexp(e, env) for e in n.elts)
    raise ValueError(type(n).__name__)


def main():
    tree = ast.parse(open(SRC).read()); progs, idx = [], []
    for fn in tree.body:
        if not (isinstance(fn, ast.FunctionDef) and fn.name.startswith('solve_')): continue
        env = {}
        try:
            for st in fn.body:
                if isinstance(st, ast.Assign): env[st.targets[0].id] = sexp(st.value, env)
                elif isinstance(st, ast.Return): progs.append(sexp(st.value, env)); idx.append(fn.name[6:])
        except ValueError:
            continue
    json.dump(progs, open(os.path.join(REPO, 'results/o0/stitch_arcdsl_corpus.json'), 'w'))
    json.dump(idx, open(os.path.join(REPO, 'results/o0/stitch_arcdsl_index.json'), 'w'))
    print(json.dumps({'programs': len(progs), 'chars': sum(map(len, progs)), 'max': max(map(len, progs))}))


if __name__ == '__main__':
    main()
