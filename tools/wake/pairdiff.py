"""Mechanism-level spectrum features computed from training pairs only (generic detectors).
Each feature is averaged over a task's training pairs -> a task spectrum vector."""
import sys,collections
sys.path.insert(0,'/home/claude/work/widen'); import gdsl
from gdsl import H,W,bg_of,objects

def shape_key(cells):
    y0=min(y for y,x in cells);x0=min(x for y,x in cells); return tuple(sorted((y-y0,x-x0) for y,x in cells))

def pair_feats(i,o):
    f={}
    hi,wi,ho,wo=H(i),W(i),H(o),W(o); bg=bg_of(i)
    same=(hi,wi)==(ho,wo); f['same_size']=same
    f['out_smaller']=ho*wo<hi*wi; f['out_larger']=ho*wo>hi*wi
    f['out_multiple']=(ho%hi==0 and wo%wi==0 and not same)
    f['out_divisor']=(hi%ho==0 and wi%wo==0 and not same)
    f['out_1x1']=ho*wo==1; f['out_tiny']=ho*wo<=9
    ci={v for r in i for v in r}; co={v for r in o for v in r}
    f['new_colour']=bool(co-ci); f['lost_colour']=bool(ci-co); f['n_colours_in']=min(len(ci),10)/10
    fg_i=sum(v!=bg for r in i for v in r); fg_o=sum(v!=bg for r in o for v in r)
    f['fg_grows']=fg_o>fg_i; f['fg_shrinks']=fg_o<fg_i
    objs_i=objects(i,bg,True,True); f['n_obj_in']=min(len(objs_i),20)/20
    f['has_singletons']=any(len(ob['cells'] if isinstance(ob,dict) else ob)==1 for ob in objs_i) if objs_i else False
    # separators
    full_rows=[y for y in range(hi) if len(set(i[y]))==1 and i[y][0]!=bg]; full_cols=[x for x in range(wi) if len({i[y][x] for y in range(hi)})==1 and i[0][x]!=bg]
    f['separators']=bool(full_rows or full_cols)
    if same:
        ch=[(y,x) for y in range(hi) for x in range(wi) if i[y][x]!=o[y][x]]
        n=len(ch); f['changed_frac']=n/(hi*wi)
        f['only_bg_changed']=n>0 and all(i[y][x]==bg for y,x in ch)
        f['only_fg_changed']=n>0 and all(i[y][x]!=bg for y,x in ch)
        f['to_bg']=n>0 and all(o[y][x]==bg for y,x in ch)
        f['recolour_only']=n>0 and all(i[y][x]!=bg and o[y][x]!=bg for y,x in ch)
        pc={o[y][x] for y,x in ch}; f['single_paint']=len(pc)==1
        if ch:
            rows={y for y,x in ch};cols={x for y,x in ch}
            f['changes_on_lines']=len(ch)>=3 and (len(rows)==1 or len(cols)==1 or sum(1 for y,x in ch if sum((y,x2) in set(ch) for x2 in (x-1,x+1))+sum((y2,x) in set(ch) for y2 in (y-1,y+1))>=1)/n>0.9)
            # moved objects: same shape present in input and output at different position
            oo=objects(o,bg,True,True)
            ks=lambda obs:collections.Counter(shape_key(ob['cells'] if isinstance(ob,dict) else ob) for ob in obs)
            ki,ko=ks(objs_i),ks(oo)
            f['shapes_preserved']=ki==ko and n>0
            f['objects_added']=sum(ko.values())>sum(ki.values())
            f['objects_removed']=sum(ko.values())<sum(ki.values())
            # changed cells adjacent to input fg (local stencil) vs far
            fgs={(y,x) for y in range(hi) for x in range(wi) if i[y][x]!=bg}
            near=sum(1 for y,x in ch if any((y+a,x+b) in fgs for a in (-1,0,1) for b in (-1,0,1)))
            f['changes_near_fg']=near/n
            f['changes_on_border']=sum(1 for y,x in ch if y in(0,hi-1) or x in(0,wi-1))/n
            f['symmetric_out_h']=o==[r[::-1] for r in o]; f['symmetric_out_v']=o==o[::-1]
    else:
        # is output a sub-grid of input?
        f['out_is_subgrid']=any(all(i[y+a][x:x+wo]==o[a] for a in range(ho)) for y in range(hi-ho+1) for x in range(wi-wo+1)) if ho<=hi and wo<=wi else False
        f['out_colours_subset']=co<=ci
    return f

def task_spectrum(train):
    acc=collections.defaultdict(float)
    for p in train:
        for k,v in pair_feats(p['input'],p['output']).items(): acc[k]+=float(v)
    return {k:v/len(train) for k,v in acc.items()}
