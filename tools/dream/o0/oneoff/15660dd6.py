CARD = "15660dd6"
READING = ("Each column of framed cells has one solid-colour cell; output one framed cell per column: the column's "
           "pattern with its foreground recoloured to that solid colour, framed in the row-indicator colour of the solid cell's row.")

from collections import Counter


def _parse(g):
    h, w = len(g), len(g[0])
    sep_rows = [r for r in range(h) if g[r][0] != 0 and all(v == g[r][0] for v in g[r])]
    if not sep_rows:
        return None
    S = Counter(g[r][0] for r in sep_rows).most_common(1)[0][0]
    sep_rows = [r for r in sep_rows if g[r][0] == S]
    # bands of rows between separators
    bands = []
    prev = -1
    for r in sep_rows + [h]:
        if r - prev > 1:
            bands.append((prev + 1, r - 1))
        prev = r
    if not bands:
        return None
    # separator columns: S in every non-separator row
    body = [r for r in range(h) if r not in sep_rows]
    sep_cols = [c for c in range(w) if all(g[r][c] == S for r in body)]
    if not sep_cols:
        return None
    ind_col = 0 if 0 not in sep_cols else None
    segs = []
    prev = -1 if ind_col is None else 0
    for c in sep_cols + [w]:
        if c - prev > 1:
            segs.append((prev + 1, c - 1))
        prev = c
    return S, bands, segs, ind_col


def _cell(g, band, seg):
    return [g[r][seg[0]:seg[1] + 1] for r in range(band[0], band[1] + 1)]


def _make(keep_S):
    def fn(g):
        P = _parse(g)
        if P is None:
            return g
        S, bands, segs, ind_col = P
        cols_out = []
        for seg in segs:
            solid = None
            pattern = None
            for band in bands:
                cell = _cell(g, band, seg)
                frame = cell[0][0]
                interior = [row[1:-1] for row in cell[1:-1]]
                ic = set(v for row in interior for v in row)
                if len(ic) == 1:
                    solid = (band, interior[0][0])
                else:
                    pattern = cell
            if solid is None or pattern is None:
                return g
            band, colour = solid
            ind = g[band[0]][ind_col] if ind_col is not None else 0
            frame = pattern[0][0]
            hh, ww = len(pattern), len(pattern[0])
            out = []
            for i in range(hh):
                row = []
                for j in range(ww):
                    if i in (0, hh - 1) or j in (0, ww - 1):
                        row.append(ind)
                    else:
                        v = pattern[i][j]
                        row.append(v if v == keep_S(S) else colour)
                out.append(row)
            cols_out.append(out)
        res = []
        for i in range(len(cols_out[0])):
            row = []
            for k, cell in enumerate(cols_out):
                if k:
                    row.append(S)
                row.extend(cell[i])
            res.append(row)
        return res
    return fn


def fam(train):
    fn = _make(lambda S: S)
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("column_solid_recolour", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
