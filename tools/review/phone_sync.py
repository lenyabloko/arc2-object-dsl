"""Sync task lines between the review page (artifact Ty8UPeb21xRCRamtphdZj2) and its phone view
(artifact 4Z1VdvcahWaj7CeZXdNyDJ, "ARC Review Mobile", Oct 1 2026). Each artifact has its own database:
    main   decisions/<group id>: task_text[tid], task_line_meta[tid] = {ts, test_seen}; expansions/<tid>
    phone  lines/<tid> = {text, ts, gid, from: phone|desktop}; expansions/<tid> (mirrored from main)
Rule (run at every line pass, before processing lines): per task the line with the later ts wins and is copied to
the other side; an empty phone text clears the line. Expansions are written to main by the line pass and mirrored to
phone. N2 (held-out) task ids are never copied (the phone page carries no N2 task).
Input: directories written by ArtifactData list with out_dir (main decisions, main expansions, phone lines, phone
expansions). Output: main_writes.json and phone_writes.json (ArtifactData batch entries; add if_version for existing
main decisions docs from the listing before running the batch) and a summary on stdout.
usage: python3 phone_sync.py <main_decisions_dir> <main_expansions_dir> <phone_lines_dir> <phone_expansions_dir> <out_dir>"""
import glob, json, os, re, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
N2 = set(x for x in re.split(r'[,\s]+', open(os.path.join(REPO, 'tools/m1b/novel_N2.txt')).read()) if x)


def docs(d):
    out = {}
    for f in glob.glob(os.path.join(d, '*.json')):
        v = json.load(open(f)); out[os.path.basename(f)[:-5]] = v.get('data', v) if isinstance(v, dict) and set(v) == {'data'} else v
    return out


def nz(s): return re.sub(r'\s+', ' ', str(s or '')).strip()


def main():
    mdec, mexp, pl, pexp, out = sys.argv[1:6]
    M, ME, P, PE = docs(mdec), docs(mexp), docs(pl), docs(pexp)
    main_line = {}
    for gid, d in M.items():
        for t, txt in (d.get('task_text') or {}).items():
            ts = ((d.get('task_line_meta') or {}).get(t) or {}).get('ts', '')
            if t not in main_line or ts > main_line[t][1]: main_line[t] = (txt or '', ts, gid)
    mw, pw, summ = [], [], {'phone_to_main': [], 'main_to_phone': [], 'exp_to_phone': [], 'cleared_on_phone': []}
    for t in sorted(set(main_line) | set(P)):
        if t in N2: continue
        m = main_line.get(t); p = P.get(t)
        mt, mts, mg = m if m else ('', '', None)
        pt, pts, pg = (p.get('text', ''), p.get('ts', ''), p.get('gid')) if p else ('', '', None)
        if nz(mt) == nz(pt): continue
        if p and pts > mts:                                        # phone is newer
            gid = mg or pg or ('T_' + t)
            if nz(pt):
                data = {'task_text': {t: pt}, 'task_line_meta': {t: {'ts': pts, 'test_seen': False, 'from': 'phone'}}}
                if gid in M:
                    mw.append({'op': 'update', 'collection': 'decisions', 'doc_id': gid, 'data': data})
                else:                                              # no decision doc for this group yet: create it
                    mw.append({'op': 'set', 'collection': 'decisions', 'doc_id': gid,
                               'data': dict(data, reviewer='len', status='draft', axes={}, misfits=[], proposal=None,
                                            **({'kind': 'task', 'task': t} if gid.startswith('T_') else {}))})
                summ['phone_to_main'].append(t)
            elif m:
                mw.append({'op': 'update', 'collection': 'decisions', 'doc_id': gid,
                           'data': {'task_text': {t: {'__delete__': True}}, 'task_line_meta': {t: {'__delete__': True}}}})
                summ['cleared_on_phone'].append(t)
        elif m:                                                    # main is newer (or phone has none)
            pw.append({'op': 'set', 'collection': 'lines', 'doc_id': t, 'data': {'text': mt, 'ts': mts, 'gid': mg, 'from': 'desktop'}})
            summ['main_to_phone'].append(t)
    for t, x in sorted(ME.items()):
        if t in N2: continue
        if PE.get(t) != x:
            pw.append({'op': 'set', 'collection': 'expansions', 'doc_id': t, 'data': x}); summ['exp_to_phone'].append(t)
    os.makedirs(out, exist_ok=True)
    json.dump(mw, open(os.path.join(out, 'main_writes.json'), 'w'), ensure_ascii=False)
    json.dump(pw, open(os.path.join(out, 'phone_writes.json'), 'w'), ensure_ascii=False)
    print(json.dumps({k: len(v) for k, v in summ.items()}), json.dumps(summ))


if __name__ == '__main__':
    main()
