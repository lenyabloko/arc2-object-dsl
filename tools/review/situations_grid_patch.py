"""Patch the live review page: the Situations grid (Fable v18a D45; Len 17:35 EDT: rebuild now). ROW = what is picked out of the input, COLUMN = how it is applied; a cell is a situation with Len's WHY; body read-only from the aligner; tasks placed by click; task details panel."""

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
for x in M['situations']: x['name'] = x['name'].split(' / ')[0]
D['situations'] = {
    'list': M['situations'], 'drafts': drafts, 'membership': members, 'groups': groups, 'task_group': {t: tg.get(t) for t in members},
    'vocab': {k: [x for x in v if x != 'unspecified'] for k, v in VOC.items() if k != 'doc'},
    'vocab_desc': dict({k + ':' + x: d for k, v in VOC.items() if k != 'doc' for x, d in v.items() if d},
                       **{'WHERE:whole_output': 'the output grid', 'WHO:whole_grid': 'the input grid'}),
    'parsed_lines': PARSED,
    'reassign': [['scale', 'evidence for tiling / output size'], ['crop', 'evidence for the candidate "extract the distinguished region"'],
                 ['palette mapping', 'evidence for the candidate "recolour by key"'], ['sparse, partition', 'evidence only']],
    'built': '2026-10-02 (P2 aligner v1, training pairs only)', 'n_design': 997,
    'heldout': sorted(json.load(open('/home/claude/work/public_repo/results/o0/t86_heldout.json'))),
    't86': {'S_stamping': sorted(t for t, v in json.load(open('/home/claude/work/public_repo/results/o0/t80b_situations.json')).items() if 'stamping' in v),
            'S_projection': sorted(t for t, v in json.load(open('/home/claude/work/public_repo/results/o0/t80b_situations.json')).items() if 'projection' in v)}}

# ---- Fable v18a / Len 17:35 EDT: situations as a grid, ROW = what is picked out of the input, COLUMN = how it is applied
ROWS = [['fg', 'foreground cells'], ['bg', 'background cells'], ['markers', 'markers'], ['input', 'the input grid'],
        ['exemplar', 'exemplar / template shape'], ['odd', 'largest / smallest / odd object'], ['colour', 'objects of one colour'],
        ['count', 'a count (pixels, objects)'], ['border', 'grid border / extent'], ['obstacle', 'first obstacle met'],
        ['axis', 'symmetry axis'], ['key', 'colour key / legend'], ['separator', 'separator / panels'],
        ['frame', 'frame / container'], ['norow', 'row not decided yet']]
# Fable v19 B.1: a situation = HOW(arg_1..arg_k) + WHY. Each column has its arguments; the grid row shows the
# column's first-listed "row" argument (marked p=1); the other arguments are chosen in the cell panel:
# a row, or "from training" (a constant the test input does not change). 'slot' = where it goes in the stored six-slot record.
COLS = [['tile', 'tile', [['extent', 'how far / how many', 'UNTIL', 1], ['where', 'which blocks get a copy', 'WHERE', 0], ['unit', 'the unit repeated', 'WHO', 0], ['colour', 'colour of the copies', 'HOW', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['stamp', 'stamp', [['anchors', 'where copies go', 'WHERE', 1], ['unit', 'what is copied', 'WHO', 0], ['colour', 'colour of the copies', 'HOW', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['extend', 'extend / draw line', [['stop', 'where it stops', 'UNTIL', 1], ['source', 'what is extended', 'WHO', 0], ['colour', 'line colour', 'HOW', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['mirror', 'mirror', [['axis', 'mirrored across', 'WHERE', 1], ['subject', 'what is mirrored', 'WHO', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['recolour', 'recolour', [['key', 'which colour becomes which', 'HOW', 1], ['subject', 'what is recoloured', 'WHO', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['fill', 'fill', [['region', 'what is filled', 'WHERE', 1], ['colour', 'fill colour', 'HOW', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['move', 'move', [['subject', 'what moves', 'WHO', 1], ['target', 'where to', 'WHERE', 0], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['extract', 'extract / crop', [['region', 'what is cut out', 'WHO', 1], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]],
        ['other', 'other', [['what', 'what is picked out', 'WHO', 1], ['how', 'how (direction, count, corner …)', 'MANNER', 0]]]]
# drafts the cell panel starts from (v19 B.2 for stamping / projection; Len's 17:00 words for the three tiling kinds); Len corrects them
DRAFT = {'markers|stamp': {'args': {'unit': 'train'}, 'why': 'one copy of the unit at every anchor, copies identical', 'src': 'Fable v19 B.2'},
         'obstacle|extend': {'args': {'source': 'markers', 'colour': 'own'}, 'why': 'extension reaches exactly the first stop cell and never crosses it', 'src': 'Fable v19 B.2'},
         'border|tile': {'args': {'unit': 'input'}, 'why': 'the unit repeats until the grid border', 'src': 'your words, 17:00'},
         'count|tile': {'args': {'unit': 'input'}, 'why': 'number of copies = number of foreground pixels', 'src': 'your words, 17:00'},
         'fg|tile': {'args': {'unit': 'input'}, 'why': 'a copy of the shape at each foreground cell', 'src': 'your words, 17:00'},
         'key|tile': {'args': {'extent': 'train', 'where': 'the one block row or column marked by the one-colour line of the input', 'unit': 'input', 'colour': 'own'}, 'why': 'the entire tile is copied, but only into the block row (or column) marked by the keyed one-colour line of the input', 'src': 'your comment, 19:58'}}
BODY = {
    'border|tile': {'WHO': 'whole_grid', 'WHERE': 'whole_output', 'HOW': 'same_shape', 'UNTIL': 'border'},
    'count|tile': {'WHO': 'whole_grid', 'WHERE': 'whole_output', 'HOW': 'same_shape', 'UNTIL': 'count'},
    'fg|tile': {'WHO': 'whole_grid', 'WHERE': 'whole_output', 'HOW': 'same_shape', 'UNTIL': 'once'},
    'norow|tile': {'WHO': 'whole_grid', 'WHERE': 'whole_output', 'HOW': 'same_shape', 'UNTIL': ''},
    'markers|stamp': {'WHO': 'marker', 'WHERE': 'at_marker', 'HOW': 'same_shape', 'UNTIL': 'once'},
    'obstacle|extend': {'WHO': 'marker', 'WHERE': 'on_line_of_sight', 'HOW': 'own_colour', 'UNTIL': 'obstacle'},
    'axis|mirror': {'WHO': 'all_objects', 'WHERE': 'mirror_position', 'HOW': 'own_colour', 'UNTIL': 'once'},
    'key|recolour': {'WHO': 'colour_class', 'WHERE': 'in_place', 'HOW': 'mapped_colour', 'UNTIL': 'once'},
    'frame|extract': {'WHO': 'region', 'WHERE': 'whole_output', 'HOW': 'same_shape', 'UNTIL': 'once'},
}
SIT2CELL = {'S_stamping': 'markers|stamp', 'S_projection': 'obstacle|extend', 'S_symmetry': 'axis|mirror'}
TILE_BY_GROUP = {'M009': 'border|tile', 'M045': 'count|tile', 'M025': 'fg|tile'}
heldout = set(D['situations']['heldout'])
# column cue from Len's own mechanism groups (the verb of the group name); the aligner (v1, training pairs) gives the row
VERB2COL = {'tile': 'tile', 'stamp': 'stamp', 'decorate': 'stamp', 'copy': 'stamp', 'stamp / decorate': 'stamp',
            'extend': 'extend', 'ray': 'extend', 'project': 'extend', 'connect': 'extend', 'draw': 'extend', 'path': 'extend',
            'reflect': 'mirror', 'recolour': 'recolour', 'fill': 'fill', 'complete': 'fill', 'move': 'move', 'sort': 'move',
            'crop': 'extract', 'select': 'extract'}
gname = {g['id']: g.get('name', '') for g in D['groups']}
def verbcol(t):
    g = tg.get(t)
    if not g: 
        for gg in D['groups']:
            if any(m[0] == t for m in gg.get('members', [])): g = gg['id']; break
    n = gname.get(g, '')
    if n.startswith('solved'): return None
    return VERB2COL.get(n.split('.')[0].split(' — ')[0].strip())
place = {}
for t, m in members.items():
    if t in heldout: continue
    al = [k for k, v in m.items() if v.startswith('aligned')]
    vc = verbcol(t)
    for sid in ('S_stamping', 'S_projection', 'S_symmetry', 'S_tiling'):
        if sid in al:
            if sid == 'S_tiling':
                cell = TILE_BY_GROUP.get(tg.get(t)) or ('norow|' + (vc or 'tile'))
            else:
                cell = SIT2CELL[sid]
                if vc and vc != cell.split('|')[1]: cell = 'norow|' + vc
            place[t] = cell
            break
held_cells = {}   # Len 19:00 EDT: the hidden T86 test tasks are no longer counted in the cells (T86 closed at placement)
tg_all = {}
for g in D['groups']:
    for m in g.get('members', []): tg_all.setdefault(m[0], [g['id'], g.get('name', '')])
# tasks that need Len and are not placed yet: put them in their group's column, row still to choose
NEED = json.load(open('/tmp/claude-0/-home-claude/47726fdd-2a5c-5c69-a676-871abe4e1a48/scratchpad/sitpage/need_ids.json'))
for t in NEED:
    if t in place or t in heldout: continue
    g = tg_all.get(t)
    if not g or g[1].startswith('solved'): continue
    vc = VERB2COL.get(g[1].split('.')[0].split(' — ')[0].strip())
    if vc: place[t] = 'norow|' + vc
D['cells'] = {'rows': ROWS, 'cols': COLS, 'body': BODY, 'draft': DRAFT, 'place': place, 'held': held_cells,
              'group': {t: v for t, v in tg_all.items()},
              'note': 'initial placement by Claude: column from the verb of your group, row from the aligner (training pairs) when it agrees; otherwise the row is left for you'}

data = json.dumps(D, separators=(',', ':')).replace('</', '<\\/')
s = s[:a] + data + s[b:]

JS = r"""
// ---------- situations as a grid (Fable v18a D45 + Len, Oct 2 17:35 EDT): ROW = what is picked out of the input, COLUMN = how it is applied ----------
let curCell=null;let sitSel=new Set();let sitTask=null;let sitSelFor=null;let cellEdits={};let declVals=null,declWhyEl=null;
(function(){if(document.getElementById('cellcss'))return;const st=document.createElement('style');st.id='cellcss';st.textContent=`
.cgrid{border-collapse:separate;border-spacing:4px;width:auto}.cgrid th{font:600 11px var(--sans);letter-spacing:.04em;color:var(--muted);text-transform:none;padding:2px 4px;border:0;text-align:center;vertical-align:bottom}
.cgrid th.rl{text-align:right;white-space:nowrap;font-size:12px;color:var(--ink);font-weight:500;vertical-align:middle}.cgrid thead th{width:96px}
.cgrid td{padding:0;border:0}.cgrid button.cell{width:96px;min-height:46px;border:1px solid var(--line);border-radius:6px;background:var(--panel);font:12px var(--mono);color:var(--muted);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px;cursor:pointer}
.cgrid button.cell.full{color:var(--ink);background:var(--bg)}.cgrid button.cell:hover{border-color:var(--accent)}.cgrid button.cell.on{border:2px solid var(--accent)}
.cgrid button.cell.target{border-style:dashed;border-color:var(--accent)}.cgrid .nyou{color:var(--unsure);font-weight:600}.cgrid .why{font-size:10px;color:var(--accept)}
.bodyrow{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}.bodyrow .slot{flex:1 1 150px;border:1px solid var(--line);border-radius:6px;padding:6px 8px;background:var(--bg)}
.bodyrow .k{font:600 11px var(--sans);letter-spacing:.06em;color:var(--muted)}.bodyrow .v{font-size:13px}.tabs{flex-wrap:wrap}`;document.head.append(st)})();
const CID=(r,c)=>r+'|'+c;
function rowsCols(){const C=D.cells;const rows=C.rows.slice(),cols=C.cols.slice();Object.values(dec).forEach(d=>{if(d&&d.kind==='axis'){const L=d.axis==='row'?rows:cols;if(!L.some(x=>x[0]===d.id))L.splice(d.axis==='row'?L.length-1:L.length,0,d.axis==='row'?[d.id,d.label]:[d.id,d.label,[['what','what is picked out','WHO',1],['where','where it goes','WHERE',0],['until','how far / until','UNTIL',0],['colour','colour','HOW',0],['how','how (direction, count, corner …)','MANNER',0]]])}});return [rows,cols]}
function cellOf(t){const d=dec['PLACE_'+t];if(d)return d.cell||null;return D.cells.place[t]||null}
function cellName(id,rows,cols){if(id==='__unplaced__')return 'Not placed yet';const [r,c]=id.split('|');const R=rows.find(x=>x[0]===r),Co=cols.find(x=>x[0]===c);return (R?R[1]:r)+' × '+(Co?Co[1]:c)}
async function placeTasks(ts,cell){for(const t of ts){const id='PLACE_'+t;if(dec[id]&&dec[id].status==='submitted')continue;const [r,c]=cell?cell.split('|'):[null,null];const d={kind:'cell_label',task:t,cell:cell,row:r,col:c,reviewer:'len',ts:new Date().toISOString(),test_seen:false,status:'draft',proposal:'submitted'};dec[id]=d;if(db){try{await db.collection('decisions').doc(id).set(d)}catch(e){saveMsg('save failed: '+(e.code||e))}}}sitSel=new Set();saveMsg(ts.length+' task'+(ts.length===1?'':'s')+(cell?' placed':' removed'));render()}
function colArgs(c){const [rows,cols]=rowsCols();const C0=cols.find(x=>x[0]===c);return (C0&&C0[2])||[['what','what is picked out','WHO',1],['where','where it goes','WHERE',0],['until','how far / until','UNTIL',0],['colour','colour','HOW',0],['how','how (direction, count, corner …)','MANNER',0]]}
function argLabel(v){if(v==='train')return 'the same in all examples';if(v==='own')return 'own colour';const [rows]=rowsCols();const R=rows.find(x=>x[0]===v);return R?R[1]:(v||'—')}
function cellDecl(cell){const d=dec['CELL_'+cell.replace('|','__')];if(d&&d.args)return {args:d.args,why:d.why||'',saved:true,ts:d.ts};const [r,c]=cell.split('|');const dr=(D.cells.draft||{})[cell];const args={};colArgs(c).forEach(a=>{args[a[0]]=(dr&&dr.args[a[0]]!=null)?dr.args[a[0]]:((a[3]&&dr)?r:'')});return {args,why:(dr&&dr.why)||(d&&d.why)||'',saved:false,src:dr&&dr.src}}
async function saveCell(cell,args,why){const id='CELL_'+cell.replace('|','__');const [r,c]=cell.split('|');const six={WHAT:c,WHY:why};colArgs(c).forEach(a=>{six[a[2]]=args[a[0]]||'unspecified'});
  const d={kind:'cell',form:'v19',cell,row:r,col:c,how:c,args,why,six_slot:six,reviewer:'len',ts:new Date().toISOString(),status:'draft',proposal:'submitted',g82:why?'declared':'draft (no WHY)'};dec[id]=d;render();if(db){try{await db.collection('decisions').doc(id).set(d);saveMsg('submitted')}catch(e){saveMsg('save failed: '+(e.code||e))}}}
function whyOf(cell){const d=dec['CELL_'+cell.replace('|','__')];return d&&d.args?d.why:''}
function exampleOf(t){if(!window.__PX){const PX={};(D.groups||[]).forEach(gg=>(gg.members||[]).forEach(m=>{if(!PX[m[0]])PX[m[0]]=[m[1],m[2]]}));window.__PX=PX}
  if(window.__PX[t])return window.__PX[t];if(TASKS&&TASKS[t]&&TASKS[t].train&&TASKS[t].train[0])return TASKS[t].train[0];if(!TASKS&&!tasksErr)loadTasks().then(()=>{if(tab==='cats')render()});return null}
function gridCounts(){const C=D.cells;if(!C)return null;const held=new Set(D.situations.heldout||[]);const all=new Set([...Object.keys(C.place),...Object.keys(needMap())]);Object.values(dec).forEach(d=>{if(d&&d.kind==='cell_label')all.add(d.task)});let pl=0,un=0;all.forEach(t=>{if(held.has(t))return;cellOf(t)?pl++:un++});return [pl,un]}
const MANNERS=['in place of the marker (replacing it)','centred on the marker','at a fixed offset from the marker','next to it (touching)','in the direction it points','toward the target','in all 4 directions','along the diagonals','once per counted item','at each corner'];
function rowUsed(vals,r){const [rows_]=rowsCols();const known=new Set(['','train','own',...MANNERS,...rows_.map(x=>x[0])]);return Object.values(vals).some(v=>v===r||(v&&!known.has(v)))}
function taskStatus(t){if((D.solved||[]).includes(t))return 'build';if(typeof lineSolved==='function'&&lineSolved(t))return 'line';if(needMap()[t])return 'need';return 'open'}
function gName(gi){return gi?gi[0]+' · '+String(gi[1]||'').replace(/\s*—\s*residual$/,''):'no group'}
function statusChip(tk,r0){const st=taskStatus(tk);const ib=el('button','chip',tk);ib.onclick=()=>selectSitTask(tk);r0.append(ib);if(st==='open')ib.title='unsolved ARC-1 example, not on your list';
  if(st==='need'){ib.style.borderColor='var(--unsure)';ib.style.color='var(--unsure)';ib.title='needs you'}
  else if(st==='build'||st==='line'){ib.style.borderColor='var(--accept)';ib.style.color='var(--accept)';ib.style.borderWidth='2px';const lb=el('span',null,st==='build'?'solved':'solved with your help');lb.style.cssText='font-size:11px;color:var(--accept);font-weight:600';ib.title=st==='build'?'solved by the build':'your line solves it';r0.append(lb)}}
async function unplace(ts){for(const t of ts){const id='PLACE_'+t;delete dec[id];if(db){try{await db.collection('decisions').doc(id).delete()}catch(e){saveMsg('undo failed: '+(e.code||e))}}}saveMsg(ts.length+' task'+(ts.length===1?'':'s')+' put back where '+(ts.length===1?'it':'they')+' started');render()}
async function clearCell(cell){const id='CELL_'+cell.replace('|','__');delete dec[id];delete cellEdits[cell];if(db){try{await db.collection('decisions').doc(id).delete()}catch(e){saveMsg('clear failed: '+(e.code||e))}}saveMsg('submitted definition cleared');render()}
function addedHere(cell){return Object.values(dec).filter(d=>d&&d.kind==='cell_label'&&d.cell===cell&&d.reviewer==='len').map(d=>d.task)}
let clearArm=null;
function canSubmit(cell){const DC=cellDecl(cell);const E=cellEdits[cell];const norm=(a,w)=>JSON.stringify([Object.keys(a||{}).sort().map(k=>[k,a[k]||'']),(w||'').trim()]);
  if(E){const A2=Object.assign({},DC.args,E.args);if(!DC.saved)return !!(E.why||'').trim()||Object.values(A2).some(v=>v);return norm(A2,E.why)!==norm(DC.args,DC.why)}
  return !DC.saved&&(!!(DC.why||'').trim()||Object.values(DC.args||{}).some(v=>v))}
function updateSubmit(){const b=document.getElementById('submitbtn');if(!b||!curCell)return;const ok=!!db&&canSubmit(curCell);b.disabled=!ok;b.title=ok?'Save the parts and WHY for this cell':'Nothing new to submit';const st=document.getElementById('submitstate');if(st){const DC=cellDecl(curCell);st.textContent=cellEdits[curCell]&&canSubmit(curCell)?'changes not submitted yet':(DC.saved?'submitted':'not submitted yet')}}
function dictList(kind){const H=x=>String(x).replace(/_/g,' ').replace(/\s+/g,' ').trim().toLowerCase();const out=new Set();const V=(D.situations&&D.situations.vocab)||{};const VD=(D.situations&&D.situations.vocab_desc)||{};
  if(kind==='col'){MANNERS.forEach(v=>out.add(H(v)));(D.mech_vocab||[]).forEach(v=>out.add(H(v)));(V.WHAT||[]).forEach(v=>{out.add(H(v));if(VD['WHAT:'+v])out.add(H(VD['WHAT:'+v]))});(D.groups||[]).forEach(g=>{const n=String(g.name||'');if(!n.startsWith('solved'))out.add(H(n.split('.')[0].split(' — ')[0]))})}
  else{['WHO','WHERE','UNTIL'].forEach(k=>(V[k]||[]).forEach(v=>{out.add(H(v));if(VD[k+':'+v])out.add(H(VD[k+':'+v]))}));Object.keys(D.concept_freq||{}).forEach(c=>out.add(H(c)));(D.known_vocab||[]).forEach(v=>{const m=/^category: (.*)$/.exec(v);if(m)out.add(H(m[1]))});const [rows_]=rowsCols();rows_.forEach(r=>out.add(H(r[1])))}
  return [...out].filter(x=>x&&x.length<60).sort()}
function ensureList(id,kind){let dl=document.getElementById(id);if(!dl){dl=document.createElement('datalist');dl.id=id;document.body.append(dl)}if(dl.dataset.kind!==kind){dl.textContent='';dictList(kind).forEach(v=>{const o=document.createElement('option');o.value=v;dl.append(o)});dl.dataset.kind=kind}return id}
let cellChecks={};(function subChecks(){if(typeof db!=='undefined'&&db){try{db.collection('cellchecks').onSnapshot(q=>{const n={};q.docs.forEach(x=>{n[x.id]=x.data()});cellChecks=n;if(tab==='cats')render()},()=>{})}catch(e){}}else setTimeout(subChecks,1500)})();
function showPanel(){setTimeout(()=>{const e=document.getElementById('cellpanel');if(e)e.scrollIntoView({behavior:'smooth',block:'start'})},0)}
function selectSitTask(t){sitTask=t;render();setTimeout(()=>{const e=document.getElementById('sittask');if(e)e.scrollIntoView({behavior:'smooth',block:'start'})},0)}
function gloss(k,v){return (D.situations.vocab_desc||{})[k+':'+v]||''}
function renderCells(S){const C=D.cells;if(!C)return;const [rows,cols]=rowsCols();const need=Object.keys(needMap()).sort();const held=new Set(D.situations.heldout||[]);
  const all=new Set([...Object.keys(C.place),...need]);Object.values(dec).forEach(d=>{if(d&&d.kind==='cell_label')all.add(d.task)});
  const byCell={};all.forEach(t=>{if(held.has(t))return;const c=cellOf(t);(byCell[c||'__unplaced__']=byCell[c||'__unplaced__']||[]).push(t)});
  const nset=new Set(need);const nPlaced=need.filter(t=>cellOf(t)).length;const nNorow=need.filter(t=>(cellOf(t)||'').startsWith('norow|')).length;
  const top=el('div','card');const hd=el('div','ghead');hd.append(el('h2',null,'Situations'));{const parts=[];if(nPlaced-nNorow)parts.push((nPlaced-nNorow)+' in a cell');if(nNorow)parts.push(nNorow+' in a cell, row still to choose');if(need.length-nPlaced)parts.push((need.length-nPlaced)+' not placed yet');hd.append(el('span','stat',need.length+' tasks need you = '+parts.join(' + ')))}top.append(hd);
  top.append(Object.assign(el('div','help','Task colours: yellow = needs you (an ARC-2 task the build does not solve yet); green = solved (by the build or by your line’s program); plain = an unsolved ARC-1 example, not on your list. In the cells, yellow counts are tasks that need you, grey counts are the examples. Column = how it is applied. Row = what is picked out of the input; inside a cell you choose which part of the action it fills. Click a cell: its definition and tasks open below the grid. To move tasks: tick them, then click the cell they belong in.'),{style:'margin-top:4px'}));
  if(sitSel.size){const bar=el('div','row');bar.style.cssText='gap:8px;margin:8px 0;padding:6px 8px;border:1px solid var(--accent);border-radius:6px';bar.append(el('b',null,sitSel.size+' selected: click a cell to move them there'));const rm=el('button','btn','Remove from their cell');rm.disabled=!db;rm.onclick=()=>placeTasks([...sitSel],null);const cl=el('button','btn','Clear');cl.onclick=()=>{sitSel=new Set();render()};bar.append(rm,cl);top.append(bar)}
  const tw=el('div','tbl');const t=el('table','cgrid');const th=document.createElement('thead');const hr=document.createElement('tr');hr.append(el('th'));cols.forEach(c=>{const h=el('th',null,c[1]);hr.append(h)});th.append(hr);t.append(th);const tb=document.createElement('tbody');
  rows.forEach(r=>{const tr=document.createElement('tr');tr.append(el('th','rl',r[1]));cols.forEach(c=>{const id=CID(r[0],c[0]);const ts=byCell[id]||[];const nN=ts.filter(x=>nset.has(x)).length;const nD=ts.length-nN;const hk=(C.held||{})[id]||0;const wy=whyOf(id);
      const b=el('button','cell'+((ts.length||hk||C.body[id])?' full':'')+(curCell===id?' on':'')+(sitSel.size?' target':''));
      if(nN)b.append(el('span','nyou',nN+' need you'));if(nD)b.append(el('span',null,nD+' task'+(nD===1?'':'s')));if(hk)b.append(el('span',null,'+'+hk+' held out'));if(wy){const sw=el('span','why','submitted ✓');sw.title='You submitted a definition (parts + WHY) for this cell';b.append(sw)}if(!ts.length&&!hk)b.append(el('span',null,'·'));
      b.title=cellName(id,rows,cols);b.onclick=()=>{if(sitSel.size){placeTasks([...sitSel],id);curCell=id}else{curCell=curCell===id?null:id;render();if(curCell)showPanel()}};const td=document.createElement('td');td.append(b);tr.append(td)});tb.append(tr)});
  t.append(tb);tw.append(t);top.append(tw);
  {const nu=(byCell['__unplaced__']||[]).length;const ub=el('button','btn'+(curCell==='__unplaced__'?' primary':''),'Not placed yet: '+nu+' tasks'+(nu!==need.length-nPlaced?' ('+(need.length-nPlaced)+' need you)':''));ub.style.marginTop='8px';ub.onclick=()=>{if(sitSel.size)return;curCell=curCell==='__unplaced__'?null:'__unplaced__';render();if(curCell)showPanel()};top.append(ub)}
  {const ad=el('div','row');ad.style.cssText='gap:6px;margin-top:8px;align-items:center';ad.append(el('span','help','Add a'));const kind=el('select');kind.style.cssText='font:12.5px var(--sans);padding:2px';kind.append(new Option('row (what is picked out)','row'),new Option('column (how it is applied)','col'));const nm=el('input');nm.type='text';nm.placeholder='start typing: suggestions from the vocabulary';nm.setAttribute('list',ensureList('axisdict_'+kind.value,kind.value));kind.onchange=()=>{nm.setAttribute('list',ensureList('axisdict_'+kind.value,kind.value))};nm.style.cssText='font:13px var(--sans);padding:3px 6px;max-width:240px';const ok=el('button','btn','Add');ok.disabled=!db;
    ok.onclick=async()=>{const n=nm.value.trim();if(!n)return;const idv='u_'+n.toLowerCase().replace(/[^a-z0-9]+/g,'_').slice(0,30);const d={kind:'axis',axis:kind.value,id:idv,label:n,reviewer:'len',ts:new Date().toISOString(),status:'draft',proposal:'submitted'};const did='AXIS_'+kind.value+'_'+idv;dec[did]=d;try{await db.collection('decisions').doc(did).set(d)}catch(e){}render()};ad.append(kind,nm,ok);top.append(ad)}
  S.append(top);
  if(!curCell)return;
  const cc=el('div','card');cc.id='cellpanel';const gh=el('div','ghead');gh.append(el('h2',null,cellName(curCell,rows,cols)));const ts=(byCell[curCell]||[]);const hk=(C.held||{})[curCell]||0;
  gh.append(el('span','stat',(ts.filter(x=>nset.has(x)).length?ts.filter(x=>nset.has(x)).length+' need you · ':'')+(ts.length-ts.filter(x=>nset.has(x)).length)+' design tasks'+(hk?' · '+hk+' held out (test set, hidden)':'')));
  const nv=el('div','nav');const cb=el('button','btn','↑ Back to grid');cb.onclick=()=>{curCell=null;render();window.scrollTo({top:0,behavior:'smooth'})};nv.append(cb);gh.append(nv);cc.append(gh);
  if(curCell!=='__unplaced__'){
    {const [r0c,c0c]=curCell.split('|');const DC=cellDecl(curCell);const A=colArgs(c0c);const E=cellEdits[curCell];const vals=Object.assign({},DC.args,E?E.args:{});const keep=()=>{cellEdits[curCell]={args:vals,why:declWhyEl?declWhyEl.value:DC.why};const w=document.getElementById('rowwarn');if(w)w.hidden=rowUsed(vals,r0c);updateSubmit()};
     const wb=el('div','whybox');wb.style.cssText='margin-top:8px;border:1px solid var(--line);border-radius:8px;padding:8px 10px;background:var(--bg)';
     const fm=el('div','row');fm.style.cssText='gap:6px;margin-top:6px;align-items:center;flex-wrap:wrap;font-size:13.5px';const C0=cols.find(x=>x[0]===c0c);fm.append(el('b',null,(C0?C0[1]:c0c)+' ('));
     A.forEach((ar,i)=>{const g=el('span');g.style.cssText='display:inline-flex;gap:4px;align-items:center';g.append(el('span','help',ar[1]+' ='));
       {const se=el('select');se.style.cssText='font:12.5px var(--sans);padding:2px;max-width:220px';se.title=ar[1];const [rows_]=rowsCols();se.append(new Option('choose…',''));const og=l=>{const g=document.createElement('optgroup');g.label=l;se.append(g);return g};{const g1=og('Fixed: the same in all examples');g1.append(new Option('the same in all examples (learned from all examples together)','train'))}if(ar[2]==='MANNER'){const g2=og('How');MANNERS.forEach(m=>g2.append(new Option(m,m)))}else{const g2=og('Read from each input (differs from example to example)');if(ar[2]==='HOW')g2.append(new Option('own colour (of each object)','own'));rows_.filter(x=>x[0]!=='norow').forEach(x=>g2.append(new Option(x[1]+(x[0]===r0c?' (this cell)':''),x[0])))}{const g3=og('Your own');g3.append(new Option('other: type your own…','__other__'))}
         const known=v=>[...se.options].some(o=>o.value===v);const ti=el('input');ti.type='text';ti.placeholder='type it';ti.setAttribute('list',ensureList(ar[2]==='MANNER'?'axisdict_col':'axisdict_row',ar[2]==='MANNER'?'col':'row'));ti.style.cssText='font:12.5px var(--sans);padding:2px 4px;width:150px';
         if(vals[ar[0]]&&!known(vals[ar[0]])){se.value='__other__';ti.value=vals[ar[0]]}else{se.value=vals[ar[0]]||'';ti.hidden=true}
         se.onchange=()=>{if(se.value==='__other__'){ti.hidden=false;vals[ar[0]]=ti.value.trim();ti.focus()}else{ti.hidden=true;vals[ar[0]]=se.value}keep()};ti.oninput=()=>{vals[ar[0]]=ti.value.trim();keep()};g.append(se,ti)}
       fm.append(g);if(i<A.length-1)fm.append(el('span',null,','))});fm.append(el('b',null,')'));wb.append(fm);if(r0c!=='norow'){const w=el('div','help');w.id='rowwarn';w.style.cssText='margin-top:6px;color:var(--unsure);display:flex;flex-wrap:wrap;gap:6px;align-items:center';w.append(el('span',null,'This cell’s property ('+argLabel(r0c)+') is not used yet. Use it as:'));A.filter(ar=>ar[2]!=='MANNER').forEach(ar=>{const ub=el('button','btn',ar[1]);ub.style.cssText='font-size:12px;padding:2px 8px';ub.onclick=()=>{vals[ar[0]]=r0c;keep();render()};w.append(ub)});w.append(el('span',null,'— or choose / type each part in the menus above, or move these tasks to another row.'));w.hidden=rowUsed(vals,r0c);wb.append(w)}
     const wl=el('div','k','WHY: what stays true in all examples and in the new one');wl.style.marginTop='8px';wb.append(wl);const wi=el('input');wi.type='text';wi.value=E&&E.why!=null?E.why:DC.why;wi.oninput=keep;declVals=vals;declWhyEl=wi;wi.placeholder='e.g. one copy of the unit at every anchor';wi.style.marginTop='4px';wb.append(wi);
     const hn=el('div','help','Each part is either read from each input (it can differ from example to example), the same in all examples (learned from all examples together), or typed by you. Put this cell’s row in the part where it belongs. If the tasks need two different rows for one part, they are two situations: add a row and move some tasks there.');hn.style.marginTop='6px';wb.append(hn);
     cc.append(wb);{const ck=cellChecks['CELL_'+curCell.replace('|','__')];if(ck&&ck.rows&&ck.rows.length){const cb=el('div');cb.style.cssText='margin-top:8px;border-left:3px solid '+(ck.ok?'var(--accept)':'var(--unsure)')+';padding:6px 10px;background:var(--bg);font-size:13px';cb.append(el('b',null,'Check of your submitted definition'+(ck.at?' ('+ck.at+')':'')+': '));ck.rows.forEach(r=>{const d=el('div');d.style.marginTop='3px';d.append(el('span','mono',r.task+' '),document.createTextNode(r.result+(r.why?' — '+r.why:'')));cb.append(d)});if(ck.next)cb.append(Object.assign(el('div','help',ck.next),{style:'margin-top:4px'}));cc.append(cb)}}}
    const bd=C.body[curCell];if(bd){const h=el('div','help','What the aligner read from these tasks’ training pairs (for comparison; nothing to write):');h.style.marginTop='8px';cc.append(h);const br=el('div','bodyrow');['WHO','WHERE','HOW','UNTIL'].forEach(k=>{if(!bd[k])return;const b=el('div','slot');b.append(el('div','k',k),el('div','v',gloss(k,bd[k])||bd[k].replace(/_/g,' ')));br.append(b)});cc.append(br)}}
  if(ts.length){if(sitSelFor!==curCell){sitSel=new Set();sitSelFor=curCell}
    const h3=el('h3',null,'Tasks in this cell ('+ts.length+') · first example of each · tick to move elsewhere · click a picture for details');h3.style.marginTop='14px';cc.append(h3);
    const GRP=t=>((C.group||{})[t]||['~',''])[0];const mm=el('div','members');let lastG=null;
    const gc={};ts.forEach(t=>{if(!nset.has(t))gc[GRP(t)]=(gc[GRP(t)]||0)+1});
    const SEC=t=>nset.has(t)?'0':(gc[GRP(t)]>1?'1'+GRP(t):'2');   // need you · groups with 2+ tasks here · single tasks (group shown on the card)
    const secName=k=>k==='0'?'Need you':k==='2'?'Single tasks from other groups':gName((C.group||{})[ts.find(x=>SEC(x)===k)]);
    ts.sort((a,b)=>SEC(a).localeCompare(SEC(b))||a.localeCompare(b)).forEach(tk=>{
      if(SEC(tk)!==lastG){lastG=SEC(tk);const gts=ts.filter(x=>SEC(x)===lastG);const hd0=el('div','help');hd0.style.cssText='grid-column:1 / -1;margin-top:10px;border-top:2px solid var(--muted);padding-top:7px;font-weight:600;color:var(--ink)';hd0.textContent=secName(lastG)+' ('+gts.length+') ';{const allOn=gts.every(x=>sitSel.has(x));const ta=el('button','btn',allOn?'untick these':'tick all '+gts.length);ta.style.cssText='font-size:11px;padding:1px 7px;margin-left:6px';ta.onclick=()=>{gts.forEach(x=>allOn?sitSel.delete(x):sitSel.add(x));render()};hd0.append(ta)}mm.append(hd0)}
      const card=el('div','mem');card.style.cursor='default';if(sitTask===tk){card.style.outline='2px solid var(--accent)';card.style.outlineOffset='3px'}
      const r0=el('div','row');r0.style.gap='6px';const cbx=document.createElement('input');cbx.type='checkbox';cbx.checked=sitSel.has(tk);cbx.onchange=()=>{cbx.checked?sitSel.add(tk):sitSel.delete(tk);render()};r0.append(cbx);
      statusChip(tk,r0);{const pd=dec['PLACE_'+tk];if(pd&&pd.cell===curCell&&pd.reviewer==='len'){const ub=el('button','btn','↩ put back');ub.title='Undo: move it back to where it started';ub.style.cssText='font-size:11px;padding:1px 6px';ub.disabled=!db;ub.onclick=()=>unplace([tk]);r0.append(ub)}}card.append(r0);if(SEC(tk)!=='1'){const gi=(C.group||{})[tk];if(gi){const gl=el('div','help',gName(gi));gl.style.cssText='font-size:11px;line-height:1.25';card.append(gl)}}
      const ex=exampleOf(tk);if(ex){const pe=pairEl(ex[0],ex[1],80);pe.style.cursor='pointer';pe.onclick=()=>selectSitTask(tk);card.append(pe)}mm.append(card)});
    cc.append(mm)}
  else cc.append(Object.assign(el('div','help',hk?'Only held-out test tasks are in this cell; they stay hidden. Your tasks are listed below.':'No tasks in this cell yet. All other tasks are listed below.'),{style:'margin-top:10px'}));
  if(curCell!=='__unplaced__'){
    const others=[...all].filter(t=>!held.has(t)&&(cellOf(t)||'__unplaced__')!==curCell);
    const h4=el('h3',null,'All other tasks ('+others.length+') · grouped by the cell they are in now · tick the ones that belong here');h4.style.marginTop='18px';cc.append(h4);
    const mvb=el('div','row');mvb.style.cssText='gap:8px;margin:6px 0;position:sticky;top:env(safe-area-inset-top,0px);z-index:2;background:var(--panel);padding:6px 0';
    const selOwn=[...sitSel].filter(t=>(cellOf(t)||'__unplaced__')===curCell),selOther=[...sitSel].filter(t=>(cellOf(t)||'__unplaced__')!==curCell);const nsel=selOther.length;const mv=el('button','btn'+(nsel?' primary':''),nsel?'Add '+nsel+' task'+(nsel===1?'':'s')+' selected below':'Add tasks selected below');mv.disabled=!db||!nsel;mv.onclick=()=>placeTasks(selOther,curCell);mvb.append(mv);if(selOwn.length){const rb=el('button','btn','Remove '+selOwn.length+' selected task'+(selOwn.length===1?'':'s')+' from this cell');rb.style.cssText='border-color:var(--reject);color:var(--reject)';rb.title='They go to Not placed yet';rb.disabled=!db;rb.onclick=()=>placeTasks(selOwn,null);mvb.append(rb)}{const sb=el('button','btn primary','Submit');sb.id='submitbtn';sb.disabled=!db||!canSubmit(curCell);sb.title=sb.disabled?'Nothing new to submit':'Save the parts and WHY for this cell';sb.onclick=()=>{const v=declVals||cellDecl(curCell).args,w=declWhyEl?declWhyEl.value.trim():cellDecl(curCell).why;delete cellEdits[curCell];saveCell(curCell,v,w)};mvb.append(sb);const DCs=cellDecl(curCell);if(cellEdits[curCell]){const dc=el('button','btn','Discard changes');dc.title='Put the parts and WHY back to what was there before your edits';dc.onclick=()=>{delete cellEdits[curCell];render()};mvb.append(dc)}{const ah=addedHere(curCell);if(ah.length){const pb=el('button','btn','Put back the '+ah.length+' task'+(ah.length===1?'':'s')+' you added');pb.title='Each goes back to where it started';pb.disabled=!db;pb.onclick=()=>unplace(ah);mvb.append(pb)}}if(DCs.saved){const armed=clearArm===curCell;const cb2=el('button','btn',armed?'Click again to clear':'Clear submitted definition');if(armed){cb2.style.borderColor='var(--reject)';cb2.style.color='var(--reject)'}cb2.disabled=!db;cb2.onclick=()=>{if(clearArm===curCell){clearArm=null;clearCell(curCell)}else{clearArm=curCell;render()}};mvb.append(cb2)}}
    if(sitSel.size){const cl=el('button','btn','Clear ticks');cl.onclick=()=>{sitSel=new Set();render()};mvb.insertBefore(cl,mvb.children[1]||null)}cc.append(mvb);
    const GRP=t=>((C.group||{})[t]||['~',''])[0];const byC={};others.forEach(t=>{const c=cellOf(t)||'__unplaced__';(byC[c]=byC[c]||[]).push(t)});
    const order=Object.keys(byC).sort((a,b)=>(a==='__unplaced__')-(b==='__unplaced__')||cellName(a,rows,cols).localeCompare(cellName(b,rows,cols)));
    const mo=el('div','members');
    order.forEach(c=>{const ts2=byC[c].sort((a,b)=>((nset.has(b))-(nset.has(a)))||GRP(a).localeCompare(GRP(b))||a.localeCompare(b));
      const hd0=el('div','help');hd0.style.cssText='grid-column:1 / -1;margin-top:10px;border-top:2px solid var(--muted);padding-top:7px;font-weight:600;color:var(--ink)';hd0.textContent=cellName(c,rows,cols)+' ('+ts2.length+(ts2.filter(x=>nset.has(x)).length?', '+ts2.filter(x=>nset.has(x)).length+' need you':'')+') ';{const allOn=ts2.every(x=>sitSel.has(x));const ta=el('button','btn',allOn?'untick these':'tick all '+ts2.length);ta.style.cssText='font-size:11px;padding:1px 7px;margin-left:6px';ta.onclick=()=>{ts2.forEach(x=>allOn?sitSel.delete(x):sitSel.add(x));render()};hd0.append(ta)}mo.append(hd0);
      ts2.forEach(tk=>{const card=el('div','mem');card.style.cursor='default';if(sitTask===tk){card.style.outline='2px solid var(--accent)';card.style.outlineOffset='3px'}
        const r0=el('div','row');r0.style.gap='6px';const cbx=document.createElement('input');cbx.type='checkbox';cbx.checked=sitSel.has(tk);cbx.onchange=()=>{cbx.checked?sitSel.add(tk):sitSel.delete(tk);render()};r0.append(cbx);
        statusChip(tk,r0);card.append(r0);
        const gi=(C.group||{})[tk];if(gi){const gl=el('div','help',gName(gi));gl.style.cssText='font-size:11px;line-height:1.25';card.append(gl)}
        const ex=exampleOf(tk);if(ex){const pe=pairEl(ex[0],ex[1],80);pe.style.cursor='pointer';pe.onclick=()=>selectSitTask(tk);card.append(pe)}mo.append(card)})});
    cc.append(mo)}
  const s2=el('span','save','');s2.id='save';cc.append(s2);S.append(cc)}
function renderSitTask(S){const c=el('div','card');c.id='sittask';const t=sitTask;
  if(!t){c.append(el('h2',null,'Task details'));c.append(el('div','help','Click a task picture above to see it here: all its examples, your line and its generated expansion, Claude’s reading.'));S.append(c);return}
  if(!TASKS){c.append(el('h2',null,'Task '+t));c.append(el('div','banner',tasksErr?('Task data failed to load: '+tasksErr):'Loading task…'));S.append(c);if(!tasksErr)loadTasks().then(()=>{if(tab==='cats')render()});return}
  const T=TASKS[t];const gh=el('div','ghead');gh.append(el('h2','mono',t));
  const SVd=(D.solved||[]).includes(t),LSd=typeof lineSolved==='function'&&lineSolved(t);gh.append(el('span','pill '+(SVd||LSd?'ok':''),SVd?'solved by the build':(LSd?'solved with your help':'not solved')));const nr=needMap()[t];if(nr&&!SVd)gh.append(el('span','pill wait','needs you'));
  const g=G.find(x=>(x.members||[]).some(m=>m[0]===t));if(g)gh.append(el('span','stat',g.id+' · '+String(g.name||'').replace(/\s*—\s*residual$/,'')));
  const nv=el('div','nav');const ob=el('button','btn','Open in Task tab ↗');ob.onclick=()=>{backTo={tab:'cats',label:'situations',scroll:window.scrollY};openTask(t)};const cb=el('button','btn','Close');cb.onclick=()=>{sitTask=null;render()};nv.append(ob,cb);gh.append(nv);c.append(gh);
  {const [rows,cols]=rowsCols();const ce=cellOf(t);const cr=el('div','row');cr.style.cssText='gap:6px;margin-top:6px;align-items:center';cr.append(el('span','help','Situation:'));if(!ce)cr.append(el('span','help','not placed yet'));else{const b=el('button','chip',cellName(ce,rows,cols));b.onclick=()=>{curCell=ce;render();showPanel()};cr.append(b)}c.append(cr)}
  const tx=el('div','cols');tx.style.marginTop='10px';
  const L=el('div');L.append(el('h3',null,'Your line (edit it here to revise) and its check'));{const lg_=g||{id:'T_'+t};const tl=(typeof taskLine==='function')?taskLine(lg_,t,null,(typeof isLocked==='function')?isLocked(lg_.id):false,false):null;if(tl)L.append(tl);else L.append(el('div','help','No line for this task yet.'))}
  const R=el('div');R.append(el('h3',null,'Claude’s reading of the rule'));const ab=(D.abs||{})[t];
  if(ab){if(ab.mechanism){const pre=el('div','mono');pre.style.cssText='font-size:12.5px;white-space:pre-wrap';pre.textContent=ab.mechanism;R.append(pre)}
    if(ab.roles&&typeof ab.roles==='object'){const rl=el('div','roles');rl.style.marginTop='6px';Object.entries(ab.roles).forEach(([k,v])=>{const r=el('span','role');r.append(el('b',null,k+': '),document.createTextNode(String(v)));rl.append(r)});R.append(rl)}}
  else R.append(el('div','help','No reading stored for this task.'));
  tx.append(L,R);c.append(tx);
  if(T){const h3=el('h3',null,'Training pairs');h3.style.marginTop='14px';c.append(h3);const ps=el('div','pairs');T.train.forEach(p=>ps.append(pairEl(p[0],p[1],150)));c.append(ps);c.append(testPairs(t,T.split,T.test,150))}
  else c.append(el('div','help','This task is not in the review data.'));
  S.append(c)}
"""
anchor = 'function renderCats(V){'
assert s.count(anchor) == 1
s = s.replace(anchor, JS + '\n' + anchor)
# Len 19:10 EDT: "ARC review" (no "group"); grid totals without "placed"; one batch count
for o_, n_ in (("<h1>ARC group review</h1>", "<h1>ARC review</h1>"), ("<title>ARC Group Review</title>", "<title>ARC Review</title>"),
               ("document.createTextNode(' batched · '+Object.keys(batches).length+' batches'))", "document.createTextNode(' batched'))")):
    assert s.count(o_) == 1, o_
    s = s.replace(o_, n_)
# Len 00:48 UTC Oct 3: a line can "solve" a task only because the expansion filled in a part the line does not state
for o_, n_ in (("const head=ok?'✓ your line solves this task':", "const head=ok?'✓ the program built from your line solves this task':"),
               ("if(ok)w.append(el('div','help','It is not in the submitted build (V29) yet,",
                "if(ok&&x.reading&&x.reading.generator){const rd=el('div');rd.style.cssText='font-size:12.5px;margin-top:4px;max-width:90ch';rd.append(el('b',null,'How the machine read your line: '),document.createTextNode(x.reading.generator));w.append(rd);w.append(el('div','help','Anything here that your line does not say was filled in by the machine from the training examples.'))}if(ok&&x.reviewer_note){const rn=el('div');rn.style.cssText='font-size:12.5px;margin-top:4px;color:var(--unsure)';rn.textContent='Your note: '+x.reviewer_note;w.append(rn)}if(ok)w.append(el('div','help','It is not in the submitted build (V29) yet,")):
    assert s.count(o_) == 1, o_
    s = s.replace(o_, n_)
# Len 02:31 UTC Oct 3: 'in grid' -> 'in cell'
# Len 02:23 UTC Oct 3: "solved by your lines" in its own green pill
o_ = "const nb=el('button','pill wait',n+' need you'+(ls?' · '+ls+' solved by your lines':''));nb.style.cssText='cursor:pointer;margin-right:10px;font-size:12px';nb.title='The ARC-2 tasks the current build (V29) does not solve. Click to list them.';nb.onclick=openNeeds;st.append(nb)"
assert s.count(o_) == 1, o_
s = s.replace(o_, "const nb=el('button','pill wait',n+' need you');nb.style.cssText='cursor:pointer;margin-right:6px;font-size:12px';nb.title='The ARC-2 tasks the current build (V29) does not solve. Click to list them.';nb.onclick=openNeeds;st.append(nb);if(ls){const lb=el('button','pill ok',ls+' solved with your help');lb.style.cssText='cursor:pointer;margin-right:10px;font-size:12px;border-color:var(--accept);color:var(--accept)';lb.title='ARC-2 tasks that the programs built from your lines solve (not in the submitted build yet). Click to list the tasks.';lb.onclick=openNeeds;st.append(lb)}")
old7 = "function renderStat(){const st=document.getElementById('stat');st.textContent='';"
assert s.count(old7) == 1
s = s.replace(old7, old7 + "{const gc=gridCounts();if(gc){const gb=el('button','pill',gc[0]+' in cell · '+gc[1]+' not in cell');gb.style.cssText='cursor:pointer;margin-right:10px;font-size:12px';gb.title='Tasks placed in a cell of the Situations grid, and tasks not placed yet. Click to open the grid.';gb.onclick=()=>{tab='cats';curCell=null;render();window.scrollTo({top:0})};st.append(gb)}}")
old = "const K=mergedCats();const S=el('div','solo');V.append(S);"
assert s.count(old) == 1
s = s.replace(old, old + "renderCells(S);renderSitTask(S);return;")
old5 = "gh.append(nv);h.append(gh);S.append(h);"
assert s.count(old5) == 1
s = s.replace(old5, "gh.append(nv);h.append(gh);{const [rows_,cols_]=rowsCols();const ce=cellOf(curTask);const cr=el('div','row');cr.style.cssText='gap:6px;margin-top:8px;align-items:center';cr.append(el('span','help','Situation:'));if(!ce)cr.append(el('span','help','not placed yet'));else{const b=el('button','chip',cellName(ce,rows_,cols_));b.onclick=()=>{curCell=ce;tab='cats';render();showPanel()};cr.append(b)}h.append(cr)}S.append(h);")
# the Categories tab is now called Situations
old6 = "['cats','Categories']"
if s.count(old6) == 1: s = s.replace(old6, "['cats','Situations']")
# Len 22:47 EDT Oct 2: a task solved by a checked cell definition counts as "solved with your help" too
oL = "const lineSolved=t=>{const x=expansions[t];return !!(x&&(x.status==='fits'||x.status==='admitted'))};"
assert s.count(oL) == 1
s = s.replace(oL, "const lineSolved=t=>{const x=expansions[t];if(x&&(x.status==='fits'||x.status==='admitted'))return true;const cc=(typeof cellChecks!=='undefined'&&cellChecks)||{};return Object.keys(cc).some(k=>((cc[k]||{}).solved_tasks||[]).includes(t))};")
oT = "lb.title='ARC-2 tasks that the programs built from your lines solve (not in the submitted build yet). Click to list the tasks.'"
assert s.count(oT) == 1
s = s.replace(oT, "lb.title='ARC-2 tasks solved by programs built from your lines or your cell definitions (not in the submitted build yet). Click to list the tasks.'")
oR = "cellChecks=n;if(tab==='cats')render()"
assert s.count(oR) == 1
s = s.replace(oR, "cellChecks=n;if(tab==='cats')render();else if(typeof renderStat==='function')renderStat()")
open(OUT, 'w').write(s)
print(len(s))
