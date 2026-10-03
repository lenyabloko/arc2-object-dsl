---
doc: fable_round_response
round: 23 (v23 rev. 5 standing orders, v23a first days)
date: 2026-10-03 18:40 EDT
from: cloud Claude (supervisor)
rule: no test output appears here; harness results are exact / wrong / abstains only
---

# Round 23 response: adopted; v22 verified; distillation batch 1 (first T94 numbers)

## 0. Adopted, with Len's answers
v23 rev. 5 and v23a are adopted as written. Len answered three questions after reading v23a
(claude/decision_v23_budget_memo_page.md):
- **Budget:** batch 1 at full scale now; batches 2–4 are decided on Oct 8 from the first T94 numbers.
- **Memo:** the Oct 12 memo is finalised on Oct 10, with the Oct 8 numbers.
- **C.8** lives on the desktop review page.

## 1. Submission (A.1, A.2)
- **ORDERS seq 22** (committed 15:00 EDT, verified on the device):
  - tonight's v21 run (seq 21) is v21's one Kaggle run;
  - after it, WSL runs daily_submit.sh only when an order names a version.
- **v22 = v21 + logging** (submission/v22, 0.61 MB):
  - The driver records per-task wall seconds. The test cell prints `PREDICTION_SET_SHA256`, `TASK_TIMES` and
    `TASK_TIMES_SORTED`. The times are anonymous: no task ids are printed.
  - The probe payload, the setup cell and the parity cell are byte-identical to v21.
  - **Local parity run** (120 eval tasks, two halves, PYTHONHASHSEED=0): digest **b6c6bfd8** = eval_digest. Max task
    68.5 s; 0 tasks over 120 s.
- **Proposal:** a single v22 submission on an order for Oct 4 after 20:00 EDT. Then **Len selects the verified run**
  as the final submission on Kaggle's My Submissions page; only he can do that.
- **Slip, recorded.** The first plumbing test of the log lines printed per-task times keyed by task id for 60
  public-eval tasks into the supervisor's own tool output. That set may include some of the sealed 21. Nothing reached
  a doc, a page or a decision, and the notebook now prints times without ids.

## 2. Distillation batch 1 (C.7 a.i): first numbers

**Setup.**
- Tasks: the first 300 of the 393 dev tasks (sorted ids), 5 independent samples each = **1,500 readings**.
  - 150 model runs of 10 tasks each.
  - Training pairs and test inputs only (tools/dream/o0/distill/tasks/).
- Reading form: v19 (column + argument rows + WHY), new rows as Datalog over cell / obj / off / px, or `other` with
  the model's own verb (distill/SPEC.md).
- L4 draft: l4_verbs.json, about 120 verbs mapped to the 8 columns or marked as having no executor. It is
  LLM-generated and not yet checked against WordNet / VerbNet.
- Judge: the engine as it stands, depth 1 plus map / seq.
  - Exact training fit on every pair.
  - One harness check per task, with the samples' fits pooled by support (G48), then by fewest open slots
    (distill_check.py; ledger results/o0/distill_harness.json).
- One engine change, generic: `fill`'s region slot now accepts definition rows, as tile's extent already did
  (v21 A.7). It is a fallback only; built-in names are unchanged. Re-run of dev depth 1: 55 / 393, with identical fit
  lists on all 393 tasks.

| T94 item | count |
|---|---|
| readings | 1,500 |
| executable (a column, directly or via L4) | 1,042 (L4-normalised 516) |
| `other` (frame without an executor) | 458 |
| fitting readings (exact on all training pairs) | 316 (273 with every slot bound by the reading) |
| tasks with a fitting reading | **78 / 300** (engine enumeration at depth 1: 45; new over enumeration: 51) |
| harness, one check per task | **74 exact, 3 wrong**, 1 abstains, 222 no fit (no check spent) |
| exact on build-failing tasks | 5 (14754a24, 3bd67248, 56dc2b01, 7d419a02, 834ec97d) of the batch's 31 |
| tasks whose best fit has ≥ 3 of 5 samples agreeing | 20 |
| new Datalog rows | 367, 0 load errors; 184 equal the changed cells on every pair |
| cost | 150 model runs, about 12 M subagent tokens: about 0.8 M per 100 readings |

**Frames and R(S).**
- 38 distinct frames fit; 11 have R(S) ≥ 2.
- The two largest are degenerate:
  - `fill(colour := train, region := d_row)` fits 30 tasks;
  - `recolour(key := train, subject := d_row)` fits 18 tasks.
  - In both, the frame key collapses every task's own row to `d_row`, and the row carries the task. Counted this way,
    R(S) is inflated (question Q1).
- The genuine multi-task frames are built-in:
  - `stamp(markers, nearest, kept, train)`: 5 tasks;
  - `stamp(markers / objects, …)`: 3 each;
  - `tile(fg, input)`: 2;
  - `extract(d_row)`: 3.
- Growth of distinct frames against tasks processed:

  | tasks processed | 25 | 50 | 100 | 150 | 200 | 250 | 300 |
  |---|---|---|---|---|---|---|---|
  | distinct frames | 7 | 11 | 17 | 23 | 36 | 37 | 38 |

  It flattens. Over 8 columns with fixed argument domains that is partly by construction, so it is not yet evidence
  for the small-signature world.

**Parts (G85 / G89): reuse of distilled rows on the other 392 dev tasks** (distill_reuse.py;
results/o0/distill_b1_reuse.json).
- 219 fitting readings used a new row; they come from 58 source tasks.
- Rows from 11 source tasks fit at least one other dev task. Most hits are tasks that the enumeration or their own
  readings already fit.
- **Two rows are needed by ≥ 2 non-source tasks**, and each was written independently by ≥ 3 of the 5 samples:

  | row (as the samples named it) | source | definition | needed on |
  |---|---|---|---|
  | `uniq` / `unique` | 31aa019c | a cell whose colour occurs exactly once in the grid | 3 tasks |
  | `cross` / `crossing` | 67a423a3 | a cell with a non-background neighbour on all four sides | 2 tasks |

- **Transfer check** (one per needed task, separate ledger results/o0/distill_transfer_harness.json):
  - **1818057f exact.** It is fitted with 67a423a3's `crossing` row in the source's frame; the task was not in batch 1
    and no reading was written for it.
  - The other 4 abstain: the fitted frame gives no answer on their test inputs.
- This is the first instance of the event v23a names: a frame that fits a task it was not distilled from, exact at the
  harness. It is one event. Both rows ride in `stamp(…, unit := train)`, a learned unit (question Q2).

**The `other` side (candidate L3 frames without executors, C.6 d).**
- 458 readings use 102 distinct head verbs. The most common:

  | verb | readings |
  |---|---|
  | complete | 37 |
  | swap | 26 |
  | classify | 22 |
  | fit | 19 |
  | rotate | 17 |
  | sort | 15 |
  | assemble | 15 |
  | chain | 12 |
  | pour | 11 |
  | scale | 10 |
  | overlay | 9 |

- On 76 tasks, ≥ 3 of the 5 samples give the same non-executable head verb (G48). Those are the first L3 candidates
  that would need executors.
- 369 of the 458 head verbs are not yet in L4.

## 3. Next (in v23a order)
1. **C.8 by Oct 6, desktop page.**
   - What it shows: as Len types a task line, the frames with R(S) ≥ 2 plus the admitted four, partially instantiated
     on that task's training pairs. Slots show as bound (by a built-in row or a bound constant) or open.
   - Ranking: by fit, then R(S).
   - Records: a pick (situation_label) or a type-past (gap).
   - Sealed tasks get no suggestions; suggestions are computed for the 393 dev tasks only.
2. **B.1** `claude/results_record.md`: first draft on Oct 4.
3. **C.1:** L1 toward 100–200 relations and the EL++ export (ELK on the Windows Protégé path).
4. **Oct 8:** T94 for batch 1 (this table, final), T95 (the first days of C.8) and the C.6 c re-measurement. Len then
   decides on batches 2–4.

## 4. Questions
- **Q1. Frame identity for R(S).** Should a frame whose slot holds a task's own distilled row count once per task, as
  now, or only when the row is the same concept up to equivalence? The second makes frame R(S) equal to part reuse,
  which is G89's count.
- **Q2. Learned units.** Both reused rows enter through `stamp(unit := train)`. v4″ excluded a learned pattern above the
  leaf. Should a learned unit at depth 1 count toward G89, or only toward R(S)?
