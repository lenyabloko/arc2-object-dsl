CARD = "d4469b4b"
READING = ("The single foreground colour of the input selects a fixed small glyph, learned from the "
           "training pairs (colour -> output pattern).")


def _key(g):
    cols = sorted(set(x for r in g for x in r) - {0})
    return tuple(cols)


def fam(train):
    table = {}
    for p in train:
        k = _key(p["input"])
        o = [list(r) for r in p["output"]]
        if k in table and table[k] != o:
            return
        table[k] = o
    if not table:
        return

    def fn(g):
        k = _key(g)
        if k in table:
            return [list(r) for r in table[k]]
        # fallback: most frequent glyph
        return [list(r) for r in next(iter(table.values()))]

    yield ("colour_to_glyph_lookup", 1, fn)


FAMILIES = [fam]
