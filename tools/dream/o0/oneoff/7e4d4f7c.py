CARD = "7e4d4f7c"
READING = ("Keep the top two rows and append one row that copies the top row with its "
           "non-background cells recoloured to the marker colour and the rest background.")


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _make(keep, paint):
    def fn(g):
        bg = _bg(g)
        out = [row[:] for row in g[:keep]]
        out.append([bg if v == bg else paint for v in g[0]])
        return out
    return fn


def fam(train):
    hs = set(len(p["output"]) for p in train)
    if len(hs) != 1:
        return
    keep = hs.pop() - 1
    if keep < 1:
        return
    paints = set()
    for p in train:
        bg = _bg(p["input"])
        for x, y in zip(p["input"][0], p["output"][-1]):
            if x != bg:
                paints.add(y)
    if len(paints) != 1:
        return
    fn = _make(keep, paints.pop())
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("top_rows_plus_recoloured_row", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
