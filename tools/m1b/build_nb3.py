"""Build a compact Kaggle submission notebook (cycle 22, V30+): like build_nb2.py, but the probe payload is the files'
UTF-8 text in one JSON object, compressed with lzma (stdlib) and base64-encoded, and the parity gate compares the
prediction digest only (G18 fix: the all-120 correct count is no longer computed or printed in the notebook, since it
includes the sealed tasks; equal digests imply equal predictions and therefore equal correctness).
Also asserts PROBE_SET_SHA = sha256 over (name, sha256(bytes)) of every probe file, so the whole payload is pinned.
Why: V30 adds 61 files (60 LLM-proposed families + prior_llm.py); build_nb2's base64-in-zlib payload would be 0.88 MB,
this one is ~0.45 MB (notebooks above ~1 MB are refused by the Kaggle API).
usage: python3 build_nb3.py <prev.ipynb> <probe_dir> <out_dir> <expected_digest> <vocab> "<probe label>" """
import base64, hashlib, json, lzma, os, re, sys
prev, probe, out, dig, vocab, label = sys.argv[1:7]
nb = json.load(open(prev))
PFX = '%%writefile /kaggle/working/probe/'
TAGS = ('# Probe payload (zlib + base64)', '# Probe payload (lzma + base64)')
cells = nb['cells']
idx = [i for i, c in enumerate(cells) if ''.join(c['source']).startswith((PFX,) + TAGS)]
first, last = min(idx), max(idx)
files = sorted(f for f in os.listdir(probe) if f.endswith(('.py', '.json')))
raw = {f: open(os.path.join(probe, f), 'rb').read() for f in files}
blob = {f: b.decode('utf-8') for f, b in raw.items()}
payload = base64.b64encode(lzma.compress(json.dumps(blob, sort_keys=True).encode(), preset=9 | lzma.PRESET_EXTREME)).decode()
set_sha = hashlib.sha256(''.join(f + hashlib.sha256(raw[f]).hexdigest() for f in files).encode()).hexdigest()
lines = [payload[i:i + 1000] for i in range(0, len(payload), 1000)]
src = (TAGS[1] + f': {len(files)} files (UTF-8 text), written byte-identical to /kaggle/working/probe\n'
       'import base64 as _b64, hashlib as _hl, json as _json, lzma as _lzma, os as _os\n'
       "_os.makedirs('/kaggle/working/probe', exist_ok=True)\n"
       '_P = (\n' + ''.join(f"    '{l}'\n" for l in lines) + ')\n'
       '_F = _json.loads(_lzma.decompress(_b64.b64decode(_P)))\n'
       'for _name in sorted(_F):\n'
       "    open(_os.path.join('/kaggle/working/probe', _name), 'wb').write(_F[_name].encode('utf-8'))\n"
       "_set = _hl.sha256(''.join(_n + _hl.sha256(_F[_n].encode('utf-8')).hexdigest() for _n in sorted(_F)).encode()).hexdigest()\n"
       f"assert _set == '{set_sha}', 'probe payload digest mismatch'\n"
       "print(len(_F), 'probe files written; set sha', _set[:16])\n")
cell = {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': src.splitlines(True)}
cells = cells[:first] + [cell] + cells[last + 1:]
occ_sha = hashlib.sha256(raw['occupancy2.py']).hexdigest()
for c in cells:
    s = ''.join(c['source'])
    if s.startswith('# Parity gate'):
        s = re.sub(r"EXPECTED_DIGEST = '[0-9a-f]+'", f"EXPECTED_DIGEST = '{dig}'", s)
        s = re.sub(r"PROBE_SHA = '[0-9a-f]+'", f"PROBE_SHA = '{occ_sha}'", s)
        s = re.sub(r"VOCAB = '[^']*'", f"VOCAB = '{vocab}'", s)
        s = re.sub(r"EXPECTED_CORRECT = \d+\n", "", s)
        s = re.sub(r"correct = None\nif sols:\n    ans = json.load\(open\(sols\[0\]\)\)\n    correct = [^\n]*\n", "", s)
        s = s.replace("'correct_of_172': correct, 'expected_correct': EXPECTED_CORRECT", "'correct_count': 'not computed (G18: includes sealed tasks)'")
        s = re.sub(r"assert correct in [^\n]*\n?", "", s)
        assert 'EXPECTED_CORRECT' not in s and 'correct =' not in s, 'parity gate rewrite incomplete'
        c['source'] = s.splitlines(True)
    if c['cell_type'] == 'markdown' and s.startswith('# ARC-AGI-2'):
        s = re.sub(r"Frozen prior vocabulary `[^`]*`", f"Frozen prior vocabulary `{vocab}`", s)
        s = re.sub(r'\n\*\*Probe:\*\*.*', '', s) + f'\n\n**Probe:** {label}'
        c['source'] = s.splitlines(True)
nb['cells'] = cells
os.makedirs(out, exist_ok=True)
p = os.path.join(out, 'arc2_lattice_rdr_submission.ipynb')
json.dump(nb, open(p, 'w'), indent=1)
print(p, os.path.getsize(p), 'bytes,', len(cells), 'cells,', len(files), 'probe files; occupancy2 sha', occ_sha[:16], 'set sha', set_sha[:16])
