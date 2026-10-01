"""Concept family "complete_shape" (test-blind; anti-unified from the member lines and their train pairs only).

One generator: find the anchors where a shape is partial, give each anchor a local frame (origin, axis u
pointing inward / back into its base, axis v across), lay the shape's template out in that frame, clip it to
the grid and to the anchor's territory, and paint it in the anchor's colour.  Members differ only in values:
  4c416de3  anchor=corner     template=exemplar orient=mirror colour=marker   territory=grid    paint=all
  9b5080bb  anchor=pin        template=induced  (pin cell + cell behind)  colour=attached  territory=grid
  0f63c0b9  anchor=seed-rows  template=profile  (rail + grid border)      colour=self      territory=near-lo
"""
from collections import Counter

CARD = "concept_complete_shape"
CONCEPT = "complete_shape"
MEMBERS = ["4c416de3", "0f63c0b9", "9b5080bb"]
READING = {
    "generator": "Every anchor of a partial shape (a frame corner, a pin on a frame/hole interface, or a lone "
                 "seed) is completed by laying the shape's template -- the exemplar copied from the anchor where "
                 "it is complete, the local offsets every training anchor gained, or a full-length rail through "
                 "the anchor (alone or with the grid-border profile) -- out in the anchor's local frame, clipped "
                 "to the grid and to the anchor's territory, in the anchor's colour (its marker's, its own, or "
                 "that of the area attached to its host).",
    "stop": "One template copy per anchor: exactly the template cells (rails run border to border), clipped at "
            "the grid edge and at the territory boundary (the middle between neighbouring anchors, tie to the "
            "lower / higher one); anchors without a colour (no single marker colour, no unique attached area) "
            "get nothing; later anchors in reading order paint over earlier ones.",
    "params": "anchor ∈ {corner, pin, seed-rows, seed-cols} · template ∈ {exemplar, induced, rail, profile} · "
              "orient ∈ {mirror, rotate} (relative to the exemplar's anchor) · colour ∈ {marker, self, attached} · "
              "territory ∈ {grid, near-lo, near-hi} · paint ∈ {all, background only}",
    "participants": "Background = most frequent colour, frame colour = next most frequent; regions = 4-connected "
                    "one-colour components, a hole = an off-border region touching one region only (its host). "
                    "Corner = a corner of the frame-colour bounding box of an 8-connected non-background blob "
                    "whose two edges are mostly frame colour (u, v point inward). Pin = a run of <= 3 cells of one "
                    "colour standing one cell out of a straight host/hole interface into the other (u = back into "
                    "its base; host = the enclosing region). Seed = a non-background cell with no non-background "
                    "8-neighbour (u across the rails, v along them). Exemplar = the largest one-colour 8-connected "
                    "blob of neither background nor frame colour, read in the frame of its nearest anchor. "
                    "Marker = the single non-background, non-frame colour on the template cells at an anchor; "
                    "attached = the adjacent hole-enclosing region (not the host's own holes) with the longest "
                    "contact.",
    "preconditions": "Input and output have the same size and some cell changes; every training input has an "
                     "anchor of the chosen kind (and an exemplar / a non-empty induced template when used); one "
                     "setting reproduces every training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
D8 = D4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
ANCHORS = ("corner", "pin", "seed-rows", "seed-cols")
TEMPLATES = ("exemplar", "induced", "rail", "profile")
ORIENTS = ("mirror", "rotate")
COLOURS = ("marker", "self", "attached")
TERRITORIES = ("grid", "near-lo", "near-hi")
PAINTS = ("all", "bg")


def _comps(g, ok, nbrs, same=True):
    H, W = len(g), len(g[0])
    lab, out = [[-1] * W for _ in range(H)], []
    for y in range(H):
        for x in range(W):
            if lab[y][x] >= 0 or not ok(g[y][x]):
                continue
            c, st, pix = g[y][x], [(y, x)], []
            lab[y][x] = len(out)
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nbrs:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and lab[p][q] < 0 and ok(g[p][q]) and (not same or g[p][q] == c):
                        lab[p][q] = len(out)
                        st.append((p, q))
            out.append((c, sorted(pix)))
    return lab, out


def _det(a):
    return a[1][0] * a[2][1] - a[1][1] * a[2][0]


def _local(p, a):
    dy, dx = p[0] - a[0][0], p[1] - a[0][1]
    return dy * a[1][0] + dx * a[1][1], dy * a[2][0] + dx * a[2][1]


class _Scene:
    """Participants of one grid, computed lazily and memoised."""

    def __init__(self, g):
        self.g, self.H, self.W, self.m = g, len(g), len(g[0]), {}
        cnt = Counter(v for r in g for v in r)
        self.bg = cnt.most_common(1)[0][0]
        rest = Counter(v for r in g for v in r if v != self.bg)
        self.F = rest.most_common(1)[0][0] if rest else None

    def get(self, key, f):
        if key not in self.m:
            self.m[key] = f()
        return self.m[key]

    def regions(self):
        def f():
            g, H, W = self.g, self.H, self.W
            lab, comps = _comps(g, lambda v: True, D4)
            contact, border = [dict() for _ in comps], [False] * len(comps)
            for y in range(H):
                for x in range(W):
                    i = lab[y][x]
                    border[i] |= y in (0, H - 1) or x in (0, W - 1)
                    for p, q in ((y + 1, x), (y, x + 1)):
                        if p < H and q < W and lab[p][q] != i:
                            j = lab[p][q]
                            contact[i][j] = contact[i].get(j, 0) + 1
                            contact[j][i] = contact[j].get(i, 0) + 1
            holes = {}
            for i in range(len(comps)):
                if not border[i] and len(contact[i]) == 1:
                    holes.setdefault(next(iter(contact[i])), []).append(i)
            return lab, comps, contact, holes
        return self.get("regions", f)

    # ------------------------------------------------------------------ anchors: (origin, u, v, host region)
    def anchors(self, kind):
        return self.get(("anchors", kind), lambda: sorted(set(getattr(self, "_" + kind.split("-")[0])(kind))))

    def _corner(self, kind):
        g, bg, F, lab = self.g, self.bg, self.F, self.regions()[0]
        res = []
        if F is None:
            return res
        for _, pix in _comps(g, lambda v: v != bg, D8, same=False)[1]:
            fp = [(y, x) for y, x in pix if g[y][x] == F]
            if len(fp) < 3:
                continue
            r0, r1 = min(y for y, _ in fp), max(y for y, _ in fp)
            c0, c1 = min(x for _, x in fp), max(x for _, x in fp)
            if r1 - r0 < 2 or c1 - c0 < 2:
                continue
            row = {r: 2 * sum(g[r][x] == F for x in range(c0, c1 + 1)) > c1 - c0 + 1 for r in (r0, r1)}
            col = {c: 2 * sum(g[y][c] == F for y in range(r0, r1 + 1)) > r1 - r0 + 1 for c in (c0, c1)}
            for r, sv in ((r0, 1), (r1, -1)):
                for c, sh in ((c0, 1), (c1, -1)):
                    if row[r] and col[c]:
                        res.append(((r, c), (sv, 0), (0, sh), lab[fp[0][0]][fp[0][1]]))
        return res

    def _pin(self, kind, maxw=3):
        lab, comps, _, holes = self.regions()
        H, W = self.H, self.W

        def L(p, q):
            return lab[p][q] if 0 <= p < H and 0 <= q < W else -1

        res = []
        for f in sorted(holes):
            for h in holes[f]:
                for own, oth in ((f, h), (h, f)):
                    for (y, x) in comps[own][1]:
                        for dy, dx in D4:                  # pin points along d into the partner region
                            py, px = dx, dy                # the run goes along the perpendicular
                            if L(y - py, x - px) != oth:
                                continue
                            for w in range(1, maxw + 1):
                                ry, rx = y + (w - 1) * py, x + (w - 1) * px
                                if L(ry, rx) != own or L(ry + dy, rx + dx) != oth or L(ry - dy, rx - dx) != own:
                                    break
                                if L(ry + py, rx + px) == oth:
                                    if L(y - dy - py, x - dx - px) == own and L(ry - dy + py, rx - dx + px) == own:
                                        u = (-dy, -dx)
                                        res += [((y + k * py, x + k * px), u, (-u[1], u[0]), f) for k in range(w)]
                                    break
        return res

    def _seed(self, kind):
        g, bg, H, W, lab = self.g, self.bg, self.H, self.W, self.regions()[0]
        u, v = ((1, 0), (0, 1)) if kind == "seed-rows" else ((0, 1), (1, 0))
        return [((y, x), u, v, lab[y][x]) for y in range(H) for x in range(W) if g[y][x] != bg and
                all(not (0 <= y + dy < H and 0 <= x + dx < W) or g[y + dy][x + dx] == bg for dy, dx in D8)]

    # ------------------------------------------------------------------ template sources and colours
    def exemplar(self):
        def f():
            bg, F = self.bg, self.F
            blobs = _comps(self.g, lambda v: v != bg and v != F, D8)[1]
            if not blobs:
                return None
            pix = min(blobs, key=lambda b: (-len(b[1]), b[1][0]))[1]
            return pix if len(pix) >= 2 else None
        return self.get("exemplar", f)

    def attached(self, host):
        lab, comps, contact, holes = self.regions()
        own, score = set(holes.get(host, ())), Counter()
        for j, k in contact[host].items():
            if j not in own and j in holes:
                score[comps[j][0]] += k
        top = [c for c, s in score.items() if s == max(score.values())]
        return top[0] if len(top) == 1 else None

    def owner(self, kind, terr):
        def f():
            A, own = self.anchors(kind), {}
            for y in range(self.H):
                for x in range(self.W):
                    best = None
                    for k, a in enumerate(A):
                        d = abs(_local((y, x), a)[0])
                        pr = a[0][0] * abs(a[1][0]) + a[0][1] * abs(a[1][1])
                        key = (d, pr if terr == "near-lo" else -pr, k)
                        if best is None or key < best:
                            best = key
                    own[(y, x)] = best[2]
            return own
        return self.get(("owner", kind, terr), f)


def _apply(sc, P, induced):
    kind, tpl, orient, colour, terr, paint = P
    g, H, W = sc.g, sc.H, sc.W
    A = sc.anchors(kind)
    if not A:
        return None
    offs, ref = induced, None
    if tpl == "exemplar":
        ex = sc.exemplar()
        if ex is None:
            return None
        ref = min(A, key=lambda a: (min(max(abs(y - a[0][0]), abs(x - a[0][1])) for y, x in ex), a))
        offs = [_local(p, ref) for p in ex]
    own = sc.owner(kind, terr) if terr != "grid" else None
    rim = [(y, x) for y in range(H) for x in range(W) if y in (0, H - 1) or x in (0, W - 1)]
    out = [list(r) for r in g]
    for k, a in enumerate(A):
        (r, c), u, v = a[0], a[1], a[2]
        if tpl in ("rail", "profile"):
            cells = [(r + t * v[0], c + t * v[1]) for t in range(-H - W, H + W)] + (rim if tpl == "profile" else [])
        else:
            if orient == "rotate" and _det(a) != _det(ref):
                u, v = v, u
            cells = [(r + i * u[0] + j * v[0], c + i * u[1] + j * v[1]) for i, j in offs]
        cells = [p for p in cells if 0 <= p[0] < H and 0 <= p[1] < W and (own is None or own[p] == k)]
        if colour == "self":
            col = g[r][c]
        elif colour == "attached":
            col = sc.attached(a[3])
        else:
            cs = {g[y][x] for y, x in cells} - {sc.bg, sc.F}
            col = cs.pop() if len(cs) == 1 else None
        if col is None:
            continue
        for y, x in cells:
            if paint == "all" or g[y][x] == sc.bg:
                out[y][x] = col
    return out


def _induce(scenes, train, kind):
    """Local offsets (in the nearest anchor's frame) of every cell the training outputs change."""
    offs = set()
    for sc, pr in zip(scenes, train):
        A = sc.anchors(kind)
        for y, (ri, ro) in enumerate(zip(pr["input"], pr["output"])):
            for x, (a, b) in enumerate(zip(ri, ro)):
                if a != b:
                    near = min(A, key=lambda n: (max(abs(y - n[0][0]), abs(x - n[0][1])), n))
                    offs.add(_local((y, x), near))
    return sorted(offs) or None


def _make(P, induced):
    def fn(grid):
        r = _apply(_Scene(grid), P, induced)
        return [list(x) for x in grid] if r is None else r
    return fn


def fam(train):
    if not train:
        return
    for pr in train:
        a, b = pr["input"], pr["output"]
        if not a or len(a) != len(b) or any(len(r) != len(s) for r, s in zip(a, b)):
            return
    if all(pr["input"] == pr["output"] for pr in train):
        return
    scenes = [_Scene(pr["input"]) for pr in train]
    found = []
    for ka, kind in enumerate(ANCHORS):
        if not all(sc.anchors(kind) for sc in scenes):
            continue
        induced = _induce(scenes, train, kind)
        for kt, tpl in enumerate(TEMPLATES):
            if (tpl == "induced" and induced is None) or (tpl == "exemplar" and not all(sc.exemplar() for sc in scenes)):
                continue
            for ko, orient in enumerate(ORIENTS):
                if ko and tpl != "exemplar":         # orientation is relative to the exemplar's anchor
                    continue
                for kc, colour in enumerate(COLOURS):
                    for kr, terr in enumerate(TERRITORIES):
                        for kp, paint in enumerate(PAINTS):
                            P = (kind, tpl, orient, colour, terr, paint)
                            try:
                                ok = all(_apply(sc, P, induced) == pr["output"] for sc, pr in zip(scenes, train))
                            except Exception:
                                ok = False
                            if ok:
                                cost = 1 + ka + kt + ko + kc + kr + kp
                                found.append((cost, len(found), "complete_shape[%s]" % ",".join(P), P, induced))
    found.sort()
    for cost, _, name, P, ind in found:
        yield name, cost, _make(P, ind)


FAMILIES = [fam]
