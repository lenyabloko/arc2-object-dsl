# Baseline B0 — deployment instructions for WSL Claude

B0 is the frozen reference that every abductive meta-learning candidate (enriched ontology, Dream/Wake) is
compared against. **B0 = V21 exactly**, the latest admitted solver. Nothing in B0 may change after it is frozen.

| Item | Value |
|---|---|
| Probe | `tools/m1b/v21` (46 files, checksums in `tools/m1b/v21_SHA256SUMS.txt`) |
| Kaggle notebook | `submission/v14` (EXPECTED digest `c93d287b…`, `correct_of_172` = 49) |
| Known results | c22-v21: G training exact 617, half A 36, N2 exact 37 / fit 41, half B 1. c23-v21-parity: digest c93d287b, 49/172, max task 60.5 s, 0 timeouts |

## Steps (run once, in order; report after step 5)

1. **Update.** `cd ~/arc/arc2-object-dsl && git pull -q`, then re-read `submission/WSL_CLAUDE.md` and this file.
2. **Verify the probe.** `cd tools/m1b/v21 && sha256sum -c ../v21_SHA256SUMS.txt` must print `OK` for all 46 files.
   Any `FAILED` → stop, write `.../wsl_results/baseline/B0/ERROR.txt` with the output, report to Len.
3. **Freeze a copy** (outside the repo, never edited afterwards):
   `mkdir -p ~/arc/wsl_work/baseline && cp -rn ~/arc/arc2-object-dsl/tools/m1b/v21 ~/arc/wsl_work/baseline/B0 && chmod -R a-w ~/arc/wsl_work/baseline/B0`
   If `~/arc/wsl_work/baseline/B0` already exists, do not overwrite it: verify it with step 2's checksums instead.
4. **Run the two baseline wake jobs** with the normal wake loop (`tools/wake/WAKE.md`), oldest first:
   - `wake_jobs/b0-v21-design.json` → training + half A rows with per-task prediction hashes (`ph`); N2 and half B as counts only.
   - `wake_jobs/b0-v21-parity.json` → full-probe parity and per-task timing on the public eval (same file as the Kaggle notebook).
   Use `PYTHONHASHSEED=0` and the same worker count for every later comparison job (record it in `summary.json`: `WAKE_WORKERS`).
5. **Kaggle.** `submission/LATEST` now names `v14` (= B0). The next daily run of `bash submission/daily_submit.sh`
   (after 00:00 UTC; skip if a submission was already made that UTC day) submits it through the parity gate.
   Its public score is B0's Kaggle score. Never retry a failed run or submission.
6. **Report** in one short paragraph: checksum result, both jobs' `summary.json` headline numbers (training exact,
   half A, N2 exact/fit, half B exact/fit, parity digest, correct_of_172, sealed count, max task seconds), and the
   submission record once available.

## Comparison protocol (every meta-learning candidate M vs B0)

- Same job types (`<M>-design`, `<M>-parity`), same data, `PYTHONHASHSEED=0`, same `WAKE_WORKERS`.
- Per-task comparison on the design splits by `ph` against `wsl_results/wake/b0-v21-design/results.jsonl`:
  gained, lost, newly wrong. Held-out splits (N2, half B, sealed): counts only, never ids.
- Also reported by the cloud session for M: ontology size (T-box, RBox, grounded concepts), new-node rate per task
  learned, reuse rate (tasks explained by existing concepts with no new code).
- M is admitted only if: no design task lost without a documented reason, no held-out count lower than B0,
  public-eval digest either identical or `correct_of_172` ≥ 49, max task time well under the 300 s alarm.

## Rules (unchanged)

- Half B, N2 and sealed are counts only: never print, copy or inspect their task ids or per-task results.
- Never touch `~/.kaggle` or credentials. No deletions anywhere. Never edit probes, notebooks, `EXPECTED.json`, `LATEST` or job files.
- The daily Kaggle submission (`submission/WSL_CLAUDE.md`) keeps priority once per UTC day.
