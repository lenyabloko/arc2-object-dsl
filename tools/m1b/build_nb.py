"""Build a Kaggle submission notebook for a new probe from the previous notebook.
usage: python3 build_nb.py <prev.ipynb> <probe_dir> <out_dir> <expected_digest> <expected_correct> "<probe label>"
Keeps every non-probe cell (bundle setup, predict_m1.py driver, parity gate, submission), replaces the
%%writefile /kaggle/working/probe/* cells with the probe directory's files (sorted, .py and .json), and sets
EXPECTED_DIGEST / EXPECTED_CORRECT in the parity gate. Writes <out_dir>/arc2_lattice_rdr_submission.ipynb."""
import json, os, re, sys, hashlib
prev, probe, out, dig, corr, label = sys.argv[1:7]
nb = json.load(open(prev))
PFX = '%%writefile /kaggle/working/probe/'
cells = nb['cells']
first = next(i for i, c in enumerate(cells) if ''.join(c['source']).startswith(PFX))
last = max(i for i, c in enumerate(cells) if ''.join(c['source']).startswith(PFX))
files = sorted((f for f in os.listdir(probe) if f.endswith(('.py', '.json'))), key=lambda f: (f != 'occupancy2.py', f))
def cell(src):
    lines = src.splitlines(True)
    return {'cell_type': 'code', 'execution_count': None, 'metadata': {}, 'outputs': [], 'source': lines}
new = [cell(PFX + f + '\n' + open(os.path.join(probe, f)).read()) for f in files]
cells = cells[:first] + new + cells[last + 1:]
for c in cells:
    s = ''.join(c['source'])
    if s.startswith('# Parity gate'):
        s = re.sub(r"EXPECTED_DIGEST = '[0-9a-f]+'", f"EXPECTED_DIGEST = '{dig}'", s)
        s = re.sub(r"EXPECTED_CORRECT = \d+", f"EXPECTED_CORRECT = {int(corr)}", s)
        c['source'] = s.splitlines(True)
    if c['cell_type'] == 'markdown' and s.startswith('# ARC-AGI-2'):
        s = re.sub(r'\n\*\*Probe:\*\*.*', '', s) + f'\n\n**Probe:** {label}'
        c['source'] = s.splitlines(True)
nb['cells'] = cells
os.makedirs(out, exist_ok=True)
p = os.path.join(out, 'arc2_lattice_rdr_submission.ipynb')
json.dump(nb, open(p, 'w'), indent=1)
occ = open(os.path.join(probe, 'occupancy2.py'), 'rb').read()
print(p, len(cells), 'cells,', len(files), 'probe files; occupancy2 sha', hashlib.sha256(occ).hexdigest()[:16])
