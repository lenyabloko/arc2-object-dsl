CARD = "6e02f1e3"
READING = ("The number of distinct colours in the input selects the output pattern (one colour: top row, "
           "two: main diagonal, three: anti-diagonal), drawn in the learned ink on a zero background.")


def _ncol(g):
    return len(set(x for r in g for x in r))


def fam(train):
    table = {}
    for p in train:
        k = (_ncol(p["input"]), len(p["input"]), len(p["input"][0]))
        o = p["output"]
        if k in table and table[k] != o:
            return
        table[k] = o

    def fn(g):
        k = (_ncol(g), len(g), len(g[0]))
        o = table.get(k)
        return [r[:] for r in o] if o is not None else None

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("ncolours_to_pattern_table", 1, fn)


FAMILIES = [fam]
