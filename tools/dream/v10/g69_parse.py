"""G69 composition parse (Fable guidance v11, T69 part 1 and the T53 re-run).

G69: "a description whose verb lifts to two schemas parses to two definitions sharing a variable; generalisation
yields the pair of tops; specialisation per half with the shared variable fixed."

Input: results/o0/v10_records.json (514 records <verb, schema, participants, generator, stop, colour_rule, params>,
parsed once under G60), results/o0/t64_frame_schema.json (20 cycle-27 frames -> schema [+ schema2]) and
results/o0/prior_concepts_v1.json (frame members).  No LLM call, no ARC grid, no solutions file.

Which records lift to two schemas (the pair is ordered later by data flow):
  own     the record's own parse already names schema2 (the verb lifted to two schemas at G60 time)
  frame   the record has one schema, belongs to a composed T64 frame (as a member task, or is the frame's own pc_
          record) and its schema is one of the frame's two; the missing half is the frame's other schema
  verb    the record has one schema, its verb is the verb of a composed T64 frame and its schema is one of that
          frame's two schemas (the verb lifts to the frame's pair)
A single-schema record in a composed frame whose schema is neither of the frame's two is counted
'frame_mismatch' and stays single (its own reading names a different schema).

How a lifted record is split (mechanical, from the record's fields only):
  * the generator is cut into segments (';' stages, then top-level calls inside a stage); each segment is scored
    against keyword lexicons of the two schemas and given to the half that scores higher (ties attach to the
    neighbouring segment's half);
  * participants are the primary schema's roles (true for all 514 records) and go to the primary half;
    params go to the half whose lexicon their key/value hits (default: primary); colour_rule 'table' goes to a
    MATCHING half, 'sequence' to a CYCLE/COUNTING half, otherwise to the second half (the one that paints last);
    the stop goes to the half holding the until(...)/stop segment, else to the generative half;
  * order: primary first, unless every segment of the other half precedes the primary's segments, or the other
    half's call is nested as a keyword argument value of the primary's call (x = count(...)): then the other
    half produces the value and comes first;
  * shared variable (one name, one type in {cells, object, colour, number, grid}): (1) an identifier that occurs
    in segments of both halves (preferring participant role names / words of participant values), else (2) the
    keyword argument that receives the nested producer call, else (3) a participant whose value text hits the
    other half's lexicon (that role is what the other half computes / consumes), else (4) the typed output of the
    first half (PATH -> its path cells, PART-WHOLE -> the selected part, COUNTING -> the count, ...);
  * a 'frame' / 'verb' lift whose record text has no segment for the second schema inherits that half's body from
    the frame's own (pc_) split, with the shared variable renamed to the member's role of the same type.
A lifted record is 'unsplit' when it has no schema, both schemas are equal, it was returned under G61, or one half
receives no evidence at all (no segment, param, colour rule or stop, and no frame half to inherit).

T53 re-run: parse rate (records with >= 1 definition carrying a schema), distinct schema tops over all definitions,
and the pair-of-tops counts of the split records (generalisation of a pair = the ordered pair of its two tops).

usage: python3 tools/dream/v10/g69_parse.py   -> results/o0/v10_records_g69.json
"""
import collections
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TOPS = ['PATH', 'LINK', 'CYCLE', 'CENTER-PERIPHERY', 'SYMMETRY', 'MATCHING', 'PART-WHOLE', 'CONTAINMENT', 'COUNTING',
        'SCALE', 'CONTACT', 'SUPPORT', 'NEAR-FAR', 'BLOCKAGE']

# keyword lexicons (lower-case regex fragments).  Only the two schemas of a record compete, so overlaps between
# schemas that never co-occur in a record are harmless.
LEX = {
    'PATH': r'\bray|cast|shoot|extend|extru|beam|trail|walk|\bstep|\blines?\b|diagonal|direction|toward|\bpath|trace'
            r'|snake|zigzag|spiral|turtle|march|sweep|propagat|outward|to (the )?(grid )?(edge|border)|until\(border'
            r'|staircase|\barm\b|\blane|homing',
    'LINK': r'connect|bridge|join|\blink|between|\bspan|wire|chain|endpoint|partner|\bpairs?\b|midpoint|both bars',
    'CYCLE': r'\btil(e|es|ed|ing)\b|repeat|period|cycl|\bmod\b|palette\[|alternat|rotate\(.*colou?r|\bshift|sequence'
             r'|continu|recur|progress|stripe|\*\s*\w|copies|every (other|k|\d)|multiple|for all k|pitch|lattice'
             r'|\bmotif',
    'CENTER-PERIPHERY': r'\bring|halo|surround|outline|\bframe\b|centre|center|concentric|stamp|\bplus\b|inflate'
                        r'|around|neighbou?r|radius|thickness|\bcross\b|square_ring|\bcore\b|middle|at distance',
    'SYMMETRY': r'mirror|reflect|symmetr|\bflip|rotat(e|ed|ion)\b|dihedral|transpose|\baxis\b|\bpose\b|opposite'
                r'|upright|\bhalf',
    'MATCHING': r'table|lookup|look up|\bkey\b|legend|\bmap\b|mapping|match|template|same shape|correspond'
                r'|substitut|\bphi\b|\bcode|atlas|palette\b|\binks?\b|[a-z]\[[a-z]|relation|\bfits?\b|\bcases?\b'
                r'|same (colou?r|marker|odd|position)|criterion|\bif\b',
    'PART-WHOLE': r'\bcrop|select|extract|panel|\bpart\b|piece|\bsplit|subgrid|component|assembl|\bcut\b|window'
                  r'|largest|smallest|odd one|unique|concat|\bwhole\b|erase|remove|retain|\bkeep|filter|output one'
                  r'|\bclip|slot|\bboard',
    'CONTAINMENT': r'\bfill|interior|inside|enclos|bbox|region|\bhole|contain|\broom|rectangle|\bbox\b|\bmask'
                   r'|housing|pocket|socket|notch|within|\binto\b',
    'COUNTING': r'count|number of|tally|histogram|\bbar\b|\bsort|\brank|\border\b|argmax|argmin|\bmost\b|\bleast'
                r'|majority|\bmode\b|plurality|\bvote|how many|#|longest|shortest|greedy|ascending|descending'
                r'|frequen|\barea\b',
    'SCALE': r'scale|upscale|downscale|stretch|factor|resiz|enlarg|shrink|zoom|kron|block size|magnif|\bx\d|blow'
             r'|compress|\b[ks] x [ks]\b|\d+\s*x\s*\d+|\bblock',
    'CONTACT': r'\bmove|translat|\bplace|\bdock|adjoin|attach|slide|push|touch|against|adjacent|\babut|\bsnap'
               r'|\balign|until\(adjacent|until\(contact|\bfree\b',
    'SUPPORT': r'\bdrop|gravity|\bfall|\brest\b|until\(rest|stack|settle|support|ground|\bland|hanging',
    'NEAR-FAR': r'nearest|closest|\bnear\b|\bfar\b|distance|proximity|voronoi',
    'BLOCKAGE': r'obstacle|\bblock(ed|s)?\b|stop at|until\(obstacle|\bwall|barrier|bounce|deflect|reflect|separator'
                r'|until\(next|until\(exit|\bexit',
}
LEXC = {s: re.compile(p) for s, p in LEX.items()}
GENERATIVE = ('PATH', 'LINK', 'CYCLE', 'CENTER-PERIPHERY', 'SUPPORT', 'CONTACT', 'SYMMETRY', 'BLOCKAGE')
DEFAULT_VERB = {'PATH': 'extend', 'LINK': 'connect', 'CYCLE': 'repeat', 'CENTER-PERIPHERY': 'surround',
                'SYMMETRY': 'reflect', 'MATCHING': 'lookup', 'PART-WHOLE': 'select', 'CONTAINMENT': 'fill',
                'COUNTING': 'count', 'SCALE': 'scale', 'CONTACT': 'move', 'SUPPORT': 'drop', 'NEAR-FAR': 'nearest',
                'BLOCKAGE': 'block'}
# what the first half hands to the second when nothing more specific is found (fallback (4))
OUT = {'PATH': ('path cells', 'cells'), 'LINK': ('link cells', 'cells'), 'CYCLE': ('repeated copies', 'cells'),
       'CENTER-PERIPHERY': ('ring cells', 'cells'), 'SYMMETRY': ('mirrored cells', 'cells'),
       'MATCHING': ('matched value', 'colour'), 'PART-WHOLE': ('selected part', 'object'),
       'CONTAINMENT': ('region interior', 'cells'), 'COUNTING': ('count', 'number'), 'SCALE': ('scaled grid', 'grid'),
       'CONTACT': ('placed object', 'object'), 'SUPPORT': ('object at rest', 'object'),
       'NEAR-FAR': ('nearest seed', 'object'), 'BLOCKAGE': ('blocking cell', 'cells')}
STOPW = set('the a an of to in on at by for from with and or as is be each every all any its it this that x y '
            'new old other same one two three four set cell cells colour color grid input output into onto per '
            'until if else then when while not no none only where which own'.split())
COLOURW = re.compile(r'colou?r|palette|ink|hue')
NUMW = re.compile(r'\b(k|n|p|d|count|number|size|length|thickness|radius|period|step|factor|distance)\b')
OBJW = re.compile(r'object|piece|shape|part|seed|marker|source|mover|template|block|unit|blob|pixel|dot|item|tile')


def lexhits(s, text):
    return len(LEXC[s].findall(text.lower())) if s in LEXC else 0


def segments(gen):
    """';' stages, then top-level calls inside a stage (a new segment starts at depth 0 before word( or word[)."""
    out = []
    for st in re.split(r';|\bthen\b', gen or ''):
        st = st.strip()
        if not st:
            continue
        cuts, depth, i = [0], 0, 0
        while i < len(st):
            ch = st[i]
            if ch in '([':
                depth += 1
            elif ch in ')]':
                depth = max(0, depth - 1)
            elif depth == 0 and i > 0 and st[i - 1] == ' ':
                m = re.match(r'[A-Za-z_][\w.]*[(\[]', st[i:])
                if m and i > cuts[-1]:
                    cuts.append(i)
            i += 1
        cuts.append(len(st))
        out += [st[a:b].strip() for a, b in zip(cuts, cuts[1:]) if st[a:b].strip()]
    return out


def idents(text):
    return [w for w in re.findall(r'[a-z_][a-z0-9_]*', text.lower()) if w not in STOPW and len(w) > 0]


def vtype(name, text=''):
    t = (name + ' ' + text).lower()
    if COLOURW.search(t):
        return 'colour'
    if NUMW.search(name.lower()):
        return 'number'
    if OBJW.search(t):
        return 'object'
    return 'cells'


def top_args(seg):
    """'op(a, b = c(d), e) rest' -> ('op', ['a', 'b = c(d)', 'e'], 'rest'); no call -> (seg, [], '')."""
    m = re.match(r'\s*([A-Za-z_][\w.]*)\s*([(\[])', seg)
    if not m:
        return seg, [], ''
    depth, start, args, i = 0, m.end(), [], m.end() - 1
    while i < len(seg):
        ch = seg[i]
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
            if depth == 0:
                args.append(seg[start:i])
                return m.group(1), [x.strip() for x in args if x.strip()], seg[i + 1:].strip()
        elif ch == ',' and depth == 1:
            args.append(seg[start:i])
            start = i + 1
        i += 1
    return m.group(1), [x.strip() for x in args + [seg[start:]] if x.strip()], ''


def split(rec, s1, s2, frame_half=None):
    """Return (defs, shared, status, note).  s1 = the record's own schema (primary half), s2 = the other half."""
    gen = rec.get('generator') or ''
    segs = segments(gen)
    sc = [(lexhits(s1, g), lexhits(s2, g)) for g in segs]
    own = [0 if h1 > h2 else 1 if h2 > h1 else None for h1, h2 in sc]
    if segs and all(o in (0, None) for o in own) and len(segs) >= 2:
        # no segment is clearly the other half's: give it the segment it scores best on, if any
        best = max(range(len(segs)), key=lambda i: (sc[i][1] - sc[i][0], i))
        if sc[best][1] >= 1 and sum(1 for i, o in enumerate(own) if i != best) >= 1:
            own[best] = 1
    for i in range(len(own)):                                 # ties attach to the neighbouring segment's half
        if own[i] is None:
            prev = next((own[j] for j in range(i - 1, -1, -1) if own[j] is not None), None)
            nxt = next((own[j] for j in range(i + 1, len(own)) if own[j] is not None), None)
            own[i] = prev if prev is not None else nxt if nxt is not None else 0
    seg_by = {0: [g for g, o in zip(segs, own) if o == 0], 1: [g for g, o in zip(segs, own) if o == 1]}
    # argument-level producer: when one half has no segment, an argument of the other half's call that belongs to
    # it ('kw = count(x)', 'colour of nearest seed', 'background at distance d') is its body; it produces the value
    # the call consumes, so it comes first, and that value is the shared variable
    producer = None
    S = (s1, s2)
    for h in (1, 0):
        if seg_by[h] or not seg_by[1 - h]:
            continue
        for g in seg_by[1 - h]:
            op, args, rest = top_args(g)
            for j, x in enumerate(args):
                if lexhits(S[h], x) > lexhits(S[1 - h], x) and lexhits(S[h], x) >= 1:
                    kw = re.match(r'(\w+)\s*=\s*(.+)$', x)
                    others = set(idents(' '.join(args[:j] + args[j + 1:]) + ' ' + rest))
                    tok = [w for w in idents(x) if w in others and w not in (op or '').lower()]
                    name = kw.group(1) if kw else (tok[0] if tok else None)
                    producer = (h, name, kw.group(2) if kw else x, op)
                    break
            if producer:
                break
        if producer:
            seg_by[h] = [producer[2]]
            break
    params = {0: {}, 1: {}}
    for k, v in (rec.get('params') or {}).items():
        t = '%s %s' % (k, v)
        params[1 if lexhits(s2, t) > lexhits(s1, t) else 0][k] = v
    if not params[1]:
        for k, v in list(params[0].items()):
            if lexhits(s2, '%s %s' % (k, v)) >= 1 and len(params[0]) > 1:
                params[1][k] = params[0].pop(k)
                break
    parts = rec.get('participants') or {}
    pmention = [(r, v) for r, v in parts.items() if lexhits(s2, str(v)) >= 1]
    cr = rec.get('colour_rule')
    if cr == 'table' and 'MATCHING' in (s1, s2):
        cr_half = 0 if s1 == 'MATCHING' else 1
    elif cr == 'sequence' and ({'CYCLE', 'COUNTING'} & {s1, s2}):
        cr_half = 0 if s1 in ('CYCLE', 'COUNTING') else 1
    else:
        cr_half = None                                        # decided after ordering: the half that paints last
    stop = rec.get('stop')
    stop_half = None
    for g, o in zip(segs, own):
        if re.search(r'until\(|stop', g.lower()):
            stop_half = o
    if stop_half is None:
        stop_half = 0 if s1 in GENERATIVE or s2 not in GENERATIVE else 1
    text_evidence = bool(seg_by[1] or params[1] or cr_half == 1 or pmention or
                         (stop_half == 1 and stop not in (None, 'none')) or lexhits(s2, stop or '') >= 1)
    inherited = False
    if not text_evidence:
        if frame_half is None:
            return None, None, 'unsplit', 'no evidence for %s in the record text' % s2
        inherited = True
    # ---- order: primary first unless the other half produces a value the primary consumes, or comes first
    pos0 = [i for i, o in enumerate(own) if o == 0]
    pos1 = [i for i, o in enumerate(own) if o == 1]
    first = 0
    if producer:
        first = producer[0]
    elif pos0 and pos1 and max(pos1) < min(pos0):
        first = 1
    if cr_half is None:
        cr_half = 1 - first
    # ---- shared variable
    pwords = {}
    for role, val in parts.items():
        pwords[role.lower()] = role
        for w in idents(str(val)):
            pwords.setdefault(w, role)
    shared = None
    opn = set(re.findall(r'([a-z_]\w*)[(\[]', gen.lower()))
    if producer:
        nm = producer[1] or (idents(producer[2]) or ['value'])[0]
        shared = {'name': nm, 'role': pwords.get(nm), 'type': vtype(nm, producer[2]), 'evidence': 'argument-producer'}
    elif seg_by[0] and seg_by[1] and not inherited:
        i0 = idents(' '.join(seg_by[0]))
        i1 = set(idents(' '.join(seg_by[1])))
        common = sorted({w for w in i0 if w in i1 and w not in opn}, key=lambda w: (w not in pwords, i0.index(w)))
        if common:
            w = common[0]
            role = pwords.get(w)
            shared = {'name': w, 'role': role, 'type': vtype(w, str(parts.get(role, ''))), 'evidence': 'shared-token'}
    if shared is None and pmention:
        role, val = max(pmention, key=lambda rv: lexhits(s2, str(rv[1])) - lexhits(s1, str(rv[1])))
        shared = {'name': role, 'role': role, 'type': vtype(role, str(val)), 'evidence': 'participant-mentions-other'}
    if shared is None and inherited and frame_half.get('shared'):
        fs = frame_half['shared']
        role = next((r for r, v in parts.items() if vtype(r, str(v)) == fs['type']), None)
        shared = {'name': role or fs['name'], 'role': role, 'type': fs['type'], 'evidence': 'frame-shared-renamed'}
    if shared is None:
        nm, ty = OUT[s1 if first == 0 else s2]
        shared = {'name': nm, 'role': None, 'type': ty, 'evidence': 'first-half-output'}
    # ---- definitions
    def verb_of(h, s):
        if h == 0:
            return rec.get('verb')
        if seg_by[1]:
            m = re.match(r'\s*([A-Za-z_]+)', seg_by[1][0])
            if m and m.group(1).lower() not in STOPW:
                return m.group(1).lower()
        return DEFAULT_VERB[s]

    def half(h):
        s = s1 if h == 0 else s2
        body = list(seg_by[h])
        if h == 1 and not body and pmention:
            body = ['%s := %s' % (r, v) for r, v in pmention]   # the other half defines / consumes that role
        d = {'schema': s, 'top': s, 'verb': verb_of(h, s),
             'participants': dict(parts) if h == 0 else {r: parts[r] for r, _ in pmention},
             'generator': ' ; '.join(body), 'stop': stop if h == stop_half else 'none',
             'colour_rule': cr if h == cr_half else 'own', 'params': params[h], 'provenance': 'record'}
        if h == 1 and inherited:
            d.update({k: frame_half[k] for k in ('verb', 'generator', 'params') if k in frame_half})
            d['provenance'] = 'frame:' + frame_half['frame']
        return d
    d0, d1 = half(0), half(1)
    defs = [d0, d1] if first == 0 else [d1, d0]
    for i, d in enumerate(defs):
        d['shared'] = shared['name']
        d['shared_dir'] = 'out' if i == 0 else 'in'
    return defs, shared, 'split', ('second half inherited from frame' if inherited else '')


def main():
    recs = json.load(open(os.path.join(REPO, 'results/o0/v10_records.json')))
    t64 = {r['frame']: r for r in json.load(open(os.path.join(REPO, 'results/o0/t64_frame_schema.json')))}
    pcs = json.load(open(os.path.join(REPO, 'results/o0/prior_concepts_v1.json')))
    comp = {f: (r['schema'], r['schema2']) for f, r in t64.items() if r['schema2']}
    verb_pair = {t64[f]['verb']: (f, p) for f, p in comp.items()}
    member_of = collections.defaultdict(list)
    for c in pcs:
        if c['id'] in comp:
            for t in c['members']:
                member_of[t].append(c['id'])
    by_id = {r['id']: r for r in recs}
    # frame halves first (pc_ records of the composed frames), so members can inherit them
    frame_split = {}
    for f, (a, b) in comp.items():
        r = by_id.get('pc_' + f)
        if r is None:
            continue
        s1, s2 = r['schema'], r['schema2'] or (b if r['schema'] == a else a)
        defs, sh, st, _ = split(r, s1, s2)
        if st == 'split':
            frame_split[f] = {d['schema']: dict(d, frame=f, shared=sh) for d in defs}
    out, counts = [], collections.Counter()
    for r in recs:
        rid = r['id']
        task = rid.split('_', 1)[1]
        frames = ['pc' if rid == 'pc_' + f else f for f in comp if rid == 'pc_' + f] or member_of.get(task, [])
        frames = [f if f != 'pc' else rid[3:] for f in frames]
        s1, s2, lift, fh = r['schema'], r['schema2'], None, None
        if s2:
            lift = 'own'
        else:
            for f in frames:
                if s1 in comp[f]:
                    s2 = comp[f][1] if comp[f][0] == s1 else comp[f][0]
                    lift, fh = 'frame', frame_split.get(f, {}).get(s2)
                    break
            if lift is None and r['verb'] in verb_pair and s1 in verb_pair[r['verb']][1]:
                f, p = verb_pair[r['verb']]
                s2 = p[1] if p[0] == s1 else p[0]
                lift, fh = 'verb', frame_split.get(f, {}).get(s2)
        row = {'id': rid, 'verb': r['verb'], 'lift': lift, 'frames': frames, 'returned': r['returned']}
        if lift is None:
            mism = any(s1 not in comp[f] for f in frames)
            row.update({'status': 'single', 'defs': [dict({k: r[k] for k in ('verb', 'participants', 'generator', 'stop',
                                                                         'colour_rule', 'params')}, schema=s1, top=s1)]
                        if s1 else [], 'note': 'frame_mismatch' if (frames and mism) else ''})
            counts['single'] += 1
            if frames and mism:
                counts['frame_mismatch'] += 1
        elif not s1 or s1 == s2 or r['returned']:
            row.update({'status': 'unsplit', 'note': 'no schema' if not s1 else 'same schema twice' if s1 == s2 else
                        'returned under G61', 'defs': [dict(schema=s1, top=s1, verb=r['verb'])] if s1 else []})
            counts['unsplit'] += 1
        else:
            defs, sh, st, note = split(r, s1, s2, fh)
            if st != 'split':
                row.update({'status': 'unsplit', 'note': note, 'pair_claimed': [s1, s2],
                            'defs': [dict({k: r[k] for k in ('verb', 'participants', 'generator', 'stop', 'colour_rule',
                                                             'params')}, schema=s1, top=s1)]})
                counts['unsplit'] += 1
            else:
                row.update({'status': 'split', 'defs': defs, 'shared': sh, 'tops': [defs[0]['top'], defs[1]['top']],
                            'note': note})
                counts['split'] += 1
                counts['split_' + lift] += 1
                if note:
                    counts['split_inherited'] += 1
        out.append(row)
    # ---- T53 re-run
    def t53(rows):
        parsed = [x for x in rows if any(d.get('schema') for d in x['defs']) and not x['returned']]
        return len(parsed), len(rows)
    sub = [x for x in out if x['id'].startswith(('d2_', 'grp_'))]
    tops_single = sorted({d['top'] for x in out for d in x['defs'] if d.get('top')})
    pairs = collections.Counter(tuple(x['tops']) for x in out if x['status'] == 'split')
    upairs = collections.Counter(tuple(sorted(x['tops'])) for x in out if x['status'] == 'split')
    tops_in_pairs = sorted({t for p in pairs for t in p})
    shared_types = collections.Counter(x['shared']['type'] for x in out if x['status'] == 'split')
    shared_ev = collections.Counter(x['shared']['evidence'] for x in out if x['status'] == 'split')
    comp_frames = {f: next((x['status'] for x in out if x['id'] == 'pc_' + f), None) for f in comp}
    n53, d53 = t53(sub)
    na, da = t53(out)
    summary = {
        'records': len(out), 'lifted_to_two': counts['split'] + counts['unsplit'], 'split': counts['split'],
        'unsplit': counts['unsplit'], 'single': counts['single'], 'single_frame_mismatch': counts['frame_mismatch'],
        'split_by_lift': {k: counts['split_' + k] for k in ('own', 'frame', 'verb')},
        'split_second_half_inherited_from_frame': counts['split_inherited'],
        'composed_frames_parsed_as_single': sum(1 for v in comp_frames.values() if v != 'split'),
        'composed_frames': comp_frames,
        'T53_parse_rate_d2_grp': '%d/%d' % (n53, d53), 'T53_parse_rate_all': '%d/%d' % (na, da),
        'distinct_tops': len(tops_single), 'tops': tops_single,
        'distinct_tops_reachable_in_pairs': len(tops_in_pairs),
        'pair_of_tops_ordered': len(pairs), 'pair_of_tops_unordered': len(upairs),
        'pair_counts': {'%s>%s' % p: n for p, n in pairs.most_common()},
        'shared_variable_types': dict(shared_types), 'shared_variable_evidence': dict(shared_ev),
        'unsplit_reasons': dict(collections.Counter(x['note'] for x in out if x['status'] == 'unsplit')),
    }
    json.dump({'summary': summary, 'records': out}, open(os.path.join(REPO, 'results/o0/v10_records_g69.json'), 'w'),
              indent=0)
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
