"""Build a compact Kaggle submission notebook: the probe directory is shipped as ONE compressed payload cell
(zlib + base64, files written byte-identical) instead of one %%writefile cell per file.
Why: notebooks above ~1 MB were refused by the Kaggle API (v14, 1.43 MB: "400 Bad Request" on SaveKernel,
2026-09-30), while v11 (0.82 MB) pushed fine.
usage: python3 build_nb2.py <prev.ipynb> <probe_dir> <out_dir> <expected_digest> <expected_correct> "<probe label>"
Keeps every non-probe cell of <prev.ipynb> (bundle setup, predict_m1.py driver, parity gate, submission), replaces
the probe cells (either %%writefile cells or an earlier payload cell), and sets EXPECTED_DIGEST, EXPECTED_CORRECT and
PROBE_SHA (sha256 of occupancy2.py) in the parity gate."""
import base64, hashlib, json, os, re, sys, zlib
prev, probe, out, dig, corr, label = sys.argv[1:7]
nb = json.load(open(prev))
PFX = '%%writefile /kaggle/working/probe/'
TAG = '# Probe payload (zlib + base64)'
cells = nb['cells']
idx = [i for i, c in enumerate(cells) if ''.join(c['source']).startswith((PFX, TAG))]
first, last = min(idx), max(idx)
files = sorted(f for f in os.listdir(probe) if f.endswith(('.py', '.json')))
blob = {f: base64.b64encode(open(os.path.join(probe, f), 'rb').read()).decode() for f in files}
payload = base64.b64encode(zlib.compress(json.dumps(blob, sort_keys=True).encode(), 9)).decode()
lines = [payload[i:i + 1000] for i in range(0, len(payload), 1000)]
src = (TAG + f': {len(files)} files, written byte-identical to /kaggle/working/probe\n'
       'import base64 as _b64, json as _json, os as _os, zlib as _zlib\n'
       "_os.makedirs('/kaggle/working/probe', exist_ok=True)\n"
       '_P = (\n' + ''.join(f"    '{l}'\n" for l in lines) + ')\n'
       'for _name, _data in _json.loads(_zlib.decompress(_b64.b64decode(_P))).items():\n'
       "    open(_os.path.join('/kaggle/working/probe', _name), 'wb').write(_b64.b64decode(_data))\n"
       "print(len(_os.listdir('/kaggle/working/probe')), 'probe files written')\n")
cell = {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': src.splitlines(True)}
cells = cells[:first] + [cell] + cells[last + 1:]
occ_sha = hashlib.sha256(open(os.path.join(probe, 'occupancy2.py'), 'rb').read()).hexdigest()
for c in cells:
    s = ''.join(c['source'])
    if s.startswith('# Parity gate'):
        s = re.sub(r"EXPECTED_DIGEST = '[0-9a-f]+'", f"EXPECTED_DIGEST = '{dig}'", s)
        s = re.sub(r"EXPECTED_CORRECT = \d+", f"EXPECTED_CORRECT = {int(corr)}", s)
        s = re.sub(r"PROBE_SHA = '[0-9a-f]+'", f"PROBE_SHA = '{occ_sha}'", s)
        c['source'] = s.splitlines(True)
    if c['cell_type'] == 'markdown' and s.startswith('# ARC-AGI-2'):
        s = re.sub(r'\n\*\*Probe:\*\*.*', '', s) + f'\n\n**Probe:** {label}'
        c['source'] = s.splitlines(True)
nb['cells'] = cells
os.makedirs(out, exist_ok=True)
p = os.path.join(out, 'arc2_lattice_rdr_submission.ipynb')
json.dump(nb, open(p, 'w'), indent=1)
print(p, os.path.getsize(p), 'bytes,', len(cells), 'cells,', len(files), 'probe files; occupancy2 sha', occ_sha[:16])
