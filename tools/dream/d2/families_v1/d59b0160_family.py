"""Family for ARC task d59b0160 -- concept: KEYWORD FILTER (information retrieval / content moderation).

A grid corner holds a *legend*: a small box closed off from the rest of the grid by an L-shaped frame of one colour
that runs from one grid edge to the other.  The colours written in the legend are the "keywords".  The rest of the
grid is a set of "documents": panels (4-connected blobs of non-background cells, typically a canvas colour sprinkled
with coloured cells).  Like a spam / keyword filter, every document whose vocabulary (its set of colours) matches
the keyword query is deleted -- repainted with the background colour -- and all other documents pass untouched.

Colours are by role only: background = colour of the largest 4-connected single-colour region (the gutters); frame = the colour forming the L that closes a corner;
keywords = non-background, non-frame colours inside that corner box.  No coordinates, sizes or colour numbers are
fixed; the legend may sit in any of the four corners and the frame box may be rectangular.

Induced parameter (small finite domain), chosen by exact fit on all training pairs:
  match in {'all', 'any', 'none', 'notall'} -- a document is deleted when it contains all keywords (conjunctive
            query), any keyword (disjunctive), no keyword, or not all keywords.
Connectivity of a document is fixed to 4 (documents are separated by background gutters).
"""


def _background(g):
    """Background = colour of the largest 4-connected single-colour region (the gutter network that separates the
    documents).  Plain majority is unreliable here: the documents' canvas colour can out-number the gutters."""
    H, W = len(g), len(g[0])
    seen, best, bg = set(), -1, None
    for r in range(H):
        for c in range(W):
            if (r, c) in seen:
                continue
            v = g[r][c]
            comp = _component(g, r, c, lambda a, b: g[a][b] == v)
            seen |= comp
            if len(comp) > best:
                best, bg = len(comp), v
    return bg


def _component(g, r, c, allowed):
    """4-connected set of cells reachable from (r, c) through cells satisfying allowed(rr, cc)."""
    H, W = len(g), len(g[0])
    seen = {(r, c)}
    stack = [(r, c)]
    while stack:
        a, b = stack.pop()
        for aa, bb in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
            if 0 <= aa < H and 0 <= bb < W and (aa, bb) not in seen and allowed(aa, bb):
                seen.add((aa, bb))
                stack.append((aa, bb))
    return seen


def _legend(g, bg):
    """Find the unique corner box closed by an L-shaped single-colour frame.
    Returns (box_cells_including_frame, keyword_colours) or None."""
    H, W = len(g), len(g[0])
    found = []
    for fr in (False, True):
        for fc in (False, True):
            R = (lambda i: H - 1 - i) if fr else (lambda i: i)
            C = (lambda j: W - 1 - j) if fc else (lambda j: j)
            for r in range(1, H - 1):
                for s in range(1, W - 1):
                    col = g[R(r)][C(s)]
                    if col == bg:
                        continue
                    L = {(R(r), C(j)) for j in range(s + 1)} | {(R(i), C(s)) for i in range(r + 1)}
                    if any(g[a][b] != col for a, b in L):
                        continue
                    comp = _component(g, R(r), C(s), lambda a, b: g[a][b] == col)
                    if comp != L:
                        continue
                    inner = {(R(i), C(j)) for i in range(r) for j in range(s)}
                    keys = {g[a][b] for a, b in inner} - {bg, col}
                    if not keys:
                        continue
                    found.append((frozenset(L | inner), frozenset(keys)))
    found = list(set(found))
    if len(found) != 1:
        return None
    return found[0]


_MATCH = {
    'all': lambda K, P: K <= P,
    'any': lambda K, P: bool(K & P),
    'none': lambda K, P: not (K & P),
    'notall': lambda K, P: not (K <= P),
}


def _make(match):
    pred = _MATCH[match]

    def fn(g):
        bg = _background(g)
        leg = _legend(g, bg)
        if leg is None:
            return None
        box, keys = leg
        H, W = len(g), len(g[0])
        out = [row[:] for row in g]
        seen = set(box)
        for r in range(H):
            for c in range(W):
                if (r, c) in seen or g[r][c] == bg:
                    continue
                doc = _component(g, r, c, lambda a, b: g[a][b] != bg and (a, b) not in box)
                seen |= doc
                vocab = {g[a][b] for a, b in doc}
                if pred(keys, vocab):
                    for a, b in doc:
                        out[a][b] = bg
        return out
    return fn


def fam_keyword_filter(train):
    if any(_legend(p["input"], _background(p["input"])) is None for p in train):
        return
    for match in ('all', 'any', 'none', 'notall'):
        fn = _make(match)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("infosec:keyword_filter[legend=corner_L_frame,match=%s,action=erase_to_bg,conn=4]" % match, 3, fn)


FAMILIES = (fam_keyword_filter,)
