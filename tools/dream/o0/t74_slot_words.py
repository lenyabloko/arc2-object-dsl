"""Fable v13 T74 (Oct 2 2026): Len's lines re-parsed for generator-slot words.

Source: the LINE string of every tools/dream/o0/lines/*.py (Len's own wording, verbatim). Slot word lists (G72 slots;
declared here once, applied by whole-word regex, case-insensitive):
  on_stop  until, stop(s), hit(s), reach(es), bounce(s), reflect(s), turn(s), when it, at the end
  anchor   midpoint, middle, between, centre/center, intersection, cross(es/ing), corner(s), meet(s)
  iterate  repeat(ed), again, until no, keep, continue(s), each time, every step, step by step
  accept   fit(s), fitting, overlap(ping), align(ed), without touching, so that
The v10 / G69 parse maps a line to schema records with no slot fields, so every slot word it contains was dropped.
Output: results/o0/t74_slot_words.json.  usage: python3 t74_slot_words.py"""
import ast, glob, json, os, re
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
WORDS = {
    'on_stop': [r'until', r'stops?', r'hits?', r'reach(es)?', r'bounces?', r'reflects?', r'turns?', r'when it', r'at the end'],
    'anchor': [r'midpoint', r'middle', r'between', r'cent(re|er)', r'intersection', r'cross(es|ing)?', r'corners?', r'meets?'],
    'iterate': [r'repeat(ed)?', r'again', r'until no', r'keep', r'continues?', r'each time', r'every step', r'step by step'],
    'accept': [r'fits?', r'fitting', r'overlap(ping)?', r'align(ed)?', r'without touching', r'so that'],
}


def line_of(path):
    for n in ast.parse(open(path).read()).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LINE' for t in n.targets):
            try: return ast.literal_eval(n.value)
            except Exception: return None
    return None


def main():
    rows = []
    for p in sorted(glob.glob(os.path.join(REPO, 'tools/dream/o0/lines/*.py'))):
        s = line_of(p)
        if not s: continue
        hit = {k: sorted({m.group(0).lower() for w in ws for m in re.finditer(r'\b' + w + r'\b', s, re.I)}) for k, ws in WORDS.items()}
        rows.append({'card': os.path.basename(p)[:-3], 'slots': {k: v for k, v in hit.items() if v}})
    n = len(rows)
    per = {k: sum(1 for r in rows if k in r['slots']) for k in WORDS}
    out = {'lines': n, 'with_any_slot_word': sum(1 for r in rows if r['slots']), 'per_slot': per, 'rows': rows}
    json.dump(out, open(os.path.join(REPO, 'results/o0/t74_slot_words.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
