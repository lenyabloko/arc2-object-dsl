---
doc: report (draft; numbers marked ▢ are filled on Oct 5)
date: drafted 2026-10-01 22:45 EDT (Fable v11 A2); T73 lead item and filled rows added 2026-10-02 11:40 EDT
for: Len, Fable — the dated stop rule (OQ7 proxy read on Oct 5, decision Oct 12)
---

# Oct 5 stop-rule report (draft)

## 0. Lead item: the generator-tier test (Fable v13/v14 T73), a no-go

- **What was tested.** The same 19 + 19 prior families re-run with a slot-augmented action binder:
  - iterate=fixpoint
  - accept=no_overlap
  - on_stop paint/turn
  The slot values were chosen from T72 residual counts over 2,007 failing fits on ARC-GEN variants.
- **Results** (design population, test-blind, one check per version):
  - priors3: wrong 83 → 81 (target ≤ 50); non-source exact 170 → 172 (target +20); new over V35's components 0
    (target ≥ 3).
  - priors4: no net change.
  - Density check on 2,660 variants: −2.2 % wrong (priors3), 0 (priors4).
- **Why.** T72 shows that about half of the wrong fits (48 % design, 55 % density) are a wrong output size or mixed missing-and-extra ink, which no slot
  reaches. The best case for the four slots on priors3 was 83 → 53.
- The detail is in claude/fable_round_13_14_response.md.

| tier expanded | size | held-out / transfer effect |
|---|---|---|
| descriptions (cycles 22, 24, 25; v10 lattice) | 60 + 23 + 7 + 1,521 | P2 = 0 every cycle; far-68 5 / 68 |
| recognisers (O₀ roles, colour roles) | 24 + 9 | precision up (wrong −51 %), fits −21 %, P2 = 0 |
| generator slots (T73) | 4 slots, 9 values | +2 exact / −2 wrong on 253 fits; 0 new |

## 1. The two OQ7 arms

| arm | definition (OQ7) | value now | Oct 5 |
|---|---|---|---|
| **P1**, ARC-1 / N1 row | clean non-source reuse per concept: exact on a design task that is not a source and that the admitted build did not already solve, averaged over the last 10 admitted concept versions | cycle 22 (LLM per task) 0.03; cycle 24 (Len's lines) 1 new over V29 from 23 lines = 0.04; cycle 25 (merged concepts) 0; cycle 27 (prior families) 5 new over V32 from 19 = 0.26; cycle 28 (second pass) 1 from 19 = 0.05 | ▢ |
| **P1**, the-99 row | same, on the 99 ARC-2 public eval design tasks | 0 in every cycle (no non-source exact gain on the 99) | ▢ |
| **P2** | N2-gate gain c ≥ 1 with b = 0 in each of the last two concept cycles | cycles 21, 22, 24, 25, 27, 28, 29: b = 0, c = 0 every time | ▢ |

**Reading by OQ7:** P1 fails → wrong granularity; P2 fails with P1 → fallback build; both fail → stop Dream.
As of Oct 1 both arms fail. ▢ (Oct 5: still / changed by …)

## 2. Supporting measurements

| measure | trajectory |
|---|---|
| V_cov exact-proper (failed same-size design tasks whose changed cells the vocabulary names exactly) | 0.18 (V29) → 0.26 (O₀ Layer 1) → 0.27 (depth-2 chains) → ▢ |
| R by layer (non-source fits per family) | cycle 22: 0.4 · lines: 1.3 · merged concepts: 5.3 · prior families: 12 (229 / 19) · second pass: 13 (253 / 19) · colour-role pass: 10 (199 / 19, but wrong fits 83 → 41) · ▢ |
| T55′ far-68 retrieval over the real-grounded pile | 5 / 68 (pass mark 20) |
| T65 second pass, non-source fits | +10 % (pass mark +50 %) |
| T68 colour roles only (no literal colours) | non-source fits −21 %, exact −7 %, wrong −51 %; members 194 → 160 |
| T59 Kaggle-side Datalog engine | pass: 4,153 / 4,153 grids; after v11 G63: 0 grids over cap |
| T58 ELK classification | pass (Oct 2): ELK's taxonomy matches the exporter; T71 picks unchanged |
| T60 / T71 generality pick by subsumption | 17 / 19 with lattice parents + sibling rule (asserted = ELK) |
| T66 blind A/B (Len's lines vs LLM readings) | no difference on the clean comparisons (paired 4 tasks identical; hash halves 0.25 vs 0.20, CI ±0.55); new over V32 0 on both sides |
| T69 composition parse | composed nodes add 0 to far-68 (5 / 68) |
| T75 ARC-GEN density (38 families, ~8,000 variants) | 1,896 wrong non-source fits, 111 member misses (priors3 29 % wrong, priors4 22 %) |
| T72 residual classes (density / design) | no slot shape 55 % / 48 %; anchor 18 % / 17 %; accept 9 % / 12 %; colour 9 % / 10 %; on_stop 6 % / 10 %; iterate 3 % / 2 % |
| T73 slot-augmented binder | no-go (§0) |
| T74 slot words in Len's lines | 9 / 38 lines (anchor 7, on_stop 3, accept 2, iterate 0) |

## 3. Kaggle

| notebook | build | public score |
|---|---|---|
| v11 | V17 | 2.50 |
| v15 | V21 (B0) | 2.50 |
| v16 | V29 | 2.50 |
| v19 | V33 | 2.50 (submitted Oct 2 01:48 UTC, parity match) |
| v20 | V34 | ▢ (Oct 3 UTC slot) |

Design coverage rose from 581 to 754 ARC-1 design tasks and from 35 to 44 half-A tasks. The public score has not moved.
Every design gain since cycle 21 is a source task of the family that solved it.

## 4. Options for Oct 12 (to be argued on Oct 5)

1. **Freeze**: the strongest staged build (V34 or later) is the notebook every night to Nov 2; Dream stops.
2. **Engine track only**: no new concept cycle; finish B2 (Route A over the materialised A-box), T60, T61 and gate
   them once; freeze if P2 stays 0.
3. **Change approach**: ▢ (only if Len and Fable want to open one; not proposed by the supervisor here)

Supervisor's recommendation: ▢ (written on Oct 5 from the numbers above).
