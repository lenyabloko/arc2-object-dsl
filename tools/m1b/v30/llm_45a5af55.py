"""Family for 45a5af55: geometry:revolution (surface of revolution / lathe turning).

The input is a striped 1-D *profile*: every row (or every column) is one uniform colour, read from the outer
edge towards the axis.  The output revolves that profile around a central axis under the square (Chebyshev)
metric, so profile entry k becomes the k-th concentric square ring:
    out[i][j] = profile[min(i, j, N-1-i, N-1-j)]
with N = 2*len(profile) (axis between pixels) or 2*len(profile)-1 (axis through the centre pixel).

Parameters (small finite domains, all induced from training):
    orient  in {rows, cols}   - which way the profile stripes run
    outer   in {first, last}  - which end of the profile is the rim
    trim    in {0, 1, 2}      - stripes beyond the axis that are not revolved (the axis position)
    parity  in {even, odd}    - axis between pixels or through a pixel
No colours, sizes or coordinates are stored.
"""


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _profile(grid, orient):
    """Colours of the stripes, or None if the grid is not striped along `orient`."""
    g = grid if orient == 'rows' else _transpose(grid)
    prof = []
    for r in g:
        if not r or any(c != r[0] for c in r):
            return None
        prof.append(r[0])
    return prof


def _revolve(prof, parity):
    L = len(prof)
    if L == 0:
        return None
    N = 2 * L if parity == 'even' else 2 * L - 1
    return [[prof[min(i, j, N - 1 - i, N - 1 - j)] for j in range(N)] for i in range(N)]


def _make(orient, outer, trim, parity):
    def fn(grid):
        prof = _profile(grid, orient)
        if prof is None:
            return None
        if outer == 'last':
            prof = prof[::-1]
        if trim:
            prof = prof[:-trim]
        return _revolve(prof, parity)
    return fn


def fam_revolution(train):
    seen = set()
    for orient in ('rows', 'cols'):
        if not all(_profile(p['input'], orient) is not None for p in train):
            continue
        for outer in ('first', 'last'):
            for trim in (0, 1, 2):
                for parity in ('even', 'odd'):
                    fn = _make(orient, outer, trim, parity)
                    if all(fn(p['input']) == p['output'] for p in train):
                        key = tuple(str(fn(p['input'])) for p in train)
                        if key in seen:
                            continue
                        seen.add(key)
                        yield ('geometry:revolution[orient=%s,outer=%s,trim=%d,parity=%s]'
                               % (orient, outer, trim, parity), 3, fn)


FAMILIES = (fam_revolution,)
