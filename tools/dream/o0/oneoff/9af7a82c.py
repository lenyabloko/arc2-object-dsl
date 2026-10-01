CARD = "9af7a82c"
READING = ("Count the cells of each colour; output one column per colour, sorted by count "
           "descending, each column filled from the top with its colour for as many cells as its count.")


def _make(bg, tie_desc):
    def fn(g):
        cnt = {}
        for r in g:
            for x in r:
                if x != bg:
                    cnt[x] = cnt.get(x, 0) + 1
        cols = sorted(cnt, key=lambda c: (-cnt[c], -c if tie_desc else c))
        h = max(cnt.values())
        return [[c if i < cnt[c] else bg for c in cols] for i in range(h)]
    return fn


def fam(train):
    for tie_desc in (False, True):
        fn = _make(0, tie_desc)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("count_histogram_columns", 1 + int(tie_desc), fn)


FAMILIES = [fam]
