#!/bin/bash
# usage: cycle.sh TAG VOCAB
T=/kaggle/input/arc-prize-2026-arc-agi-2
mkdir -p m1b; rm -f m1b/$1_train.jsonl m1b/$1_deval.jsonl
M1B_VOCAB=$2 python3 occupancy2.py --challenges $T/arc-agi_training_challenges.json --solutions $T/arc-agi_training_solutions.json --out m1b/$1_train.jsonl --seconds 60 &
M1B_VOCAB=$2 python3 occupancy2.py --challenges $T/arc-agi_evaluation_challenges.json --solutions $T/arc-agi_evaluation_solutions.json --keys dev_eval_nl.txt --out m1b/$1_deval.jsonl --seconds 60 &
wait
