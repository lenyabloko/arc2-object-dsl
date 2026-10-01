CARD = "9110e3c5"
READING = ("The output is a fixed small pattern chosen by the input's most frequent non-background "
           "colour, with the colour-to-pattern table learned from the training pairs.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _key(g, bg):
    cnt = {}
    for r in g:
        for x in r:
            if x != bg:
                cnt[x] = cnt.get(x, 0) + 1
    if not cnt:
        return None
    best = max(cnt.values())
    ks = [k for k in cnt if cnt[k] == best]
    return ks[0] if len(ks) == 1 else None


def fam(train):
    bg = _bg([x for p in train for x in p["input"]])
    table = {}
    for p in train:
        k = _key(p["input"], bg)
        if k is None:
            return
        if k in table and table[k] != p["output"]:
            return
        table[k] = p["output"]
    if len(table) >= len(train):
        return  # no sharing: lookup explains nothing
    freq = {}
    for p in train:
        t = tuple(map(tuple, p["output"]))
        freq[t] = freq.get(t, 0) + 1
    default = [list(r) for r in max(freq, key=lambda t: freq[t])]

    def fn(g):
        k = _key(g, bg)
        o = table.get(k, default)
        return [r[:] for r in o]
    yield ("dominant_colour_lookup", 1.0 + 0.1 * len(table), fn)


FAMILIES = [fam]
