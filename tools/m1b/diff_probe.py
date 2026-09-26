"""Reviewer aid: which candidate differentiators separate prior-indistinguishable conflicting cases?"""
import json, collections, sys
from occupancy import *
def extra(nodes, grid):
    H, W = len(grid), len(grid[0])
    sizes = [len(n["pix"]) for n in nodes]; colors = [n["color"] for n in nodes]
    shapes = [norm_shape(n["pix"]) for n in nodes]; boxes = [bbox(n["pix"]) for n in nodes]
    inner = [interior(n["pix"]) for n in nodes]
    ranks = sorted(set(sizes), reverse=True)
    owner = {p: i for i, n in enumerate(nodes) for p in n["pix"]}
    res = []
    for i, n in enumerate(nodes):
        a = set(); r0, c0, r1, c1 = boxes[i]
        a.add(f"D1:size_rank={ranks.index(sizes[i])}" if ranks.index(sizes[i]) < 4 else "D1:size_rank>3")
        a.add(f"D1:size_rank_asc={sorted(set(sizes)).index(sizes[i])}")
        same = [j for j in range(len(nodes)) if colors[j] == colors[i]]
        a.add(f"D2:n_same_color={min(len(same),5)}")
        for j in range(len(nodes)):
            if j != i and shapes[j] == shapes[i] and colors[j] is not None: a.add(f"D3:shape_as_color={colors[j]}")
        touch = {owner[(r+dr, c+dc)] for r, c in n["pix"] for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)) if owner.get((r+dr, c+dc), i) != i}
        a.add(f"D4:n_touch={min(len(touch),4)}")
        a.add("D5:top_half" if (r0+r1)/2 < H/2 else "D5:bottom_half"); a.add("D5:left_half" if (c0+c1)/2 < W/2 else "D5:right_half")
        a.add(f"D8:height={r1-r0+1}"); a.add(f"D8:width={c1-c0+1}")
        for j in range(len(nodes)):
            if j != i and nodes[j]["pix"] <= inner[i] and colors[j] is not None: a.add(f"D7:contains_color={colors[j]}")
            if j != i and colors[j] is not None and not (boxes[j][2] < r0 or boxes[j][0] > r1): a.add(f"D9:row_with_color={colors[j]}")
            if j != i and colors[j] is not None and not (boxes[j][3] < c0 or boxes[j][1] > c1): a.add(f"D9:col_with_color={colors[j]}")
        if sizes[i] == max(sizes[j] for j in same): a.add("D10:largest_of_its_color")
        if sizes[i] == min(sizes[j] for j in same): a.add("D10:smallest_of_its_color")
        a.add(f"D11:n_cells_of_color_in_bbox={sum(1 for r in range(r0,r1+1) for c in range(c0,c1+1) if grid[r][c]==colors[i])==sizes[i]}")
        res.append(a)
    return res
ch = json.load(open(sys.argv[1])); rows = [json.loads(l) for l in open(sys.argv[2])]
keys = set(open(sys.argv[3]).read().replace(',', '\n').split()) if len(sys.argv) > 3 else None
fam = collections.Counter(); tasks_resolved = collections.defaultdict(set); ntasks = 0
for r in rows:
    if keys and r["task"] not in keys: continue
    st = r.get("statuses", {})
    if r.get("occupied") or "not_occupied" not in st.values(): continue
    ab = next(a for a, s in st.items() if s == "not_occupied")
    cases = []
    try:
        for p in ch[r["task"]]["train"]:
            nodes, bg, at, src, others = prepare(p["input"], ab)
            ex = extra(nodes, p["input"])
            for n, a, s, o, e in zip(nodes, at, src, others, ex):
                cases.append((frozenset(a), candidate_labels(n, s, p["input"], p["output"], bg, o), e))
    except Exception: continue
    conf = [(x, y) for i, x in enumerate(cases) for y in cases[i+1:] if x[0] == y[0] and not (x[1] & y[1])]
    if not conf: continue
    ntasks += 1
    for f in "D1 D2 D3 D4 D5 D7 D8 D9 D10 D11".split():
        sep = sum(1 for x, y in conf if {a for a in x[2] if a.startswith(f+":")} != {a for a in y[2] if a.startswith(f+":")})
        if sep == len(conf): tasks_resolved[f].add(r["task"])
print("tasks with prior-indistinguishable conflicts:", ntasks)
for f, s in sorted(tasks_resolved.items(), key=lambda kv: -len(kv[1])): print(f, len(s))
