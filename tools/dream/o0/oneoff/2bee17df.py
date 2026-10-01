CARD = "2bee17df"
READING = "Every interior row or column that is entirely background between the two frame edges gets its background cells filled with the new colour."


def fam(train):
    # infer fill colour: the colour that appears in outputs where inputs were background
    bg = 0
    fills = set()
    for p in train:
        for ri, ro in zip(p['input'], p['output']):
            for a, b in zip(ri, ro):
                if a != b:
                    if a != bg:
                        return
                    fills.add(b)
    if len(fills) != 1:
        return
    fc = fills.pop()

    def f(g):
        h, w = len(g), len(g[0])
        o = [list(r) for r in g]
        for r in range(1, h - 1):
            if all(g[r][c] == bg for c in range(1, w - 1)):
                for c in range(1, w - 1):
                    o[r][c] = fc
        for c in range(1, w - 1):
            if all(g[r][c] == bg for r in range(1, h - 1)):
                for r in range(1, h - 1):
                    o[r][c] = fc
        return o
    if all(f(p['input']) == p['output'] for p in train):
        yield ('open_lines_fill', 1, f)


FAMILIES = [fam]
