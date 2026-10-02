"""Line expansion for 8698868d: genus matching of loose holed tiles into the pinholed panels of a board (test-blind; train pairs only)."""
from collections import Counter

CARD = "8698868d"
LINE = "Genus: Picture: a *board* of tiled solid panels, each panel marked with a few background-coloured pinholes, and a set of loose solid *tiles* elsewhere on the background, each pierced by background holes. The number of pinholes on a panel is its genus label;"
READING = {
    "generator": "Each panel of the board receives the loose tile whose number of background holes equals the panel's number of pinholes: "
                 "the panel is redrawn solid in its own colour and the tile is stamped centred inside it, the tile's holes painted in the panel colour "
                 "(so a one-cell panel-coloured frame surrounds the tile when the tile is two cells smaller).",
    "stop": "One tile per panel; drawing stops when every panel of the board has been filled (the output is the board, or the input with the board refilled).",
    "params": "hole count ∈ {4-connected hole components, 8-connected hole components, panel pinhole cells vs tile 4-components, cells} · "
              "hole fill ∈ {panel colour, background, tile colour} · unmatched panel ∈ {fail, left solid} · "
              "out ∈ {board crop, in place with tiles erased, in place with tiles kept}",
    "participants": "background = most frequent colour; objects = 4-connected non-background regions; a panel = a single-colour 4-connected "
                    "region whose bounding box holds only its colour and background cells, the background cells strictly inside (pinholes/holes); "
                    "board = the one object made of two or more panels that exactly tile its bounding box; tiles = objects that are a single panel; "
                    "genus = number of hole components (pinholes on a panel, holes in a tile); matching by equal genus, several same-genus "
                    "panels and tiles paired in reading order.",
    "preconditions": "Every input has exactly one such board and at least one loose tile; each panel has a tile of its genus (unless the unmatched "
                     "variant is chosen) that fits inside the panel; the output has the board's shape (or the input's for the in-place variants).",
}

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
N8 = N4 + ((1, 1), (1, -1), (-1, 1), (-1, -1))


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _comps(cells, nb):
    """Connected components of a set of (r, c) cells."""
    cells = set(cells)
    seen, out = set(), []
    for s in sorted(cells):
        if s in seen: continue
        seen.add(s)
        st, comp = [s], []
        while st:
            r, c = st.pop()
            comp.append((r, c))
            for dr, dc in nb:
                q = (r + dr, c + dc)
                if q in cells and q not in seen:
                    seen.add(q)
                    st.append(q)
        out.append(sorted(comp))
    return out


def _panel(g, comp, bg):
    """comp: single-colour 4-component -> panel dict or None (bbox must hold only colour + strictly interior bg cells)."""
    col = g[comp[0][0]][comp[0][1]]
    r0 = min(r for r, _ in comp); r1 = max(r for r, _ in comp)
    c0 = min(c for _, c in comp); c1 = max(c for _, c in comp)
    holes = []
    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            v = g[r][c]
            if v == col: continue
            if v != bg: return None
            if r in (r0, r1) or c in (c0, c1): return None
            holes.append((r, c))
    return {"col": col, "box": (r0, c0, r1, c1), "holes": holes}


def scene(g):
    """-> (bg, board_box, board_panels, tiles) or None."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    fg = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
    boards, tiles = [], []
    for obj in _comps(fg, N4):
        bycol = {}
        for r, c in obj: bycol.setdefault(g[r][c], []).append((r, c))
        pans, ok = [], True
        for col, cells in bycol.items():
            for comp in _comps(cells, N4):
                p = _panel(g, comp, bg)
                if p is None: ok = False; break
                pans.append(p)
            if not ok: break
        if not ok: continue
        r0 = min(r for r, _ in obj); r1 = max(r for r, _ in obj)
        c0 = min(c for _, c in obj); c1 = max(c for _, c in obj)
        if len(pans) == 1:
            if pans[0]["box"] == (r0, c0, r1, c1): tiles.append(pans[0])
            continue
        area = sum((p["box"][2] - p["box"][0] + 1) * (p["box"][3] - p["box"][1] + 1) for p in pans)
        if area != (r1 - r0 + 1) * (c1 - c0 + 1): continue
        boards.append(((r0, c0, r1, c1), sorted(pans, key=lambda p: p["box"])))
    if len(boards) != 1 or not tiles: return None
    return bg, boards[0][0], boards[0][1], sorted(tiles, key=lambda p: p["box"])


COUNTS = [  # (name, panel counter, tile counter)
    ("comp4", ("comp", N4), ("comp", N4)),
    ("comp8", ("comp", N8), ("comp", N8)),
    ("pcells", ("cells", None), ("comp", N4)),
    ("cells", ("cells", None), ("cells", None)),
]


def _genus(p, how):
    kind, nb = how
    return len(p["holes"]) if kind == "cells" else len(_comps(p["holes"], nb))


def solve(g, cnt, fill, unmatched, out):
    sc = scene(g)
    if sc is None: raise ValueError("no board/tiles")
    bg, (R0, C0, R1, C1), pans, tiles = sc
    _, phow, thow = cnt
    tg = {}
    for t in tiles: tg.setdefault(_genus(t, thow), []).append(t)
    pg = {}
    for p in pans: pg.setdefault(_genus(p, phow), []).append(p)
    assign = {}
    for k, ps in pg.items():
        ts = tg.get(k, [])
        if len(ts) == 1:
            for p in ps: assign[id(p)] = ts[0]
        elif ts and len(ts) == len(ps):
            for p, t in zip(ps, ts): assign[id(p)] = t
        elif ts or unmatched == "fail":
            raise ValueError("ambiguous or missing genus match")
    if out == "board":
        canvas = [list(row[C0:C1 + 1]) for row in g[R0:R1 + 1]]
        oy, ox = R0, C0
    else:
        canvas = [list(row) for row in g]
        oy, ox = 0, 0
        if out == "erase":
            for t in tiles:
                r0, c0, r1, c1 = t["box"]
                for r in range(r0, r1 + 1):
                    for c in range(c0, c1 + 1): canvas[r][c] = bg
    for p in pans:
        r0, c0, r1, c1 = p["box"]
        ph, pw = r1 - r0 + 1, c1 - c0 + 1
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1): canvas[r - oy][c - ox] = p["col"]
        t = assign.get(id(p))
        if t is None: continue
        tr0, tc0, tr1, tc1 = t["box"]
        th, tw = tr1 - tr0 + 1, tc1 - tc0 + 1
        if th > ph or tw > pw or (ph - th) % 2 or (pw - tw) % 2: raise ValueError("tile does not fit centred")
        dy, dx = r0 + (ph - th) // 2, c0 + (pw - tw) // 2
        hv = {"panel": p["col"], "bg": bg, "tile": t["col"]}[fill]
        for i in range(th):
            for j in range(tw):
                v = g[tr0 + i][tc0 + j]
                canvas[dy + i - oy][dx + j - ox] = t["col"] if v == t["col"] else hv
    return canvas


def fam(train):
    scs = []
    for p in train:
        sc = scene(p["input"])
        if sc is None: return
        scs.append(sc)
    outs = []
    for o in ("board", "erase", "keep"):
        def shp(sc, g, o=o):
            if o == "board":
                r0, c0, r1, c1 = sc[1]
                return (r1 - r0 + 1, c1 - c0 + 1)
            return (len(g), len(g[0]))
        if all(shp(sc, p["input"]) == (len(p["output"]), len(p["output"][0])) for sc, p in zip(scs, train)): outs.append(o)
    k = 0
    for o in outs:
        for cnt in COUNTS:
            for fill in ("panel", "bg", "tile"):
                for um in ("fail", "solid"):
                    fn = (lambda cnt, fill, um, o: (lambda g: solve(g, cnt, fill, um, o)))(cnt, fill, um, o)
                    try:
                        ok = all(fn(p["input"]) == p["output"] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        yield ("genus:%s:%s:%s:%s" % (cnt[0], fill, um, o), 10 + k, fn)
                        k += 1


FAMILIES = [fam]
