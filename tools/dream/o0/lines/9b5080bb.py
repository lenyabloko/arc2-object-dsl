"""Line family for card 9b5080bb (test-blind; induced only from train pairs).

Reading: a "frame" region encloses one or more "hole" regions of another colour.  The straight
frame/hole interface carries ports (connectors): a one-cell pin of frame colour standing into the
hole (male on the frame, socket in the hole) or a one-cell pin of hole colour standing into the
frame (socket in the frame).  Every port is occupied by a male plug in the colour of the area
attached to the frame (the other frame region it touches): the pin cell plus the cell(s) behind
it along the pin's axis.
"""

CARD = "9b5080bb"
LINE = "occupy portals/ports (male/feamale connectors) with male plugs of attached area color"
READING = {
    "generator": "Every port on a frame/hole interface (a pin of one colour standing out of a flat edge into "
                 "the other colour) is overwritten by a plug in the colour of the area attached to that frame: "
                 "the pin cell(s) plus the cell(s) behind it along the pin's axis.",
    "stop": "One plug per port, of fixed length L along the pin's axis (pin cell first, then into its base); "
            "nothing else changes.",
    "params": "L ∈ {1,2,3} · port kind ∈ {both, frame pins only, hole pins only} · port width ∈ {1, ≤2, ≤3} · "
              "attached ∈ {adjacent frame region, any adjacent non-hole region} (longest contact wins)",
    "participants": "4-connected single-colour components. Hole = component off the border whose outside "
                    "neighbours all belong to one component (its frame); frame = component enclosing a hole; "
                    "ports = pins on a frame/hole interface (front and both lateral cells of the partner colour, "
                    "the cell behind and both shoulders of the pin's own colour); attached area = the adjacent "
                    "region (a frame by default, not one of its own holes) with the longest contact.",
    "preconditions": "Input and output have the same size; at least one frame encloses a hole, has an attached "
                     "area and carries a port; every changed cell lies on a plug.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _comps(g):
    H, W = len(g), len(g[0])
    lab = [[-1] * W for _ in range(H)]
    comps = []
    for y in range(H):
        for x in range(W):
            if lab[y][x] >= 0:
                continue
            c, i = g[y][x], len(comps)
            st, pix = [(y, x)], []
            lab[y][x] = i
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in D4:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and lab[p][q] < 0 and g[p][q] == c:
                        lab[p][q] = i
                        st.append((p, q))
            comps.append((c, pix))
    return lab, comps


def _analyse(g, maxw):
    """-> list of (frame id, frame comp, hole comp, ports) and adjacency contact counts."""
    H, W = len(g), len(g[0])
    lab, comps = _comps(g)
    n = len(comps)
    contact = [dict() for _ in range(n)]
    border = [False] * n
    for y in range(H):
        for x in range(W):
            i = lab[y][x]
            if y in (0, H - 1) or x in (0, W - 1):
                border[i] = True
            for dy, dx in ((1, 0), (0, 1)):
                p, q = y + dy, x + dx
                if p < H and q < W and lab[p][q] != i:
                    j = lab[p][q]
                    contact[i][j] = contact[i].get(j, 0) + 1
                    contact[j][i] = contact[j].get(i, 0) + 1
    holes_of = {}
    for i in range(n):
        if not border[i] and len(contact[i]) == 1:
            f = next(iter(contact[i]))
            holes_of.setdefault(f, []).append(i)

    def L(p, q):
        return lab[p][q] if 0 <= p < H and 0 <= q < W else -1

    ports = []                                   # (frame, kind, cells, back direction)
    for f in sorted(holes_of):
        for h in holes_of[f]:
            for own, oth, kind in ((f, h, "frame"), (h, f, "hole")):
                cells = comps[own][1]
                for (y, x) in cells:
                    for dy, dx in D4:            # d = direction the pin points (into the partner)
                        py, px = dx, dy          # perpendicular
                        # run start: the cell before (along perp) must be partner, i.e. lateral end
                        if L(y - py, x - px) != oth:
                            continue
                        for w in range(1, maxw + 1):
                            ry, rx = y + (w - 1) * py, x + (w - 1) * px
                            if L(ry, rx) != own or L(ry + dy, rx + dx) != oth or L(ry - dy, rx - dx) != own:
                                break
                            if L(ry + py, rx + px) == oth:          # run ends here
                                if (L(y - dy - py, x - dx - px) == own and
                                        L(ry - dy + py, rx - dx + px) == own):
                                    run = [(y + k * py, x + k * px) for k in range(w)]
                                    ports.append((f, kind, run, (-dy, -dx)))
                                break
    return lab, comps, contact, holes_of, ports


def _attached(f, comps, contact, holes_of, mode):
    hs = set(holes_of.get(f, ()))
    score = {}
    for j, k in contact[f].items():
        if j in hs or j == f:
            continue
        if mode == "frame" and j not in holes_of:
            continue
        c = comps[j][0]
        score[c] = score.get(c, 0) + k
    if not score:
        return None
    best = max(score.values())
    top = [c for c, v in score.items() if v == best]
    return top[0] if len(top) == 1 else None


def _make(Lp, kind, maxw, mode):
    def fn(g):
        lab, comps, contact, holes_of, ports = _analyse(g, maxw)
        out = [list(r) for r in g]
        H, W = len(g), len(g[0])
        att = {}
        for f, k, run, (by, bx) in ports:
            if kind != "both" and k != kind:
                continue
            if f not in att:
                att[f] = _attached(f, comps, contact, holes_of, mode)
            col = att[f]
            if col is None:
                continue
            for (y, x) in run:
                for s in range(Lp):
                    p, q = y + s * by, x + s * bx
                    if 0 <= p < H and 0 <= q < W:
                        out[p][q] = col
        return out
    return fn


def fam(train):
    if not train:
        return
    for pr in train:
        a, b = pr["input"], pr["output"]
        if len(a) != len(b) or any(len(r) != len(s) for r, s in zip(a, b)):
            return
    # precondition: every training input has a frame with a hole and at least one port
    for pr in train:
        if not _analyse(pr["input"], 3)[4]:
            return
    cost = 0
    for maxw in (1, 2, 3):
        for kind in ("both", "frame", "hole"):
            for Lp in (2, 1, 3):
                for mode in ("frame", "any"):
                    cost += 1
                    fn = _make(Lp, kind, maxw, mode)
                    try:
                        ok = all(fn(pr["input"]) == pr["output"] for pr in train)
                    except Exception:
                        ok = False
                    if ok:
                        yield ("plug_ports(L=%d,kind=%s,w<=%d,attached=%s)" % (Lp, kind, maxw, mode), cost, fn)


FAMILIES = [fam]
