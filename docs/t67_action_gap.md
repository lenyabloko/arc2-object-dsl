---
doc: test report T67 (Fable v11 C3(b), D38)
date: 2026-10-02 06:35 UTC
for: Len, Fable: the generator spec that remains after the colour-role pass
---

# T67: action gap for the 45 nameable-but-failing tasks

**Pass criterion:** for each task, the needed action vs what is available, grouped by missing generator.
**Status:** met for the 12 tasks that remain after the solved proxy.

## 1. Counts

- `vcov_v29.json` has **45** exact-proper tasks, as stated in round 8/9 §3.
- **33** are already exact in the O0 ledgers (priors2/3/4, lines, concepts). **12 remain.**
- 7 of the 33 are exact only in the literal-capable passes (priors2/priors3), not in priors4 (roles only): 150deff5, 15663ba9, 1e5d6875, 272f95fa, 626c0bcc, 9caba7c3, e45ef808.
  - These are colour gaps that roles-only reopens.
  - D39 closes them: the learned-constant stratum fills the slots the roles-only stratum leaves empty.
- **Colour-only gaps among the 12: 1 (14754a24).**
  - The action fits, but `CR.background` picks the noise colour on the test input.
  - v12's `train_background` role fixes it (checked: all three fitting programs then match the one-off on the test input).
  - priors4 did not yet have that role.
- The 98 available family modules were run on the training pairs of the 12 tasks.
  - Only 2 tasks get a training fit: 14754a24 (template_cover_completion) and a25697e4 (dock_piece_by_matching). Both are test-wrong against the reference.
  - The other 10 get no fitting program from any module.
- What "nameable" names (v34 occupancy2 segmentation, recomputed):
  - On 18 of the 45 (5 of the 12 remaining), the exactly named target set is the background-coloured region itself.
  - The lattice segmentation treats colour 0 as background, so a non-zero background becomes an object, and `size_rank=0`, `largest_of_its_color` or `n_holes=k` names it.
  - On those tasks the naming selects nothing: everything is in the action.

Gap types: missing stop rule 4, missing parameter 4, missing generator 2, colour choice only 1, composition (+ missing split step) 1.

## 2. Groups, ranked by size (the generator spec)

| rank | group | n | generator spec | members |
|---|---|---|---|---|
| 1 | **A** on-stop clause for ray / slide | 3 | DRAW or MOVE(emitter, dir) with stop in {edge, contact, onto target, length = longest sibling run} and on_stop in {none, paint the reached grid side (side-side conflicts -> role colour), replace target, erase + bar at the opposite edge}, trail in {none, all swept, swept AND colour class}, plus a per-object branch on the measured property. | 13f06aa5, 758abdf0, fc10701f |
| 2 | **C** virtual-anchor construction | 3 | POINT(anchors) in {missing 4th rectangle corner, far bbox corner +/- 1 on the side picked by marker order, partner marker's cell, lattice origin + (i*p, j*p) registered from a partial copy}, used as an endpoint / target / stamp site by the existing connect, move and stamp actions. | 1478ab18, c4d067a0, e4941b18 |
| 3 | **B** legend as sequence or shape table | 2 | LEGEND kinds += {ordered sequence (collinear singletons), shape table (D8-canonical glyph -> colour)}; act += {bridge consecutive pairs (width = patch), bidirectional substitute (glyph -> fill and fill -> glyph)}. | 3e6067c3, b20f7c8b |
| 4 | **D** split and explode | 1 | CUT(object, line) -> parts; each part MOVEs by its own rule (to its frame corner / away from the cut); an empty-corner part is removed. | 4a21e3da |
| 5 | **E** iterated local rule (cellular automaton) | 1 | ITERATE over rows (or steps): cell <- T(neighbourhood), with T learned from the training pairs; stop at the last row or a fixed point. | b5bb5719 |
| 6 | **F** dock acceptance by complement | 1 | DOCK criterion += complement: piece part + body = the body's filled bbox, with any opening side and grid-edge contact allowed. | a25697e4 |
| 7 | **COLOUR** colour role only (not a generator) | 1 | wire the v12 G68 train_background role into template_cover_completion (and other priors4 families that use CR.background) | 14754a24 |

## 3. Per task: needed action vs available

### A: on-stop clause for ray / slide (3)

**13f06aa5**: missing stop rule; vcov name `D1:size_rank=0` (nbccg), named set bg_only
- *needed:* RAY from each multi-colour object's odd-coloured port cell, direction away from the object centre, every 2nd cell in the port colour, stop at the grid edge; ON STOP paint the whole grid side reached in the port colour, and cells where two painted sides meet take novel_colour.
- *closest available:* priors4/prior3 ray_cast_to_stop (emitter=port, dirs=away from object centre, pattern=every k-th cell, stop=edge): its documented menu covers the ray part, but it has no action at the stop; 0 programs on this task.
- *gap:* No terminal action: "on reaching the edge, paint that grid side; side-side conflicts take a role colour". occupancy2 border paints around an object bbox, not a grid side.
- *reference:* `arrow_dotted_ray_edge_s2_c0` (tools/dream/o0/oneoff/13f06aa5.py)

**758abdf0**: missing stop rule; vcov name `D10:largest_of_its_color` (nbccg), named set mixed
- *needed:* For every stub (run attached to the frame line on one grid side): if its length < L (L = longest stub in the grid) EXTEND it along its axis to length L in its own colour; else ERASE it and paint a length-L bar in the frame-line colour at the opposite grid edge of the same row/column.
- *closest available:* priors4 ray_cast_to_stop (emitter=run end carrying its length) and fam_extend_repeat_stamp (stub inducer): 0 fitting programs.
- *gap:* Stop "length = longest sibling run" is missing, and so is a per-object branch on that measure whose else-arm is erase + project to the opposite edge.
- *reference:* `stub_fix_L2` (tools/dream/o0/oneoff/758abdf0.py)

**fc10701f**: missing stop rule; vcov name `D10:largest_of_its_color` (nbccg), named set mixed
- *needed:* MOVE the block of the surviving colour along its row/column toward the aligned block of the vanishing colour, stop ON the target (replace it, not at contact); paint the swept cells that were hole-colour cells with novel_colour.
- *closest available:* fam_move_slide_until_contact (contact|through stop, trail on all swept cells), priors4 translate_object (toward anchor, stop=contact), fam_move_toward_anchor: 0 fitting programs.
- *gap:* Stop "onto the target, replacing it" and a trail restricted to one crossed colour class (the holes) are missing. All colours are roles (vanishing, novel).
- *reference:* `slide_gate_both` (tools/dream/o0/oneoff/fc10701f.py)

### C: virtual-anchor construction (3)

**1478ab18**: missing generator; vcov name `D1:size_rank=0` (nbccg), named set bg_only
- *needed:* CONSTRUCT the missing fourth corner of the square spanned by three corner dots (the background bbox corner); DRAW segments from the missing corner to each adjacent corner and the diagonal between those two corners, over background, in novel_colour.
- *closest available:* fam_connect_aligned_pair / priors4 bridge_aligned_pairs (segments between aligned same-colour items, diagonals allowed): 0 fitting programs.
- *gap:* The missing corner is not an item, so nothing can use it as an endpoint, and the two square sides between present dots must not be drawn. Needs a virtual-point construction (rectangle-completing corner) as a connect endpoint.
- *reference:* `missing_corner_triangle_f8` (tools/dream/o0/oneoff/1478ab18.py)

**c4d067a0**: missing parameter; vcov name `D12:n_holes=5` (nbccg), named set bg_only
- *needed:* Read the key lattice (1-cell marks at pitch q) and the partially traced enlargement (s x s squares at pitch p); register the traced squares to their key cells; STAMP an s x s square of the key cell's colour at origin + (i*p, j*p) for every non-background key cell (i, j).
- *closest available:* fam_stamp_complete_partial_matches (complete partial copies under D8 x block scale s), priors4 kronecker_tiling, concept_stamp_replicate (layout=blowup): 0 fitting programs.
- *gap:* Block size s and pitch p must be independent (existing scale ties the gaps to s), and the origin comes from registering the partial copy: a lattice of constructed positions.
- *reference:* `drafting:pantograph[registration=unique]` (tools/dream/d2/families_v1/c4d067a0_family.py)

**e4941b18**: missing parameter; vcov name `adjColor=5` (nbccg), named set mixed
- *needed:* With the solid rectangle as anchor and two single-cell markers on one side: MOVE the other marker into the corner marker's cell, and MOVE the corner marker (rank_colour -1) to the cell just outside the rectangle's far corner on its far edge row, on the side the marker pair points to.
- *closest available:* fam_move_to_position (key_marker|clamp|lattice|corner|codes|dock|edge_line targets), priors4 translate_object, compose_objmap (per-object vectors): 0 fitting programs.
- *gap:* The target points are constructed landmarks: the anchor's far bbox corner plus one cell outward, with the side picked by the marker order, and the partner marker's cell (a swap chain). They are not in any target menu.
- *reference:* `marker_swap_corner_dir_8` (tools/dream/o0/oneoff/e4941b18.py)

### B: legend as sequence or shape table (2)

**3e6067c3**: missing parameter; vcov name `D12:n_holes=5` (nbccg), named set bg_only
- *needed:* Read the collinear singleton cells as an ordered sequence of box labels; for each consecutive pair (a, b) BRIDGE the background corridor between the facing frames of boxes a and b, as wide as the inner patch, in a's label colour (reading order forward|reverse by fit).
- *closest available:* priors4 bridge_aligned_pairs (pairs same-colour / facing items by span or sight) + legend_lookup_substitution (legend kinds entries|corner|cross|lattice|fenced|header); priors4 turtle_path_walk: 0 programs.
- *gap:* No legend kind "ordered sequence", and no pairing "consecutive elements of an external list"; the bridge width must equal the patch width.
- *reference:* `graph:walk[order=forward,paint=tail]` (tools/dream/d2/families_v1/3e6067c3_family.py)

**b20f7c8b**: missing parameter; vcov name `D10:smallest_of_its_color` (mcccg), named set obj_only
- *needed:* Parse the legend panel into a shape -> colour table with D8-canonical shape keys; FILL solid, in the key colour, every framed box whose inner glyph matches a key, and REDRAW every solid box whose colour is a table value as frame + that key's glyph (inverse lookup).
- *closest available:* priors4 legend_lookup_substitution (keys colour|position|band|colour set; act recolour|glyph) and fam_recolour_objects (shape match with exemplars): 0 programs.
- *gap:* Shape-valued keys up to D8, and the value -> key direction in the same pass, are missing.
- *reference:* `legend_box_swap` (tools/dream/o0/oneoff/b20f7c8b.py)

### D: split and explode (1)

**4a21e3da**: composition (+ missing split step); vcov name `alignedColor=2` (nbccg), named set mixed
- *needed:* For each border marker DRAW the cutting line perpendicular to its edge across the object (to its last object pixel) in the marker colour; SPLIT the object along the line(s); MOVE each piece rigidly to the frame corner of its side (toward the marker edge along an uncut axis); REMOVE the cut-away quarter whose corner touches no marker edge.
- *closest available:* priors4 ray_cast_to_stop (border-marker emitter, inward normal) then priors4 translate_object (stop=contact with edge): 0 programs.
- *gap:* The ray and the move exist; the step that cuts one object into parts along a drawn line and gives each part its own move is missing.
- *reference:* `drafting:exploded_view[extent=object,cutaway=True]` (tools/dream/d2/families_v1/4a21e3da_family.py)

### E: iterated local rule (cellular automaton) (1)

**b5bb5719**: missing generator; vcov name `D1:size_rank=0` (nbccg), named set bg_only
- *needed:* ITERATE rows top to bottom: a background cell whose two upper-diagonal neighbours are both coloured takes T(a, b) from a pair table learned on the training pairs (default equal -> the other colour, unequal -> right); stop at the last row.
- *closest available:* none: priors4 learned_key_table applies a key -> value table once, and stamp_local_stencil / turtle_path_walk are not iterated neighbourhood rules. 0 programs.
- *gap:* An iterated local rule (1-D cellular automaton over rows) with a learned table.
- *reference:* `diag_pair_growth` (tools/dream/o0/oneoff/b5bb5719.py)

### F: dock acceptance by complement (1)

**a25697e4**: missing stop rule; vcov name `color_least_common` (nbccg), named set mixed
- *needed:* For each two-colour piece, search D8 motions (a mirror swaps its two colours) and translations so that one colour part exactly fills a single-colour timber's notch (timber + part = the timber's filled bbox); move it there and erase the original.
- *closest available:* priors4/prior3 dock_piece_by_matching dock:pocket[pieces=multi,motion=dihedral-swap,result=move]: fits all training pairs. On test input 0 it docks nothing (output = input), where the D2 reference docks two pieces. Test input 1 agrees.
- *gap:* Acceptance criterion: "complement to the filled bbox" is needed in place of "pocket opening toward the piece's side". Not colour: priors3 (literals allowed) gives the same miss.
- *reference:* `mechanics:mortise_tenon[motions=dihedral,mirror=swap]` (tools/dream/d2/families_v1/a25697e4_family.py)

### COLOUR: colour role only (not a generator) (1)

**14754a24**: colour choice only; vcov name `multicolor` (mcccg), named set obj_only
- *needed:* COVER: choose disjoint plus pieces on non-background cells holding >= 2 marker (least-frequent ink) cells, greedily by marker count; RECOLOUR the pieces' noise cells with novel_colour.
- *closest available:* priors4 template_cover_completion cover[mode=fill,piece=plus1,ev=rank-1,sup=nonbg,sel=greedy,minm=1,clip=1]: fits all training pairs, test wrong (prior3 too).
- *gap:* CR.background(g) flips on the test input: the noise colour 5 outnumbers 0 (187 vs 155 cells; 0 wins in every training input). With the background replaced by the training background (v12 G68 train_background), all three fitting programs give the one-off's test prediction.
- *reference:* `plus_greedy_m4_min2` (tools/dream/o0/oneoff/14754a24.py)

## 4. Available actions (catalogue used)

| verb | where | what gets drawn / changed |
|---|---|---|
| recolour | occupancy2 labels recolor:const / src; fam_recolour_objects; fam_recolour_by_colour_map; concept_recolour_by_mapping; prior3/priors4 colour_from_nearest_seed, learned_key_table, legend_lookup_substitution (recolour / halo / glyph / erase / rings) | repaint whole objects / cells by a feature, a shape match, a colour map, a key table or an in-grid legend keyed by colour, position, band or colour set |
| remove | occupancy2 remove; gdsl object_filter; concept_denoise | erase objects to background; repaint noise by class majority |
| move | occupancy2 move:dr,dc and slide:dir (until contact); fam_move_by_vector, fam_move_slide_until_contact (contact / through, optional trail on all swept cells), fam_move_to_position (key_marker / clamp / lattice / corner / codes / dock / edge_line), fam_move_toward_anchor; priors4 translate_object (k / contact / tail; move / copy); gdsl gravity/object_gravity/move_to_target; concept_rearrange; pack_objects_in_order; fam_segment_pack_pieces; priors4 dock_piece_by_matching (cover / pocket / marker / label / connector / slide) | rigid translation (optionally D8) of objects to a constant vector, until contact, toward an anchor or into a docking placement |
| line / ray | occupancy2 EFFECTS ray (8 dirs over background) and connect (to same-colour owner); gdsl rays/connect; fam_connect_aligned_pair (+full lines); priors4 bridge_aligned_pairs, ray_cast_to_stop (emitters marker / lone / body / port / run / border; solid / period k / run-length; stops edge / toggle / cancel / block / past), conditional_line_fill, turtle_path_walk; fam_ray_orthogonal_directed, fam_ray_diagonal_from_object, fam_ray_walker_turn_split; fam_lines (edge-marker projection); prior_action (least-action curves); prior_optics | straight or turning lines from emitters or between aligned items, painted until a stop rule ends them |
| region fill | occupancy2 EFFECTS fill_interior, bbox_fill; gdsl fill_enclosed, colour_select_fill; fam_fill_bg_windows; fam_fill_region_by_property; priors4 rectangle_from_delimiters | fill enclosed / bbox / walled regions or delimiter rectangles |
| outline / halo | occupancy2 EFFECTS border, outline8; gdsl outline; priors4 distance_rings_halo; fam_recolour_by_distance_layers; concept_decorate | rings, frames and accentuated locations around objects |
| stamp / copy / complete | fam_stamp_template_at_markers, fam_stamp_local_stencil, fam_stamp_copy_to_congruent_target, fam_stamp_complete_partial_matches (D8 x block scale s); priors4 stamp_stencil_at_anchors, template_cover_completion (open / greedy / exact cover), propagate_panel_template, mirror_symmetry_completion; concept_stamp_replicate, concept_complete_shape; fam_extend_repeat_stamp, fam_extend_periodic_fill; gdsl symmetrize/period_extend | paint copies of a template at sites, complete partial copies, continue periodic patterns, complete symmetry |
| canvas / summary | gdsl geometric/tile/scale/fractal/crop/panels/kronecker; fam_transform_kronecker, priors4 kronecker_tiling; fam_crop_*; fam_combine_boolean_panels; fam_summarise_*; priors4 count_bar_chart, select_odd_or_extremal; concept_extract_marked_region; fam_transform_objects | whole-grid transforms, crops, blow-ups and summaries (output-size changing) |
| composition | compose_lift (library on parts), compose_ctx (part op with context), compose_objmap/objmap2 (per-object action learner), gdsl search2 (2-step residual) | sequences / per-part lifts of the actions above, each step induced from training pairs |
| colour parameters | tools/dream/o0/colour_roles.py: background, rank_colour(k), novel_colour (+ input_colours, vanishing_colours); v12 G68 amended set adds vanishing, inert, common, panel_marker, train_background, new_in_some, then learned constant (last) | not an action: every colour slot of every action above takes one of these |

O0 items (`tools/dream/o0/items`: RCC-8, Allen, rays, between, nearest, mirror/rotation/translate_of ...) are roles, i.e. predicates, and add no action.

## 5. Method and limits

- **Solved proxy (as briefed):** V34 full-solver results are not in the cloud.
  - Exact in the priors2/3/4 ledgers (members_exact | exact_other), the line ledger (own_exact | pop_exact_other | held_exact_tasks) or the concept ledger.
  - One-offs (oneoff_ledger) and the D2 families do not count: D26 keeps them out of the build.
  - 8 of the 12 have an exact one-off; the 4 tasks from the 99 have an exact D2 family in V30.
- **Needed action:** taken from the one-off / D2 program and its reading, and checked against the training pairs by eye.
- **Closest available:** the member family named in the priors ledgers plus the module sweep.
- **Test agreement:** compared against the one-off / D2 prediction on the test input.
  - The references are exact by their ledgers, so no solutions file was opened.
  - Training pairs only for every fit. No ids from novel_N2 are used (0 of the 45 are in it).
- **a25697e4 diagnosis:** "acceptance criterion" is inferred from the family's documented pocket rule and the observed no-op on test input 0. It is plausible, not traced line by line.
- **No new solver code.** The probe scripts are in the session scratchpad, not the repo.

Files: results/o0/t67_action_gap.json, docs/t67_action_gap.md.
