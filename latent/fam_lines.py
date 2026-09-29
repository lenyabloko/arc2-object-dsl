"""Own primitives (no Codex code): edge-marker projection with combination."""
import sys; sys.path.insert(0,'/home/claude/work/widen')
import gdsl
from gdsl import H, W, bg_of

EDGES=('top','bottom','left','right')
def edge_marks(g,bg,e):
    h,w=H(g),W(g)
    if e=='top': return {c for c in range(w) if g[0][c]!=bg}
    if e=='bottom': return {c for c in range(w) if g[h-1][c]!=bg}
    if e=='left': return {r for r in range(h) if g[r][0]!=bg}
    return {r for r in range(h) if g[r][w-1]!=bg}
def edge_colour(g,bg,e,i):
    h,w=H(g),W(g)
    return {'top':g[0][i] if e=='top' else None,'bottom':g[h-1][i] if e=='bottom' else None,
            'left':g[i][0] if e=='left' else None,'right':g[i][w-1] if e=='right' else None}[e]

def added_colour(train):
    """The single colour painted onto background cells in every pair (role: new paint)."""
    cs=None
    for p in train:
        i,o=p['input'],p['output']
        if (H(i),W(i))!=(H(o),W(o)): return None
        bg=bg_of(i)
        ch={o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x]!=o[y][x] and i[y][x]==bg}
        cs=ch if cs is None else cs|ch
    return next(iter(cs)) if cs and len(cs)==1 else None

def project(g,rows_from,cols_from,op,paint):
    bg=bg_of(g);h,w=H(g),W(g)
    R=set().union(*[edge_marks(g,bg,e) for e in rows_from]) if rows_from else set()
    C=set().union(*[edge_marks(g,bg,e) for e in cols_from]) if cols_from else set()
    if not R and not C: return None
    used_r={0} if 'top' in cols_from else set(); used_r|={h-1} if 'bottom' in cols_from else set()
    used_c={0} if 'left' in rows_from else set(); used_c|={w-1} if 'right' in rows_from else set()
    out=[r[:] for r in g]
    for y in range(h):
        if y in used_r: continue
        for x in range(w):
            if x in used_c or g[y][x]!=bg: continue
            a,b=y in R,x in C
            hit={'and':a and b,'or':a or b,'xor':a!=b}[op]
            if hit: out[y][x]=paint
    return out

def fam_edge_projection(train):
    i0,o0=train[0]['input'],train[0]['output']
    if (H(i0),W(i0))!=(H(o0),W(o0)): return
    paint=added_colour(train)
    if paint is None: return
    # which edges carry markers in every training input (role: marker edges)
    def edges_with(g): bg=bg_of(g); return {e for e in EDGES if edge_marks(g,bg,e) and len(edge_marks(g,bg,e))<(W(g) if e in('top','bottom') else H(g))}
    common=None
    for p in train:
        es=edges_with(p['input']); common=es if common is None else common&es
    if not common: return
    rowE=[e for e in ('left','right') if e in common]; colE=[e for e in ('top','bottom') if e in common]
    for op in ('and','or','xor'):
        if rowE and colE:
            yield (f"project:{op}[rows={'+'.join(rowE)},cols={'+'.join(colE)}]",4,lambda g,rowE=rowE,colE=colE,op=op:project(g,rowE,colE,op,paint))
    if rowE: yield (f"project:rows[{'+'.join(rowE)}]",4,lambda g,rowE=rowE:project(g,rowE,[], 'or',paint))
    if colE: yield (f"project:cols[{'+'.join(colE)}]",4,lambda g,colE=colE:project(g,[],colE,'or',paint))

FAMILIES=(fam_edge_projection,)
