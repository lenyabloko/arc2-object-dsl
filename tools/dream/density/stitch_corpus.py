"""Fable v14 O3 / T76 corpus: every function of the generator modules exported as one Stitch program (s-expression).

Corpus = the solver's generator modules in the current probe (tools/m1b/v35: fam_*, prior_*, compose_*, concept_*,
prior2_*/prior3_*/prior4_* files), plus tools/dream/o0/lines/*.py (line families). Conversion is a plain Python-AST to
s-expression walk in the style of neurosym.python_to_s_exp (Stitch's own Python corpora): (NodeType child ...), statement
lists as (/seq ...), call targets kept by name (g_<name>), attribute names kept (a_<name>), local variables and
arguments renamed by first use within the function (&0, &1, ...), small integers kept (i<n>), other constants
collapsed by type (s, f). One program per top-level function or method; functions with fewer than 8 AST nodes are
skipped. Output: results/o0/stitch_corpus.json (list of strings) and results/o0/stitch_corpus_index.json (module,
function per program) for mapping abstractions back to modules (T76 counts modules per abstraction).
usage: python3 stitch_corpus.py"""
import ast, glob, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))


class Conv:
    def __init__(self): self.locals = {}

    def name(self, n):
        if n in self.locals: return self.locals[n]
        return 'g_' + n

    def local(self, n):
        if n not in self.locals: self.locals[n] = '&%d' % len(self.locals)
        return self.locals[n]

    def const(self, v):
        if isinstance(v, bool): return 'b%d' % int(v)
        if isinstance(v, int): return 'i%d' % v if -10 <= v <= 30 else 'iN'
        if isinstance(v, float): return 'f'
        if isinstance(v, str): return 's'
        if v is None: return 'None'
        return 'c'

    def go(self, node):
        if isinstance(node, str): return 'k_' + node
        if node is None: return 'None'
        if isinstance(node, list):
            items = [x for x in (self.go(x) for x in node) if x is not None]
            return '(/seq %s)' % ' '.join(items) if items else 'nil'
        if isinstance(node, ast.Name):
            return self.locals.get(node.id, 'g_' + node.id) if isinstance(node.ctx, ast.Load) else self.local(node.id)
        if isinstance(node, ast.arg): return self.local(node.arg)
        if isinstance(node, ast.Constant): return self.const(node.value)
        if isinstance(node, ast.Attribute): return '(Attribute %s a_%s)' % (self.go(node.value), node.attr)
        if isinstance(node, (ast.Load, ast.Store, ast.Del)): return None
        parts = [type(node).__name__]
        for f, v in ast.iter_fields(node):
            if f in ('type_comment', 'ctx', 'lineno', 'col_offset', 'end_lineno', 'end_col_offset', 'kind'): continue
            if isinstance(v, ast.AST) or isinstance(v, list):
                s = self.go(v)
                if s is not None: parts.append(s)
            elif isinstance(v, str):
                parts.append(('op_' if f == 'op' else 'k_') + v)
            elif v is None:
                parts.append('None')
        if len(parts) == 1: return parts[0]
        return '(' + ' '.join(parts) + ')'


def size(n): return sum(1 for _ in ast.walk(n))


def main():
    probe = os.path.join(REPO, 'tools/m1b/v35')
    pats = ['fam_*.py', 'prior_*.py', 'compose_*.py', 'concept_*.py', 'prior2_*.py', 'prior3_*.py', 'prior4_*.py']
    files = sorted(set(f for p in pats for f in glob.glob(os.path.join(probe, p))))
    files += sorted(glob.glob(os.path.join(REPO, 'tools/dream/o0/lines/*.py')))
    progs, index = [], []
    for f in files:
        try: tree = ast.parse(open(f).read())
        except SyntaxError: continue
        mod = os.path.relpath(f, REPO)
        defs = []
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): defs.append((n.name, n))
            if isinstance(n, ast.ClassDef):
                defs += [(n.name + '.' + m.name, m) for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
        for name, d in defs:
            if size(d) < 8: continue
            c = Conv()
            for a in d.args.args + d.args.kwonlyargs: c.local(a.arg)
            progs.append(c.go(d.body)); index.append({'module': mod, 'function': name, 'nodes': size(d)})
    json.dump(progs, open(os.path.join(REPO, 'results/o0/stitch_corpus.json'), 'w'))
    json.dump(index, open(os.path.join(REPO, 'results/o0/stitch_corpus_index.json'), 'w'))
    mods = len(set(x['module'] for x in index))
    print(json.dumps({'modules': mods, 'files': len(files), 'programs': len(progs), 'nodes': sum(x['nodes'] for x in index)}))


if __name__ == '__main__':
    main()
