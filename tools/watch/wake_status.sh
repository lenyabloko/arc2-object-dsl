#!/bin/bash
# One-screen status of the WSL wake loop:  bash tools/watch/wake_status.sh
R=~/arc/arc2-object-dsl; OUT=/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/wsl_results/wake
L=$(ps -eo pid,etime,args | awk '$3=="/bin/bash" && $4 ~ /wake_loop\.sh$/')
if [ -n "$L" ]; then echo "wake loop: RUNNING  (pid, uptime: $(echo $L | awk '{print $1", "$2}'))"; else echo "wake loop: NOT RUNNING  -> cd ~/arc/wsl_work/wake && nohup setsid ./wake_loop.sh >> wake_loop.log 2>&1 < /dev/null &"; fi
J=$(ps -eo etime,args | awk '/[w]ake_eval\.py/ {for(i=1;i<=NF;i++) if($i ~ /wake_jobs\/.*\.json$/){print $1, $i; exit}}')
if [ -n "$J" ]; then echo "current job: $(echo $J | awk '{print $2}' | xargs basename)  (running for $(echo $J | awk '{print $1}'))"; else echo "current job: none (idle, next check within 5 min)"; fi
echo "jobs:"
for j in $R/wake_jobs/*.json; do id=$(basename $j .json); d=$OUT/$id
  if [ -f $d/summary.json ]; then s="done   "; elif [ -f $d/ERROR.txt ]; then s="FAILED "; elif [ "$id" = "$(echo $J | awk '{print $2}' | xargs -r basename 2>/dev/null | sed 's/.json$//')" ]; then s="running"; else s="pending"; fi
  echo "  $s $id"; done
HB=/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox/status/STATUS.txt; [ -f $HB ] && { echo "cloud Claude:"; sed 's/^/  /' $HB | head -3; }
