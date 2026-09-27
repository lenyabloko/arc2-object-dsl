#!/bin/bash
# Daily gated Kaggle submission (run in WSL):  bash submission/daily_submit.sh
# Pulls the repo, pushes the newest submission/<version> kernel, waits for it, checks the parity gate
# (digest_match true AND correct_of_172 == expected), and only then submits. Never retries a failure.
# Writes a result record into the Windows repo folder so the cloud session can read it.
set -u
REPO=~/arc/arc2-object-dsl
COMP=arc-prize-2026-arc-agi-2
REPORT_DIR=/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/submissions
STATE=~/arc/.submitted_versions
mkdir -p "$REPORT_DIR"; touch "$STATE"
cd "$REPO" && git pull -q || { echo "git pull failed"; exit 1; }
V=$(cat submission/LATEST)                      # e.g. v2
DIR=submission/$V
KID=$(python3 -c "import json;print(json.load(open('$DIR/kernel-metadata.json'))['id'])")
EXP=$(python3 -c "import json;print(json.load(open('$DIR/EXPECTED.json'))['correct_of_172'])")
HASH=$(sha256sum "$DIR"/*.ipynb | cut -c1-16)
TODAY=$(date -u +%F)
rec() { python3 - "$@" <<'PY'
import json, sys
k = sys.argv[1::2]; v = sys.argv[2::2]
print(json.dumps(dict(zip(k, v))))
PY
}
out() { rec date "$TODAY" version "$V" kernel "$KID" "$@" | tee "$REPORT_DIR/$TODAY.json"; }
if grep -q "^$TODAY " "$STATE"; then out status skipped reason "already submitted today (UTC)"; exit 0; fi
if grep -q " $HASH$" "$STATE"; then out status skipped reason "this notebook version was already submitted; waiting for a newer one"; exit 0; fi
PUSH=$(kaggle kernels push -p "$DIR" 2>&1); echo "$PUSH"
KV=$(echo "$PUSH" | grep -o 'version [0-9]*' | head -1 | cut -d' ' -f2)
[ -n "$KV" ] || { out status push_failed detail "$(echo "$PUSH" | tail -1)"; exit 1; }
for i in $(seq 1 90); do                       # up to ~3 hours
  S=$(kaggle kernels status "$KID" 2>&1)
  case "$S" in *COMPLETE*) break;; *ERROR*|*CANCEL*) out status kernel_error kernel_version "$KV" detail "$S"; exit 1;; esac
  sleep 120
done
case "$S" in *COMPLETE*) ;; *) out status kernel_timeout kernel_version "$KV"; exit 1;; esac
OUTD=~/arc/out/${V}_$KV; mkdir -p "$OUTD"
kaggle kernels output "$KID" -p "$OUTD" >/dev/null 2>&1
P="$OUTD/parity_report.json"
[ -f "$P" ] || { out status no_parity_report kernel_version "$KV"; exit 1; }
OK=$(python3 -c "import json;r=json.load(open('$P'));print(int(r.get('digest_match') is True and r.get('correct_of_172')==$EXP))")
cp "$P" "$REPORT_DIR/${TODAY}_parity.json"
[ "$OK" = 1 ] || { out status parity_failed kernel_version "$KV"; exit 1; }
MSG="$V kernel v$KV parity ok $(date -u +%H%M%S)"
SUB=$(kaggle competitions submit -c "$COMP" -k "$KID" -f submission.json -v "$KV" -m "$MSG" 2>&1); echo "$SUB"
sleep 20
# Do not trust the CLI's reply text: confirm by finding our unique message in the submissions list.
if kaggle competitions submissions -c "$COMP" --csv 2>/dev/null | grep -qF "$MSG"; then
  echo "$TODAY $HASH" >> "$STATE"; out status submitted kernel_version "$KV" message "$MSG" detail "$(echo "$SUB" | tail -1)"
else
  out status submit_failed kernel_version "$KV" detail "$(echo "$SUB" | tail -1)"; exit 1
fi
