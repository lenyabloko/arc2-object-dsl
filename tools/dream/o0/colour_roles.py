"""Declared colour roles (Fable v11 F-i / D38 / G68, Oct 1 2026).

T65 found that the bindings that transferred were colour roles. v11 promotes three of them to first-class vocabulary:
every generator's colour parameter must be one of these roles or a role-bound value (the colour of a named
participant: anchor, marker, container, the object itself ...), never a literal.

  background(g)            the most frequent colour of grid g; ties -> the colour more frequent over the training
                           inputs (when a train list is given), then the lower colour number
  rank_colour(g, k, bg)    ink colours of g (all colours except bg) ordered by cell count, descending, ties by lower
                           colour number; k = 1, 2, ... counts from the most frequent, k = -1, -2, ... from the least;
                           None when g has fewer than |k| ink colours
  novel_colour(train)      the one colour that appears in every training output and in none of the corresponding
                           inputs; None if no such single colour exists. It is learned from the training pairs (a test
                           input cannot show it), so at prediction time it is a constant fixed by the role.

Also role-bound helpers used by several families:
  input_colours(train)     colours present in every training input
  vanishing_colours(train) colours present in every training input and absent from every training output

Deterministic; no task ids; pure functions of the grids.
"""
from collections import Counter

ROLES = ("background", "rank_colour", "novel_colour")
RANKS = (1, 2, 3, -1, -2)


def background(g, train=None):
    c = Counter(v for r in g for v in r)
    if train:
        tc = Counter(v for p in train for r in p["input"] for v in r)
        return max(c, key=lambda k: (c[k], tc.get(k, 0), -k))
    return max(c, key=lambda k: (c[k], -k))


def rank_colour(g, k, bg=None):
    if bg is None:
        bg = background(g)
    tal = Counter(v for r in g for v in r if v != bg)
    order = sorted(tal, key=lambda x: (-tal[x], x))
    i = k - 1 if k > 0 else len(order) + k
    return order[i] if 0 <= i < len(order) else None


def novel_colour(train):
    cand = None
    for p in train:
        cin = {v for r in p["input"] for v in r}
        new = {v for r in p["output"] for v in r} - cin
        cand = new if cand is None else cand & new
        if not cand:
            return None
    return next(iter(cand)) if cand and len(cand) == 1 else None


def input_colours(train):
    s = None
    for p in train:
        c = {v for r in p["input"] for v in r}
        s = c if s is None else s & c
    return s or set()


def vanishing_colours(train):
    out = set()
    for p in train:
        out |= {v for r in p["output"] for v in r}
    return input_colours(train) - out


def resolve(role, g, train=None, bg=None):
    """role: ('background',) | ('rank', k) | ('novel',)  ->  a colour or None"""
    if role[0] == "background":
        return background(g, train)
    if role[0] == "rank":
        return rank_colour(g, role[1], bg if bg is not None else background(g, train))
    if role[0] == "novel":
        return novel_colour(train) if train else None
    raise ValueError(role)


def all_roles():
    return [("background",), ("novel",)] + [("rank", k) for k in RANKS]
