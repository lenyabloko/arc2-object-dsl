#!/bin/bash
# Record our Kaggle submission list (status + public score) for the cloud session (run in WSL):
#   bash submission/record_scores.sh
# Read-only: uses the kaggle CLI's own auth; never reads or copies credential files. Creates no temp files.
COMP=arc-prize-2026-arc-agi-2
REPORT_DIR=/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/submissions
mkdir -p "$REPORT_DIR"
T=$(date -u +%FT%H%MZ)
if CSV=$(kaggle competitions submissions -c "$COMP" --csv 2>/dev/null); then
  printf '# recorded %s\n%s\n' "$T" "$CSV" > "$REPORT_DIR/scores.txt"; echo "scores recorded -> $REPORT_DIR/scores.txt"
else
  echo "# $T: kaggle competitions submissions failed" > "$REPORT_DIR/scores.txt"
fi
