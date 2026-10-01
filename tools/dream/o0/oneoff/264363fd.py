CARD = "264363fd"
READING = "A small template in the background shows a marker's decoration; erase it, and at every marker inside the big rectangles stamp the template's 3x3 core and, along each axis where the template has arms, draw a line of the arm colour across the whole rectangle."


def _border_bg(g):
    H, W = len(g), len(g[0])
    cnt = {}
    for r in range(H):
        for c in range(W):
            if r in (0, H - 1) or c in (0, W - 1):
                cnt[g[r][c]] = cnt.get(g[r][c], 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps8(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and not seen[r][c]:
                st = [(r, c)]
                seen[r][c] = True
                cells = []
                while st:
                    y, x = st.pop()
                    cells.append((y, x))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                                seen[ny][nx] = True
                                st.append((ny, nx))
                out.append(cells)
    return out


def _solve(g):
    H, W = len(g), len(g[0])
    bg = _border_bg(g)
    cnt = {}
    for row in g:
        for v in row:
            if v != bg:
                cnt[v] = cnt.get(v, 0) + 1
    rect = max(cnt, key=lambda k: cnt[k])
    comps = _comps8(g, bg)
    rects = [cs for cs in comps if any(g[r][c] == rect for r, c in cs)]
    temps = [cs for cs in comps if not any(g[r][c] == rect for r, c in cs)]
    mcnt = {}
    markers = []
    for cs in rects:
        for r, c in cs:
            if g[r][c] != rect:
                markers.append((r, c))
                mcnt[g[r][c]] = mcnt.get(g[r][c], 0) + 1
    out = [row[:] for row in g]
    if not temps or not mcnt:
        return out
    mcol = max(mcnt, key=lambda k: mcnt[k])
    temp = max(temps, key=len)
    centers = [(r, c) for r, c in temp if g[r][c] == mcol]
    if not centers:
        return out
    tr = sum(r for r, _ in temp) / len(temp)
    tc = sum(c for _, c in temp) / len(temp)
    cr, cc = min(centers, key=lambda p: ((p[0] - tr) ** 2 + (p[1] - tc) ** 2, p))
    T = {(r - cr, c - cc): g[r][c] for r, c in temp}
    for r, c in temp:
        out[r][c] = bg
    lines = []
    for axis, far in (("v", ((2, 0), (-2, 0))), ("h", ((0, 2), (0, -2)))):
        arm = [T[o] for o in far if o in T]
        if arm:
            lines.append((axis, arm[0]))
    marks = [(r, c) for r, c in markers if g[r][c] == mcol]
    mset = set(markers)
    for r, c in marks:
        for axis, col in lines:
            dirs = ((1, 0), (-1, 0)) if axis == "v" else ((0, 1), (0, -1))
            for dy, dx in dirs:
                y, x = r + dy, c + dx
                while 0 <= y < H and 0 <= x < W and g[y][x] != bg:
                    if (y, x) not in mset:
                        out[y][x] = col
                    y += dy
                    x += dx
    for r, c in marks:
        for (dy, dx), v in T.items():
            if max(abs(dy), abs(dx)) > 1:
                continue
            y, x = r + dy, c + dx
            if 0 <= y < H and 0 <= x < W and g[y][x] != bg:
                out[y][x] = v
    return out


def fam(train):
    try:
        if all(_solve(p["input"]) == p["output"] for p in train):
            yield ("template_stamp_lines", 1, _solve)
    except Exception:
        pass


FAMILIES = [fam]
