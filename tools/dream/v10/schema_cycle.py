"""CYCLE image schema of the v10 description lattice (Fable guidance v10).

A CYCLE rule repeats a unit with a period: tile a grid, repeat an object or a row prefix along a vector,
complete a periodic texture, continue a seeded sequence, recolour elements by index mod k, cyclically shift
rows / item attributes / corner blocks, grow a run one cell per row, or recur a row rule downward.

Lattice:  schema CYCLE (depth 0, every generator free)
          -> one step (depth 1): verb | stop class | colour rule | parameter value | role selector
          -> two steps (depth 2): any two compatible steps; stop class -> member only once the class is fixed.
A node is a dict of choices {slot: value}; slots are 'verb', 'stop', 'stop_member', 'colour',
'param:<name>' and 'role:<name>'.  Free slots are fitted from the training pairs by family(node).
Menus are drawn from the CYCLE records in results/o0/v10_records.json (verbs, stops, roles, params); the
concrete generators ("kinds") below each declare the slot values they realise.

Synthetic only: no ARC data is read here.  Pure stdlib, deterministic (random.Random with string seeds).
draw(node, seed): seeds 4t..4t+3 are the four pairs of synthetic task t (task-level constants such as the
generator, its parameters and literal colours are shared; sizes, positions and object colours vary per pair).
"""
import itertools
import random
import zlib

SCHEMA = "CYCLE"
BG = 0
KEEP = "keep"

# ----------------------------------------------------------------------------------------------- grid helpers


def _dims(g):
    return (len(g), len(g[0]) if g else 0)


def _new(h, w, v=BG):
    return [[v] * w for _ in range(h)]


def _cp(g):
    return [list(r) for r in g]


def _T(g):
    return [list(r) for r in zip(*g)] if g else []


def _flr(g):
    return [list(r[::-1]) for r in g]


def _fud(g):
    return [list(r) for r in g[::-1]]


def _r90(g):
    return [list(r) for r in zip(*g[::-1])]


def _r180(g):
    return [list(r[::-1]) for r in g[::-1]]


def _r270(g):
    return [list(r) for r in zip(*g)][::-1]


def _bbox(g, skip=()):
    r0 = c0 = 10 ** 9
    r1 = c1 = -1
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if v != BG and v not in skip:
                if r < r0: r0 = r
                if r > r1: r1 = r
                if c < c0: c0 = c
                if c > c1: c1 = c
    if r1 < 0:
        return None
    return (r0, r1, c0, c1)


def _crop(g, bb):
    r0, r1, c0, c1 = bb
    return [list(row[c0:c1 + 1]) for row in g[r0:r1 + 1]]


def _colours(g):
    return sorted({v for row in g for v in row if v != BG})


def _count(g, v):
    return sum(row.count(v) for row in g)


def _cells(g):
    return [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != BG]


def _paste(dst, src, r0, c0):
    for r, row in enumerate(src):
        for c, v in enumerate(row):
            dst[r0 + r][c0 + c] = v


def _ok_grid(g, lim=20):
    if not isinstance(g, list) or not g or not isinstance(g[0], list) or not g[0]:
        return False
    h, w = len(g), len(g[0])
    if h > lim or w > lim:
        return False
    return all(len(r) == w and all(isinstance(v, int) and 0 <= v <= 9 for v in r) for r in g)


def _comps8(g):
    h, w = _dims(g)
    seen = [[False] * w for _ in range(h)]
    out = []
    for r in range(h):
        for c in range(w):
            if g[r][c] == BG or seen[r][c]:
                continue
            st = [(r, c)]
            seen[r][c] = True
            cs = []
            while st:
                a, b = st.pop()
                cs.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < h and 0 <= y < w and not seen[x][y] and g[x][y] != BG:
                            seen[x][y] = True
                            st.append((x, y))
            out.append(sorted(cs))
    return out


def _shape(rng, h, w, cols, dens=0.65, full=True, ncol=None):
    """Random h x w multicolour shape; full=True: every row and column holds ink (bbox = whole block)."""
    for _ in range(80):
        g = [[rng.choice(cols) if rng.random() < dens else BG for _ in range(w)] for _ in range(h)]
        if full:
            if any(all(v == BG for v in row) for row in g):
                continue
            if any(all(g[r][c] == BG for r in range(h)) for c in range(w)):
                continue
        elif not any(v for row in g for v in row):
            continue
        if ncol is not None and len(_colours(g)) != ncol:
            continue
        return g
    return None


def _asym(U):
    if U == _flr(U) or U == _fud(U) or U == _r180(U):
        return False
    if len(U) == len(U[0]) and (U == _r90(U) or U == _T(U)):
        return False
    return True


# ------------------------------------------------------------------------------------------- kind framework


class _Kind:
    """One concrete generator family.  slots: slot -> declared domain (tuple)."""
    name = ""
    base = 1.0
    slots = {}

    def valid(self, a):
        return True

    def raw_assigns(self, dom):
        keys = sorted(dom)
        for vals in itertools.product(*(dom[k] for k in keys)):
            a = dict(zip(keys, vals))
            if self.valid(a):
                yield a

    def assigns(self, dom):
        return self.raw_assigns(dom)

    def pre(self, train):
        return True

    def induce(self, a, train):
        yield {}

    def apply(self, a, ctx, g):
        raise NotImplementedError

    def cost(self, a, ctx):
        return self.base

    def task(self, a, rt):
        return {}

    def gen(self, a, tc, rp, pi):
        raise NotImplementedError

    def progname(self, a, ctx):
        parts = ["%s=%s" % (k.split(":")[-1], a[k]) for k in sorted(a) if len(self.slots.get(k, ())) > 1]
        parts += ["%s=%s" % (k, ctx[k]) for k in sorted(ctx) if ctx[k] is not None and k != "T"]
        if ctx.get("T") is not None:
            parts.append("table=" + "".join(str(ctx["T"][p]) for p in sorted(ctx["T"])))
        return "%s.%s[%s]" % (SCHEMA, self.name, ",".join(parts))

    def _safe(self, a, ctx, g):
        try:
            return self.apply(a, ctx, g)
        except Exception:
            return None

    def mkfn(self, a, ctx):
        def fn(g, _s=self, _a=a, _c=ctx):
            return _s._safe(_a, _c, g)
        return fn

    def fit(self, train, dom):
        if not self.pre(train):
            return
        for a in self.assigns(dom):
            for ctx in self.induce(a, train):
                if ctx is None:
                    continue
                if all(self._safe(a, ctx, i) == o for i, o in train):
                    yield (self.progname(a, ctx), round(self.cost(a, ctx), 3), self.mkfn(a, ctx))


def _same_dims(train):
    return all(_dims(i) == _dims(o) for i, o in train)


def _sz(gs):
    return all(_ok_grid(g, 30) for g in gs)


# ------------------------------------------------------------------------------------------------- tiling


def _unit(g, sel):
    if sel == "input grid":
        return g
    bb = _bbox(g)
    return _crop(g, bb) if bb else None


def _slot_tf(U, i, j, mode):
    if mode == "identity":
        return U
    if mode == "mirror":
        B = U
        if i % 2:
            B = _fud(B)
        if j % 2:
            B = _flr(B)
        return B
    if mode == "rot4":
        return {(0, 0): U, (0, 1): _r90(U), (1, 1): _r180(U), (1, 0): _r270(U)}[(i, j)]
    raise ValueError(mode)


def _tile(U, r, c, mode):
    h, w = _dims(U)
    if r * h > 30 or c * w > 30 or r < 1 or c < 1:
        return None
    if mode == "rot4" and (h != w or (r, c) != (2, 2)):
        return None
    out = _new(r * h, c * w)
    for i in range(r):
        for j in range(c):
            _paste(out, _slot_tf(U, i, j, mode), i * h, j * w)
    return out


class TileConst(_Kind):
    """copy(dihedral(unit, slot)) over a constant r x c layout (grp_M124, grp_M062, grp_M026, oo_c92b942c)."""
    name = "tile_const"
    base = 1.0
    slots = {"verb": ("tile",), "stop": ("count",), "stop_member": ("count:layout",), "colour": ("own",),
             "param:layout": ("1x2", "2x1", "1x3", "3x1", "2x2", "3x3"), "param:per_copy": ("identity", "mirror", "rot4"),
             "role:unit": ("input grid", "fg bbox crop")}

    def valid(self, a):
        return a["param:per_copy"] != "rot4" or a["param:layout"] == "2x2"

    def pre(self, train):
        return all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + {"identity": 0, "mirror": .2, "rot4": .3}[a["param:per_copy"]] + \
            (.1 if a["role:unit"] != "input grid" else 0)

    def apply(self, a, ctx, g):
        U = _unit(g, a["role:unit"])
        if U is None:
            return None
        r, c = map(int, a["param:layout"].split("x"))
        return _tile(U, r, c, a["param:per_copy"])

    def gen(self, a, tc, rp, pi):
        r, c = map(int, a["param:layout"].split("x"))
        if a["param:per_copy"] == "rot4":
            h = w = rp.randint(2, 4)
        else:
            h = rp.randint(2, min(5, 20 // r))
            w = rp.randint(2, min(5, 20 // c))
        cols = rp.sample(range(1, 10), rp.randint(1, 3))
        if a["role:unit"] == "input grid":
            U = _shape(rp, h, w, cols, 0.6, full=False)
            if U is None:
                return None
            if pi == 0 and _crop(U, _bbox(U)) == U:
                return None                      # a bg margin tells 'input grid' from 'fg bbox crop'
            inp = U
        else:
            U = _shape(rp, h, w, cols, 0.6, full=True)
            if U is None:
                return None
            H, W = rp.randint(h + 1, min(h + 7, 14)), rp.randint(w + 1, min(w + 7, 14))
            inp = _new(H, W)
            _paste(inp, U, rp.randint(0, H - h), rp.randint(0, W - w))
        if not _asym(U):
            return None
        return inp, self.apply(a, {}, inp)


class TileNcol(_Kind):
    """layout k x k with k = number of distinct colours (grp_M026 count = #distinct colours)."""
    name = "tile_ncol"
    base = 1.5
    slots = {"verb": ("tile",), "stop": ("count",), "stop_member": ("count:colours",), "colour": ("own",),
             "param:per_copy": ("identity", "mirror"), "role:unit": ("input grid", "fg bbox crop")}

    def pre(self, train):
        return all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.2 if a["param:per_copy"] == "mirror" else 0) + \
            (.1 if a["role:unit"] != "input grid" else 0)

    def apply(self, a, ctx, g):
        U = _unit(g, a["role:unit"])
        if U is None:
            return None
        k = len(_colours(U))
        return _tile(U, k, k, a["param:per_copy"])

    def gen(self, a, tc, rp, pi):
        k = (2, 3, 2, 3)[pi]
        h, w = rp.randint(2, 4), rp.randint(2, 4)
        cols = rp.sample(range(1, 10), k)
        if a["role:unit"] == "input grid":
            U = _shape(rp, h, w, cols, 0.75, full=False, ncol=k)
            if U is None or (pi == 0 and _crop(U, _bbox(U)) == U):
                return None
            inp = U
        else:
            U = _shape(rp, h, w, cols, 0.75, full=True, ncol=k)
            if U is None:
                return None
            H, W = rp.randint(h + 1, h + 6), rp.randint(w + 1, w + 6)
            inp = _new(H, W)
            _paste(inp, U, rp.randint(0, H - h), rp.randint(0, W - w))
        if not _asym(U):
            return None
        return inp, self.apply(a, {}, inp)


# ------------------------------------------------------------------------------------------------ repeating

_DIRS = {"right": (0, 1), "down": (1, 0), "left": (0, -1), "up": (-1, 0), "downright": (1, 1)}


def _marker_dir(bb, mr, mc):
    r0, r1, c0, c1 = bb
    if r0 <= mr <= r1 and mc == c1 + 1:
        return "right"
    if r0 <= mr <= r1 and mc == c0 - 1:
        return "left"
    if c0 <= mc <= c1 and mr == r1 + 1:
        return "down"
    if c0 <= mc <= c1 and mr == r0 - 1:
        return "up"
    if mr == r1 + 1 and mc == c1 + 1:
        return "downright"
    return None


class RepeatObject(_Kind):
    """copy(template object) * (size+gap) along a direction until the border (grp_M039, oo_12422b43)."""
    name = "repeat_object"
    base = 1.2
    slots = {"verb": ("repeat",), "stop": ("border",), "stop_member": ("border:clip", "border:whole"),
             "colour": ("own", "literal"), "param:direction": ("right", "down", "left", "up", "downright"),
             "param:gap": (0, 1, 2), "role:unit": ("object",),
             "role:vector": ("template size+gap", "marker direction")}

    def assigns(self, dom):
        seen = set()
        for a in self.raw_assigns(dom):
            if a["role:vector"] == "marker direction":
                a = dict(a)
                a["param:direction"] = "|".join(dom["param:direction"])   # read per grid from the marker
            k = tuple(sorted(a.items(), key=lambda t: t[0]))
            if k in seen:
                continue
            seen.add(k)
            yield a

    def pre(self, train):
        return _same_dims(train) and all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.3 if a["role:vector"] != "template size+gap" else 0) + \
            (.2 if a["colour"] == "literal" else 0) + (.1 if a["stop_member"] == "border:whole" else 0) + \
            .02 * a["param:gap"]

    def induce(self, a, train):
        Ls = [None]
        if a["colour"] == "literal":
            i, o = train[0]
            ch = {o[r][c] for r in range(len(o)) for c in range(len(o[0]))
                  if o[r][c] != i[r][c] and o[r][c] != BG}
            if len(ch) != 1:
                return
            Ls = list(ch)
        Ms = [None]
        if a["role:vector"] == "marker direction":
            cand = None
            for i, o in train:
                cs = {v for v in _colours(i) if _count(i, v) == 1}
                cand = cs if cand is None else cand & cs
            Ms = sorted(cand or ())
        for L in Ls:
            for M in Ms:
                yield {"L": L, "M": M}

    def apply(self, a, ctx, g):
        H, W = _dims(g)
        out = _cp(g)
        skip = ()
        M = ctx.get("M")
        if a["role:vector"] == "marker direction":
            pos = [(r, c) for r, c, v in _cells(g) if v == M]
            if len(pos) != 1:
                return None
            mr, mc = pos[0]
            out[mr][mc] = BG
            skip = (M,)
        bb = _bbox(g, skip)
        if bb is None:
            return None
        r0, r1, c0, c1 = bb
        h, w = r1 - r0 + 1, c1 - c0 + 1
        if a["role:vector"] == "marker direction":
            d = _marker_dir(bb, mr, mc)
            if d is None or d not in a["param:direction"].split("|"):
                return None
        else:
            d = a["param:direction"]
        dy, dx = _DIRS[d]
        gap = a["param:gap"]
        sy, sx = dy * (h + gap), dx * (w + gap)
        tpl = [(r - r0, c - c0, g[r][c]) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)
               if g[r][c] != BG and g[r][c] not in skip]
        L = ctx.get("L")
        whole = a["stop_member"] == "border:whole"
        for k in range(1, 41):
            R0, C0 = r0 + k * sy, c0 + k * sx
            if R0 > H - 1 or C0 > W - 1 or R0 + h - 1 < 0 or C0 + w - 1 < 0:
                break
            if whole and not (R0 >= 0 and C0 >= 0 and R0 + h <= H and C0 + w <= W):
                break
            for dr, dc, v in tpl:
                rr, cc = R0 + dr, C0 + dc
                if 0 <= rr < H and 0 <= cc < W:
                    out[rr][cc] = v if L is None else L
        return out

    def task(self, a, rt):
        pool = list(range(1, 10))
        rt.shuffle(pool)
        return {"L": pool[0], "M": pool[1], "pool": pool[2:]}

    def gen(self, a, tc, rp, pi):
        H, W = rp.randint(10, 16), rp.randint(10, 16)
        h, w = rp.randint(2, 3), rp.randint(2, 3)
        T = _shape(rp, h, w, rp.sample(tc["pool"], rp.randint(1, 2)), 0.7, full=True)
        gap = a["param:gap"]
        marker = a["role:vector"] == "marker direction"
        d = rp.choice(a["param:direction"].split("|")) if marker else a["param:direction"]
        dy, dx = _DIRS[d]

        def rng_for(n, s, dd):
            if dd == 1:
                return 0, n - 2 * s - gap
            if dd == -1:
                return s + gap, n - s
            return (1, n - s - 1) if marker else (0, n - s)
        lo, hi = rng_for(H, h, dy)
        lo2, hi2 = rng_for(W, w, dx)
        if T is None or hi < lo or hi2 < lo2:
            return None
        r0, c0 = rp.randint(lo, hi), rp.randint(lo2, hi2)
        inp = _new(H, W)
        _paste(inp, T, r0, c0)
        ctx = {"L": tc["L"] if a["colour"] == "literal" else None, "M": tc["M"] if marker else None}
        if marker:
            mr, mc = {"right": (r0 + h // 2, c0 + w), "left": (r0 + h // 2, c0 - 1),
                      "down": (r0 + h, c0 + w // 2), "up": (r0 - 1, c0 + w // 2),
                      "downright": (r0 + h, c0 + w)}[d]
            if not (0 <= mr < H and 0 <= mc < W):
                return None
            inp[mr][mc] = tc["M"]
        out = self.apply(a, ctx, inp)
        if out is None:
            return None
        if pi == 0:                                  # make clip vs whole visible in a training pair
            b = dict(a)
            b["stop_member"] = "border:whole" if a["stop_member"] == "border:clip" else "border:clip"
            if self.apply(b, ctx, inp) == out:
                return None
        return inp, out


class RepeatPrefix(_Kind):
    """each row's prefix (col 0 .. last ink) repeated with period len+gap to the border (d2_1ae2feb7, grp_M009 1D)."""
    name = "repeat_prefix"
    base = 1.1
    slots = {"verb": ("repeat",), "stop": ("border",), "stop_member": ("border:edge",), "colour": ("own",),
             "param:axis": ("row", "col"), "param:gap": (0, 1), "role:unit": ("row prefix",)}

    def pre(self, train):
        return _same_dims(train) and all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + .05 * a["param:gap"] + (.01 if a["param:axis"] == "col" else 0)

    def apply(self, a, ctx, g):
        G = g if a["param:axis"] == "row" else _T(g)
        W = len(G[0])
        out = []
        for row in G:
            nz = [c for c, v in enumerate(row) if v != BG]
            if not nz:
                out.append(list(row))
                continue
            if nz[0] != 0:
                return None
            e = nz[-1]
            p = e + 1 + a["param:gap"]
            out.append([row[c % p] if c % p <= e else BG for c in range(W)])
        return out if a["param:axis"] == "row" else _T(out)

    def gen(self, a, tc, rp, pi):
        L, X = rp.randint(10, 18), rp.randint(4, 10)
        G = _new(X, L)
        for r in rp.sample(range(X), rp.randint(2, min(4, X))):
            n = rp.randint(2, 4)
            cols = rp.sample(range(1, 10), rp.randint(1, 3))
            G[r][:n] = [rp.choice(cols) if (j in (0, n - 1) or rp.random() < .8) else BG for j in range(n)]
        inp = G if a["param:axis"] == "row" else _T(G)
        return inp, self.apply(a, {}, inp)


class RepeatCount(_Kind):
    """copy(template) N times side by side, N = number of marker cells (d2_b0039139, oo_4852f2fa)."""
    name = "repeat_count"
    base = 1.4
    slots = {"verb": ("print",), "stop": ("count",), "stop_member": ("count:markers",), "colour": ("own",),
             "param:axis": ("row", "col"), "param:gap": (0, 1), "role:unit": ("object",),
             "role:count": ("marker cells",)}

    def pre(self, train):
        return all(_dims(i) != _dims(o) for i, o in train)

    def cost(self, a, ctx):
        return self.base + .05 * a["param:gap"] + (.01 if a["param:axis"] == "col" else 0)

    def induce(self, a, train):
        cand = None
        for i, o in train:
            cs = set(_colours(i))
            cand = cs if cand is None else cand & cs
        for M in sorted(cand or ()):
            yield {"M": M}

    def apply(self, a, ctx, g):
        M = ctx["M"]
        N = _count(g, M)
        bb = _bbox(g, (M,))
        if N == 0 or bb is None:
            return None
        U = [[BG if v == M else v for v in row] for row in _crop(g, bb)]
        h, w = _dims(U)
        gap = a["param:gap"]
        if a["param:axis"] == "row":
            out = _new(h, N * w + (N - 1) * gap)
            for j in range(N):
                _paste(out, U, 0, j * (w + gap))
        else:
            out = _new(N * h + (N - 1) * gap, w)
            for j in range(N):
                _paste(out, U, j * (h + gap), 0)
        return out if _sz([out]) else None

    def task(self, a, rt):
        pool = list(range(1, 10))
        rt.shuffle(pool)
        Ns = [1, 2, 3, 4]
        rt.shuffle(Ns)
        return {"M": pool[0], "pool": pool[1:], "Ns": Ns}

    def gen(self, a, tc, rp, pi):
        H, W = rp.randint(8, 14), rp.randint(8, 14)
        h, w = rp.randint(2, 3), rp.randint(2, 3)
        T = _shape(rp, h, w, rp.sample(tc["pool"], rp.randint(1, 2)), .7, full=True)
        if T is None:
            return None
        r0, c0 = rp.randint(0, H - h), rp.randint(0, W - w)
        inp = _new(H, W)
        _paste(inp, T, r0, c0)
        N = tc["Ns"][pi]
        free = [(r, c) for r in range(H) for c in range(W)
                if not (r0 - 1 <= r <= r0 + h and c0 - 1 <= c <= c0 + w)]
        rp.shuffle(free)
        put = []
        for r, c in free:
            if all(max(abs(r - x), abs(c - y)) > 1 for x, y in put):
                put.append((r, c))
            if len(put) == N:
                break
        if len(put) < N:
            return None
        for r, c in put:
            inp[r][c] = tc["M"]
        return inp, self.apply(a, {"M": tc["M"]}, inp)


# ----------------------------------------------------------------------------------------- periodic texture


def _period_fill(g, M):
    H, W = _dims(g)
    known = [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != M]
    cands = sorted(((py, px) for py in range(1, H + 1) for px in range(1, W + 1)),
                   key=lambda t: (t[0] * t[1], t[0], t[1]))
    for py, px in cands:
        if py * px > len(known):
            break
        tab = {}
        ok = True
        for r, c, v in known:
            k = (r % py, c % px)
            u = tab.get(k)
            if u is None:
                tab[k] = v
            elif u != v:
                ok = False
                break
        if ok and len(tab) == py * px:
            return [[tab[(r % py, c % px)] for c in range(W)] for r in range(H)]
    return None


def _diag_fill(g, M):
    H, W = _dims(g)
    known = [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != M]
    for k in range(2, 9):
        for s in (1, -1):
            tab = {}
            ok = True
            for r, c, v in known:
                x = (r + s * c) % k
                u = tab.get(x)
                if u is None:
                    tab[x] = v
                elif u != v:
                    ok = False
                    break
            if ok and len(tab) == k:
                return [[tab[(r + s * c) % k] for c in range(W)] for r in range(H)]
    return None


class CompletePeriodic(_Kind):
    """extend(periodic pattern) over masked cells (grp_M009, grp_M053, len_0607ce86, d2_135a2760)."""
    name = "complete_periodic"
    base = 1.0
    slots = {"verb": ("complete",), "stop": ("none",), "stop_member": ("none",), "colour": ("own",),
             "param:lattice": ("grid", "diagonal"), "param:mask": ("bg", "occluder"),
             "role:unit": ("periodic tile",)}

    def pre(self, train):
        return _same_dims(train) and all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.1 if a["param:lattice"] == "diagonal" else 0) + \
            (.2 if a["param:mask"] == "occluder" else 0)

    def induce(self, a, train):
        src = set()
        for i, o in train:
            for r in range(len(i)):
                for c in range(len(i[0])):
                    if i[r][c] != o[r][c]:
                        src.add(i[r][c])
        if len(src) != 1:
            return
        M = src.pop()
        if (a["param:mask"] == "bg") != (M == BG):
            return
        if any(_count(o, M) for i, o in train):
            return
        yield {"M": M} if a["param:mask"] == "occluder" else {}

    def apply(self, a, ctx, g):
        M = ctx.get("M", BG)
        if not _count(g, M):
            return None
        return (_period_fill if a["param:lattice"] == "grid" else _diag_fill)(g, M)

    def task(self, a, rt):
        return {"M": rt.randint(1, 9)}

    def gen(self, a, tc, rp, pi):
        H, W = rp.randint(8, 16), rp.randint(8, 16)
        M = tc["M"] if a["param:mask"] == "occluder" else BG
        pool = [v for v in range(1, 10) if v != M]
        if a["param:lattice"] == "grid":
            py, px = rp.randint(2, 4), rp.randint(2, 4)
            tile = [[rp.choice(rp.sample(pool, 3)) for _ in range(px)] for _ in range(py)]
            if len(_colours(tile)) < 2:
                return None
            out = [[tile[r % py][c % px] for c in range(W)] for r in range(H)]
        else:
            k, s = rp.randint(2, 4), rp.choice((1, -1))
            seq = rp.sample(pool, k)
            out = [[seq[(r + s * c) % k] for c in range(W)] for r in range(H)]
        inp = _cp(out)
        for _ in range(rp.randint(1, 3)):
            h, w = rp.randint(1, 4), rp.randint(1, 4)
            r0, c0 = rp.randint(0, H - h), rp.randint(0, W - w)
            for r in range(r0, r0 + h):
                for c in range(c0, c0 + w):
                    inp[r][c] = M
        ctx = {"M": M} if a["param:mask"] == "occluder" else {}
        if self.apply(a, ctx, inp) != out:
            return None                              # not recoverable from what is left visible
        return inp, out


# ------------------------------------------------------------------------------------- seeded progressions


class LinesSeeded(_Kind):
    """full lines through m seeds, repeated every seed spacing, colours cycling (grp_M065, oo_0a938d79)."""
    name = "lines_seeded"
    base = 1.2
    slots = {"verb": ("extend",), "stop": ("border",), "stop_member": ("border:edge",), "colour": ("sequence",),
             "param:seeds": (2, 3), "role:axis": ("cols", "rows", "long axis"), "role:unit": ("seed cells",)}

    def pre(self, train):
        return _same_dims(train) and all(len(_cells(i)) <= 3 for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.2 if a["role:axis"] == "long axis" else 0) + .01 * a["param:seeds"]

    def apply(self, a, ctx, g):
        H, W = _dims(g)
        m = a["param:seeds"]
        cells = _cells(g)
        if len(cells) != m:
            return None
        ori = a["role:axis"]
        if ori == "long axis":
            ori = "cols" if W > H else ("rows" if H > W else None)
            if ori is None:
                return None
        G = g if ori == "cols" else _T(g)
        cells = sorted(((c, r, v) for r, c, v in _cells(G)))
        xs = [c for c, r, v in cells]
        if len(set(xs)) != m:
            return None
        d = xs[1] - xs[0]
        if any(xs[i + 1] - xs[i] != d for i in range(m - 1)):
            return None
        h, w = _dims(G)
        out = _new(h, w)
        i, x = 0, xs[0]
        while x < w:
            for r in range(h):
                out[r][x] = cells[i % m][2]
            i += 1
            x += d
        return out if ori == "cols" else _T(out)

    def gen(self, a, tc, rp, pi):
        ori = a["role:axis"]
        if ori == "long axis":
            ori = ("cols", "rows")[pi] if pi < 2 else rp.choice(("cols", "rows"))
            Lc, X = rp.randint(13, 20), rp.randint(5, 10)
        else:
            Lc = rp.randint(10, 20)
            X = rp.randint(Lc + 1, 20) if (pi == 0 and Lc < 20) else rp.randint(4, 12)
        m = a["param:seeds"]
        d = rp.randint(2, 4)
        p0 = rp.randint(0, 3)
        if p0 + m * d >= Lc:
            return None
        G = _new(X, Lc)
        for j, v in enumerate(rp.sample(range(1, 10), m)):
            G[rp.randrange(X)][p0 + j * d] = v
        inp = G if ori == "cols" else _T(G)
        if a["role:axis"] == "long axis" and len(inp) == len(inp[0]):
            return None
        return inp, self.apply(a, {}, inp)


class ContinueSequence(_Kind):
    """collinear seeds continued with constant or growing gaps, colours cycling (grp_M074, oo_72207abc)."""
    name = "continue_sequence"
    base = 1.2
    slots = {"verb": ("continue",), "stop": ("border",), "stop_member": ("border:edge",),
             "colour": ("sequence",), "param:gap_rule": ("constant", "increasing"), "param:axis": ("row", "col"),
             "role:unit": ("seed cells",)}

    def pre(self, train):
        return _same_dims(train) and all(2 <= len(_cells(i)) <= 6 for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.2 if a["param:gap_rule"] == "increasing" else 0) + \
            (.01 if a["param:axis"] == "col" else 0)

    def apply(self, a, ctx, g):
        G = g if a["param:axis"] == "row" else _T(g)
        cells = _cells(G)
        if len(cells) < 2 or len({r for r, c, v in cells}) != 1:
            return None
        r = cells[0][0]
        ps = [c for _, c, _ in cells]
        cs = [v for _, _, v in cells]
        gaps = [ps[i + 1] - ps[i] for i in range(len(ps) - 1)]
        inc = 1 if a["param:gap_rule"] == "increasing" else 0
        if any(gaps[i + 1] != gaps[i] + inc for i in range(len(gaps) - 1)):
            return None
        out = _cp(G)
        m, gap, pos, j = len(ps), gaps[-1], ps[-1], len(ps)
        W = len(G[0])
        while True:
            gap += inc
            pos += gap
            if pos >= W:
                break
            out[r][pos] = cs[j % m]
            j += 1
        return out if a["param:axis"] == "row" else _T(out)

    def gen(self, a, tc, rp, pi):
        L, X = rp.randint(12, 20), rp.randint(3, 9)
        inc = a["param:gap_rule"] == "increasing"
        m = rp.randint(3, 4) if inc else rp.randint(2, 4)
        g0 = rp.randint(1, 2) if inc else rp.randint(1, 3)
        p = rp.randint(0, 2)
        ps = [p]
        gap = g0
        for _ in range(m - 1):
            p += gap
            ps.append(p)
            gap += 1 if inc else 0
        if ps[-1] + gap >= L:
            return None
        G = _new(X, L)
        r = rp.randrange(X)
        for c, v in zip(ps, rp.sample(range(1, 10), m)):
            G[r][c] = v
        inp = G if a["param:axis"] == "row" else _T(G)
        return inp, self.apply(a, {}, inp)


# ------------------------------------------------------------------------------------------- cyclic recolour


def _elements(g, typ):
    H, W = _dims(g)
    if typ == "column":
        out = [[(r, c) for r in range(H) if g[r][c] != BG] for c in range(W)]
        return [e for e in out if e]
    if typ == "row":
        out = [[(r, c) for c in range(W) if g[r][c] != BG] for r in range(H)]
        return [e for e in out if e]
    comps = _comps8(g)
    comps.sort(key=lambda cs: (min(c for _, c in cs), min(r for r, _ in cs)))
    return comps


class RecolourCyclic(_Kind):
    """recolour(element[i], palette[i mod k]) in scan order (grp_M028, oo_b457fec5)."""
    name = "recolour_cyclic"
    base = 1.3
    slots = {"verb": ("recolour",), "stop": ("none",), "stop_member": ("none",), "colour": ("sequence",),
             "param:k": (2, 3), "param:order": ("forward", "backward"),
             "role:element": ("column", "row", "object")}

    def pre(self, train):
        if not _same_dims(train):
            return False
        for i, o in train:
            if i == o:
                return False
            for r in range(len(i)):
                for c in range(len(i[0])):
                    if (i[r][c] == BG) != (o[r][c] == BG):
                        return False
        return True

    def cost(self, a, ctx):
        return self.base + (.1 if a["param:order"] == "backward" else 0) + .05 * a["param:k"] + \
            {"column": 0, "row": .01, "object": .02}[a["role:element"]] + \
            .01 * sum(1 for v in ctx["P"].values() if v == KEEP)

    def _res(self, a, n, i):
        return (i if a["param:order"] == "forward" else n - 1 - i) % a["param:k"]

    def induce(self, a, train):
        obs = {}
        for i, o in train:
            el = _elements(i, a["role:element"])
            for idx, cells in enumerate(el):
                outs = {o[r][c] for r, c in cells}
                if len(outs) != 1:
                    return
                v = outs.pop()
                keep = all(o[r][c] == i[r][c] for r, c in cells)
                obs.setdefault(self._res(a, len(el), idx), []).append((v, keep))
        opts = []
        for res in range(a["param:k"]):
            ob = obs.get(res)
            if not ob:
                return
            o = []
            if len({v for v, _ in ob}) == 1:
                o.append(ob[0][0])
            if all(kp for _, kp in ob):
                o.append(KEEP)
            if not o:
                return
            opts.append(o)
        for combo in itertools.product(*opts):
            yield {"P": dict(enumerate(combo))}

    def apply(self, a, ctx, g):
        el = _elements(g, a["role:element"])
        if not el:
            return None
        out = _cp(g)
        for idx, cells in enumerate(el):
            v = ctx["P"].get(self._res(a, len(el), idx))
            if v is None:
                return None
            if v != KEEP:
                for r, c in cells:
                    out[r][c] = v
        return out

    def progname(self, a, ctx):
        P = ctx["P"]
        return "%s.%s[k=%s,order=%s,element=%s,P=%s]" % (
            SCHEMA, self.name, a["param:k"], a["param:order"], a["role:element"],
            "/".join(str(P[i]) for i in sorted(P)))

    def task(self, a, rt):
        k = a["param:k"]
        P = rt.sample(range(1, 10), k)
        if rt.random() < .25:
            P[rt.randrange(k)] = KEEP
        ns = [3, 4, 5, 6]
        rt.shuffle(ns)
        return {"P": P, "ns": ns}

    def gen(self, a, tc, rp, pi):
        n = tc["ns"][pi]
        g = rp.choice([v for v in range(1, 10) if v not in tc["P"]])
        typ = a["role:element"]
        if typ in ("column", "row"):
            H, W = rp.randint(5, 12), rp.randint(max(8, 2 * n), 18)
            off = rp.randint(0, 1)
            xs = sorted(rp.sample(range(off, W, 2), n)) if len(range(off, W, 2)) >= n else None
            if xs is None:
                return None
            G = _new(H, W)
            for x in xs:
                for r in range(H - rp.randint(1, H), H):
                    G[r][x] = g
            inp = G if typ == "column" else _T(G)
        else:
            H, W = rp.randint(8, 14), rp.randint(8, 14)
            inp = _new(H, W)
            occ = [[False] * W for _ in range(H)]
            placed = 0
            for _ in range(200):
                h, w = rp.randint(1, 2), rp.randint(1, 3)
                r0, c0 = rp.randint(0, H - h), rp.randint(0, W - w)
                if any(occ[r][c] for r in range(max(0, r0 - 1), min(H, r0 + h + 1))
                       for c in range(max(0, c0 - 1), min(W, c0 + w + 1))):
                    continue
                for r in range(r0, r0 + h):
                    for c in range(c0, c0 + w):
                        inp[r][c] = g
                        occ[r][c] = True
                placed += 1
                if placed == n:
                    break
            if placed < n:
                return None
        P = dict(enumerate(tc["P"]))
        return inp, self.apply(a, {"P": P}, inp)


# ------------------------------------------------------------------------------------------- cyclic shifts


def _shift_row(row, s, cyclic):
    W = len(row)
    if cyclic:
        return [row[(c - s) % W] for c in range(W)]
    return [row[c - s] if 0 <= c - s < W else BG for c in range(W)]


class ShiftRows(_Kind):
    """shift(row r, slope*r + b), cyclic or padded (grp_M047)."""
    name = "shift_rows"
    base = 1.2
    slots = {"verb": ("shift",), "stop": ("none",), "stop_member": ("none",), "colour": ("own",),
             "param:axis": ("row", "col"), "param:mode": ("cyclic", "pad"), "param:slope": (1, -1),
             "role:unit": ("row",)}

    def pre(self, train):
        return _same_dims(train) and all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.1 if a["param:mode"] == "pad" else 0) + (.01 if a["param:axis"] == "col" else 0) + \
            (.01 if a["param:slope"] < 0 else 0) + .005 * abs(ctx["b"])

    def induce(self, a, train):
        i, o = train[0]
        if a["param:axis"] == "col":
            i, o = _T(i), _T(o)
        cyc = a["param:mode"] == "cyclic"
        W = len(i[0])
        for r, row in enumerate(i):
            if not any(row) or (cyc and len(set(row)) == 1):
                continue
            ss = range(W) if cyc else range(-W + 1, W)
            bs = sorted({s - a["param:slope"] * r for s in ss if _shift_row(row, s, cyc) == o[r]},
                        key=lambda b: (abs(b), b))
            for b in bs:
                yield {"b": b}
            return

    def apply(self, a, ctx, g):
        G = g if a["param:axis"] == "row" else _T(g)
        cyc = a["param:mode"] == "cyclic"
        out = [_shift_row(row, a["param:slope"] * r + ctx["b"], cyc) for r, row in enumerate(G)]
        return out if a["param:axis"] == "row" else _T(out)

    def task(self, a, rt):
        return {"b": rt.randint(0, 1)}

    def gen(self, a, tc, rp, pi):
        H = rp.randint(4, 8)
        W = rp.randint(H + 2, 13)
        cols = rp.sample(range(1, 10), rp.randint(1, 3))
        G = [[rp.choice(cols) if rp.random() < .55 else BG for _ in range(W)] for _ in range(H)]
        if any(not any(row) or len(set(row)) == 1 for row in G):
            return None
        inp = G if a["param:axis"] == "row" else _T(G)
        return inp, self.apply(a, {"b": tc["b"]}, inp)


class PermuteItems(_Kind):
    """reassign(attribute sequence of bars := reverse | rotate +-1) keeping geometry (grp_M080, grp_M078)."""
    name = "permute_items"
    base = 1.3
    slots = {"verb": ("permute",), "stop": ("none",), "stop_member": ("none",), "colour": ("sequence",),
             "param:attribute": ("colour", "height"), "param:perm": ("reverse", "rot+1", "rot-1"),
             "role:unit": ("bars",)}

    def pre(self, train):
        return _same_dims(train) and all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + {"reverse": 0, "rot+1": .05, "rot-1": .06}[a["param:perm"]] + \
            (.01 if a["param:attribute"] == "height" else 0)

    def apply(self, a, ctx, g):
        H, W = _dims(g)
        items = []
        for c in range(W):
            nz = [r for r in range(H) if g[r][c] != BG]
            if not nz:
                continue
            if nz != list(range(H - len(nz), H)):
                return None
            vs = {g[r][c] for r in nz}
            if len(vs) != 1:
                return None
            items.append([c, vs.pop(), len(nz)])
        n = len(items)
        if n < 2:
            return None
        k = 1 if a["param:attribute"] == "colour" else 2
        seq = [it[k] for it in items]
        p = a["param:perm"]
        new = seq[::-1] if p == "reverse" else \
            [seq[(i - 1) % n] for i in range(n)] if p == "rot+1" else [seq[(i + 1) % n] for i in range(n)]
        out = _new(H, W)
        for it, v in zip(items, new):
            it[k] = v
            c, col, hh = it
            for r in range(H - hh, H):
                out[r][c] = col
        return out

    def gen(self, a, tc, rp, pi):
        n, H = rp.randint(3, 6), rp.randint(5, 10)
        W = 2 * n + 1
        cols = rp.sample(range(1, 10), n)
        G = _new(H, W)
        for j in range(n):
            for r in range(H - rp.randint(1, H - 1), H):
                G[r][2 * j + 1] = cols[j]
        out = self.apply(a, {}, G)
        if out is None:
            return None
        if pi < 3:                                   # every training pair must tell the permutations apart
            for p in self.slots["param:perm"]:
                if p != a["param:perm"]:
                    b = dict(a)
                    b["param:perm"] = p
                    if self.apply(b, {}, G) == out:
                        return None
        return G, out


class RotateCorners(_Kind):
    """corner block i -> corner i+1 (cw | ccw), unrotated (oo_bc93ec48)."""
    name = "rotate_corners"
    base = 1.0
    slots = {"verb": ("rotate",), "stop": ("none",), "stop_member": ("none",), "colour": ("own",),
             "param:direction": ("cw", "ccw"), "role:unit": ("corner block",)}

    def pre(self, train):
        return _same_dims(train) and all(i != o for i, o in train)

    def cost(self, a, ctx):
        return self.base + (.01 if a["param:direction"] == "ccw" else 0)

    def apply(self, a, ctx, g):
        H, W = _dims(g)
        cells = _cells(g)
        if not cells:
            return None
        for k in range(1, min(H, W) // 2 + 1):
            if all((r < k or r >= H - k) and (c < k or c >= W - k) for r, c, _ in cells):
                break
        else:
            return None
        org = [(0, 0), (0, W - k), (H - k, W - k), (H - k, 0)]        # clockwise order
        blocks = [[row[c0:c0 + k] for row in g[r0:r0 + k]] for r0, c0 in org]
        st = 1 if a["param:direction"] == "cw" else -1
        out = _new(H, W)
        for i in range(4):
            r0, c0 = org[(i + st) % 4]
            _paste(out, blocks[i], r0, c0)
        return out

    def gen(self, a, tc, rp, pi):
        k = rp.randint(2, 4)
        H, W = rp.randint(2 * k + 1, 2 * k + 6), rp.randint(2 * k + 1, 2 * k + 6)
        org = [(0, 0), (0, W - k), (H - k, W - k), (H - k, 0)]
        G = _new(H, W)
        for i in sorted(rp.sample(range(4), rp.randint(2, 3))):
            S = _shape(rp, k, k, rp.sample(range(1, 10), rp.randint(1, 2)), .6, full=True)
            if S is None:
                return None
            _paste(G, S, *org[i])
        return G, self.apply(a, {}, G)


# ------------------------------------------------------------------------------------------- growth / recurrence


class _Grow(_Kind):
    base = 1.0
    stop_rows = None

    def pre(self, train):
        return all(len(i) == 1 and len(o) > 1 for i, o in train)

    def apply(self, a, ctx, g):
        if len(g) != 1:
            return None
        row = g[0]
        W = len(row)
        nz = [c for c, v in enumerate(row) if v != BG]
        if not nz or nz != list(range(len(nz))) or len({row[c] for c in nz}) != 1:
            return None
        L0, col = len(nz), row[0]
        H = self.rows(W, L0)
        if H < 1 or H > 30:
            return None
        return [[col if c < min(W, L0 + i) else BG for c in range(W)] for i in range(H)]

    def gen(self, a, tc, rp, pi):
        W = rp.randint(6, 16) if self.name == "grow_count" else rp.randint(4, 14)
        L0 = rp.randint(1, W // 2) if self.name == "grow_count" else rp.randint(1, W - 2)
        if pi == 0 and W // 2 == W - L0 + 1:
            return None
        inp = [[rp.randint(1, 9)] * L0 + [BG] * (W - L0)]
        return inp, self.apply(a, {}, inp)


class GrowCount(_Grow):
    """row_i = run(L0 + i), W/2 rows (oo_bbc9ae5d)."""
    name = "grow_count"
    slots = {"verb": ("grow",), "stop": ("count",), "stop_member": ("count:width/2",), "colour": ("own",),
             "role:unit": ("run",)}

    def rows(self, W, L0):
        return W // 2


class GrowBorder(_Grow):
    """row_i = run(L0 + i) until the run fills the width (grp_M066 range: grid edge)."""
    name = "grow_border"
    base = 1.05
    slots = {"verb": ("grow",), "stop": ("border",), "stop_member": ("border:edge",), "colour": ("own",),
             "role:unit": ("run",)}

    def rows(self, W, L0):
        return W - L0 + 1


_ECA = (90, 150, 30, 18, 126, 22, 60, 102)


class RecurRows(_Kind):
    """row[r] = f(row[r-1] neighbourhood), table fitted from the pairs (grp_M084, oo_b5bb5719)."""
    name = "recur_rows"
    base = 1.5
    slots = {"verb": ("recur",), "stop": ("border",), "stop_member": ("border:edge",), "colour": ("table",),
             "param:neigh": ("3-up", "2-diag"), "role:unit": ("seed row",)}

    def _offs(self, a):
        return (-1, 0, 1) if a["param:neigh"] == "3-up" else (-1, 1)

    def pre(self, train):
        if not _same_dims(train):
            return False
        for i, o in train:
            if len(i) < 2 or any(any(row) for row in i[1:]) or len(_colours(i[:1])) != 1 or i == o:
                return False
        return True

    def cost(self, a, ctx):
        return self.base + (.1 if a["param:neigh"] == "3-up" else 0)

    def induce(self, a, train):
        offs = self._offs(a)
        T = {tuple(0 for _ in offs): 0}
        for i, o in train:
            W = len(o[0])
            for r in range(1, len(o)):
                prev = [1 if v != BG else 0 for v in o[r - 1]]
                for c in range(W):
                    pat = tuple(prev[c + d] if 0 <= c + d < W else 0 for d in offs)
                    v = 1 if o[r][c] != BG else 0
                    if T.setdefault(pat, v) != v:
                        return
        yield {"T": T}

    def apply(self, a, ctx, g):
        H, W = _dims(g)
        if H < 2 or any(any(row) for row in g[1:]):
            return None
        cs = _colours(g[:1])
        if len(cs) != 1:
            return None
        col, T, offs = cs[0], ctx["T"], self._offs(a)
        cur = [1 if v != BG else 0 for v in g[0]]
        out = [list(g[0])]
        for r in range(1, H):
            nxt = []
            for c in range(W):
                v = T.get(tuple(cur[c + d] if 0 <= c + d < W else 0 for d in offs))
                if v is None:
                    return None
                nxt.append(v)
            out.append([col if v else BG for v in nxt])
            cur = nxt
        return out

    def task(self, a, rt):
        if a["param:neigh"] == "3-up":
            rule = rt.choice(_ECA)
            T = {(l, m, r): (rule >> (4 * l + 2 * m + r)) & 1 for l in (0, 1) for m in (0, 1) for r in (0, 1)}
        else:
            op = rt.choice(("xor", "or"))
            T = {(l, r): (l ^ r) if op == "xor" else (l | r) for l in (0, 1) for r in (0, 1)}
        return {"T": T}

    def gen(self, a, tc, rp, pi):
        H, W = rp.randint(6, 12), rp.randint(7, 17)
        inp = _new(H, W)
        col = rp.randint(1, 9)
        for c in rp.sample(range(W), rp.randint(1, 3)):
            inp[0][c] = col
        return inp, self.apply(a, {"T": tc["T"]}, inp)


# --------------------------------------------------------------------------------------------------- lattice

KINDS = [TileConst(), TileNcol(), RepeatObject(), RepeatPrefix(), RepeatCount(), CompletePeriodic(),
         LinesSeeded(), ContinueSequence(), RecolourCyclic(), ShiftRows(), PermuteItems(), RotateCorners(),
         GrowCount(), GrowBorder(), RecurRows()]


def _union(slot):
    out = []
    for K in KINDS:
        for v in K.slots.get(slot, ()):
            if v not in out:
                out.append(v)
    return out


def _menu():
    slots = []
    for K in KINDS:
        for s in K.slots:
            if s not in slots:
                slots.append(s)
    members = _union("stop_member")
    return {
        "schema": SCHEMA,
        "verbs": _union("verb"),
        "stop_classes": {c: [m for m in members if m.split(":")[0] == c] for c in _union("stop")},
        "colour_rules": _union("colour"),
        "params": {s.split(":", 1)[1]: _union(s) for s in slots if s.startswith("param:")},
        "roles": {s.split(":", 1)[1]: _union(s) for s in slots if s.startswith("role:")},
        "generators": {K.name: {s: list(v) for s, v in K.slots.items()} for K in KINDS},
        # record verbs (results/o0/v10_records.json, schema CYCLE) -> lattice verb
        "verb_aliases": {"tile": "tile", "stamp": "tile", "repeat": "repeat", "replicate": "repeat",
                         "propagate": "repeat", "print": "print", "extend": "extend|complete",
                         "complete": "complete", "denoise": "complete", "anneal": "complete",
                         "redraw": "complete", "rule": "extend", "graduate": "extend", "fill": "extend",
                         "continue": "continue", "extrapolate": "continue", "recolour": "recolour",
                         "cycle": "recolour", "shift": "shift", "permute": "permute", "rotate": "permute",
                         "copy": "rotate|tile", "grow": "grow", "expand": "grow", "resize": "grow",
                         "recur": "recur"},
    }


MENU = _menu()

# nodes whose generator could not be drawn or recognised in the self-test (binding sets); their
# specialisations are pruned with them.
PRUNED = []


def _compat(node):
    res = []
    for K in KINDS:
        if any(s not in K.slots for s in node if not s.startswith("_")):
            continue
        dom = {}
        for s, vals in K.slots.items():
            if s in node:
                if node[s] not in vals:
                    break
                dom[s] = (node[s],)
            else:
                dom[s] = tuple(vals)
        else:
            al = list(K.raw_assigns(dom))
            if not al:
                continue
            dom = {s: tuple(v for v in dom[s] if any(x[s] == v for x in al)) for s in dom}
            res.append((K, dom))
    return res


def key(node):
    comps = []
    for K, dom in _compat(node):
        restr = ["%s=%s" % (s, "|".join(map(str, dom[s]))) for s in sorted(dom) if tuple(dom[s]) != tuple(K.slots[s])]
        comps.append(K.name + ("(" + ",".join(restr) + ")" if restr else ""))
    return SCHEMA + ":" + ("+".join(sorted(comps)) if comps else "EMPTY")


def _steps():
    st = [("verb", v) for v in MENU["verbs"]]
    st += [("stop", c) for c in MENU["stop_classes"]]
    st += [("stop_member", m) for ms in MENU["stop_classes"].values() for m in ms]
    st += [("colour", c) for c in MENU["colour_rules"]]
    st += [("param:" + p, v) for p, d in MENU["params"].items() for v in d]
    st += [("role:" + r, v) for r, d in MENU["roles"].items() for v in d]
    return st


def _member_legal(node):
    """stop class -> member: the member step needs its class fixed (bound, or implied by the other choices)."""
    m = node.get("stop_member")
    if m is None:
        return True
    cls = m.split(":")[0]
    if node.get("stop") == cls:
        return True
    rest = {s: v for s, v in node.items() if s != "stop_member"}
    comp = _compat(rest)
    return bool(rest) and bool(comp) and all(dom["stop"] == (cls,) for K, dom in comp)


def _pruned(node):
    items = set(node.items())
    return any(set(p.items()) <= items for p in PRUNED)


def depth(node):
    return sum(1 for s in node if not s.startswith("_"))


_NODES = None


def nodes():
    """Every node at depth <= 2 below CYCLE, one per distinct generator key (shallowest kept)."""
    global _NODES
    if _NODES is not None:
        return [dict(n) for n in _NODES]
    out, seen = [], set()

    def add(n):
        if not _member_legal(n) or _pruned(n) or not _compat(n):
            return
        k = key(n)
        if k in seen:
            return
        seen.add(k)
        out.append(n)
    add({})
    st = _steps()
    for s, v in st:
        add({s: v})
    for (s1, v1), (s2, v2) in itertools.combinations(st, 2):
        if s1 != s2:
            add({s1: v1, s2: v2})
    _NODES = out[:400]
    return [dict(n) for n in _NODES]


# ------------------------------------------------------------------------------------------- draw / family


def _ok_pair(pr):
    return isinstance(pr, tuple) and len(pr) == 2 and _ok_grid(pr[0]) and _ok_grid(pr[1]) and pr[0] != pr[1]


def draw(node, seed):
    """Deterministic synthetic pair; seeds 4t..4t+3 share task t's generator, parameters and literal colours."""
    comp = _compat(node)
    if not comp:
        return None
    k = key(node)
    t, pi = divmod(int(seed), 4)
    K, dom = comp[zlib.crc32(("%s|%d" % (k, t)).encode()) % len(comp)]
    rt = random.Random("%s|task|%d" % (k, t))
    al = list(K.assigns(dom))
    a = al[rt.randrange(len(al))]
    tc = K.task(a, rt)
    for att in range(80):
        rp = random.Random("%s|pair|%d|%d" % (k, seed, att))
        try:
            pr = K.gen(a, tc, rp, pi)
        except Exception:
            pr = None
        if pr is not None and _ok_pair(pr):
            return pr
    return None


def _norm(train):
    out = []
    for p in train:
        if isinstance(p, dict):
            out.append((p["input"], p["output"]))
        else:
            out.append((p[0], p[1]))
    return out


def family(node):
    """fam(train) yields (name, cost, fn), cheapest first; every program reproduces every training pair."""
    comp = _compat(node)

    def fam(train):
        tr = _norm(train)
        if not tr or not all(_ok_grid(i, 30) and _ok_grid(o, 30) for i, o in tr):
            return
        progs = []
        for K, dom in comp:
            for name, cost, fn in K.fit(tr, dom):
                progs.append((cost, len(progs), name, fn))
        progs.sort(key=lambda x: (x[0], x[1]))
        seen = set()
        for cost, _, name, fn in progs:
            if name not in seen:
                seen.add(name)
                yield (name, cost, fn)
    return fam
