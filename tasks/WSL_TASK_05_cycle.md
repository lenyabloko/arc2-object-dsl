# WSL Task 05 — overnight measurement batch (cycle 7)

Kaggle duty first: after 00:00 UTC on 28 Sep run `bash submission/daily_submit.sh` (LATEST=v5).

## Setup (once)
```bash
cd ~/arc/arc2-object-dsl && git pull
mkdir -p ~/arc/wsl_work/codex_subset && tar xzf /mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/datasets/codex_atoms.tgz -C ~/arc/wsl_work/codex_subset
export CODEX_ROOT=~/arc/wsl_work/codex_subset
export S0_REPS=$CODEX_ROOT/s0_reps.json
export S0_REPS_USED=~/arc/arc2-object-dsl/results/m1b/s0_reps_used.json
```
These three variables must be set in the environment that runs `admit_par.py` (it passes `os.environ` through).
Use the updated `tools/m1b/occupancy2_current.py` from this pull. **Per-task alarm: 120 s** (atoms are slower; the cloud
baseline used 120) — if `admit_par.py` hard-codes 60, change that argument in your runner only.

## Proposals (run all in one batch, `--base V6`, 4 workers)
| tag | vocabulary | question |
|---|---|---|
| V6 | `fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms` | acceptance: must reproduce training 83, half A 2, half B 0 |
| V6used | `fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms_used` | downward pass: retire 399 atoms, keep the 21 that are used |
| V6prim | `fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms_primary` | upward: promote the 21 used atoms from fallback to primary concepts |
| V6d13 | `fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,D13` | new prior: position relative to the largest object |
| V6d14 | `fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,D14` | new prior: bounding-box density (full / high / low) |

If V6 does not reproduce 83 / 2 / 0, stop after it and report (environment mismatch) — do not report the others.

## Deliverables → `/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/wsl_results/T5/`
`admission.json`, the five `*_summary.json`, the ten jsonl files, and `REPORT.md` (table of T / half A / half B /
occupied / wall time per proposal, plus each admission verdict). Same hard rules as Task 01 (work in ~/arc/wsl_work,
never the sealed ids, no task-specific code, no new concepts of your own).
