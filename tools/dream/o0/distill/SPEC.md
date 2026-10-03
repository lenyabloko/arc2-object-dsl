# Distillation reading spec (batch 1)

You read ARC tasks and write, for each task, ONE reading: what the transformation is, stated as a situation in the
engine's vocabulary. A program checks every reading against the task's training pairs. You see **training pairs and
test inputs only**. Never guess or write a test output.

Grids are lists of strings; each character is a colour digit 0–9 (0 is usually the background, but the background
is the most common colour of a grid).

## The form: S = HOW(arguments) + WHY

**HOW** is one of the 8 columns below. Each argument takes one value from its list. Two special values exist:
- `"train"` means one constant learned from all the training examples together, used unchanged on the test input.
- `"open"` means you are unsure. The program then tries every value for that slot.

| column | arguments (allowed values) | WHY (what must hold on every pair) |
|---|---|---|
| `tile` | extent ∈ {train, pixel_count, object_count, fg, bg, border, marks, uniform_line}; unit ∈ {input} | every block of the output is the unit (the input) or empty; the extent says which blocks get a copy |
| `stamp` | anchors ∈ {markers, marks, fg, objects, grid_corners, obj_corners, centre, across}; unit ∈ {train, exemplar}; rest ∈ {kept, cleared}; place ∈ {nearest, topleft} | one copy of the unit at every anchor, copies identical; rest = whether the other input cells stay |
| `extend` | stop ∈ {obstacle, border}; source ∈ {markers, fg, train, segments}; colour ∈ {own, train, hit} | every line reaches exactly the first stop cell and never crosses it |
| `mirror` | axis ∈ {axis}; subject ∈ {fg} | the output is symmetric about the axis found on the input |
| `recolour` | key ∈ {train, key, nearest}; subject ∈ {fg, markers, largest, smallest, odd, train, segments, input} | every subject cell of colour a becomes key(a); nothing else changes |
| `fill` | region ∈ {bg, frame, between, region}; colour ∈ {train, own} | every cell of the region is filled; nothing outside it changes |
| `move` | subject ∈ {fg, markers, largest, smallest, odd, train, segments}; target ∈ {train, border, obstacle, target} | the subject keeps its shape (and ends in contact for obstacle) |
| `extract` | region ∈ {largest, smallest, odd, frame, fg, exemplar, region, panels} | the output is exactly the region's box cut from the input |

**Rows** (the values that name parts of a grid):
- `fg`: all non-background cells.
- `bg`: the background cells.
- `border`: the grid's border cells.
- `input`: the whole input.
- `markers`: isolated cells (all 8 neighbours are background).
- `marks`: single cells, except those touching a shape (unless at that shape's top-left corner).
- `objects`: each object (8-connected component).
- `largest`, `smallest`: the largest or smallest object.
- `odd`: the one object whose colour (or else shape) no other object has.
- `exemplar`: the largest multi-coloured component.
- `segments`: straight one-cell-wide single-colour runs.
- `frame`: the interior of the one rectangular outline object.
- `region`: the largest enclosed background area.
- `between`: background cells between two objects on one row or column.
- `panels`: stripes of the grid cut by full separator lines.
- `separator`: full rows or columns of one non-background colour.
- `centre`: the centre cells of objects (and of the grid).
- `grid_corners`, `obj_corners`: the corner cells of the grid, or of each object's box.
- `axis`: candidate symmetry axes.
- `key`: colour pairs a → b shown as 2-cell components of two colours.
- `uniform_line`: the one all-one-colour row or column.
- `pixel_count`, `object_count`: counts, used by tile's extent.
- `obstacle`, `target`, `across`: what stops a line or a move, the object a move goes to, and across a separator.

**Forms.** A flat reading is `{"how": ..., "args": {...}}`. Two nested forms exist:
- **map:** apply an inner situation to every sub-node and paste the results back. Write
  `{"form": "map", "scale": "panel" | "object" | "part", "sub": {flat}}`.
- **seq:** apply a first situation to the whole grid, then a second one to its result. Write
  `{"form": "seq", "sub": {flat}, "outer": {flat}}`.

Use a nested form only when the flat one cannot say it.

**New rows.** If a slot needs a part of the grid that no row names, define it as a cell set in Datalog and use its
name as the argument value.
- Base relations:
  - `cell(Y, X, C)`: non-background cells.
  - `px(Y, X, C)`: all cells.
  - `obj(O, Y, X)`: cell (Y, X) is in the single-colour 8-connected component O.
  - `off(DY, DX)`: the 8 neighbour offsets.
- Syntax:
  - Horn rules; `!` is negation (stratified).
  - Head aggregates `count(...)`, `min(V)`, `max(V)`.
  - Comparisons and arithmetic with `=`, e.g. `Y2 = Y + DY`.
  - Variables are upper-case.
- The output predicate must be binary: `name(Y, X)`.
- Example: an isolated cell next to a shape:
  ```
  osize(O, count(Y, X)) :- obj(O, Y, X).
  single(O) :- osize(O, N), N = 1.
  shape(O) :- osize(O, N), N > 1.
  touch(M) :- single(M), obj(M, Y, X), off(DY, DX), Y2 = Y + DY, X2 = X + DX, obj(S, Y2, X2), shape(S).
  near_shape(Y, X) :- touch(M), obj(M, Y, X).
  ```
- Define a new row only if it is needed.

**If no column fits,** write `"how": "other"`, give your own head verb in `"verb"`, and describe the slots in
`"slots"` (free text: slot name → what fills it). This is recorded as a frame that cannot be executed yet. That is
an honest and useful answer. Do not force a wrong column.

## Output

Write a JSON list, one object per task, to the file path you are given:
```json
[{"task": "<id>",
  "reading": "<one or two plain sentences: what happens>",
  "verb": "<your own head verb, e.g. 'copy', 'draw line', 'rotate'>",
  "frame": {"how": "stamp", "args": {"anchors": "markers", "unit": "train", "rest": "kept", "place": "nearest"}},
  "new_rows": [{"name": "near_shape", "datalog": "<rules>"}],
  "slots": {"<slot>": "<what fills it>"},
  "why": "<the condition that holds on every pair>",
  "invariants": ["<what never changes>"],
  "confidence": "high" | "medium" | "low"}]
```
Omit `new_rows` and `slots` when they are empty. Write one reading per task: your best one, not a list of options.
