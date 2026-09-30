# O0 — seed vocabulary (Fable guidance v9)

Each item is one file `items/<NAME>.py` whose `ITEM["name"] == NAME`, with the schema in `harness.py`'s docstring.

Rules for items (G30 b, G54, G57):
- Written from a precise definition (RCC-8, Allen, cardinal directions, rays, symmetry), never from a task.
- No task data, no coordinate / size / colour constants; parameters only from small finite declared domains.
- Role functions `fn(grid, inds, bg, **params) -> {i: set(j)}`; concepts `-> set(i)`.
  `inds` are the lattice objects (`kind == "object"`) plus one individual per background cell (`kind == "cell"`).
  Unless the definition says otherwise, the SECOND argument ranges over objects only (cell–cell pairs are not
  enumerated), so a role costs O(#individuals × #objects).
- Speed: <= 50 ms per 30x30 grid with ~900 individuals; deterministic (no sets iterated into outputs without sort,
  no randomness).
- Declare subsumptions (`subsumes`) that must hold on every grid (G20); the harness checks them.

Check: `python3 harness.py <probe_dir> check NAME [NAME ...]` → fire ratio per grid (phi_grid), pair density,
determinism, errors, subsumption results. Coverage: `python3 harness.py <probe_dir> vcov <c32> <e99> out.json NAMES`.
