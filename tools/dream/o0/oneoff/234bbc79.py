CARD = "234bbc79"
READING = ("The pieces are chained left to right: each piece is moved so its left connector cell sits right next to "
           "the previous piece's right connector in the same row, connectors take their piece's colour, and the width shrinks to fit.")
from collections import Counter


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            st = [(r, c)]
            seen[r][c] = True
            cells = []
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        st.append((ny, nx))
            out.append(cells)
    return out


def _params(train):
    bgc = Counter()
    gone = None
    for p in train:
        for r in p["input"]:
            bgc.update(r)
        a = {v for r in p["input"] for v in r}
        b = {v for r in p["output"] for v in r}
        gone = (a - b) if gone is None else (gone & (a - b))
    bg = bgc.most_common(1)[0][0]
    if not gone or len(gone) != 1:
        return None
    return bg, gone.pop()


def _make(bg, conn):
    def fn(g):
        H = len(g)
        pieces = []
        for cells in _comps(g, bg):
            body = [g[y][x] for y, x in cells if g[y][x] != conn]
            colour = Counter(body).most_common(1)[0][0] if body else conn
            cons = sorted([(x, y) for y, x in cells if g[y][x] == conn])
            pieces.append((min(x for _, x in cells), cells, colour, cons))
        pieces.sort(key=lambda p: p[0])
        placed = {}
        prev_right = None
        for i, (_, cells, colour, cons) in enumerate(pieces):
            if i == 0:
                dy, dx = 0, 0
            else:
                lx, ly = cons[0]
                dy, dx = prev_right[0] - ly, prev_right[1] + 1 - lx
            for y, x in cells:
                ny, nx = y + dy, x + dx
                if not (0 <= ny < H) or nx < 0:
                    raise ValueError("off grid")
                placed[(ny, nx)] = colour
            if cons:
                rx, ry = cons[-1]
                prev_right = (ry + dy, rx + dx)
        W = max(x for _, x in placed) + 1
        out = [[bg] * W for _ in range(H)]
        for (y, x), v in placed.items():
            out[y][x] = v
        return out
    return fn


def fam(train):
    pr = _params(train)
    if pr is None:
        return
    fn = _make(*pr)
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("chain_pieces_by_connectors", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
