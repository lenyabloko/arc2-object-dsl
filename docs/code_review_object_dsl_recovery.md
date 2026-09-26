### Code review: `recovery` vs `main`, starting with the `object_dsl_recovery` tree

What I reviewed: the committed code in `experiments/object_dsl_recovery/` at `recovery` HEAD `023678b2357662e675262b032488aabec5e059d5`, compared with the branch point `a79a57ccf39887a85120660538c61f64389f8442`. That's `search.py`, `object_queries.py`, `run_experiment.py`, `select_evaluation_families.py`, `freeze_suite.py`, the `check_*.py` controls and `resume_obsolete_snapshot_cleanup.ps1`. I checked it against `AGENTS.md`, `docs/OBJECT_DSL_RECOVERY_NORTH_STAR.md` and the package README.

Found 2 issues:

1. **Interpreter agreement on `slide_node` statements is guaranteed by construction, not tested.** North Star commitment 2 says: "Keep executable programs, connector representations and actual intermediate object states connected. State honestly which semantics remain unchecked." `slide_node` isn't an existing DSL primitive with a registered shadow connector. It's a new macro in `search.py`. The direct interpreter and the shadow interpreter both call the same Python `slide_node()`. The connector instruction records the guard only as a descriptive string, plus a digest of `search.py` itself. So for the statement behind the one fully solved evaluation task (`88e364bc`), "both execution paths agreed on intermediate object states" can't fail, which makes it tautological. The README's caveat covers "existing DSL primitive implementations", and this macro isn't one of them. The results should say the guard semantics are unchecked, or the guard should be lowered into connector-level operations (unit `move_node` plus an explicit clearance query) that the shadow interpreter runs itself.

   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L90-113
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L131-137
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L151-164
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L234-238

2. **An out-of-fragment test input stops the whole batch instead of being preserved** (North Star commitment 4 says: "Preserve failures and unresolved cases"; the README says: "Keep every failed, unresolved and out-of-fragment case"). `synth()` catches only `QueryGap` when it runs a found program on test inputs. `execute()` can also raise `FragmentGap`, for example `object_count_outside_fragment` from `abstract()`, `unresolved_binding` or `slide_bound_exhausted`. When that happens, the `synth` stage exits with an error, no disposition is recorded, and the remaining tasks never run. `replay()` has the same narrow `except`. The order-sensitivity check has a related gap: it runs the program in reverse with no `try`, so a query step that runs before its reference exists can raise `QueryGap("empty_direction_reference")` and abort the run. This hasn't happened yet only because every evaluation program so far has had a single statement.

   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/run_experiment.py#L54-62
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/run_experiment.py#L81-85
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L48-57

Not reviewed yet: `experiments/object_dsl_verification/`, `docs/KAGGLE_VERIFICATION_HANDOFF.md`, `deploy/kaggle/README.md`, the `ontology/no_magic_change_artifacts/*.json` records and the committed `evidence/` and `fixtures/` data.

---

#### Below the threshold but worth a look

1. **The `slide_node` macro was developed after looking at the scored errors on the fixed family** (confidence about 60; this is about process, not a code defect). North Star commitment 4 says: "Do not replace failed tests with easier ones or expand the architecture to postpone a decision". The README says: "Do not extend this experiment with new family-specific executors ... after seeing the results." `RESULTS.md` discloses that the swept-clearance guard followed inspection of the scored error. The macro looks generic rather than family-specific, and the disclosure is honest. Still, the 2/3 result on this family is adaptive and shouldn't be read as transfer evidence. Freezing a new ARC2 evaluation family before the next change would give a clean measurement.

2. **The "resumable" cleanup script can't resume after an interrupted archive write** (confidence about 70). If the script stops partway through `CopyTo` into the gzip, it leaves a truncated archive. On the next run, the archive already exists, so the script goes to the verify branch. There the hash doesn't match, or `GZipStream` throws, and the script stops with "Archive hash mismatch" every time until someone deletes that file by hand. This fails safely, since no source gets removed. Possible fix: write to `*.partial`, verify it, then rename it into place.

   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/resume_obsolete_snapshot_cleanup.ps1#L52-67

3. **The timestamp check fails under PowerShell 7** (confidence about 50, and it only matters for unpinned targets). In PowerShell 7, `ConvertFrom-Json` turns ISO-8601 strings into `DateTime` values. `[string]$target.lastWriteUtc` then produces a culture-style string instead of the round-trip `'o'` format, so the timestamp comparison throws. Windows PowerShell 5.1 doesn't do this conversion. Also, `Get-PSDrive C,G,E` runs under `$ErrorActionPreference = 'Stop'`. On a machine without a G: drive, it throws after all the deletions, so `complete` and `finishedUtc` never get written.

   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/resume_obsolete_snapshot_cleanup.ps1#L44-50
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/resume_obsolete_snapshot_cleanup.ps1#L79-82

4. **Proposal starvation in search** (confidence about 45, a heuristic effect rather than a correctness bug). `proposal_order` puts every query-bound move first, and `infer` evaluates only the first 64 proposals for each state. When objects have enclosing parents, `direction_hypotheses` generates many queries across the 6 scopes, multiplied by up to 5 selectors. Those alone can fill the 64 slots, so recolor, remove and literal-move steps never get tried. That limits multi-statement programs on real ARC2 tasks, even though the synthetic controls still pass.

   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L331-342
   https://gitlab.com/lenyabloko/arc_extended_arga/-/blob/023678b2357662e675262b032488aabec5e059d5/experiments/object_dsl_recovery/search.py#L415-420

---

Method: this repo is on GitLab and the session had no GitHub or GitLab access, so I didn't post anything as an MR comment. I rebuilt the diff by reading git objects directly from your local `.git` and reviewed it by hand. I didn't use the plugin's parallel agent pass, git blame or the history of earlier MRs. This file isn't tracked by git. Keep it out of recovery commits, as `AGENTS.md` asks.
