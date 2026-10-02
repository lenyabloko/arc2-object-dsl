"""Patch the live review page: categories are situations (decision CATEGORIES-ARE-SITUATIONS, Fable v17a; build items
1-3). Adds D.situations (four seed situations with six-slot templates, candidate drafts, P2 membership, groups) and a
Situations section at the top of the Categories tab; grid-check categories are relabelled as evidence; "add a new
category" becomes "declare a situation" (G82: draft until WHY is checked by rollout)."""
import json, re, sys
SRC, OUT = sys.argv[1], sys.argv[2]
s = open(SRC).read()
# strip the publish skeleton (the Artifact tool adds it again)
body_at = s.index('<body>') + len('<body>')
s = s[body_at:]
s = s[:s.rindex('</body></html>')]
M = json.load(open('/home/claude/work/public_repo/results/o0/situation_membership.json'))
VOC = json.load(open('/home/claude/work/public_repo/tools/dream/o0/template_vocab.json'))
PARSED = {r['card']: r for r in json.load(open('/home/claude/work/public_repo/results/o0/t83_parsed.json'))}
a = s.index('<script id="data" type="application/json">') + len('<script id="data" type="application/json">')
b = s.index('</script>', a)
D = json.loads(s[a:b])
members = M['membership']
groups = {}
for g in D['groups']:
    ts = [m[0] for m in g.get('members', [])]
    for S in M['situations']:
        k = sum(1 for t in ts if members.get(t, {}).get(S['id'], '').startswith('aligned'))
        if k: groups.setdefault(S['id'], []).append([g['id'], g.get('name', ''), k, len(ts)])
for v in groups.values(): v.sort(key=lambda x: (-x[2] / max(1, x[3]), -x[2]))
tg = {}
for g in D['groups']:
    for m in g.get('members', []): tg.setdefault(m[0], g['id'])
drafts = [
    {"id": "S_recolour_by_key", "name": "recolour by key (candidate)", "draft": True,
     "template": {"WHO": "colour_class", "WHAT": "recolour", "WHERE": "in_place", "HOW": "mapped_colour", "UNTIL": "once", "WHY": ""},
     "open": "the colour for a key the training pairs did not show", "note": "from the palette-mapping grid check; declared only if a WHY can be stated (G82)"},
    {"id": "S_extract_region", "name": "extract the distinguished region (candidate)", "draft": True,
     "template": {"WHO": "region", "WHAT": "extract", "WHERE": "whole_output", "HOW": "same_shape", "UNTIL": "once", "WHY": ""},
     "open": "which region (the one that differs, is framed or is marked)", "note": "from the crop grid check; declared only if a WHY can be stated (G82)"},
]
OPEN = {'S_tiling': 'UNTIL', 'S_stamping': 'WHERE', 'S_projection': 'UNTIL', 'S_symmetry': 'WHERE', 'S_recolour_by_key': 'HOW', 'S_extract_region': 'WHO'}
for x in M['situations'] + drafts: x['open_slot'] = OPEN[x['id']]
for x in M['situations']: x['note'] = 'seed template written by Claude from Fable v17 (a placeholder): your definition replaces it (v18 B.2)'
D['situations'] = {
    'list': M['situations'], 'drafts': drafts, 'membership': members, 'groups': groups, 'task_group': {t: tg.get(t) for t in members},
    'vocab': {k: [x for x in v if x != 'unspecified'] for k, v in VOC.items() if k != 'doc'},
    'vocab_desc': {k + ':' + x: d for k, v in VOC.items() if k != 'doc' for x, d in v.items() if d},
    'parsed_lines': PARSED,
    'reassign': [['scale', 'evidence for tiling / output size'], ['crop', 'evidence for the candidate "extract the distinguished region"'],
                 ['palette mapping', 'evidence for the candidate "recolour by key"'], ['sparse, partition', 'evidence only']],
    'built': '2026-10-02 (P2 aligner v1, training pairs only)'}
data = json.dumps(D, separators=(',', ':')).replace('</', '<\\/')
s = s[:a] + data + s[b:]

JS = r'''
// ---------- situations (decision CATEGORIES-ARE-SITUATIONS, Oct 2): a category is a situation ----------
let curSit=null;
const SLOTS=['WHO','WHAT','WHERE','HOW','UNTIL','WHY'];
async function setSitLabel(sid,t,label){const id='SIT_'+sid+'_'+t;const cur=dec[id];
  if(cur&&cur.status==='submitted')return;
  if(cur&&cur.label===label){delete dec[id];render();if(db)db.collection('decisions').doc(id).delete().then(()=>saveMsg('label removed')).catch(e=>saveMsg('remove failed: '+(e.code||e)));return}
  const d={kind:'situation_label',task:t,situation:sid,label:label,reviewer:'len',ts:new Date().toISOString(),test_seen:false,status:'draft',proposal:'submitted'};
  dec[id]=d;render();if(!db){saveMsg('not saved: no database in this view');return}
  try{await db.collection('decisions').doc(id).set(d);saveMsg('label saved · goes into the next review batch')}catch(e){saveMsg('save failed: '+(e.code||e))}}
function sitTemplate(S){const t=el('table');const tb=document.createElement('tbody');
  SLOTS.forEach(k=>{const tr=document.createElement('tr');const th=el('th',null,k);th.style.width='90px';const td=el('td');
    const v=(S.template||{})[k]||'';const open=S.open_slot===k;
    if(k==='WHY'){td.textContent=v||'— missing: a situation needs its invariant (G82)';if(!v)td.style.color='var(--reject)'}
    else{const sp=el('span','pill',v||'—');td.append(sp);const gl=(D.situations.vocab_desc||{})[k+':'+v];if(gl)td.append(el('span','help',' '+gl));if(open){const o=el('span','pill wait','open');o.style.marginLeft='6px';o.title='open role, filled on the test input: '+S.open;td.append(o)}}
    tr.append(th,td);tb.append(tr)});t.append(tb);const w=el('div','tbl');w.append(t);return w}
function declareForm(){const w=el('div');w.style.cssText='margin-top:12px;padding-top:10px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:6px';
  w.append(el('h3',null,'Declare a situation (this is how a new category is added)'));
  w.append(el('div','help','Six short fields from the base vocabulary, the open role, and the WHY (mandatory). A declared situation is a draft until Claude checks its WHY by rollout on at least one design task the aligner places in it (G82).'));
  const f={};const row=el('div','row');row.style.cssText='gap:8px;flex-wrap:wrap;align-items:flex-end';
  const nm=el('input');nm.type='text';nm.placeholder='name, e.g. gravity / support';nm.style.cssText='font:13px var(--sans);padding:4px 6px;min-width:200px;max-width:280px';row.append(nm);
  ['WHO','WHAT','WHERE','HOW','UNTIL'].forEach(k=>{const c=el('div');c.style.cssText='display:flex;flex-direction:column;gap:2px';c.append(el('span','help',k));const sel=el('select');sel.style.cssText='font:12.5px var(--sans);padding:3px';sel.append(new Option('choose…',''));(D.situations.vocab[k]||[]).forEach(v=>sel.append(new Option(v,v)));f[k]=sel;c.append(sel);row.append(c)});
  w.append(row);const op=el('input');op.type='text';op.placeholder='open role: what the test input leaves to fill (e.g. landing row)';op.style.cssText='font:13px var(--sans);padding:4px 6px;max-width:560px';
  const why=el('input');why.type='text';why.placeholder='WHY (mandatory): the invariant every instance keeps, e.g. falls until supported';why.style.cssText='font:13px var(--sans);padding:4px 6px;max-width:560px';
  const ok=el('button','btn primary','Declare situation');const msg=el('span','save');ok.disabled=!db;
  ok.onclick=async()=>{const n=nm.value.trim();const tpl={};let miss=[];['WHO','WHAT','WHERE','HOW','UNTIL'].forEach(k=>{tpl[k]=f[k].value;if(!tpl[k])miss.push(k)});tpl.WHY=why.value.trim();if(!tpl.WHY)miss.push('WHY');
    if(!n){msg.textContent='give it a name';return}if(miss.length){msg.textContent='fill: '+miss.join(', ');return}
    const id='SITDECL_'+n.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'').slice(0,40);
    const d={kind:'situation_declaration',name:n,template:tpl,open:op.value.trim(),reviewer:'len',ts:new Date().toISOString(),test_seen:false,status:'draft',proposal:'submitted',g82:'draft: WHY not yet checked by rollout'};
    dec[id]=d;try{await db.collection('decisions').doc(id).set(d);msg.textContent='declared (draft until checked)';render()}catch(e){msg.textContent='could not save: '+(e.code||e)}};
  w.append(op,why);const r2=el('div','row');r2.append(ok,msg);w.append(r2);if(!db)w.append(el('span','help','situations cannot be saved in this view'));return w}
function renderSituations(S){const SD=D.situations;if(!SD)return;
  const mine=Object.entries(dec).filter(([k,d])=>d&&d.kind==='situation_declaration').map(([k,d])=>({id:k,name:d.name+' (declared by you)',template:d.template,open:d.open,draft:true,note:d.g82||'draft'}));
  const all=[...SD.list,...SD.drafts,...mine];if(!curSit||!all.find(x=>x.id===curSit))curSit=SD.list[0].id;
  const intro=el('div','card');intro.append(el('h2',null,'Categories are situations'));
  const p=el('p',null,'A category is a situation: who acts, what changes, where, how, until when, and why. The why is the invariant that decides what the training pairs leave open on the test input, so every category must have one. A task belongs to a situation when the aligner instantiates it on the task’s training pairs with the invariant holding, not by a vote. Your ✓ and ✗ on a task are labels: the only supervised signal the project has. They are used to check the aligner (T85), never as its input.');const p2=el('p',null,'The four seed templates are placeholders Claude wrote from v17. Under Fable v18 (B.2) the stamping and projection generators are written only from your own definitions: please declare them with the form below, named stamping and projection, by Oct 4. Your definition replaces the placeholder, and the generator code will reference no task.');p2.style.cssText='margin:8px 0 0;max-width:80ch;color:var(--unsure)';p.style.cssText='margin:8px 0 0;max-width:80ch';intro.append(p,p2);
  const nav=el('div','chips');nav.style.marginTop='10px';all.forEach(x=>{const n=Object.values(SD.membership).filter(m=>(m[x.id]||'').startsWith('aligned')).length;const b=el('button','chip',x.name+(x.draft?'':' · '+n));if(x.id===curSit){b.style.borderColor='var(--accent)';b.style.color='var(--accent)'}if(x.draft)b.style.borderStyle='dashed';b.onclick=()=>{curSit=x.id;render()};nav.append(b)});intro.append(nav);
  intro.append(declareForm());S.append(intro);
  const X=all.find(x=>x.id===curSit);const cc=el('div','card');const gh=el('div','ghead');gh.append(el('h2',null,X.name));
  const mem=Object.entries(SD.membership).filter(([t,m])=>m[X.id]).map(([t,m])=>[t,m[X.id]]);const nal=mem.filter(x=>x[1].startsWith('aligned')).length;
  gh.append(el('span','stat',X.draft?'draft (G82): not used by the aligner or the filler':'aligned on '+nal+' design tasks · invariant failed on '+(mem.length-nal)));cc.append(gh);
  if(X.note)cc.append(Object.assign(el('div','help',X.note),{style:'margin-top:4px'}));
  const cols=el('div','cols');cols.style.marginTop='10px';const L=el('div');L.append(el('h3',null,'Template'),sitTemplate(X));
  if(X.open)L.append(Object.assign(el('div','help','Open role: '+X.open),{style:'margin-top:6px'}));
  const gs=(SD.groups||{})[X.id]||[];if(gs.length){L.append(Object.assign(el('h3',null,'Mechanism groups with aligned members'),{style:'margin-top:12px'}));const gl=el('div','chips');gs.slice(0,30).forEach(([gid,nm,k,n])=>{const b=el('button','chip',gid+' '+k+'/'+n);b.title=nm;b.onclick=()=>{backTo={tab:'cats',label:'situation '+X.name,scroll:window.scrollY};tab='groups';if(typeof setView==='function'&&typeof GVIEW!=='undefined'&&GVIEW!=='mech')setView('mech');if(GI[gid]!=null){cur=GI[gid];memIdx=0}render();window.scrollTo({top:0})};gl.append(b)});L.append(gl)}
  const R=el('div');R.append(el('h3',null,'Membership (P2 alignment, training pairs only)'));
  if(!mem.length)R.append(el('div','help',X.draft?'Drafts have no membership until their WHY is checked.':'No design task aligned yet.'));
  else{const tw=el('div','tbl');tw.style.maxHeight='520px';tw.style.overflow='auto';const t=el('table');const th=document.createElement('thead');th.innerHTML='<tr><th>task</th><th>aligner</th><th>group</th><th>your label</th></tr>';t.append(th);const tb=document.createElement('tbody');
    mem.sort((a,b)=>(b[1].startsWith('aligned')-a[1].startsWith('aligned'))||a[0].localeCompare(b[0])).forEach(([tk,st])=>{const tr=document.createElement('tr');
      const c1=el('td');const ib=el('button','chip',tk);ib.onclick=()=>{backTo={tab:'cats',label:'situation '+X.name,scroll:window.scrollY};openTask(tk)};c1.append(ib);
      const c2=el('td');c2.append(el('span','pill '+(st.startsWith('aligned')?'ok':'wait'),st));
      const c3=el('td',null,(SD.task_group||{})[tk]||'—');c3.style.fontFamily='var(--mono)';
      const c4=el('td');const lab=dec['SIT_'+X.id+'_'+tk];const lk=lab&&lab.status==='submitted';
      const y=el('button','xbtn'+(lab&&lab.label==='in'?' on':''),'✓ in');if(lab&&lab.label==='in'){y.style.borderColor='var(--accept)';y.style.color='var(--accept)'}y.disabled=lk||!db;y.onclick=()=>setSitLabel(X.id,tk,'in');
      const n=el('button','xbtn'+(lab&&lab.label==='out'?' on':''),'✗ out');n.disabled=lk||!db;n.onclick=()=>setSitLabel(X.id,tk,'out');c4.append(y,document.createTextNode(' '),n);
      tr.append(c1,c2,c3,c4);tb.append(tr)});t.append(tb);tw.append(t);R.append(tw)}
  const s2=el('span','save','');s2.id='save';R.append(s2);
  cols.append(L,R);cc.append(cols);S.append(cc)}
'''
anchor = 'function renderCats(V){'
assert s.count(anchor) == 1
s = s.replace(anchor, JS + '\n' + anchor)
old = "const K=mergedCats();const S=el('div','solo');V.append(S);"
assert s.count(old) == 1
s = s.replace(old, old + "renderSituations(S);")
old2 = "intro.append(el('h2',null,'Categories over the lattice axes'));"
assert s.count(old2) == 1
s = s.replace(old2, "intro.append(el('h2',null,'Evidence: grid checks (no longer categories)'));")
old3 = "const p=el('p',null,'Categories group your conceptual-lattice axes. A group appears in a category when at least half of its tasks show evidence for it (an exact check on the grids, the primitive that solves it, or the task reading). Your part is correction only: ✗ removes a group or task that does not fit; each correction is tested by the next cycle as a perturbation.');"
assert s.count(old3) == 1
s = s.replace(old3, "const p=el('p',null,'These grid checks (palette, crop, scale, sparse, partition, …) and the earlier categories are kept as evidence: observations shown on task and group cards. They decide nothing on a test input, so they are no longer categories. Reassigned: '+D.situations.reassign.map(x=>x[0]+' → '+x[1]).join('; ')+'. Your earlier corrections here are kept.');")
old4 = "intro.append(catGraph(K));intro.append(newCatForm(K));S.append(intro);"
assert s.count(old4) == 1
s = s.replace(old4, "intro.append(catGraph(K));S.append(intro);")
open(OUT, 'w').write(s)
print(len(s))
