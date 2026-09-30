---
doc: supervisor_evidence
round: 1
date: 2026-09-29
from: cloud Claude (supervisor)
for: Fable (formal review), Len
---

# Supervisor evidence, round 1 (design splits only; held-out counts pending on WSL)

Written while Fable works on fable_guidance_v1. Everything below was measured on the design splits (ARC-1
training, N1, dev-eval half A); no held-out task id was inspected. B0 = frozen V21.

## 1. The biggest MDL violation was in the answer slots, not in the concept library

V21 builds attempts as: lattice (per-object decision lists) first; the G library (verified whole-grid programs,
almost all named single concepts from the priors) only fills attempt 2 when the lattice has < 2 distinct predictions.

- Measured on the 31 design tasks where the lattice's programs are wrong: in **13** of them the lattice produced
  two wrong decision lists of 3–8 rules that took both slots, while G had a correct one-concept program that never
  got a slot (mech:lockkey, optics:project, colour-map, recolour-by-size_rank, key-position, periodic-fill,
  act-conserve:capacity[gravity], stencil, recolour-shape-match, arith-residue, arith-shift, complement+colour-map,
  objmap2 with one clause).
- **V23** (MDL attempt ordering): when every lattice program has 3+ rules, consult G and rank all candidates by a
  description class — lattice ≤ 2 rules or G ≤ 2 concepts / decision entries → 0; 3 → 1; longer → 2; near-miss
  guesses (not exact on training) → 3; ties keep the old order.
  Result: 21 of those 22 lattice-wrong/G-available tasks right (V21: 8). No loss on the 47 design tasks V21
  solves with 3+-rule lattice programs.
- This is consistent with guard G7 (slot ordering by precision class) and the rule-count calibration in G6.

## 2. Memorised tables crowded out concepts inside the G search (a Kraft/MDL failure of the search, not the code)

`gdsl.search` kept the first 6 programs that fit the training pairs, in candidate order, and only then discarded
those that refuse a test input. On 7d1f7ee8 the first 6 were shape→colour lookup tables (cost 3, i.e. cheap by the
current code although their description length grows with the table), all refusing the test's unseen shapes; the
correct topology concept "inside → colour of the outermost container" (topo:recolour, touches_border / is_inside,
a 2-entry table) was never reached.

- **V24** = V23 + (a) a program that refuses a test input no longer uses up a slot; (b) topology lookup tables cost
  0.5 per entry beyond two. 7d1f7ee8 is now solved.
- Open: the same should hold for every family with a lookup table (recolour-by-shape, recolour-objects,
  key-colour maps…): their cost ignores table size. See question Q-A below.

## 3. Abductions so far (Dream by the supervisor, with Len's review)

Each is a family in `latent/prior_abduced.py` (or a selector), defined in its own domain, parameters induced from
training pairs. "Alone" = the family run by itself on all 1000 training + 120 evaluation tasks.

| Concept (domain) | Lift / reading | Source task | Alone: exact / wrong | Held-out fires |
|---|---|---|---|---|
| Cavity (topology, 3D reading) | grid = cut through a 3D scene; space enclosed by one box | e73095fd | 1 / 0 | 0 |
| Rainbow (optics: dispersion) | drop spectrum repeated along a ray; bows around the drop | 3979b1a8 | 1 / 0 | 0 |
| Line of sight (optics) | the one odd-coloured object lights its rows and columns | 4f537728 | 1 / 0 | 0 |
| Nearest neighbour (geometry: proximity) | the body takes the colour of the nearest object (Euclidean) | 6df30ad6 | 2 / 0 (also aabf363d) | 0 |
| Innermost interval (topology: nesting) | same-colour pairs on a line nest like brackets; join the innermost | 5ad8a7c0 (N1) | 1 / 0 | 0 |
| Dashed border (graphics) | one segment on the border loop is a dash; dash = gap all round | 30f42897 (N1) | 1 / 0 | 0 |
| Inside → outermost colour (topology) | already in the library; found only after the slot fix (§2) | 7d1f7ee8 | — | — |
| Square hole (topology: zone shape) | a hole of a shape that is a square is filled (new zone feature is_square) | 44d8ac46 | refactor: lattice 3 rules → 1 concept | — |
| Boundary roles (topology: vertex/edge/interior) | each solid rectangle recoloured by cell role; actions own / bg / literal | b6afb2da | **4 / 0** (also 4347f46a, 50cb2852, bb43febb) | 0 |
| Reaction on contact (chemistry: A + B → C) | touching cells of two colours react; product replaces one, the other vanishes | d90796e8 | 1 / 0 | 0 |
| Panel dyed by its marker (colour arithmetic +k) | each separated panel takes its single marker's colour + k | 54d9e175 | 1 / 0 | 0 |

Observed reuse: **1.5 tasks per abduced concept** (13 exact over 9 new families), 0 wrong answers, 0 fires on held-out
splits. One MDL lesson: boundary roles first stored a per-colour table (fired 4 times, 1 wrong: an unseen colour);
re-parameterised with colour-free actions (keep own colour / background / literal), i.e. a shorter description, it
fired 4 times with 0 wrong. Generalising the parameterisation raised reuse and removed the error. Each abduction took
10–30 minutes of supervisor time. Tasks examined and not yet abduced (no concept found quickly): 1acc24af,
1e5d6875, 7ec998c9, 252143c9, 37ce87bb (a count-difference bar: arithmetic), 1478ab18 (a right triangle on the
diagonal pair enclosing the loose dot), 984d8a3e, ecb67b6d.

## 4. Where wrong answers come from (G library, training, V21)

Of 20 G programs that fit training but fail the test, 14 are compositions (objmap2 multi-clause decision lists,
lift, near-miss guesses); the single-concept ones are recolour-by-width, codex:connect, crop:object
most_frequent_shape (2), pack. This matches the lattice calibration: enumerations and compositions carry the errors.

## 5. Negative result: concepts as flat attributes are not abduction (V22, cycle 20)

Seven concept families added as flat lattice attributes with a tie-break preference: 603 design tasks, V21 71
correct / 31 wrong; V22 69 / 34 (+3 −5); exception-RDR-only variant 70 / 34 (+5 −6). Low-level motion concepts
("can move up") coincided with other features. Supports G3/G10 (concepts enter Wake only through seeds and the
graph neighbourhood, not as a bigger attribute list).

## 6. Pending measurements (WSL, batch-0047)

c24-b0-v21-full, c25-v23-full, c26-v24-full (new wake mode "full": the Kaggle attempt ordering on training +
half A, N2 and half B as counts), c27-v24-parity. Local backup runs (design only) are in progress.

## 7. Questions for Fable

- **Q-A (costs of lookup tables).** Give one code-length formula for every family whose program includes a table
  (key → action/colour), so that memorised tables stop being "cost 3". Is 0.5 bit-units per entry beyond two
  compatible with the ring code (G1) and the chance-fit margin (G5)?
- **Q-B (reuse rate).** With reuse ≈ 1.2 tasks per abduced concept on ~1100 public tasks, what does your
  convergence model (Q3/Q7) predict for held-out reuse, and how many grounded concepts would be needed before
  held-out N2 moves by the McNemar threshold (c ≥ 5)? Is abduction at this granularity the wrong level, i.e. should
  Dream abduce more abstract concepts (e.g. "nesting" rather than "innermost interval on a line")?
- **Q-C (slot policy).** Check V23's class ordering against G5–G7. Should the chance-fit margin replace the class
  number, and how should near-miss guesses (not exact on training) be ranked?
- **Q-D (NO_SEED failures).** Most unsolved ARC-2-style design tasks produce no seed at all. What is the cheapest
  sound procedure for Dream proposals when the signal has no seeds?
