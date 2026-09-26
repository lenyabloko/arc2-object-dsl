"""Build the v2 Kaggle notebook (lattice/RDR probe) with an embedded, frozen probe and a parity gate.
usage: python build_v2.py <vocab> <expected_digest> <expected_correct> <outdir>"""
import hashlib, json, os, sys

vocab, digest, correct, outdir = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
here = os.path.dirname(os.path.abspath(__file__))
probe = open(os.path.join(here, "frozen_v3_occupancy2.py")).read()
driver = open(os.path.join(here, "predict_m1.py")).read()
probe_sha = hashlib.sha256(probe.encode()).hexdigest()


def code(src):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": src.splitlines(keepends=True)}


cells = [
    {"cell_type": "markdown", "metadata": {}, "source": [
        "# ARC-AGI-2: conceptual lattice + RDR over ARCGraph objects (symbolic, no neural model)\n",
        f"Frozen prior vocabulary `{vocab}`. Per task, RDR decision lists over lattice concepts are induced\n",
        "from the training pairs only and executed on the test inputs. Unresolved slots get a 1x1 placeholder,\n",
        "so any non-zero score comes from the induced rules.\n"]},
    code("""import hashlib, json, subprocess, sys, zipfile, os
from pathlib import Path
BUNDLE_SHA = '9eedcc404d6015a2c84db58c63ec97c3e55f282faaed5fb9eb479afe0a6ab4fb'
bundles = [p for p in Path('/kaggle/input').rglob('candidate.bundle')]
assert len(bundles) == 1, bundles
payload = bundles[0].parent
assert hashlib.sha256(bundles[0].read_bytes()).hexdigest() == BUNDLE_SHA
cand = Path('/kaggle/working/cand')
if not cand.exists():
    with zipfile.ZipFile(bundles[0]) as z:
        z.extractall(cand)
deps = Path('/kaggle/working/deps')
try:
    import rdflib  # noqa
except ImportError:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-index', '--no-deps', '--target', str(deps),
                    str(payload / 'rdflib-7.6.0-py3-none-any.whl')], check=True)
challenges = [p for p in Path('/kaggle/input').rglob('arc-agi_test_challenges.json')]
assert len(challenges) == 1, challenges
Path('/kaggle/working/probe').mkdir(exist_ok=True)
print(payload, challenges[0])
"""),
    code("%%writefile /kaggle/working/probe/occupancy2.py\n" + probe),
    code("%%writefile /kaggle/working/predict_m1.py\n" + driver),
    code(f"""# Parity gate: the notebook must replicate the local result on the public 120-task evaluation set.
PROBE_SHA = '{probe_sha}'
VOCAB = '{vocab}'
EVAL_SHA = 'e7c62a4bd211867c6b538f66b8013b81f299663c82ca062f49a52bf439d6e4e8'
EXPECTED_DIGEST = '{digest}'
EXPECTED_CORRECT = {correct}
assert hashlib.sha256(Path('/kaggle/working/probe/occupancy2.py').read_bytes()).hexdigest() == PROBE_SHA
evals = [p for p in Path('/kaggle/input').rglob('arc-agi_evaluation_challenges.json')
         if hashlib.sha256(p.read_bytes()).hexdigest() == EVAL_SHA]
assert evals, 'identical public evaluation file not found; parity cannot be verified'
sols = list(evals[0].parent.glob('arc-agi_evaluation_solutions.json'))
env = dict(os.environ, PYTHONHASHSEED='0', OMP_NUM_THREADS='1', MPLBACKEND='Agg',
           PYTHONPATH=os.pathsep.join([str(deps), os.environ.get('PYTHONPATH', '')]))
def run(ch, out):
    subprocess.run([sys.executable, '/kaggle/working/predict_m1.py', '--candidate', str(cand),
                    '--probe', '/kaggle/working/probe', '--vocab', VOCAB, '--challenges', str(ch),
                    '--out', out, '--task-seconds', '120'], check=True, env=env)
    return json.load(open(out))
ev = run(evals[0], '/kaggle/working/parity_eval.json')
digest = hashlib.sha256(json.dumps(ev, sort_keys=True).encode()).hexdigest()
correct = None
if sols:
    ans = json.load(open(sols[0]))
    correct = sum(any(ev[k][i][a] == t for a in ('attempt_1', 'attempt_2')) for k in ans for i, t in enumerate(ans[k]))
report = {{'eval_file': str(evals[0]), 'prediction_digest': digest, 'digest_match': digest == EXPECTED_DIGEST,
          'correct_of_172': correct, 'expected_correct': EXPECTED_CORRECT}}
json.dump(report, open('/kaggle/working/parity_report.json', 'w'), indent=1)
print(report)
assert digest == EXPECTED_DIGEST, 'PARITY FAILED: predictions differ from the frozen local run'
assert correct in (None, EXPECTED_CORRECT), f'PARITY FAILED: expected {{EXPECTED_CORRECT}} correct, got {{correct}}'
"""),
    code("""sub = run(challenges[0], '/kaggle/working/submission.json')
src = json.load(open(challenges[0]))
assert set(sub) == set(src) and all(len(sub[k]) == len(src[k]['test']) for k in src)
print(len(sub), 'tasks written')
"""),
]
nb = {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                                   "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
os.makedirs(outdir, exist_ok=True)
json.dump(nb, open(os.path.join(outdir, "arc2_lattice_rdr_submission.ipynb"), "w"), indent=1)
meta = {"id": "lenyabloko/arc2-lattice-rdr-symbolic-submission", "title": "ARC2 lattice RDR symbolic submission",
        "code_file": "arc2_lattice_rdr_submission.ipynb", "language": "python", "kernel_type": "notebook",
        "is_private": True, "enable_gpu": False, "enable_tpu": False, "enable_internet": False,
        "dataset_sources": ["lenyabloko/arc2-object-dsl-stationary-payload-v4", "lenyabloko/arc2-public-evaluation-parity-v1"],
        "competition_sources": ["arc-prize-2026-arc-agi-2"], "kernel_sources": [], "model_sources": []}
json.dump(meta, open(os.path.join(outdir, "kernel-metadata.json"), "w"), indent=2)
print("built", outdir, "probe", probe_sha[:12])
