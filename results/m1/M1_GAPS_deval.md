# M1 gap report: public-eval dev (99 non-sealed)
Summary: {'needs_>2_attribute_or_>5_rule_concept': 13, 'indistinguishable_under_priors': 15}

## 16b78196 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:-12,-9': 1, 'move:-14,-9': 1, 'move:-13,-11': 1, 'move:-14,-15': 1, 'remove': 35, 'keep': 60}; cases: 99

## 16de56c4 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 18, 'recolor:const:3': 1, 'recolor:const:6': 2, 'move:0,7': 2}; cases: 23

## 1818057f (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 67, 'move:-1,0': 1, 'recolor:const:8': 10, 'move:3,2': 4, 'move:7,2': 3, 'move:6,3': 7, 'move:8,8': 2, 'move:4,3': 1, 'move:1,2': 3, 'move:7,0': 1, 'move:5,4': 1, 'move:4,9': 1, 'move:3,6': 1, 'move:2,7': 1}; cases: 103
- same prior intent, different change: pair0@(1,5) color=4 size=1 -> ['keep', 'move:-1,-1']  vs  pair0@(6,9) color=4 size=1 -> ['move:-1,-3', 'move:-1,-9']
- same prior intent, different change: pair0@(3,8) color=4 size=2 -> ['keep', 'move:-3,-4']  vs  pair0@(4,8) color=4 size=2 -> ['move:-1,0', 'move:-4,-4']

## 247ef758 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 69, 'remove': 12}; cases: 81

## 28a6681f (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 7, 'keep': 70}; cases: 77

## 2c181942 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 18, 'remove': 37}; cases: 55

## 31f7f899 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 67, 'remove': 16}; cases: 83

## 332f06d7 (nbvcg) — indistinguishable_under_priors
- label classes: {'move:-9,-6': 1, 'move:-9,-7': 1, 'keep': 82, 'recolor:const:0': 3, 'move:5,-1': 1, 'move:5,-3': 1, 'move:3,0': 1, 'move:-4,-4': 1, 'remove': 3, 'move:8,3': 1}; cases: 95
- same prior intent, different change: pair0@(3,7) color=1 size=5 -> ['keep', 'move:-1,-5']  vs  pair1@(7,9) color=1 size=5 -> ['move:-3,-3', 'move:-3,-4']

## 409aa875 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 45, 'move:8,6': 1, 'move:7,6': 1}; cases: 47
- same prior intent, different change: pair2@(7,8) color=2 size=1 -> ['move:-1,-2', 'move:-1,-3']  vs  pair2@(12,13) color=2 size=1 -> ['keep', 'move:-1,0']

## 4c3d4a41 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 34, 'move:-1,0': 8, 'move:-3,0': 1, 'move:-2,0': 3, 'move:6,2': 2, 'move:6,3': 2, 'remove': 18, 'move:5,4': 2}; cases: 70

## 5961cc34 (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 16, 'keep': 4, 'recolor:adj': 4, 'recolor:const:2': 44}; cases: 68
- same prior intent, different change: pair0@(2,2) color=1 size=4 -> ['recolor:const:8', 'remove']  vs  pair1@(13,9) color=1 size=4 -> ['recolor:const:2']
- same prior intent, different change: pair0@(2,3) color=1 size=4 -> ['recolor:const:8', 'remove']  vs  pair1@(13,9) color=1 size=4 -> ['recolor:const:2']

## 6e453dd6 (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 23, 'move:0,5': 1, 'keep': 29, 'move:7,1': 1, 'move:7,2': 1, 'slide:up': 1, 'move:4,0': 1, 'move:0,2': 1, 'move:0,1': 3}; cases: 61
- same prior intent, different change: pair0@(0,2) color=0 size=1 -> ['move:0,3', 'move:0,4']  vs  pair2@(0,4) color=0 size=1 -> ['keep', 'move:0,-1']
- same prior intent, different change: pair0@(2,2) color=0 size=2 -> ['move:-1,4', 'move:-1,6']  vs  pair2@(9,5) color=0 size=2 -> ['keep', 'move:-3,-2']

## 71e489b6 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 36, 'move:3,0': 2, 'move:-9,0': 1, 'remove': 3, 'move:5,0': 1, 'move:6,0': 1, 'move:3,3': 1, 'move:4,0': 1, 'move:2,0': 1, 'move:-1,0': 1, 'move:0,7': 1, 'move:-2,0': 1}; cases: 50
- same prior intent, different change: pair0@(5,0) color=0 size=17 -> ['move:1,0', 'move:10,0']  vs  pair0@(8,0) color=0 size=17 -> ['keep', 'move:-1,0']
- same prior intent, different change: pair0@(5,0) color=0 size=17 -> ['move:1,0', 'move:10,0']  vs  pair0@(16,0) color=0 size=17 -> ['move:-1,0', 'move:-10,0']

## 7491f3cf (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 185, 'move:2,-12': 1, 'move:1,-12': 1, 'move:0,-12': 1, 'move:-1,-12': 1, 'move:-2,-12': 1}; cases: 190
- same prior intent, different change: pair2@(2,19) color=9 size=5 -> ['move:1,-12']  vs  pair2@(4,19) color=9 size=5 -> ['move:-1,-12']

## 7b0280bc (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 61, 'move:-6,8': 1, 'move:-5,2': 1, 'move:7,2': 2, 'move:9,7': 2, 'move:9,2': 2, 'move:7,0': 1, 'move:5,9': 1, 'move:9,5': 1, 'recolor:const:5': 2, 'move:14,0': 1}; cases: 75
- same prior intent, different change: pair1@(5,13) color=4 size=1 -> ['keep', 'move:-1,-7']  vs  pair1@(1,5) color=4 size=1 -> ['move:1,8', 'move:10,-5']
- same prior intent, different change: pair1@(6,12) color=7 size=4 -> ['keep', 'move:1,-5']  vs  pair1@(1,3) color=7 size=4 -> ['move:11,2', 'move:11,6']

## 8b9c3697 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 49, 'remove': 17, 'move:0,-8': 1, 'move:1,9': 1, 'move:8,0': 2, 'slide:up': 4}; cases: 74
- same prior intent, different change: pair1@(16,4) color=2 size=1 -> ['move:-11,2', 'move:-6,11']  vs  pair1@(9,6) color=2 size=1 -> ['move:-4,0', 'move:0,10']

## 8f215267 (nbhcg) — indistinguishable_under_priors
- label classes: {'remove': 47, 'keep': 72}; cases: 119
- same prior intent, different change: pair0@(9,11) color=8 size=1 -> ['keep', 'move:-1,-10']  vs  pair0@(19,18) color=8 size=1 -> ['move:-10,-11', 'move:-10,-13']
- same prior intent, different change: pair0@(10,11) color=8 size=1 -> ['keep', 'move:-1,-10']  vs  pair0@(19,18) color=8 size=1 -> ['move:-10,-11', 'move:-10,-13']

## 8f3a5a89 (nbhcg) — indistinguishable_under_priors
- label classes: {'remove': 10, 'keep': 48}; cases: 58
- same prior intent, different change: pair0@(1,10) color=1 size=2 -> ['recolor:const:8', 'remove']  vs  pair2@(10,9) color=1 size=2 -> ['keep', 'move:-2,-8']
- same prior intent, different change: pair0@(1,10) color=1 size=2 -> ['recolor:const:8', 'remove']  vs  pair2@(11,9) color=1 size=2 -> ['keep', 'move:-1,0']

## 9385bd28 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 63, 'recolor:const:9': 1, 'move:6,-5': 1, 'move:2,-6': 1, 'recolor:const:6': 1, 'move:0,-7': 2}; cases: 69

## 9aaea919 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 85, 'remove': 30, 'recolor:const:5': 30}; cases: 145

## 9bbf930d (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 115, 'remove': 10}; cases: 125

## aa4ec2a5 (nbvcg) — indistinguishable_under_priors
- label classes: {'move:9,7': 5, 'move:9,5': 1, 'move:6,3': 2, 'move:7,2': 1, 'move:7,1': 1, 'keep': 36, 'move:9,-4': 4, 'move:9,1': 1, 'move:12,0': 2, 'move:7,0': 1, 'move:9,-8': 2, 'move:9,-9': 2, 'move:9,-10': 1, 'move:7,5': 2, 'move:9,4': 1, 'move:9,2': 1, 'move:5,1': 2, 'move:9,0': 3, 'move:6,0': 1, 'move:6,-2': 1, 'recolor:const:8': 3, 'move:-10,0': 1, 'move:-9,0': 1, 'move:-11,-2': 1, 'move:-6,6': 1, 'move:-10,-6': 1, 'move:-10,-7': 1}; cases: 79
- same prior intent, different change: pair0@(2,6) color=1 size=6 -> ['move:8,4', 'move:8,5']  vs  pair1@(11,10) color=1 size=6 -> ['keep', 'move:-1,-1']
- same prior intent, different change: pair0@(2,6) color=1 size=6 -> ['move:8,4', 'move:8,5']  vs  pair1@(11,11) color=1 size=6 -> ['keep', 'move:-1,-2']

## c7f57c3e (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 36, 'move:4,6': 1, 'move:-1,0': 1, 'move:-3,0': 1, 'move:-4,9': 1, 'recolor:const:8': 2, 'move:12,0': 1, 'move:4,-9': 1, 'remove': 4}; cases: 48
- same prior intent, different change: pair0@(11,10) color=2 size=2 -> ['keep', 'move:1,0']  vs  pair0@(13,10) color=2 size=2 -> ['move:-1,0', 'move:-2,0']

## cbebaa4b (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 28, 'keep': 9, 'move:6,3': 1, 'move:1,1': 1, 'move:3,3': 1, 'move:-2,1': 1}; cases: 41
- same prior intent, different change: pair0@(4,8) color=2 size=1 -> ['move:10,2', 'move:12,8']  vs  pair1@(17,4) color=2 size=1 -> ['move:-10,11', 'move:-10,3']
- same prior intent, different change: pair0@(7,8) color=2 size=1 -> ['move:-1,0', 'move:-1,4']  vs  pair1@(17,4) color=2 size=1 -> ['move:-10,11', 'move:-10,3']

## d59b0160 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 28, 'keep': 60, 'move:0,-4': 1, 'move:-5,0': 1, 'move:-7,0': 1, 'move:-1,-8': 1, 'recolor:largest': 2, 'move:7,-9': 1, 'move:3,-7': 1, 'move:3,-10': 1, 'move:6,-5': 1, 'move:6,-6': 1, 'move:-2,2': 1, 'move:3,-11': 1, 'move:8,-7': 1, 'move:5,-3': 1, 'move:10,1': 1, 'move:8,-4': 1, 'move:-3,6': 1, 'move:5,3': 1, 'move:3,3': 1, 'move:4,-2': 1}; cases: 109

## dd6b8c4b (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 44, 'move:2,0': 2, 'remove': 13, 'recolor:const:9': 5, 'move:-1,1': 1, 'move:1,0': 1}; cases: 66
- same prior intent, different change: pair0@(5,5) color=2 size=1 -> ['keep']  vs  pair1@(5,5) color=2 size=1 -> ['recolor:const:9']
- same prior intent, different change: pair0@(5,4) color=3 size=1 -> ['keep', 'move:-1,2']  vs  pair1@(5,4) color=3 size=1 -> ['recolor:const:9']

## dfadab01 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:4': 18, 'remove': 17, 'recolor:const:6': 7, 'keep': 4, 'recolor:const:7': 6}; cases: 52

## e3721c99 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 8, 'recolor:const:3': 5, 'recolor:const:1': 2, 'recolor:const:2': 5, 'remove': 2, 'recolor:const:4': 3}; cases: 25

