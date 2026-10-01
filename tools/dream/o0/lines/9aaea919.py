"""Line family for card 9aaea919 (test-blind; induced only from train pairs).

Reading: the grid holds vertical chains of repeated stamps (same shape, same colour, same
columns, constant period).  Under some chains sits a "bottom marker" (a differently shaped
object, the bottom-most thing in those columns).  Each marker colour triggers an action that is
induced from the training pairs: either "recolour the chain above into colour r" (r induced; gray
in the card) or "add stamps on top of the chain above", the number of added stamps being the
number of links that were recoloured (the "gray links").  Markers that acted are removed or kept,
also as induced.
"""
from collections import Counter

CARD = "9aaea919"
LINE = ("apply bottom markers to stamp chain: red marker - recolor chain into gray, green marker - "
        "add as many stamps at the  top as the number of gray links")
READING = {
    "generator": "Each bottom marker acts on the stamp chain directly above it: a recolour-marker repaints "
                 "every link of its chain in the induced recolour colour, and a grow-marker stacks copies of "
                 "its chain's top stamp upward (same period) as many times as there are recoloured links in "
                 "the grid; the markers themselves are erased (or kept, as induced).",
    "stop": "A recolour stops after the chain's own links; growth stops after exactly N new stamps, N = number "
            "of recoloured (gray) links in the grid (clipped at the grid edge); nothing else changes.",
    "params": "marker action table ∈ {marker colour → recolour-to-r | grow} (induced) · count N ∈ {gray links, "
              "own links, number of recolour markers} · marker ∈ {erased, kept} (induced) · connectivity ∈ {4, 8}",
    "participants": "Single-colour connected components on the background (most frequent colour).  A chain is a "
                    "vertical stack of identical components (colour, shape, column span) with constant period "
                    "(period of a 1-link chain: stamp height + gap induced from multi-link chains).  A marker is "
                    "the bottom-most component in its columns whose nearest component above (column overlap) has "
                    "a different shape/colour; that component's chain is the marker's chain.",
    "preconditions": "Same-size input/output; at least one marker under a chain in every training input; each "
                     "marker colour has one consistent action across the training pairs (one recolour target, "
                     "grow or not); and the induced program reproduces every training pair.",
}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _objects(g, bg, conn):
    H, W = len(g), len(g[0])
    nb = ((-1, 0), (1, 0), (0, -1), (0, 1))
    if conn == 8:
        nb += ((-1, -1), (-1, 1), (1, -1), (1, 1))
    seen = [[False] * W for _ in range(H)]
    objs = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] == bg:
                continue
            c = g[y][x]
            st, pix = [(y, x)], []
            seen[y][x] = True
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and not seen[p][q] and g[p][q] == c:
                        seen[p][q] = True
                        st.append((p, q))
            ys = [p[0] for p in pix]
            xs = [p[1] for p in pix]
            r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
            objs.append({"c": c, "pix": frozenset(pix), "r0": r0, "r1": r1, "c0": c0, "c1": c1,
                         "shape": frozenset((a - r0, b - c0) for a, b in pix)})
    objs.sort(key=lambda o: (o["r0"], o["c0"], o["c"]))
    return objs


def _same(a, b):
    return a["c"] == b["c"] and a["shape"] == b["shape"] and a["c0"] == b["c0"]


def _grid_gaps(objs):
    """Gaps between consecutive identical stacked components (rows between stamp bottom and next top)."""
    gaps = Counter()
    for o in objs:
        above = [q for q in objs if _same(q, o) and q["r1"] < o["r0"]]
        if above:
            q = max(above, key=lambda t: t["r1"])
            gaps[o["r0"] - q["r1"] - 1] += 1
    return gaps


def _overlap(a, b):
    return min(a["c1"], b["c1"]) - max(a["c0"], b["c0"]) + 1


def _parse(g, bg, conn):
    """Return objs, [(marker, chain)] with chain listed bottom link first."""
    objs = _objects(g, bg, conn)
    out = []
    for o in objs:
        if any(q is not o and q["r0"] > o["r1"] and _overlap(q, o) > 0 for q in objs):
            continue  # not bottom-most in its columns
        above = [q for q in objs if q["r1"] < o["r0"] and _overlap(q, o) > 0]
        if not above:
            continue
        a = max(above, key=lambda t: (t["r1"], _overlap(t, o)))
        if a["c"] == o["c"] and a["shape"] == o["shape"]:
            continue  # o is the bottom stamp of a chain, not a marker
        chain, cur, per = [a], a, None
        while True:
            cand = [q for q in objs if _same(q, a) and q["r1"] < cur["r0"]]
            if not cand:
                break
            nxt = max(cand, key=lambda t: t["r1"])
            d = cur["r0"] - nxt["r0"]
            if per is not None and d != per:
                break
            per = d
            chain.append(nxt)
            cur = nxt
        out.append((o, chain))
    return objs, out


def _period(chain, grid_gaps, train_gap):
    if len(chain) >= 2:
        return chain[0]["r0"] - chain[1]["r0"]
    h = chain[0]["r1"] - chain[0]["r0"] + 1
    gap = grid_gaps.most_common(1)[0][0] if grid_gaps else train_gap
    return h + gap


def _make(table, count, erase, conn, train_gap):
    def fn(g):
        bg = _bg(g)
        objs, mk = _parse(g, bg, conn)
        gaps = _grid_gaps(objs)
        H, W = len(g), len(g[0])
        out = [r[:] for r in g]
        acts = [(m, ch, table[m["c"]]) for m, ch in mk if m["c"] in table]
        recol = [(m, ch, a) for m, ch, a in acts if a[0] == "recolor"]
        gray = sum(len(ch) for _, ch, _ in recol)
        colour_of = {}
        for m, ch, a in recol:
            for s in ch:
                for p, q in s["pix"]:
                    out[p][q] = a[1]
            colour_of[id(ch[0])] = a[1]
        for m, ch, a in acts:
            if a[0] != "grow":
                continue
            n = gray if count == "gray" else (len(ch) if count == "own" else len(recol))
            per = _period(ch, gaps, train_gap)
            top = ch[-1]
            col = colour_of.get(id(ch[0]), top["c"])
            for j in range(1, n + 1):
                for p, q in top["pix"]:
                    p2 = p - per * j
                    if 0 <= p2 < H:
                        out[p2][q] = col
        if erase:
            for m, ch, a in acts:
                for p, q in m["pix"]:
                    out[p][q] = bg
        return out
    return fn


def _induce(train, conn):
    table, erase_votes, gaps = {}, set(), Counter()
    for pr in train:
        gi, go = pr["input"], pr["output"]
        bg = _bg(gi)
        objs, mk = _parse(gi, bg, conn)
        gaps.update(_grid_gaps(objs))
        gaps.update(_grid_gaps(_objects(go, _bg(go), conn)))
        if not mk:
            return None
        for m, ch in mk:
            vals = {go[p][q] for s in ch for p, q in s["pix"]}
            if len(vals) != 1:
                return None
            v = vals.pop()
            mv = {go[p][q] for p, q in m["pix"]}
            if mv == {bg}:
                erase_votes.add(True)
            elif mv == {m["c"]}:
                erase_votes.add(False)
            else:
                return None
            if v != ch[0]["c"]:
                act = ("recolor", v)
            else:
                # did the chain grow upward in the output?
                top = ch[-1]
                per = ch[0]["r0"] - ch[1]["r0"] if len(ch) >= 2 else None
                grew = False
                if per is None:
                    # any copy of the top stamp right above it (some gap) counts as growth
                    h = top["r1"] - top["r0"] + 1
                    for gp in range(0, h + 1):
                        cells = [(p - h - gp, q) for p, q in top["pix"]]
                        if all(0 <= a < len(go) and go[a][b] == v and gi[a][b] == bg for a, b in cells):
                            grew = True
                            break
                else:
                    cells = [(p - per, q) for p, q in top["pix"]]
                    grew = all(0 <= a < len(go) and go[a][b] == v and gi[a][b] == bg for a, b in cells)
                act = ("grow",) if grew else ("none",)
            old = table.get(m["c"])
            if old is None or old == ("none",):
                table[m["c"]] = act
            elif act != ("none",) and act != old:
                return None
    if len(erase_votes) != 1:
        return None
    table = {k: v for k, v in table.items() if v != ("none",)}
    if not table:
        return None
    train_gap = gaps.most_common(1)[0][0] if gaps else 1
    return table, erase_votes.pop(), train_gap


def fam(train):
    if not train:
        return
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
    prev = None
    for ci, conn in enumerate((4, 8)):
        objs = [_objects(p["input"], _bg(p["input"]), conn) for p in train]
        if objs == prev:
            continue
        prev = objs
        ind = _induce(train, conn)
        if ind is None:
            continue
        table, erase, tgap = ind
        has_grow = any(a[0] == "grow" for a in table.values())
        counts = ("gray", "own", "nrecolor") if has_grow else ("gray",)
        for k, count in enumerate(counts):
            fn = _make(table, count, erase, conn, tgap)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("stamp_chain_markers[%s,conn%d]" % (count, conn), 10 + k + 5 * ci, fn)
            except Exception:
                continue


FAMILIES = [fam]
