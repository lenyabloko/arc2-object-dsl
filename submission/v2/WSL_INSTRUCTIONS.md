# v2 submission — steps for WSL Claude (manual, gated)

Run from `~/arc/arc2-object-dsl` after `git pull`.

1. Push the notebook (new kernel):
   `kaggle kernels push -p submission/v2`
2. Poll until finished: `kaggle kernels status lenyabloko/arc2-lattice-rdr-symbolic-submission`
   (expect COMPLETE; about 10–20 minutes).
3. Download outputs: `kaggle kernels output lenyabloko/arc2-lattice-rdr-symbolic-submission -p out_v2`
4. Open `out_v2/parity_report.json`. **Submit only if** `digest_match` is `true` **and** `correct_of_172` is `3`.
   If either differs, or the kernel ERRORed: do not submit, do not retry; report the file contents.
5. If the gate passes, submit that kernel version to the competition:
   `kaggle competitions submit -c arc-prize-2026-arc-agi-2 -k lenyabloko/arc2-lattice-rdr-symbolic-submission -f submission.json -v <version> -m "v2 lattice RDR V3 vocab, parity 3/172"`
   (`<version>` = the version number shown by step 1).
6. Report: submission id, status, and public score when COMPLETE (`kaggle competitions submissions -c arc-prize-2026-arc-agi-2`).

Never print, copy or move Kaggle credential files.
