"""Concept family stamp_replicate (test-blind; anti-unified from the member lines' code and train pairs).

One generator: find the templates and the sites, then at every site paint a copy of the site's template,
translated so that the template's anchor lands on the site's anchor, coloured by ONE induced colour rule,
on a canvas.  The member lines differ only in parameter values:
  b190f7f5  layout=blowup  (sites = pattern cells scaled by the stamp size, colour = site colour)
  7d18a6fb  layout=marker  (sites = markers in the cropped host area, template = same-colour glyph, centre anchor)
  409aa875  layout=throw   (site = d steps along each arrowhead's direction, constant colour, hit object recoloured)
  9aaea919  layout=stack   (sites = links of the chain above a bottom marker (+ N periods above it), colour table)
Shared steps written once: background, components, anchors, the stamp record (cells, dy, dx, site colour),
colour-rule and collision-colour induction from the outputs, the drawing loop (clip, collisions, hit policy,
erasing), and the verify loop.
"""
from collections import Counter
from functools import lru_cache

CARD = "concept_stamp_replicate"
CONCEPT = "stamp_replicate"
MEMBERS = ["409aa875", "b190f7f5", "7d18a6fb", "9aaea919"]
READING = {
    "generator": "Find the templates and the sites, then at every site paint a copy of the site's template, "
                 "translated so the template's anchor lands on the site's anchor and coloured by one induced rule "
                 "(the template's own colours, the site's colour, a constant, or a site-colour table), on a canvas "
                 "(the input, the cropped host area, or a blank blow-up); cells reached twice take an induced "
                 "collision colour.",
    "stop": "One copy per site (a chain site also gets N copies one period apart upward, N counted from the "
            "recoloured stamps); copies are clipped to the canvas (and to the host area); nothing else changes "
            "except the erased markers/templates and, under hit=object, the objects a copy lands on.",
    "params": "layout ∈ {blowup, marker, throw, stack} · split ∈ {halves, separator, self} · gap ∈ {0, 1} · "
              "host ∈ {area, grid} · inset ∈ {0, 1} · canvas ∈ {crop, in place} · "
              "anchor ∈ {centre, centre-ceil, tl, tr, bl, br} · d ∈ {1..max(H,W)-1} · pol ∈ {+1, -1} · "
              "src ∈ {apex pixel, whole glyph} · conn ∈ {4, 8} · count ∈ {recoloured links, own links, "
              "recolouring markers, none} · colour ∈ {own, site colour, constant c, table site colour → c|own} "
              "(induced) · collision colour (induced) · hit ∈ {paint, recolour hit object, skip} · "
              "erase ∈ {none, markers, templates, both}",
    "participants": "Background: most frequent colour. blowup: the input splits (equal halves, either side of a "
                    "single uniform line, or itself) into a one-colour template part and a pattern part; sites = "
                    "the pattern's non-background cells scaled by the template size (+gap). marker: host = the "
                    "4-connected one-colour component with the largest bbox holding foreign colours (or the whole "
                    "grid); sites = 8-connected one-colour markers in the host (area colour cleared); template = "
                    "the largest same-colour component outside the host (grid: the unique largest same-colour "
                    "component). throw: glyphs = 8-connected components; site = apex (medoid) moved d steps along "
                    "the centroid->apex direction; template = apex pixel or glyph. stack: chains = vertical runs of "
                    "identical one-colour components with constant period; site = the chain above a bottom marker; "
                    "templates = its links (in place) and its top link (stacked upward).",
    "preconditions": "The layout's participants exist in every training input (unique template/pattern split, at "
                     "least one site), the output size matches the canvas (blow-up, crop or in place), one colour "
                     "rule explains every stamped cell, and the induced program reproduces every training pair.",
}

OWN, KEY = -1, -2
ANCHORS = ("centre", "centre-ceil", "tl", "tr", "bl", "br")


# ---------------------------------------------------------------- shared participants
def _t(g):
    return tuple(tuple(r) for r in g)


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _sgn(x):
    return (x > 0) - (x < 0)


def _obj(g, cells):
    ys, xs = [p[0] for p in cells], [p[1] for p in cells]
    box = (min(ys), min(xs), max(ys), max(xs))
    cnt = Counter(g[y][x] for y, x in cells)
    return {"c": max(sorted(cnt), key=cnt.get), "cells": cells, "box": box,
            "px": tuple((y, x, g[y][x]) for y, x in cells),
            "shape": frozenset((y - box[0], x - box[1]) for y, x in cells)}


@lru_cache(maxsize=512)
def _comps(g, bg, conn, mono, box=None, inside=True):
    """Connected components of non-bg cells (one colour if mono), restricted to cells in (or out of) box."""
    H, W = len(g), len(g[0])
    nb = [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (conn == 8 or not (a and b))]

    def ok(y, x):
        return g[y][x] != bg and (box is None or (box[0] <= y <= box[2] and box[1] <= x <= box[3]) == inside)
    seen, out = set(), []
    for y in range(H):
        for x in range(W):
            if (y, x) in seen or not ok(y, x):
                continue
            seen.add((y, x))
            st, cells = [(y, x)], []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if (0 <= p < H and 0 <= q < W and (p, q) not in seen and ok(p, q)
                            and (not mono or g[p][q] == g[y][x])):
                        seen.add((p, q))
                        st.append((p, q))
            out.append(_obj(g, sorted(cells)))
    return tuple(out)


def _anchor(box, a):
    r0, c0, r1, c1 = box
    if a == "centre":
        return r0 + (r1 - r0) // 2, c0 + (c1 - c0) // 2
    if a == "centre-ceil":
        return r0 + (r1 - r0 + 1) // 2, c0 + (c1 - c0 + 1) // 2
    return (r0 if a[0] == "t" else r1), (c0 if a[1] == "l" else c1)


def _plan(canvas, bg, stamps, erase=None, objs=(), clip=None):
    """stamps: [(cells ((y, x, own colour), ...), dy, dx, site colour)]; erase/objs/clip in canvas coords."""
    H, W = len(canvas), len(canvas[0])
    er = {k: [p for p in v if 0 <= p[0] < H and 0 <= p[1] < W] for k, v in (erase or {}).items()}
    return {"canvas": canvas, "bg": bg, "stamps": stamps, "erase": er, "objs": objs,
            "owner": {p: i for i, o in enumerate(objs) for p in o}, "clip": clip or (0, 0, H - 1, W - 1)}


# ---------------------------------------------------------------- layouts: grid -> plan (templates + sites)
def _blowup(g, v, rule):
    split, gap = v
    bg, H, W = _bg(g), len(g), len(g[0])
    cands = [(g, g)] if split == "self" else []
    if split == "halves":
        if W % 2 == 0:
            cands.append(([r[:W // 2] for r in g], [r[W // 2:] for r in g]))
        if H % 2 == 0:
            cands.append((g[:H // 2], g[H // 2:]))
    if split == "separator":
        for tr in (0, 1):
            gg = list(zip(*g)) if tr else list(g)
            ln = [i for i, r in enumerate(gg) if len(set(r)) == 1 and r[0] != bg]
            if len(ln) == 1 and 0 < ln[0] < len(gg) - 1:
                A, B = gg[:ln[0]], gg[ln[0] + 1:]
                cands.append((list(zip(*A)), list(zip(*B))) if tr else (A, B))
    roles = []
    for A, B in cands:
        ca, cb = ({c for r in X for c in r} - {bg} for X in (A, B))
        if split == "self":
            if ca:
                roles.append((A, B))
        elif len(ca) == 1 < len(cb):
            roles.append((A, B))
        elif len(cb) == 1 < len(ca):
            roles.append((B, A))
    if len(roles) != 1:
        return None
    T, Pt = roles[0]
    sh, sw, ph, pw = len(T), len(T[0]), len(Pt), len(Pt[0])
    Ho, Wo = ph * sh + (ph - 1) * gap, pw * sw + (pw - 1) * gap
    if Ho > 30 or Wo > 30:
        return None
    cells = tuple((a, b, T[a][b]) for a in range(sh) for b in range(sw) if T[a][b] != bg)
    st = [(cells, i * (sh + gap), j * (sw + gap), Pt[i][j]) for i in range(ph) for j in range(pw) if Pt[i][j] != bg]
    return _plan([[bg] * Wo for _ in range(Ho)], bg, st)


def _marker(g, v, rule):
    host, inset, anchor, crop = v
    bg, H, W = _bg(g), len(g), len(g[0])
    if host == "area":
        best = None
        for o in _comps(g, bg, 4, True):
            r0, c0, r1, c1 = o["box"]
            if any(g[y][x] not in (bg, o["c"]) for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)):
                k = ((r1 - r0 + 1) * (c1 - c0 + 1), len(o["cells"]), -r0, -c0)
                if best is None or k > best[0]:
                    best = (k, o["box"])
        if best is None:
            return None
        box = (best[1][0] + inset, best[1][1] + inset, best[1][2] - inset, best[1][3] - inset)
        if box[0] > box[2] or box[1] > box[3]:
            return None
        fc = Counter(g[y][x] for y in range(box[0], box[2] + 1)
                     for x in range(box[1], box[3] + 1)).most_common(1)[0][0]
        marks = [m for m in _comps(g, bg, 8, True, box, True) if m["c"] != fc]
        mc, tpl = {m["c"] for m in marks}, {}
        for o in _comps(g, bg, 8, True, box, False):
            if o["c"] in mc and len(o["cells"]) > len(tpl[o["c"]]["cells"] if o["c"] in tpl else ()):
                tpl[o["c"]] = o
    else:
        box, fc, tpl, marks = (0, 0, H - 1, W - 1), bg, {}, []
        objs = _comps(g, bg, 8, True)
        for c in sorted({o["c"] for o in objs}):
            os_ = [o for o in objs if o["c"] == c]
            n = max(len(o["cells"]) for o in os_)
            big = [o for o in os_ if len(o["cells"]) == n]
            if len(big) == 1 and n > 1 and len(os_) > 1:
                tpl[c] = big[0]
                marks += [o for o in os_ if o is not big[0]]
    marks = [m for m in marks if m["c"] in tpl]
    if not marks:
        return None
    oy, ox = (box[0], box[1]) if crop else (0, 0)
    canvas = [list(r[box[1]:box[3] + 1]) for r in g[box[0]:box[2] + 1]] if crop else [list(r) for r in g]
    if fc != bg:
        for y in range(box[0], box[2] + 1):
            for x in range(box[1], box[3] + 1):
                if g[y][x] == fc:
                    canvas[y - oy][x - ox] = bg
    st = []
    for m in marks:
        t = tpl[m["c"]]
        (ty, tx), (my, mx) = _anchor(t["box"], anchor), _anchor(m["box"], anchor)
        st.append((t["px"], my - ty - oy, mx - tx - ox, m["c"]))
    er = {"markers": [(y - oy, x - ox) for m in marks for y, x in m["cells"]],
          "templates": [(y - oy, x - ox) for t in tpl.values() for y, x in t["cells"]]}
    clip = None if crop else (box[0], box[1], box[2], box[3])
    return _plan(canvas, bg, st, er, clip=clip)


@lru_cache(maxsize=64)
def _glyphs(g, bg):
    """8-connected components with apex (unique medoid) and direction sign(apex - centroid), or None."""
    out = []
    for o in _comps(g, bg, 8, False):
        cells, n = o["cells"], len(o["cells"])
        s0, s1 = sum(p[0] for p in cells), sum(p[1] for p in cells)
        q = sum(a * a + b * b for a, b in cells)
        sc = sorted((n * (a * a + b * b) - 2 * (a * s0 + b * s1) + q, (a, b)) for a, b in cells)
        apex, dv = sc[0][1], None
        if n > 1 and sc[0][0] < sc[1][0]:
            dv = (_sgn(n * apex[0] - s0), _sgn(n * apex[1] - s1))
            dv = None if dv == (0, 0) else dv
        out.append((o, apex, dv))
    return tuple(out)


def _throw(g, v, rule):
    d, pol, src = v
    bg = _bg(g)
    gl = _glyphs(g, bg)
    st = [(((ay, ax, g[ay][ax]),) if src == "pixel" else o["px"], pol * d * dv[0], pol * d * dv[1], o["c"])
          for o, (ay, ax), dv in gl if dv is not None]
    if not st:
        return None
    objs = tuple(o["cells"] for o, _, _ in gl)
    return _plan([list(r) for r in g], bg, st, {"markers": [p for c in objs for p in c]}, objs)


@lru_cache(maxsize=64)
def _chains(g, bg, conn):
    """[(bottom marker, chain bottom link first, period or None)] and the grid's usual gap between links."""
    objs = _comps(g, bg, conn, True)
    col = {}
    for o in objs:                                      # identical stacked components: same colour/shape/column
        col.setdefault((o["c"], o["shape"], o["box"][1]), []).append(o)

    def ov(a, b):
        return min(a["box"][3], b["box"][3]) - max(a["box"][1], b["box"][1]) + 1
    sites = []
    for o in objs:
        if any(q["box"][0] > o["box"][2] and ov(q, o) > 0 for q in objs):
            continue                                    # not the bottom-most thing in its columns
        above = [q for q in objs if q["box"][2] < o["box"][0] and ov(q, o) > 0]
        if not above:
            continue
        a = max(above, key=lambda q: (q["box"][2], ov(q, o)))
        if a["c"] == o["c"] and a["shape"] == o["shape"]:
            continue                                    # o is a chain's bottom link, not a marker
        ch, per = [a], None
        while True:
            cand = [q for q in col[(a["c"], a["shape"], a["box"][1])] if q["box"][2] < ch[-1]["box"][0]]
            if not cand:
                break
            nx = max(cand, key=lambda q: q["box"][2])
            if per is not None and ch[-1]["box"][0] - nx["box"][0] != per:
                break
            per = ch[-1]["box"][0] - nx["box"][0]
            ch.append(nx)
        sites.append((o, tuple(ch), per))
    gaps = Counter()
    for k in sorted(col, key=lambda k: (k[0], k[2], sorted(k[1]))):
        rows = sorted((o["box"][0], o["box"][2]) for o in col[k])
        gaps.update(b[0] - a[1] - 1 for a, b in zip(rows, rows[1:]) if b[0] > a[1])
    return tuple(sites), (gaps.most_common(1)[0][0] if gaps else 1)


def _stack(g, v, rule):
    conn, count = v
    bg = _bg(g)
    sites, gap = _chains(g, bg, conn)
    if not sites:
        return None
    st = [(s["px"], 0, 0, m["c"]) for m, ch, _ in sites for s in ch]
    if rule is not None and count != "none":
        recol = [ch for m, ch, _ in sites if _resolve(rule, m["c"], ch[0]["c"]) not in (None, ch[0]["c"])]
        n = sum(map(len, recol)) if count == "links" else len(recol)
        for m, ch, per in sites:
            if _resolve(rule, m["c"], ch[0]["c"]) != ch[0]["c"]:
                continue                                # only chains kept in their own colour grow
            top = ch[-1]
            per = per or (top["box"][2] - top["box"][0] + 1 + gap)
            st += [(top["px"], -per * j, 0, m["c"]) for j in range(1, (len(ch) if count == "own" else n) + 1)]
    return _plan([list(r) for r in g], bg, st, {"markers": [p for m, _, _ in sites for p in m["cells"]]})


# (name, cost, planner, plan depends on the colour rule)
LAYOUTS = (("blowup", 0, _blowup, False), ("marker", 2, _marker, False),
           ("throw", 4, _throw, False), ("stack", 4, _stack, True))


def _domains(lname, pairs):
    """(name, cost, value) over the layout's small parameter domain, gated by the in/out sizes."""
    same = all(len(g) == len(o) and len(g[0]) == len(o[0]) for g, o in pairs)
    smaller = all(len(o) * len(o[0]) < len(g) * len(g[0]) for g, o in pairs)
    bigger = all(len(o) * len(o[0]) > len(g) * len(g[0]) for g, o in pairs)
    if lname == "blowup" and bigger:
        for si, s in enumerate(("halves", "separator", "self")):
            for gap in (0, 1):
                yield "split=%s,gap=%d" % (s, gap), si + gap, (s, gap)
    if lname == "marker":
        for host, crop in ((("area", True),) if smaller else ()) + ((("area", False), ("grid", False)) if same else ()):
            for inset in ((0, 1) if host == "area" else (0,)):
                for ai, a in enumerate(ANCHORS):
                    yield ("host=%s,inset=%d,anchor=%s,%s" % (host, inset, a, "crop" if crop else "in_place"),
                           ai + 2 * inset + (host == "grid"), (host, inset, a, crop))
    if lname == "throw" and same:
        dmax = max(max(len(g), len(g[0])) for g, _ in pairs)
        for pol in (1, -1):
            for src in ("pixel", "glyph"):
                for d in range(1, dmax):
                    yield "d=%d,pol=%+d,src=%s" % (d, pol, src), d + 3 * (pol < 0) + 2 * (src == "glyph"), (d, pol, src)
    if lname == "stack" and same:
        for ci, conn in enumerate((4, 8)):
            for ki, k in enumerate(("links", "own", "markers", "none")):
                yield "conn=%d,count=%s" % (conn, k), 3 * ci + ki, (conn, k)


# ---------------------------------------------------------------- colour rule, drawing loop
def _resolve(rule, key, own):
    if rule[0] == "own":
        return own
    if rule[0] == "key":
        return key
    if rule[0] == "const":
        return rule[1]
    v = rule[1].get(key)
    return own if v == OWN else v


def _rules(plans, outs, hit):
    """Colour rules consistent with every singly-stamped output cell, and the collision colour."""
    poss, multi = {}, set()
    for P, o in zip(plans, outs):
        cv = P["canvas"]
        if (len(o), len(o[0])) != (len(cv), len(cv[0])):
            return [], None
        cnt, first = Counter(), {}
        r0, c0, r1, c1 = P["clip"]
        for cells, dy, dx, key in P["stamps"]:
            for y, x, c in cells:
                t = (y + dy, x + dx)
                if r0 <= t[0] <= r1 and c0 <= t[1] <= c1:
                    cnt[t] += 1
                    first[t] = (key, c)
        for t, n in cnt.items():
            v = o[t[0]][t[1]]
            if n > 1:
                multi.add(v)
            elif not (hit == "skip" and t in P["owner"]):
                key, c = first[t]
                s = {v} | ({OWN} if v == c else set()) | ({KEY} if v == key else set())
                poss[key] = poss[key] & s if key in poss else s
    if not poss or not all(poss.values()):
        return [], None
    allk = set.intersection(*poss.values())
    rules = [("own",)] * (OWN in allk) + [("key",)] * (KEY in allk) + [("const", c) for c in sorted(allk) if c >= 0]
    if not rules:
        rules = [("table", {k: (OWN if OWN in s else min(c for c in s if c >= 0)) for k, s in poss.items()
                            if OWN in s or any(c >= 0 for c in s)})]
        if len(rules[0][1]) != len(poss):
            return [], None
    return rules, (next(iter(multi)) if len(multi) == 1 else None)


def _render(P, rule, hit, ccol, erase):
    out = [list(r) for r in P["canvas"]]
    for k in erase:
        for y, x in P["erase"].get(k, ()):
            out[y][x] = P["bg"]
    hits, recol, owner = {}, {}, P["owner"]
    r0, c0, r1, c1 = P["clip"]
    for cells, dy, dx, key in P["stamps"]:
        for y, x, c in cells:
            t = (y + dy, x + dx)
            col = _resolve(rule, key, c)
            if col is not None and r0 <= t[0] <= r1 and c0 <= t[1] <= c1:
                hits.setdefault(t, []).append(col)
    for t in sorted(hits):
        col = ccol if (len(hits[t]) > 1 and ccol is not None) else hits[t][-1]
        if hit != "paint" and t in owner:
            if hit == "object" and (recol.get(owner[t]) != ccol or ccol is None):
                recol[owner[t]] = col               # several hits on one object: the collision colour wins
            continue
        out[t[0]][t[1]] = col
    for i in sorted(recol):
        for y, x in P["objs"][i]:
            out[y][x] = recol[i]
    return out


def _rname(rule):
    if rule[0] in ("own", "key"):
        return rule[0]
    if rule[0] == "const":
        return "const(%d)" % rule[1]
    return "table(%s)" % ",".join("%d:%s" % (k, "own" if v == OWN else v) for k, v in sorted(rule[1].items()))


def _make(planner, v, rule, hit, ccol, er):
    def fn(grid):
        P = planner(_t(grid), v, rule)
        return None if P is None else _render(P, rule, hit, ccol, er)
    return fn


def fam(train):
    if not train:
        return
    pairs = [(_t(p["input"]), p["output"]) for p in train]
    if any(not g or not g[0] or not o or not o[0] for g, o in pairs):
        return
    if all([list(r) for r in g] == o for g, o in pairs):
        return
    outs, found = [o for _, o in pairs], []
    for lname, lcost, planner, late in LAYOUTS:
        for pname, pcost, v in _domains(lname, pairs):
            plans = [planner(g, v, None) for g, _ in pairs]
            if None in plans:
                continue
            hits = ("paint", "object", "skip") if any(P["owner"] for P in plans) else ("paint",)
            ers = [()] + [e for e in (("markers",), ("templates",), ("markers", "templates"))
                          if any(all(P["erase"].get(k) for k in e) for P in plans)]
            for hi, hit in enumerate(hits):
                rules, ccol = _rules(plans, outs, hit)
                for rule in rules:
                    pl = [planner(g, v, rule) for g, _ in pairs] if late else plans
                    if None in pl:
                        continue
                    for ei, er in enumerate(ers):
                        if all(_render(P, rule, hit, ccol, er) == o for P, o in zip(pl, outs)):
                            rc = {"own": 0, "key": 1, "const": 1, "table": 3}[rule[0]]
                            name = "stamp_replicate[%s:%s,colour=%s%s,hit=%s,erase=%s]" % (
                                lname, pname, _rname(rule), "" if ccol is None else ",collide=%d" % ccol,
                                hit, "+".join(er) or "none")
                            found.append((10 + lcost + pcost + rc + hi + ei, len(found), name,
                                          (planner, v, rule, hit, ccol, er)))
                            break
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, _, name, spec in found:
        yield name, cost, _make(*spec)


FAMILIES = [fam]
