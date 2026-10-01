"""Line family for card 3de23699 (test-blind; written from the reviewer's line and train pairs only).

Reading: some colour demarcates a rectangular area (four corner markers, a frame, L-brackets,
two rails ...): all of its cells lie on the perimeter of its own bounding box, touching all four
sides, and that box encloses other content. Everything inside the area is extracted (cropped)
and every object cell is repainted with the markers' colour.
"""

CARD = "3de23699"
LINE = "extract all objects inside the demarcated area and recolor the objects into makers' color"
READING = {
    "generator": "Crop the area enclosed by the markers and paint every non-background cell "
                 "in it with the markers' colour, leaving background cells as background.",
    "stop": "The output ends at the demarcated area's edge (strictly inside the markers, or the "
            "tight box of the enclosed objects / the box including the markers, per `crop`).",
    "params": "crop in {interior, tight, inclusive} · sel in {largest, smallest} (which demarcating "
              "colour when several qualify) · bg = most frequent input colour",
    "participants": "Markers: a colour whose cells all lie on the perimeter of their bounding box, "
                    "touching all four sides, box at least 3x3, with non-background cells of other "
                    "colours strictly inside. Objects: all non-background cells strictly inside that box.",
    "preconditions": "Every grid has at least one such demarcating colour, and its interior contains "
                     "at least one non-background cell.",
}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _candidates(g, bg):
    """Colours that demarcate a rectangle: (colour, r0, c0, r1, c1)."""
    H, W = len(g), len(g[0])
    cells = {}
    for r in range(H):
        for c in range(W):
            v = g[r][c]
            if v != bg:
                cells.setdefault(v, []).append((r, c))
    out = []
    for col in sorted(cells):
        pts = cells[col]
        r0 = min(p[0] for p in pts); r1 = max(p[0] for p in pts)
        c0 = min(p[1] for p in pts); c1 = max(p[1] for p in pts)
        if r1 - r0 < 2 or c1 - c0 < 2:
            continue
        if any(r0 < r < r1 and c0 < c < c1 for r, c in pts):
            continue  # a cell off the perimeter: not a demarcation
        sides = (any(r == r0 for r, _ in pts), any(r == r1 for r, _ in pts),
                 any(c == c0 for _, c in pts), any(c == c1 for _, c in pts))
        if not all(sides):
            continue
        inner = any(g[r][c] != bg for r in range(r0 + 1, r1) for c in range(c0 + 1, c1))
        if not inner:
            continue
        out.append((col, r0, c0, r1, c1))
    return out


def _pick(cands, sel):
    if not cands:
        return None
    key = lambda t: ((t[3] - t[1] + 1) * (t[4] - t[2] + 1), -t[0])
    return max(cands, key=key) if sel == "largest" else min(cands, key=key)


def _make(crop, sel):
    def fn(g):
        bg = _bg(g)
        d = _pick(_candidates(g, bg), sel)
        if d is None:
            return None
        col, r0, c0, r1, c1 = d
        if crop == "inclusive":
            R0, C0, R1, C1 = r0, c0, r1, c1
        else:
            R0, C0, R1, C1 = r0 + 1, c0 + 1, r1 - 1, c1 - 1
            if crop == "tight":
                pts = [(r, c) for r in range(R0, R1 + 1) for c in range(C0, C1 + 1) if g[r][c] != bg]
                if pts:
                    R0 = min(p[0] for p in pts); R1 = max(p[0] for p in pts)
                    C0 = min(p[1] for p in pts); C1 = max(p[1] for p in pts)
        out = []
        for r in range(R0, R1 + 1):
            row = []
            for c in range(C0, C1 + 1):
                v = g[r][c]
                inside = r0 < r < r1 and c0 < c < c1
                row.append(col if (v != bg and (inside or v == col)) else (v if v == col else bg))
            out.append(row)
        return out
    return fn


def fam(train):
    for p in train:
        if not _candidates(p["input"], _bg(p["input"])):
            return
    progs = []
    for ci, crop in enumerate(("interior", "tight", "inclusive")):
        for si, sel in enumerate(("largest", "smallest")):
            progs.append(("extract_recolor_to_marker[crop=%s,sel=%s]" % (crop, sel), 1 + ci + si, _make(crop, sel)))
    progs.sort(key=lambda t: t[1])
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = repr(outs)
        if sig in seen:
            continue  # identical behaviour on train to a cheaper program
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
