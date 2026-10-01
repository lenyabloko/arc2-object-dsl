"""Prior-concept families mined from solution texts (cycle 27, Oct 1 2026): stratum L_priors2, after L_concepts.
Len: find common prior concepts spanning several solution lines (WordNet/VerbNet-style synonym classes and action
frames). 314 one-off readings were grouped into 20 concept frames; each prior2_<concept>.py anti-unifies the one-off
programs of its member tasks (tools/dream/o0/prior_check.py). continue_progression is left out (D26: it solves no
non-member task). Mechanics as in L_concepts below.

(L_concepts notes:)

Each concept_<name>.py states ONE Layer-2 mechanism concept (stamp_replicate, decorate, denoise, extract_marked_region,
recolour_by_mapping, complete_shape, rearrange) as a single family whose parameters span the reviewer's task lines
grouped under that concept (anti-unified test-blind by a language-model implementer from the member lines' code and
the member tasks' training pairs; tools/dream/o0/concept_check.py measures it against the separate line families).

Stage rule: like L_lines (prior_lines.py), the stage runs LAST and only fills attempt slots that every earlier stratum
left empty, so it can never displace an earlier attempt. Own clock: FAM_S seconds per family, STAGE_S per stage, never
more than the task's remaining time minus RESERVE_S (caps are hang guards, set well above the measured times; see
tools/dream/o0/linetime.py with FAM_MODULE=prior_concepts).
"""
import glob, importlib, json, os, signal, time

import prior_lines as _PL

FAM_S, STAGE_S, RESERVE_S = 25.0, 40.0, 3.0
_HERE = os.path.dirname(os.path.abspath(__file__))
_FAMS = None
_Cap, _capped, _fit_and_predict = _PL._Cap, _PL._capped, _PL._fit_and_predict


def families():
    global _FAMS
    if _FAMS is None:
        _FAMS = []
        for path in sorted(glob.glob(os.path.join(_HERE, 'prior2_*.py'))):
            name = os.path.basename(path)[:-3]
            try:
                mod = importlib.import_module(name)
                _FAMS.extend((name[7:], f) for f in mod.FAMILIES)
            except Exception:
                continue
    return _FAMS


def search(task, taken=(), need=2):
    """programs from the concept families that reproduce every training pair, in concept-name order then yield order;
    predictions equal to one in `taken` are skipped; stops once `need` programs are found."""
    outer = signal.getitimer(signal.ITIMER_REAL)[0]
    budget = STAGE_S if not outer else min(STAGE_S, outer - RESERVE_S)
    if budget <= 0.5: return []
    t_end = time.time() + budget
    seen = set(taken); found = []
    for src, fam in families():
        if len(found) >= need: break
        left = t_end - time.time()
        if left <= 0.05: break
        try:
            progs = _capped(min(FAM_S, left), _fit_and_predict, fam, task)
        except _Cap:
            continue
        except Exception:
            continue
        for name, preds in progs:
            key = json.dumps(preds)
            if key in seen: continue
            seen.add(key)
            found.append({"abstraction": "prior2", "specific": False, "mode": "prior2", "rules": ([], []),
                          "program": name, "source": src, "preds": preds})
    return found
