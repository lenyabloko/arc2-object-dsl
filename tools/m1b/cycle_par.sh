#!/bin/bash
# usage: cycle_par.sh TAG VOCAB [WORKERS]   -- same measurement as cycle.sh, sharded over N processes
T=/kaggle/input/arc-prize-2026-arc-agi-2; N=${3:-$(nproc)}; mkdir -p m1b/shards
python3 - "$N" <<'PY'
import json, sys
n = int(sys.argv[1])
tr = sorted(json.load(open('/kaggle/input/arc-prize-2026-arc-agi-2/arc-agi_training_challenges.json')))
ev = [k for k in open('dev_eval_nl.txt').read().split() if k]
jobs = [('train', k) for k in tr] + [('deval', k) for k in ev]
for i in range(n):
    for split in ('train', 'deval'):
        open(f'm1b/shards/{split}_{i}.txt', 'w').write('\n'.join(k for j, (s, k) in enumerate(jobs) if s == split and j % n == i))
PY
rm -f m1b/shards/$1_*.jsonl
for i in $(seq 0 $((N-1))); do
  ( M1B_VOCAB=$2 python3 occupancy2.py --challenges $T/arc-agi_training_challenges.json --solutions $T/arc-agi_training_solutions.json --keys m1b/shards/train_$i.txt --out m1b/shards/$1_train_$i.jsonl --seconds 60
    [ -s m1b/shards/deval_$i.txt ] && M1B_VOCAB=$2 python3 occupancy2.py --challenges $T/arc-agi_evaluation_challenges.json --solutions $T/arc-agi_evaluation_solutions.json --keys m1b/shards/deval_$i.txt --out m1b/shards/$1_deval_$i.jsonl --seconds 60 ) &
done
wait
cat m1b/shards/$1_train_*.jsonl > m1b/$1_train.jsonl; cat m1b/shards/$1_deval_*.jsonl > m1b/$1_deval.jsonl
