---
doc: fable_round_response
responds_to: claude/fable_guidance_v17_oct12.md (13:40 EDT Oct 2); also v15 memo, v16 synthesis
date: 2026-10-02 (14:05 EDT)
from: cloud Claude (supervisor)
---

# Round 17 response: T80 no-go; the residuals it targets do not occupy build slots

> Follow-up: Fable v18 (14:45 EDT) accepted the correction, withdrew T80, and put two situation generators (stamping, projection) in scope, written from Len's definitions. See claude/fable_round_18_response.md.

## 0. Headline: measure before building P2/P3 in full

Before building the aligner and filler in full, I measured how much open-slot filling over the *existing* families
can gain at most. The bound is near zero where it counts.

**1. The 60 T80 cases are mostly not wrong answers in the build.**
- 18 of the 28 "size" cases are **empty predictions**: the program fits the training pairs and returns nothing on the
  test input.
  - prior_check counts that as wrong.
  - The build skips it (`_fit_and_predict` drops programs with an empty prediction), so it never takes a slot.
- The 60 cases come from 36 distinct tasks, and **33 of the 36 are tasks the build already solves** (not in V32's
  failure list).
  - Strata after V32 fill only empty slots, so a prior family's wrong answer there never reaches the submission.
- Flipping all 60 cases to exact would add at most **3** design tasks: 52df9849, da2b0fe3, e633a9e5.
- The same holds for the whole T72 table: the 124 wrong design fits come from 66 tasks, and only 7 of them are build
  failures.
- **Correction to round 13–14:** the T72 residual table describes the families measured in isolation. It does not
  describe the build. The "48 % size/mixed" figure was read as the build's error profile in v15–v17, and it is not.

**2. Where it can count, the existing families offer no right candidate.**
- Population: the 153 design tasks the build still fails (V32 failures minus everything a V33–V35 stratum already
  solves; 34 of them ARC-2).
- Every program of the 38 prior families that fits the training pairs was pooled: up to 5 per family, non-empty
  predictions only. Script: tools/dream/o0/t80b_design.py.
- Only **8** of 153 tasks get any candidate, and 3 of those have an open choice.
- The expected output is in the pool for **0** tasks.
- So no selection rule (invariants, relational preference, runner-up for slot 2) can gain anything on these tasks
  from the existing families. This is an upper bound, not a measurement of one rule.

**3. Density check of P3 (ARC-GEN, design-side instrument only, G74).**
- Same pooled selection on 1,330 variants of the 266 fitted ARC-1 tasks.
- Selection used invariants v1, which keeps candidates that preserve every training-pair invariant: acts, size rule,
  palette, keeps-ink, keeps-background, output symmetry, colours kept.
- Results:
  - pass@1: 676 → 677
  - pass@2: 713 → 713
  - 204 variants have an open choice; 56 are forced simulations (no candidate keeps the invariants).
- **Abstention would cost more than it saves.** Abstaining on forced simulations would drop 46 wrong answers but also
  10 right ones (18 %). That conflicts with b = 0, so the invariants stay a re-ordering rule and do not abstain.
- An earlier feasibility sample (267 wrong density cases, the five situation families) agrees: the expected output is
  among the fitting programs' predictions in 24 cases (9 %), and in none of the 24 size cases.

**Reading.**
- The four situations need *new values computed from the test input*: output size from the test's structure, every
  marker, the test obstacle, the test axis.
- The existing families cannot produce those values on build-failing tasks; most of them do not even fit those tasks.
- Under v17's scope rule ("no new families") T80 cannot pass in a way that changes the build. Even a pass on the 60
  cases would add ≤ 3 design tasks.
- This does not refute the situation hypothesis. It shows that the hypothesis cannot be tested by re-selecting among
  what the families already generate.

## 0b. T80 as defined: no-go (V36 not built)

- **Setup.**
  - The same 38 families, measured over the whole design population (tools/dream/o0/t80_design.py).
  - For each (family, task), every fitting program is kept, up to 8.
  - base = the harness's first fit.
  - P3 = invariant-keeping candidates first (G80). Empty predictions are never chosen while a non-empty one exists,
    and the base order stands under forced simulation.
  - One check per version (P3 v1). Results: results/o0/t80_priors{3,4}.jsonl.txt.

| | priors3 | priors4 | v17 criterion |
|---|---|---|---|
| T80 cases (60) flipped to exact | 3 | 1 | **≥ 15 of 60: fail (4)** |
| new wrong (base exact → P3 not) | 0 | 0 | ≤ 3: pass |
| non-source exact, base → P3 | 170 → 175 | 158 → 161 | – |
| fits with an open choice (distinct predictions > 1) | 53 / 447 | 31 / 359 | T84 |
| forced simulations (no candidate keeps the invariants) | 31 | 14 | T84 |

- **What the gains are.** All 8 new exact answers come from the invariants, since every base prediction there was
  non-empty: 5582e5ca (×3), aabf363d, 4f537728 (×2), d037b0a7.
- **None of them changes the build.** None of these tasks is in V32's failure list.
- **Density agrees in direction:** pooled pass@1 676 → 677.
- **Under v17 §6:** T80 fails, so V36 does not ship. The Oct 12 report says the template did not decide the
  residuals.
- **What can be added from §0.** The residuals it targeted were mostly not build slots. The decisive limit is that
  the existing families offer no right candidate on build-failing tasks. So the situation hypothesis is untested for
  lack of situation mechanisms, not only for lack of a working aligner.

## 0a. How this reads under claude/ideas_priors_as_situations.md

- The ideas document (§2) says a prior can act only by choosing among the programs consistent with the training
  pairs, H(D), or by extending H(D) with a program that agrees with the pairs and differs off them.
- §0 measured the first branch over the existing families. On the 153 build-failing design tasks, H(D) from the 38
  prior families is empty for 145 tasks and holds no correct program for the other 8, so choosing among H(D) gains
  nothing.
- That leaves the second branch. §3 and §5 of the ideas document give a situation its own mechanism, a generator
  rolled out with candidate open values and accepted by the invariant.
- v17 assumed the existing families are those mechanisms. On the tasks that matter they do not even fit. A test of
  the situation hypothesis therefore needs the four situation mechanisms themselves, which v17 §0 currently rules out.
- §7's division of labour holds for what was built:
  - The parser is the "translator" (37 / 38 lines into closed slots).
  - The aligner is the part that does not yet work (T83).
  - "Proposer of bindings for open slots" has not been tried.

## 1. P1 parser and T83 (done)

**P1.**
- Closed vocabulary for the six slots: tools/dream/o0/template_vocab.json, drawn from O₀ roles, the action binder,
  the stop set and the colour roles.
- Each line was parsed using only its own text (4 parser agents, ~10 lines each, each line independently).
- **37 of 38 parse.** The failure is d2acf2cb ("the first example does inverse", G81).
- Results: results/o0/t83_parsed.json.
- In Len's lines UNTIL is unspecified 27 times, HOW 15 times and WHERE 14 times. The sentences name WHO and WHAT; they
  rarely state the stop or place.

**P2 aligner v1 (tools/dream/o0/template_align.py).**
- Per-pair candidate values per slot, from closed definitions over the training pairs only.
- A value is kept only if it holds on every pair; relational values weigh 2, object-level values 1.

**T83, all four slots agreeing:**

| scoring | lines agreeing | target |
|---|---|---|
| strict | 0 / 38 | ≥ 30 |
| lenient (parsed "unspecified" not scored) | 0 / 38 | ≥ 30 |
| parsed value among the kept values | 3 / 38 | ≥ 30 |

Per slot (lenient): WHAT 9 / 37, WHO 6 / 37, WHERE 19 / 37, UNTIL 26 / 37.

- **Most misses are OPEN.** For WHAT and WHO, 15 / 38 have no value whose definition holds on all training pairs. On
  these hard tasks the closed definitions are too strict per pair, so the pairs do not align into one template value.
- **Reading.** By your own rule this is "low agreement, so stop and say so". It is fair to add that v1 is a
  one-afternoon aligner, and a stronger one might do better. I did not tune it against the parsed lines, because that
  would be fitting the agreement target.

## 2. What I propose instead (your call; nothing built yet)

1. **Protect the score (§4 of v17).** I am building this now, since it does not depend on T80: a deadline guard in
   the Kaggle driver.
   - The driver writes submission.json after every task.
   - It stops starting new tasks once the elapsed time passes the projected budget by 25 %; the remaining tasks get
     placeholders.
   - It goes into v21 = V34 + guard, with the same probe. The parity digest must stay b6c6bfd8, and is verified before
     staging.
2. **Second attempt:**
   - On build-failing design tasks the prior pool is almost always empty, so P3's runner-up adds nothing measurable.
   - It is cheap and harmless, so it can ride along in v21 if you want it. My measurement predicts no gain.
3. **The situation hypothesis.**
   - **What a fair test needs.** It needs generators that compute the open value from the test input: tiling
     count/size, stamp-at-every-marker with a learned offset, ray-to-test-obstacle, reflect-across-detected-axis.
     Each generator would be written once from its situation definition, not from a task, and admitted through T43.
   - **Cost.** These are four new families, which v17 §0 rules out.
   - **Upper bound, measured (training pairs only, aligner v1 definitions).** 20 of the 153 build-failing design
     tasks instantiate at least one of the four situations on every training pair:

     | situation | tasks |
     |---|---|
     | stamping | 10 |
     | projection | 6 |
     | tiling | 5 |
     | symmetry | 1 |

     2 of the 20 are ARC-2 (results/o0/t80b_situations.json). That is the most four situation generators could add
     on design. The existing families already implement these mechanisms and still fail these tasks, so a realistic
     yield is a fraction of 20.
4. **The Oct 12 report.** It would say:
   - the template parse works (37 / 38);
   - a v1 aligner does not align these tasks (0–3 / 38);
   - the existing families hold no correct candidate for any build-failing task;
   - so open-slot filling over them has a measured bound of 0, and V36 is not built.

## 3. Files

- tools/dream/o0/template_vocab.json, template_align.py, invariants.py, t80b_design.py
- tools/dream/density/t80_feasibility.py, t80_pool.py
- results/o0/t83_parsed.json, t83_result.json, t80b_population.json, t80b_design.jsonl.txt, t80b_situations.json, t80_feasibility.jsonl.txt,
  t80_pool_{0,1}.jsonl.txt
