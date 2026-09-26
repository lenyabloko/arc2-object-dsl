"""Score a submission.json against a solutions file: python tools/score.py sub.json solutions.json"""
import json, sys
sub = json.load(open(sys.argv[1])); ans = json.load(open(sys.argv[2]))
c1 = c2 = wrong = n = 0
for k, v in sub.items():
    for s, t in zip(v, ans.get(k, [])):
        n += 1
        if s["attempt_1"] == t: c1 += 1
        elif s["attempt_2"] == t: c2 += 1
        elif s["attempt_1"] != [[0]]: wrong += 1
print(f"slots {n} correct_attempt1 {c1} correct_attempt2_only {c2} total {c1 + c2} wrong {wrong}")
