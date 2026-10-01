CARD = "8719f442"
READING = ("The pattern is enlarged so each coloured cell becomes a solid pattern-sized block in the "
           "middle of a ring one block wide, and a copy of the original pattern is placed in every "
           "ring position that touches a solid block edge-to-edge.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(bg_mode):
    def fn(g):
        h, w = len(g), len(g[0])
        bg = 0 if bg_mode == "zero" else _bg(g)
        MH, MW = h + 2, w + 2
        out = [[bg] * (MW * w) for _ in range(MH * h)]
        filled = set()
        for i in range(h):
            for j in range(w):
                if g[i][j] != bg:
                    filled.add((i + 1, j + 1))
                    for a in range(h):
                        for b in range(w):
                            out[(i + 1) * h + a][(j + 1) * w + b] = g[i][j]
        ring = set()
        for (I, J) in filled:
            for dI, dJ in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                X, Y = I + dI, J + dJ
                if 0 <= X < MH and 0 <= Y < MW and (X in (0, MH - 1) or Y in (0, MW - 1)):
                    ring.add((X, Y))
        for (X, Y) in ring:
            for a in range(h):
                for b in range(w):
                    out[X * h + a][Y * w + b] = g[a][b]
        return out
    return fn


def fam(train):
    for name, cost, mode in (("enlarge_with_pattern_ring", 1, "zero"),
                             ("enlarge_with_pattern_ring_majbg", 2, "maj")):
        fn = _make(mode)
        ok = True
        for p in train:
            try:
                if fn(p["input"]) != p["output"]:
                    ok = False
                    break
            except Exception:
                ok = False
                break
        if ok:
            yield (name, cost, fn)
            return


FAMILIES = [fam]
