"""RCC-8 EC (externally connected) on cell sets: x and y share no cell and some cell of x is a 4-neighbour of a cell
of y. Randell, Cui & Cohn (1992), region connection calculus; grid reading: connection = 4-adjacency."""
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def ec(grid, inds, bg):
    owner = {}
    for i, x in enumerate(inds):
        for p in x["pix"]: owner.setdefault(p, []).append(i)
    out = {}
    for i, x in enumerate(inds):
        s = set()
        for (y, c) in x["pix"]:
            for dy, dx in N4:
                for j in owner.get((y + dy, c + dx), ()):
                    if j != i and not (inds[j]["pix"] & x["pix"]): s.add(j)
        if s: out[i] = s
    return out


ITEM = {"name": "rcc8_EC", "layer": 1, "iri": "qsr:EC", "kind": "role", "params": {}, "subsumes": [],
        "definition": "x and y are externally connected: disjoint cell sets with at least one 4-adjacent pair of cells.",
        "fn": ec}
