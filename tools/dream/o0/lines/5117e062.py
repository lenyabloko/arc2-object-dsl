"""Reviewer line for 5117e062 (Len): "extract the shape with center pixel colored or decorated in the center".
Implemented literally, test-blind (train pairs only):
  generator      among the shapes (connected non-background objects, multicolour), pick the one whose centre is marked
                 (a centre cell of its bounding box carries a different colour than the shape's body) and output that
                 shape cropped to its bounding box; the centre mark is recoloured to the body colour (or kept / erased /
                 used to paint the shape, whichever the training pairs select)
  stop           the crop is the selected shape's bounding box
  params         conn ∈ {8, 4} · sel ∈ {centre_mark, any_mark, centre_filled} · crop ∈ {shape, raw}
                 · mark ∈ {to_body, keep, to_bg, paint}
  participants   background = most common input colour; shapes = connected components of non-background cells (any
                 colours); body colour = the shape's most frequent colour; marks = its other-coloured cells; centre
                 cells = the middle row(s) x middle column(s) of the shape's bounding box
  preconditions  every training input has exactly one selected shape and every training output equals its rendering"""
from collections import Counter

CARD = "5117e062"
LINE = "extract the shape with center pixel colored or decorated in the center"
READING = {
    "generator": "Find the one shape whose centre is marked (the middle cell of its bounding box has a different colour "
                 "from the shape's body) and output that shape cropped to its bounding box, with the centre mark "
                 "recoloured to the body colour.",
    "stop": "The output is exactly the selected shape's bounding box.",
    "params": "conn ∈ {8, 4} · sel ∈ {centre_mark, any_mark, centre_filled} · crop ∈ {shape, raw} · "
              "mark ∈ {to_body, keep, to_bg, paint}",
    "participants": "Background = most common input colour; shapes = connected components of non-background cells "
                    "(multicolour); body colour = the shape's most frequent colour; mark = its other-coloured cell(s); "
                    "centre = middle row(s) x middle column(s) of the shape's bounding box.",
    "preconditions": "Each training input has exactly one shape passing the selector, and each training output is that "
                     "shape's bounding-box crop (output smaller than input).",
}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _shapes(g, bg, conn):
    H, W = len(g), len(g[0])
    steps = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn == 8:
        steps += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    seen = [[False] * W for _ in range(H)]
    out = []
    for y in range(H):
        for x in range(W):
            if seen[y][x] or g[y][x] == bg:
                continue
            seen[y][x] = True
            stack, cells = [(y, x)], []
            while stack:
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for dy, dx in steps:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            out.append(_describe(g, sorted(cells)))
    return out


def _describe(g, cells):
    ys = [c[0] for c in cells]; xs = [c[1] for c in cells]
    r0, r1, c0, c1 = min(ys), max(ys), min(xs), max(xs)
    h, w = r1 - r0 + 1, c1 - c0 + 1
    centre = {(r0 + (h - 1) // 2, c0 + (w - 1) // 2), (r0 + h // 2, c0 + (w - 1) // 2),
              (r0 + (h - 1) // 2, c0 + w // 2), (r0 + h // 2, c0 + w // 2)}
    cnt = Counter(g[y][x] for y, x in cells)
    cset = set(cells)
    centre_cols = {g[y][x] for y, x in centre if (y, x) in cset}
    # body = most frequent colour; ties prefer a colour not on the centre, then the smaller value
    body = sorted(cnt, key=lambda c: (-cnt[c], c in centre_cols, c))[0]
    marks = [(y, x) for y, x in cells if g[y][x] != body]
    mcnt = Counter(g[y][x] for y, x in marks)
    mark_col = sorted(mcnt, key=lambda c: (-mcnt[c], c))[0] if mcnt else None
    return {"cells": cells, "cset": cset, "box": (r0, r1, c0, c1), "centre": centre, "body": body,
            "marks": set(marks), "mark_col": mark_col, "odd": h % 2 == 1 and w % 2 == 1}


def _selected(s, sel):
    if sel == "centre_mark":
        return bool(s["marks"] & s["centre"])
    if sel == "any_mark":
        return bool(s["marks"])
    if sel == "centre_filled":
        return s["odd"] and bool(s["centre"] & s["cset"])
    return False


def _pick(g, conn, sel, strict):
    bg = _bg(g)
    cands = [s for s in _shapes(g, bg, conn) if _selected(s, sel)]
    if strict and len(cands) != 1:
        return None, bg
    if not cands:
        return None, bg
    cands.sort(key=lambda s: (-len(s["cells"]), s["box"]))        # deterministic fallback on ambiguous test inputs
    return cands[0], bg


def _render(g, s, bg, crop, mark):
    r0, r1, c0, c1 = s["box"]
    out = []
    for y in range(r0, r1 + 1):
        row = []
        for x in range(c0, c1 + 1):
            inside = (y, x) in s["cset"]
            v = g[y][x] if (inside or crop == "raw") else bg
            if inside:
                if mark == "paint":
                    v = s["mark_col"]
                elif (y, x) in s["marks"]:
                    v = s["body"] if mark == "to_body" else (bg if mark == "to_bg" else v)
            row.append(v)
        out.append(row)
    return out


def _program(conn, sel, crop, mark, strict=False):
    def fn(g):
        s, bg = _pick(g, conn, sel, strict)
        if s is None:
            raise ValueError("no shape passes the selector")
        return _render(g, s, bg, crop, mark)
    return fn


CONNS = [(8, 0), (4, 1)]
SELS = [("centre_mark", 0), ("any_mark", 1), ("centre_filled", 1)]
CROPS = [("shape", 0), ("raw", 1)]
MARKS = [("to_body", 0), ("keep", 0), ("to_bg", 1), ("paint", 1)]


def fam(train):
    if not train:
        return
    for p in train:                                  # precondition: output is a strict sub-size crop
        a, b = p["input"], p["output"]
        if not b or not b[0] or len(b) > len(a) or len(b[0]) > len(a[0]) or (len(b) == len(a) and len(b[0]) == len(a[0])):
            return
    found = []
    for conn, kc in CONNS:
        for sel, ks in SELS:
            picks = []
            for p in train:
                s, bg = _pick(p["input"], conn, sel, True)
                if s is None:
                    break
                picks.append((s, bg))
            if len(picks) != len(train):
                continue
            for crop, kr in CROPS:
                for mark, km in MARKS:
                    if mark == "paint" and any(s["mark_col"] is None for s, _ in picks):
                        continue
                    if all(_render(p["input"], s, bg, crop, mark) == p["output"] for p, (s, bg) in zip(train, picks)):
                        found.append((kc + ks + kr + km, conn, sel, crop, mark))
    found.sort(key=lambda t: t[0])
    for cost, conn, sel, crop, mark in found:
        yield f"centre_marked_shape[conn={conn},sel={sel},crop={crop},mark={mark}]", cost, _program(conn, sel, crop, mark)


FAMILIES = [fam]
