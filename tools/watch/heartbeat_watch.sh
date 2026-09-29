#!/bin/bash
# Watchdog for the cloud Claude session. Run detached in WSL:  nohup bash tools/watch/heartbeat_watch.sh >/dev/null 2>&1 &
# Every 10 minutes it reads cloud_outbox/status/heartbeat.json. If the heartbeat is older than its stale_after_minutes
# (default 90), it logs the event and shows one Windows notification per stale episode. Read-only; never deletes anything.
HB=/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/status/heartbeat.json
LOG=$HOME/arc/heartbeat_watch.log
ALERTED=0
while true; do
  if [ -f "$HB" ]; then
    read AGE LIMIT DOING < <(python3 - "$HB" <<'PY'
import json, sys, datetime
h = json.load(open(sys.argv[1]))
t = datetime.datetime.strptime(h["alive_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
age = int((datetime.datetime.utcnow() - t).total_seconds() // 60)
print(age, h.get("stale_after_minutes", 90), h.get("doing", "")[:80].replace("\n", " "))
PY
)
    if [ "${AGE:-0}" -gt "${LIMIT:-90}" ]; then
      if [ "$ALERTED" = 0 ]; then
        echo "$(date -Is) STALE ${AGE} min (limit ${LIMIT}) last: ${DOING}" >> "$LOG"
        powershell.exe -NoProfile -Command "[reflection.assembly]::loadwithpartialname('System.Windows.Forms')|Out-Null;[reflection.assembly]::loadwithpartialname('System.Drawing')|Out-Null;\$n=New-Object System.Windows.Forms.NotifyIcon;\$n.Icon=[System.Drawing.SystemIcons]::Warning;\$n.Visible=\$true;\$n.ShowBalloonTip(15000,'ARC cloud Claude','No heartbeat for ${AGE} min. Last: ${DOING//\'/}','Warning');Start-Sleep 16;\$n.Dispose()" >/dev/null 2>&1
        ALERTED=1
      fi
    else
      [ "$ALERTED" = 1 ] && echo "$(date -Is) alive again (${AGE} min)" >> "$LOG"
      ALERTED=0
    fi
  fi
  sleep 600
done
