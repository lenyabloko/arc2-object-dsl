# Standing instructions for WSL Claude (Kaggle operator)

You are the Kaggle operator for `~/arc/arc2-object-dsl`. The cloud session builds and verifies
notebooks; you only push, verify and submit them. Re-read this file after every `git pull` — it is
the current source of truth and supersedes older instructions (including `submission/v2/WSL_INSTRUCTIONS.md`).

## Every time you are started
1. `cd ~/arc/arc2-object-dsl && git pull`
2. Re-read this file and `submission/LATEST`.
3. Check the UTC date: `date -u`. The Kaggle limit is 1 submission per UTC day (resets 00:00 UTC = 8 pm EDT).
4. If no submission has been made today (UTC), run:
   `bash submission/daily_submit.sh`
   It pushes the notebook named in `submission/LATEST`, waits for the Kaggle run, checks the parity
   gate (`digest_match` true and `correct_of_172` equal to `submission/<version>/EXPECTED.json`),
   submits only if both hold, and writes the outcome to
   `/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/submissions/<date>.json`.
5. Report to Len in one short paragraph: version, kernel version, parity result, submission id/status,
   and the public score once it is COMPLETE (`kaggle competitions submissions -c arc-prize-2026-arc-agi-2`).
6. If a submission was made earlier today outside the script, do not run it again until after 00:00 UTC.

## Rules (never break these)
- Never print, copy, move or edit Kaggle credential files (`~/.kaggle/`, `kaggle.json`, tokens).
- Submit only through `daily_submit.sh` (or an identical manual sequence) and only when the parity gate passes.
- Never retry a failed kernel run or a failed/rejected submission; report it instead.
- Never edit notebooks, `EXPECTED.json`, `LATEST`, or anything under `tools/`; those come from the cloud session.
- Do not delete files anywhere without Len's explicit permission.
- Never run the old v1 kernel (`arc2-object-dsl-symbolic-submission-v1`) again.

## Optional: fully automatic daily run (only if Len says so)
Install a systemd user timer that runs step 1 and step 4 daily at 00:20 UTC:
`systemctl --user` service `arc2-daily-submit` with
`ExecStart=/bin/bash -lc 'cd ~/arc/arc2-object-dsl && git pull -q && bash submission/daily_submit.sh'`
and timer `OnCalendar=*-*-* 00:20:00 UTC`, `Persistent=true`.
