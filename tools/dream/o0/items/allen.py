"""Allen's interval relations (Allen 1983, "Maintaining knowledge about temporal intervals") on the row or column
projection of individuals. The projection of an individual on an axis is the closed integer interval [min, max] of
its cells' row (axis=row) or column (axis=col) indices, read as the half-open real interval [min, max + 1) covered by
those unit cells. Allen's continuous definitions then give these discrete readings (x = first argument, y = second):
  before    x.max + 1 <  y.min                       (gap of at least one index)
  meets     x.max + 1 == y.min                       (adjacent, no gap, no shared index)
  overlaps  x.min < y.min <= x.max < y.max
  during    y.min < x.min and x.max < y.max          (strictly inside on both ends)
  starts    x.min == y.min and x.max < y.max
  finishes  x.max == y.max and x.min > y.min
  equals    x.min == y.min and x.max == y.max        (irreflexive here: x != y as individuals)
Only the 7 base relations are declared; the 6 inverses are the same relation with the arguments swapped.
The second argument ranges over objects only (README); the first over all individuals (objects and background cells).
Cost: intervals are computed once per call and individuals are grouped by interval, so each distinct interval is
answered once with sorted-list range queries over the distinct object intervals (bisect), then copied to its members."""
from bisect import bisect_left, bisect_right

RELS = ("before", "meets", "overlaps", "during", "starts", "finishes", "equals")


def _interval(pix, k):
    if len(pix) == 1:
        v = next(iter(pix))[k]
        return v, v
    vs = [p[k] for p in pix]
    return min(vs), max(vs)


def allen(grid, inds, bg, axis="row", rel="before"):
    k = 0 if axis == "row" else 1
    groups = {}                                   # interval -> [i, ...] over all individuals
    ogroups = {}                                  # interval -> frozenset(object j) over objects (second argument)
    for i, x in enumerate(inds):
        if not x["pix"]:
            continue
        iv = _interval(x["pix"], k)
        groups.setdefault(iv, []).append(i)
        if x.get("kind") == "object":
            ogroups.setdefault(iv, set()).add(i)
    if not ogroups:
        return {}
    okeys = sorted(ogroups)                       # sorted by (min, max)
    omins = [c for c, _ in okeys]
    by_max = sorted(okeys, key=lambda t: (t[1], t[0]))
    omaxs = [d for _, d in by_max]

    def query(a, b):
        """Object intervals (c, d) with (a, b) rel (c, d)."""
        if rel == "before":                      # c >= b + 2
            return okeys[bisect_left(omins, b + 2):]
        if rel == "meets":                       # c == b + 1
            return okeys[bisect_left(omins, b + 1):bisect_right(omins, b + 1)]
        if rel == "overlaps":                    # a < c <= b and d > b
            return [t for t in okeys[bisect_right(omins, a):bisect_right(omins, b)] if t[1] > b]
        if rel == "during":                      # c < a and d > b
            return [t for t in okeys[:bisect_left(omins, a)] if t[1] > b]
        if rel == "starts":                      # c == a and d > b
            return [t for t in okeys[bisect_left(omins, a):bisect_right(omins, a)] if t[1] > b]
        if rel == "finishes":                    # d == b and c < a
            return [t for t in by_max[bisect_left(omaxs, b):bisect_right(omaxs, b)] if t[0] < a]
        if rel == "equals":
            return [(a, b)] if (a, b) in ogroups else []
        raise ValueError(rel)

    out = {}
    for iv in sorted(groups):
        hits = query(*iv)
        if not hits:
            continue
        js = set()
        for t in hits:
            js |= ogroups[t]
        for i in groups[iv]:
            s = js - {i} if i in js else set(js)  # only 'equals' can contain i itself
            if s:
                out[i] = s
    return out


ITEM = {"name": "allen", "layer": 1, "iri": "allen:interval_relation", "kind": "role",
        "params": {"axis": ["row", "col"], "rel": list(RELS)}, "subsumes": [],
        "definition": ("x R y for Allen's (1983) base interval relation R in {before, meets, overlaps, during, starts, "
                       "finishes, equals} between the projections of x and y on the row (or column) axis; projection = "
                       "closed integer interval [min, max] of the individual's cell row (or column) indices, read as the "
                       "half-open interval [min, max+1). Discrete readings: before x.max+1 < y.min; meets x.max+1 == "
                       "y.min; overlaps x.min < y.min <= x.max < y.max; during y.min < x.min and x.max < y.max; starts "
                       "x.min == y.min and x.max < y.max; finishes x.max == y.max and x.min > y.min; equals same "
                       "interval (x != y). Inverses are the same relation with arguments swapped. y ranges over objects."),
        "fn": allen}
