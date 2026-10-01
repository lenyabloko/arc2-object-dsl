---
doc: review_page_audit_status
responds_to: claude/fable_review_page_audit_v1.md
date: 2026-09-30 (19:55 EDT)
from: cloud Claude (supervisor)
page: claude.ai artifact Ty8UPeb21xRCRamtphdZj2, version 77
---

# Review-page audit v1: implementation status

All nine audit items are on the page. T48–T52 pass on a mock database loaded with the live collections
(`review/accept.js`). One change follows Fable's Sep 30 note relayed by Len: the card Len needs is a mechanism card, not
a role card, so the card form is generator-first (§2).

## 1. Items

| # | item | status | where on the page |
|---|---|---|---|
| 1 | Test outputs hidden, reveal log, test_seen (G56) | done | every split; reveal writes to `looks`; the task note and any card citing the task are flagged |
| 2 | Card form + `priors` collection + harness write-back (G57) | done | Priors tab: mechanism card (default) and role / concept card; results appear in `h_*` fields on the card |
| 3 | Signal panel | done | "What the solver found" (C_t, background share, whether V29 or O₀ names the changed set exactly) + "What the generator must produce": each training input dimmed, residual cells in their output colour |
| 4 | Packet queue (G-D, G-E) | done | Packets tab: 269 unsolved design tasks in 19 packets by failure signature and residual shape; one structured ask per packet; answers stored as decisions `P_<packet>` |
| 5 | Freshness (G-F) | done | build from `cycle/current` (now V29; the stale Sep 29 state and its sealed-set counts are gone); statuses labelled "as of V29" |
| 6 | Per-decision feedback (G-G) | done | `feedback/<decision id>`: kept / received / recorded, effect, covering family; all 10 of Len's decisions annotated |
| 7 | Vocabulary tab (G-H) | done | V29 built-ins, mechanism cards, the 24 O₀ roles grouped by kind with is-a indents and pair density |
| 8 | Ledger columns (G-I) | done | Δ design, P1 (ARC-1 / ARC-2), P2 (b, c), V_cov exact-proper, R_layer; cycles 19–23 and O₀ Layer 1 added |
| 9 | Keep list | kept | mechanism spec, categories graph, batch digest, keyboard stepping, withheld held-out; §4: "Promote to mechanism card" pre-fills a card from a group's mechanism spec |

## 2. Mechanism card (generator-first)

- **Required fields:** name, generator (what gets drawn), stop condition, parameters with finite domains (width,
  period, direction, colour source), participants and how each is found, preconditions.
- **Optional fields:** order / crossings / border, image schema or citation, relations to other cards, tasks.
- **Card path:**
  1. Len saves the card.
  2. The supervisor implements it literally as a family module in `tools/dream/o0/mech/<card>.py`, test-blind.
  3. `tools/dream/o0/mech_admit.py` measures it on the design population (ARC-1 training minus N2, plus the 99):
     - lint;
     - on how many tasks the preconditions hold, and training fit;
     - round trip on the card's own tasks;
     - exact solves, with one harness check per fitted task, split into own / other / new over V29;
     - Reuse (R), counted at cycle A.
  4. The supervisor writes the results back onto the card.
- **Worked example: `halo_ring`, authored by Claude.**
  - preconditions hold on 256 of 997 design tasks;
  - training fit on 3, all exact;
  - 0 new over V29;
  - round trip 0 of 11 on the halo packet.

  Reading: the halo packet needs more than a plain ring. This is the kind of answer the card path is meant to give
  Len.

## 3. Acceptance tests

| test | result |
|---|---|
| T48 | outputs hidden by default; reveal adds one `looks` row; task flagged test_seen: pass |
| T49 | halo_ring shows status, lint, precondition rate, round trip, solves; appears in the Vocabulary tab: pass |
| T50 | top packet 49 tasks (≥ 10); C_t or ⊤ on every packet; LLM-cleared tasks (83) absent: pass |
| T51 | 0 need-you tasks already solved by V29; header build V29: pass |
| T52 | 10 of 10 human decisions annotated (no batch has been submitted, so "per submitted batch" is vacuous): pass |

## 4. Open points for round 10

1. **Packet order.** Packets are ordered by size, with expected reuse = 1, because R per item does not exist
   before cycle A.
2. **Admission of the 24 Layer-1 roles.** They are "checked, not admitted". If v10 accepts pair density as φ for
   roles, they can be admitted at once.
3. **Card template.** The mechanism card fields follow the Sep 30 relay. v10's template will replace them if it
   differs.
