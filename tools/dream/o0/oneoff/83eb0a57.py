CARD = "83eb0a57"
READING = "The largest patterned rectangle is the board; every smaller piece is pasted onto it (largest first) at the unique offset where its marker-coloured cells coincide exactly with the board's marker cells, and the board is output."

from collections import Counter


def _objects(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    objs = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            stack = [(r, c)]
            seen[r][c] = True
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            r0 = min(y for y, _ in cells); r1 = max(y for y, _ in cells)
            c0 = min(x for _, x in cells); c1 = max(x for _, x in cells)
            sub = [g[y][c0:c1 + 1] for y in range(r0, r1 + 1)]
            objs.append(sub)
    return objs


def _solve(g, against_composite):
    bg = Counter(v for row in g for v in row).most_common(1)[0][0]
    objs = _objects(g, bg)
    if not objs:
        return [row[:] for row in g]
    objs.sort(key=lambda o: -(len(o) * len(o[0])))
    board = objs[0]
    H, W = len(board), len(board[0])
    cnt = Counter(v for row in board for v in row)
    main = cnt.most_common(1)[0][0]
    keys = set(cnt) - {main}
    out = [row[:] for row in board]
    for piece in objs[1:]:
        h, w = len(piece), len(piece[0])
        if h > H or w > W:
            continue
        pk = [(y, x) for y in range(h) for x in range(w) if piece[y][x] in keys]
        if not pk:
            continue
        ref = out if against_composite else board
        hits = []
        for oy in range(H - h + 1):
            for ox in range(W - w + 1):
                good = True
                for y in range(h):
                    for x in range(w):
                        if (piece[y][x] in keys) != (ref[oy + y][ox + x] in keys):
                            good = False
                            break
                        if piece[y][x] in keys and piece[y][x] != ref[oy + y][ox + x]:
                            good = False
                            break
                    if not good:
                        break
                if good:
                    hits.append((oy, ox))
        if len(hits) >= 1:
            oy, ox = hits[0]
            for y in range(h):
                for x in range(w):
                    out[oy + y][ox + x] = piece[y][x]
    return out


def fam(train):
    for name, cost, comp in (("board_paste", 1, False), ("board_paste_comp", 2, True)):
        fn = (lambda comp: (lambda g: _solve(g, comp)))(comp)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
