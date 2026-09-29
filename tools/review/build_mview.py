"""Mechanism view for the review page: regroup all 1,050 review tasks by mechanism, classify every task under the
enriched priors, add prior-domain categories, and carry the abstract readings. Spectral groups stay as groups_v1."""
import json, re, glob, os, collections, math
S0='/home/claude/work/s0'; LAT='/home/claude/work/latent'; W='/home/claude/work/widen'
D=json.load(open(f'{S0}/review_groups_pre_analysis.json')) if not os.path.exists(f'{S0}/mview/base.json') else json.load(open(f'{S0}/mview/base.json'))
T=json.load(open(f'{S0}/tasks.json'))
O=json.load(open(f'{S0}/taskan/mechanism_ontology.json')); SUB=O['subclasses']; ASG=dict(O['assign'])
P=json.load(open(f'{S0}/taskan/halfA_placement.json'))
for k,v in P['new_subclasses'].items():
    if k not in SUB: SUB[k]=dict(v); SUB[k]['tasks']=[]
ABS={d['task']:d for d in json.load(open(f'{S0}/taskan/abs_all.json'))}
for r in P['readings']:
    ABS[r['task']]=r; ASG[r['task']]=r['subclass']
L=json.load(open(f'{S0}/taskan/ontology_links.json')); N=L['nodes']
A=set(x for x in re.split(r'[,\s]+',open(f'{W}/deval_a.txt').read()) if x)
N2=set(x for x in re.split(r'[,\s]+',open(f'{W}/novel_N2.txt').read()) if x)
pop=[t for ms in D['members'].values() for t in ms]            # the 1,050 review tasks (half B excluded)
# ---- status under V18 (lattice + G-DSL, WSL job c15) and the composition engines (next build)
v6={}
for f in ['m1b/a_atoms_train.jsonl','m1b/a_atoms_deval.jsonl']:
    for l in open(f'{W}/{f}'): d=json.loads(l); v6[d['task']]=d['test_exact']
C15={json.loads(l)['task']:json.loads(l) for l in open('/mnt/user-data/uploads/arc_extended_arga/cloud_outbox/wsl_results/wake/c15-v18/results.jsonl')}
DOM={'prior_topology':'topology','prior_geometry':'geometry','prior_combinatorics':'combinatorics','prior_optics':'optics',
     'prior_mechanics':'mechanics','prior_fluids':'fluids','prior_action':'action','prior_arithmetic':'arithmetic'}
DNAME={'topology':'Topology','geometry':'Geometry & symmetry','combinatorics':'Combinatorics & order','optics':'Optics & occlusion',
       'mechanics':'Mechanics & equilibrium','fluids':'Fluids & flow','action':'Least action & conservation','arithmetic':'Arithmetic & sets'}
MOD={}   # task -> list of {module, domain, prog}
for f in sorted(glob.glob(f'{LAT}/out_*.jsonl')):
    m=os.path.basename(f)[4:-6]
    if m in ('compose_objmap',): continue          # superseded by the deterministic run
    mod=m.replace('_det','')
    for l in open(f):
        r=json.loads(l)
        if r.get('exact') and r.get('prog') and not str(r['prog']).startswith(('colour-map','identity')) and r['task'] not in N2:
            dom=DOM.get('prior_'+mod.split('prior_')[-1]) if mod.startswith('prior_') else ('composition' if mod.startswith('compose') else 'group primitive')
            MOD.setdefault(r['task'],[]).append({'module':mod,'domain':dom,'prog':r['prog']})
status={}
for t in pop:
    g=C15.get(t,{})
    if g.get('exact'): status[t]={'by':'whole-grid DSL (V18)','program':g['progs'][0] if g.get('progs') else None}
    elif v6.get(t): status[t]={'by':'lattice (RDR rules)','program':None}
comp={t for t in pop if t not in status and any(x['domain']=='composition' for x in MOD.get(t,[]))}
# ---- grounding: mechanism -> prior domains through shared grounding concepts
gi=collections.defaultdict(set)
for a,b in L['grounded_in']: gi[a].add(b)
dom_concepts=collections.defaultdict(set)
for k,v in N.items():
    if v['kind']=='prior' and v.get('domain') in DNAME: dom_concepts[v['domain']]|=gi.get(k,set())
def grounded_domains(mech): return sorted(d for d,cs in dom_concepts.items() if gi.get(mech,set())&cs)
# ---- group assignment
def solver_head(t):
    s=status[t]
    if s['by'].startswith('lattice'): return 'solved.lattice_rdr'
    p=s['program'] or ''
    h=re.split(r'[\[:(+ ]',p)[0].strip() or 'other'
    return 'solved.'+h
grp={}
for t in pop:
    if t in ASG: grp[t]=ASG[t]
    elif t in status: grp[t]=solver_head(t)
    else: grp[t]='unplaced'
by=collections.defaultdict(list)
for t in pop: by[grp[t]].append(t)
# ---- old per-task info
old_of={t:g for g,ms in D['members'].items() for t in ms}
old_labels={}; oldG={g['id']:g for g in D['groups']}
for g in D['groups']:
    for t,labs in (g.get('task_labels') or {}).items(): old_labels[t]=labs
tcc=json.load(open(f'{S0}/task_codex_classes.json')); tcr=json.load(open(f'{S0}/task_codex_rules.json'))
cls_freq=collections.Counter(c for t in pop for c in set(tcc.get(t,[])))
rule_freq=collections.Counter(c for t in pop for c in set(tcr.get(t,[])))
CS=json.load(open(f'{S0}/cat_strength.json'))
cat_base={c:sum(1 for t in pop if CS.get(t,{}).get(c,0)>=2)/len(pop) for c in next(iter(CS.values()))}
def pairs(t,k=3): return [[a,b] for a,b in T[t]['train'][:k]]
def pretty(s): return s.replace('solved.','solved · ').replace('_',' ')
groups=[]; members={}
order=sorted(by.items(),key=lambda kv:(-len(kv[1]),kv[0]))
for i,(key,ts) in enumerate(order):
    gid='M%03d'%(i+1)
    sub=SUB.get(key,{})
    # medoid: most confident abstract reading, else first
    ts=sorted(ts,key=lambda t:(-(ABS.get(t,{}).get('confidence') or 0),t))
    med=ts[0]
    n=len(ts)
    # categories: prior domains (solve evidence per task, grounding at group level) + original categories
    dcount=collections.Counter(d for t in ts for d in {x['domain'] for x in MOD.get(t,[])} if d in DNAME)
    cats=[]
    for d in DNAME:
        cov=dcount[d]/n; gd=d in grounded_domains(key)
        if cov>=0.3 or gd:
            fams=collections.Counter(x['prog'].split('[')[0].split('(')[0] for t in ts for x in MOD.get(t,[]) if x['domain']==d)
            cats.append({'axes':[],'classes':[],'id':'p_'+d,'cov':round(max(cov,0.5 if gd else 0),2),'lift':round(max(cov,0.5)*4,1),'score':round(max(cov,0.5 if gd else 0)*2,3),
                         'concepts':[[f,c] for f,c in fams.most_common(4)]+([['grounded in '+', '.join(sorted(b.split('.',1)[-1].replace('_',' ') for b in gi.get(key,set())&dom_concepts[d])[:3]),1]] if gd else []),
                         'evidence':'solved by this prior on %d of %d members'%(dcount[d],n)+(' · grounded' if gd else '')})
    for c,base in cat_base.items():
        k=sum(1 for t in ts if CS.get(t,{}).get(c,0)>=2)
        if n and k/n>=0.5 and base>0:
            cats.append({'axes':[],'classes':[],'id':c,'cov':round(k/n,2),'lift':round((k/n)/base,1),'score':round((k/n)*min(3,(k/n)/base),3),'concepts':[]})
    cats.sort(key=lambda c:-c['score'])
    ccl=collections.Counter(c for t in ts for c in set(tcc.get(t,[])))
    codex_classes=[{'c':c,'k':k,'lift':round((k/n)/(cls_freq[c]/len(pop)),1),'kind':'class','chain':[]} for c,k in ccl.most_common() if k>=max(2,math.ceil(0.4*n)) and (k/n)/(cls_freq[c]/len(pop))>=1.8][:8] if n>1 else []
    crl=collections.Counter(c for t in ts for c in set(tcr.get(t,[])))
    codex_rules=[{'c':c,'k':k,'lift':round((k/n)/(rule_freq[c]/len(pop)),1)} for c,k in crl.most_common() if k>=max(1,math.ceil(0.3*n))][:6]
    nsol=sum(t in status for t in ts)
    mech={kk:sub.get(kk) for kk in ('parent','definition','parameters','detector','primitive_sketch','coverage_risk')} if sub else None
    rule=(sub.get('definition') if sub else None) or ('Tasks already solved by the %s program family.'%pretty(key) if key.startswith('solved.') else 'Not yet placed in the mechanism ontology.')
    g={'id':gid,'n':n,'n_heldout':0,'coh':None,'medoid':med,'med_split':T[med]['split'],'name':pretty(key),'key':key,
       'med_pairs':pairs(med),'members':[[t]+T[t]['train'][0] for t in ts],'atoms':[],'cats':cats,'cats_other':[],'axes':[],'onto':[],'codex':[],
       'rule':rule,'grid':{},'codex_classes':codex_classes,'codex_common':[],'codex_rules':codex_rules,'codex_rules_cov':sum(1 for t in ts if tcr.get(t)),
       'tree_counts':{},'task_labels':{t:old_labels[t] for t in ts if t in old_labels},'n_solved':nsol,'n_comp':sum(t in comp for t in ts),
       'mechanism':mech,'residual':key.endswith('.residual'),'v1':collections.Counter(old_of.get(t) for t in ts).most_common(),
       'priors':[[DNAME[d],c] for d,c in dcount.most_common()],'grounded':grounded_domains(key)}
    # needs you: unsolved and (residual group or low-confidence / literal reading)
    def needs(t):
        if t in status: return None
        a=ABS.get(t)
        if not a: return 'no reading yet'
        r=[]
        if key.endswith('.residual'): r.append('no generic mechanism found')
        c=a.get('confidence')
        if isinstance(c,(int,float)) and c<0.6: r.append('uncertain reading (%.2f)'%c)
        if a.get('abstraction_level') in (1,'1'): r.append('could not abstract')
        return '; '.join(r) or None
    g['needs']={t:needs(t) for t in ts if needs(t)}; g['n_needs']=len(g['needs'])
    groups.append(g); members[gid]=ts
# ---- prior-domain categories (two new roots)
K=D['cats']; cats=[c for c in K['categories'] if not c['id'].startswith(('p_','r_prior'))]
roots=[('r_prior_phys','Physics & common-sense priors','laws of the physical world read into the grid: light, bodies, liquids, economy of motion'),
       ('r_prior_math','Mathematical priors','structure-preserving maps and invariants: topology, symmetry groups, orderings, arithmetic and sets')]
parent={'optics':'r_prior_phys','mechanics':'r_prior_phys','fluids':'r_prior_phys','action':'r_prior_phys',
        'topology':'r_prior_math','geometry':'r_prior_math','combinatorics':'r_prior_math','arithmetic':'r_prior_math'}
new=[]
for rid,name,gloss in roots:
    new.append({'id':rid,'name':name,'gloss':gloss,'parents':[],'axes':[],'classes':[],'seeds':[],'concepts':[],'n_any':0,'n_strong':0,'samples':[],'atoms':[],'children':['p_'+d for d,p in parent.items() if p==rid]})
for d,dn in DNAME.items():
    node=N.get('prior.'+d,{})
    solved=[t for t in pop if any(x['domain']==d for x in MOD.get(t,[]))]
    fam=collections.Counter(x['prog'].split('[')[0].split('(')[0] for t in pop for x in MOD.get(t,[]) if x['domain']==d)
    grounded_groups=[g['id'] for g in groups if d in g['grounded']]
    conc=[{'c':f,'why':'prior family (tasks it solves exactly)','n':c,'weak':False,'aliases':[],'classes':[]} for f,c in fam.most_common(14)]
    gconc=sorted(dom_concepts[d])
    classes=[N[c]['label'] if c in N and N[c].get('label') else c for c in gconc][:24]
    samp=[]; seen=set()
    for t in solved:
        if grp[t] not in seen: seen.add(grp[t]); samp.append(t)
        if len(samp)>=10: break
    new.append({'id':'p_'+d,'name':dn,'gloss':node.get('comment','')+(' · solves %d review tasks exactly; grounds %d mechanism groups'%(len(solved),len(grounded_groups))),
                'parents':[parent[d]],'axes':[],'classes':classes,'seeds':[],'concepts':conc,'n_any':len(solved)+len(grounded_groups),'n_strong':len(solved),
                'samples':samp,'atoms':[],'children':[]})
K['categories']=cats+new
# ---- assemble
D2=dict(D)
D2['groups_v1']=D['groups']; D2['groups']=groups
D2['members']=dict(D['members']); D2['members'].update(members)
D2['status']=status; D2['solved']=sorted(status); D2['composed']=sorted(comp)
D2['abs']={t:{k:ABS[t].get(k) for k in ('mechanism','roles','varies_across_pairs','invariant','generalisation_axes','abstraction_level','family_key','confidence')} for t in pop if t in ABS}
D2['task_priors']={t:MOD[t] for t in pop if t in MOD}
D2['group_of']={t:grp[t] for t in pop}
D2['prior_names']=DNAME
D2['view_meta']={'build':'V18 (lattice + 152 G-DSL families incl. 8 prior domains) + composition engines (next build)',
                 'n_groups':len(groups),'n_solved':len(status),'n_composed':len(comp),'n_tasks':len(pop)}
json.dump(D2,open(f'{S0}/mview/review_groups_mview.json','w'))
print(D2['view_meta']); print('groups by kind: mechanism',sum(1 for g in groups if g['mechanism']),'solved-family',sum(1 for g in groups if g['key'].startswith('solved.')),'residual',sum(g['residual'] for g in groups))
print('top groups',[(g['id'],g['name'],g['n'],g['n_solved']) for g in groups[:12]])
print('prior cats',[(c['name'],c['n_strong']) for c in new])
