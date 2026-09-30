"""Group g10 family: geometry:bounding_box.

Mechanism (computational geometry, axis-aligned bounding box / minimum bounding rectangle):
a set of anchor cells (the "markers", all cells of one colour m) is partitioned into groups; every group
spans its axis-aligned bounding box; the box is shrunk (inset) by d cells on every side and rendered on the
background either as its boundary (a frame) or as a filled region, in a paint colour chosen by role.
If the anchor colour is the background itself, the anchors are the whole canvas, so the box is the grid border.

Finite parameter domains (all induced from the task's own training pairs):
  m     anchor colour      : any colour present in every training input (non-background first, background = canvas last)
  group anchor grouping    : 'rook' -> one box per component of anchors linked by sharing a row or column (tried first)
                             'all'  -> one box spanned by all anchors
  d     inset              : {0, 1, 2, -1}   (-1 = one-cell outset around the anchors)
  style rendering          : {'outline', 'fill'}
  paint paint colour role  : 'const:c' (c = the single colour added in every training output),
                             'object' (the dominant input colour that is neither background nor anchor),
                             'anchor' (the anchor colour itself)
Only background cells are painted; anchors and other objects are preserved.
Up to 3 training-exact programs are yielded in preference order (non-background anchors, const paint, rook, small inset, outline first).
"""
from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _colours(g):
    return {v for row in g for v in row}


def _groups(cells, mode):
    if not cells:
        return []
    if mode == 'all':
        return [cells]
    # 'rook': union-find over cells sharing a row or a column
    parent = list(range(len(cells)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first_in_row, first_in_col = {}, {}
    for i, (r, c) in enumerate(cells):
        for key, table in ((r, first_in_row), (c, first_in_col)):
            j = table.setdefault(key, i)
            if j != i:
                a, b = find(i), find(j)
                if a != b:
                    parent[a] = b
    comps = {}
    for i, rc in enumerate(cells):
        comps.setdefault(find(i), []).append(rc)
    return list(comps.values())


def _boxes(groups, d):
    out = []
    for grp in groups:
        rs = [r for r, _ in grp]
        cs = [c for _, c in grp]
        r0, r1, c0, c1 = min(rs) + d, max(rs) - d, min(cs) + d, max(cs) - d
        if r0 <= r1 and c0 <= c1:
            out.append((r0, r1, c0, c1))
    return out


def _render(g, boxes, style, colour, bg):
    H, W = len(g), len(g[0])
    out = [row[:] for row in g]
    for r0, r1, c0, c1 in boxes:
        for r in range(max(r0, 0), min(r1, H - 1) + 1):
            edge_row = r == r0 or r == r1
            for c in range(max(c0, 0), min(c1, W - 1) + 1):
                if style == 'outline' and not (edge_row or c == c0 or c == c1):
                    continue
                if g[r][c] == bg:
                    out[r][c] = colour
    return out


def _object_colour(g, bg, m):
    cnt = Counter(v for row in g for v in row if v != bg and v != m)
    if not cnt:
        return None
    top = cnt.most_common(2)
    if len(top) == 2 and top[0][1] == top[1][1]:
        return None
    return top[0][0]


def _make(m, mode, d, style, paint):
    def fn(g):
        bg = _bg(g)
        if paint == 'object':
            colour = _object_colour(g, bg, m)
            if colour is None:
                return [row[:] for row in g]
        elif paint == 'anchor':
            colour = m
        else:
            colour = paint
        cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == m]
        return _render(g, _boxes(_groups(cells, mode), d), style, colour, bg)
    return fn


def fam_bounding_box(train):
    if not train:
        return
    # quick structural rejection: same shape, changes only on background cells, one added colour per pair
    added = []
    for p in train:
        a, b = p['input'], p['output']
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            return
        bg = _bg(a)
        cols = set()
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y:
                    if x != bg:
                        return
                    cols.add(y)
        if len(cols) > 1:
            return
        added.append(cols)
    if not any(added):
        return
    const = {c for s in added for c in s}
    anchors = set.intersection(*(_colours(p['input']) for p in train))
    bgs = {_bg(p['input']) for p in train}
    order = sorted(anchors - bgs) + sorted(anchors & bgs)  # canvas (background) anchors last
    found = 0
    for m in order:
        paints = []
        if len(const) == 1:
            paints.append(next(iter(const)))
        paints += ['object', 'anchor']
        for paint in paints:
            if paint == 'anchor' and const and const != {m}:
                continue
            for mode in ('rook', 'all'):
                for d in (0, 1, 2, -1):
                    for style in ('outline', 'fill'):
                        fn = _make(m, mode, d, style, paint)
                        if fn(train[0]['input']) != train[0]['output']:
                            continue
                        if all(fn(p['input']) == p['output'] for p in train[1:]):
                            pname = paint if isinstance(paint, str) else f'const:{paint}'
                            yield (f'geometry:bounding_box[anchor={m},group={mode},inset={d},'
                                   f'style={style},paint={pname}]', 3, fn)
                            found += 1
                            if found >= 3:
                                return


FAMILIES = (fam_bounding_box,)
