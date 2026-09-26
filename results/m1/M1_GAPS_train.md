# M1 gap report: training (1000)
Summary: {'needs_>2_attribute_or_>5_rule_concept': 98, 'indistinguishable_under_priors': 100}

## 025d127b (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:3,-2': 1, 'move:0,1': 3, 'keep': 3, 'remove': 8, 'move:9,1': 1, 'move:5,1': 1}; cases: 17

## 06df4c85 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:6,0': 12, 'keep': 145, 'move:6,3': 1, 'move:6,6': 3, 'move:3,0': 5, 'move:9,0': 2}; cases: 168

## 08ed6ac7 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:2': 2, 'recolor:const:1': 2, 'recolor:const:4': 2, 'recolor:const:3': 2}; cases: 8

## 09629e4f (nbccg) — indistinguishable_under_priors
- label classes: {'move:6,0': 8, 'move:8,-8': 3, 'move:0,-2': 4, 'move:3,-4': 4, 'keep': 20, 'move:9,-2': 2, 'move:3,-8': 1, 'move:1,-8': 2, 'move:1,3': 3, 'move:-7,3': 1, 'move:-3,0': 2, 'move:-6,-4': 5, 'move:-2,-4': 3, 'move:-5,4': 4, 'move:-8,1': 3, 'move:0,4': 8, 'move:3,8': 3, 'move:-4,1': 5, 'move:2,0': 1, 'move:-6,9': 1, 'move:1,8': 3, 'move:4,5': 7, 'move:4,-4': 1, 'move:-2,6': 3, 'move:0,-5': 1, 'recolor:const:6': 3, 'recolor:const:3': 3, 'recolor:const:0': 19, 'recolor:const:4': 4, 'recolor:const:2': 3, 'move:-7,6': 1, 'move:-4,4': 1, 'move:-8,9': 1, 'move:-6,0': 1, 'move:-4,7': 1, 'move:-3,-4': 1, 'move:3,1': 6, 'move:1,-4': 4, 'move:5,3': 1, 'move:0,5': 1, 'move:5,-9': 1, 'move:2,-6': 2, 'move:0,-9': 2, 'move:2,7': 2, 'move:7,9': 1, 'move:8,1': 1, 'move:8,4': 2, 'move:3,3': 1, 'move:6,-3': 2, 'move:-3,1': 3, 'move:9,-5': 2, 'move:7,0': 1, 'move:-8,-6': 2, 'move:-9,5': 1, 'move:-8,0': 1, 'move:-3,5': 1, 'move:-3,9': 2, 'move:1,7': 1, 'move:-4,-8': 1, 'move:4,-6': 2, 'move:-6,2': 1}; cases: 180
- same prior intent, different change: pair0@(8,1) color=3 size=1 -> ['move:-6,3', 'move:-6,4']  vs  pair2@(6,9) color=3 size=1 -> ['move:2,-3', 'move:2,-4']
- same prior intent, different change: pair0@(6,1) color=6 size=1 -> ['move:-1,3', 'move:-1,4']  vs  pair1@(8,1) color=6 size=1 -> ['move:0,7', 'move:0,8']

## 0a2355a6 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:1': 7, 'recolor:const:2': 3, 'recolor:const:3': 4, 'recolor:const:4': 1}; cases: 15

## 0becf7df (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:3': 1, 'keep': 12, 'recolor:const:8': 1, 'recolor:largest': 2, 'recolor:const:2': 2, 'recolor:const:4': 2, 'recolor:adj': 1, 'move:-2,1': 1, 'recolor:const:7': 1, 'move:2,1': 1, 'move:1,0': 1, 'move:4,0': 1, 'move:0,1': 1}; cases: 27

## 0d3d703e (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:9': 2, 'recolor:const:1': 1, 'recolor:const:2': 1, 'recolor:const:6': 3, 'recolor:const:4': 2, 'recolor:const:8': 1, 'recolor:const:3': 1, 'recolor:const:5': 1}; cases: 12

## 0d87d2a6 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 20, 'recolor:const:1': 3, 'move:6,0': 1, 'move:-8,3': 1, 'move:7,9': 1, 'move:8,4': 1}; cases: 27

## 11dc524f (nbhcg) — indistinguishable_under_priors
- label classes: {'remove': 8, 'move:1,0': 2, 'keep': 3, 'move:2,0': 1, 'move:-1,0': 1}; cases: 15
- same prior intent, different change: pair0@(6,4) color=5 size=2 -> ['move:1,0']  vs  pair2@(7,4) color=5 size=2 -> ['keep']

## 17829a00 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 65, 'remove': 33, 'slide:up': 2}; cases: 100

## 17cae0c1 (nbvcg) — indistinguishable_under_priors
- label classes: {'recolor:const:6': 6, 'recolor:const:3': 9, 'recolor:const:1': 6, 'recolor:const:9': 6, 'recolor:const:4': 3}; cases: 30
- same prior intent, different change: pair2@(0,3) color=5 size=1 -> ['recolor:const:6']  vs  pair2@(0,7) color=5 size=1 -> ['recolor:const:3']
- same prior intent, different change: pair2@(0,3) color=5 size=1 -> ['recolor:const:6']  vs  pair3@(0,1) color=5 size=1 -> ['recolor:const:3']

## 18286ef8 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 90, 'move:0,-1': 2, 'recolor:const:9': 3, 'move:1,1': 1, 'move:0,1': 2, 'move:-3,-7': 1}; cases: 99
- same prior intent, different change: pair0@(4,4) color=5 size=3 -> ['keep', 'move:0,1']  vs  pair0@(4,6) color=5 size=3 -> ['move:0,-1', 'move:0,-2']
- same prior intent, different change: pair2@(4,7) color=5 size=3 -> ['move:0,1', 'move:0,2']  vs  pair2@(4,9) color=5 size=3 -> ['keep', 'move:0,-1']

## 1acc24af (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 9, 'recolor:const:2': 8}; cases: 17
- same prior intent, different change: pair0@(8,10) color=5 size=3 -> ['recolor:const:2']  vs  pair2@(8,8) color=5 size=3 -> ['keep', 'move:0,3']
- same prior intent, different change: pair0@(8,10) color=5 size=3 -> ['recolor:const:2']  vs  pair3@(8,4) color=5 size=3 -> ['keep']

## 1c02dbbe (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 65, 'move:0,7': 1, 'move:2,0': 2, 'move:-4,4': 1, 'move:2,-5': 1, 'remove': 2, 'move:0,8': 2, 'move:0,4': 4, 'move:0,2': 1, 'move:6,0': 1, 'move:0,-1': 1, 'move:5,2': 1, 'move:-1,0': 1}; cases: 83
- same prior intent, different change: pair1@(3,4) color=5 size=10 -> ['move:0,5', 'move:0,6']  vs  pair1@(3,8) color=5 size=10 -> ['move:0,1', 'move:0,2']
- same prior intent, different change: pair1@(3,4) color=5 size=10 -> ['move:0,5', 'move:0,6']  vs  pair1@(3,9) color=5 size=10 -> ['keep', 'move:0,1']

## 1c56ad9f (nbhcg) — indistinguishable_under_priors
- label classes: {'move:3,0': 4, 'keep': 45, 'remove': 37, 'move:2,0': 1, 'move:1,0': 1, 'move:0,1': 1}; cases: 89
- same prior intent, different change: pair0@(5,4) color=5 size=8 -> ['keep', 'move:-3,-1']  vs  pair0@(8,4) color=5 size=8 -> ['move:-3,0', 'move:-6,-1']

## 1d61978c (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:2': 23, 'recolor:const:8': 31, 'keep': 3}; cases: 57
- same prior intent, different change: pair0@(3,7) color=5 size=1 -> ['recolor:const:8']  vs  pair0@(11,4) color=5 size=1 -> ['recolor:const:2']
- same prior intent, different change: pair0@(3,7) color=5 size=1 -> ['recolor:const:8']  vs  pair0@(10,5) color=5 size=1 -> ['recolor:const:2']

## 1da012fc (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:4': 2, 'recolor:const:6': 1, 'recolor:const:3': 2, 'recolor:const:2': 2, 'keep': 9}; cases: 16

## 1e0a9b12 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 10, 'remove': 10}; cases: 20

## 1e81d6f9 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 67, 'remove': 13}; cases: 80
- same prior intent, different change: pair0@(8,14) color=2 size=1 -> ['keep', 'move:-6,-5']  vs  pair1@(12,14) color=2 size=1 -> ['move:-11,-13', 'recolor:const:0']

## 1f642eb9 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 19, 'move:3,0': 1, 'move:1,0': 3, 'move:-1,0': 2, 'move:-2,0': 2, 'move:2,0': 1}; cases: 28
- same prior intent, different change: pair1@(3,4) color=8 size=2 -> ['move:1,0', 'move:2,0']  vs  pair1@(5,4) color=8 size=2 -> ['keep', 'move:-1,0']
- same prior intent, different change: pair2@(6,3) color=8 size=3 -> ['move:-1,0']  vs  pair2@(7,3) color=8 size=3 -> ['move:-2,0']

## 20981f0e (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 2, 'move:1,0': 2, 'keep': 34, 'move:1,1': 2, 'slide:up': 1, 'move:1,-1': 2, 'move:0,1': 2, 'move:6,0': 1, 'move:4,6': 1}; cases: 47
- same prior intent, different change: pair0@(4,7) color=1 size=3 -> ['move:-1,-4', 'move:-1,1']  vs  pair1@(3,3) color=1 size=3 -> ['move:1,1', 'move:6,1']
- same prior intent, different change: pair0@(2,13) color=1 size=3 -> ['move:1,-10', 'move:1,0']  vs  pair0@(8,13) color=1 size=3 -> ['keep', 'move:-5,-10']

## 2204b7a8 (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:4': 3, 'recolor:const:7': 2, 'keep': 6, 'recolor:const:1': 2, 'recolor:const:2': 1, 'recolor:const:8': 3, 'recolor:const:9': 3}; cases: 20
- same prior intent, different change: pair0@(6,4) color=3 size=1 -> ['recolor:const:7']  vs  pair0@(3,3) color=3 size=1 -> ['recolor:const:4']
- same prior intent, different change: pair0@(3,3) color=3 size=1 -> ['recolor:const:4']  vs  pair0@(7,8) color=3 size=1 -> ['recolor:const:7']

## 22806e14 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 2, 'move:5,1': 1, 'keep': 15, 'move:-5,1': 1, 'move:1,6': 1, 'move:5,2': 2, 'move:8,9': 1, 'move:8,-8': 1, 'move:12,-2': 1, 'move:1,5': 1, 'move:9,4': 1}; cases: 27

## 228f6490 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 21, 'move:-7,1': 1, 'move:3,0': 1, 'remove': 6, 'move:6,0': 2, 'move:0,-5': 1, 'move:0,4': 1}; cases: 33

## 22a4bbc2 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 29, 'move:3,0': 1, 'move:15,1': 1, 'move:-6,0': 3, 'recolor:const:2': 4, 'move:6,0': 1, 'move:3,-1': 1, 'move:4,2': 1, 'move:-3,2': 1, 'move:3,1': 1, 'move:4,1': 1, 'move:7,0': 1}; cases: 45
- same prior intent, different change: pair0@(12,0) color=1 size=4 -> ['keep']  vs  pair0@(9,0) color=1 size=4 -> ['move:3,0', 'recolor:const:2']
- same prior intent, different change: pair0@(13,0) color=8 size=6 -> ['recolor:const:2']  vs  pair1@(15,0) color=8 size=6 -> ['keep', 'move:-12,1']

## 230f2e48 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 21, 'remove': 12}; cases: 33
- same prior intent, different change: pair1@(3,3) color=2 size=1 -> ['keep', 'move:0,-1']  vs  pair1@(3,5) color=2 size=1 -> ['move:0,-2', 'move:0,-3']
- same prior intent, different change: pair2@(9,3) color=2 size=1 -> ['keep', 'move:-1,1']  vs  pair2@(9,5) color=2 size=1 -> ['move:-1,-1', 'move:-1,2']

## 2546ccf6 (ccgbr) — indistinguishable_under_priors
- label classes: {'move:5,5': 1, 'keep': 53, 'move:0,-5': 1, 'move:0,5': 1}; cases: 56
- same prior intent, different change: pair0@(0,5) color=0 size=16 -> ['move:0,5', 'move:10,-5']  vs  pair0@(0,10) color=0 size=16 -> ['keep', 'move:10,-10']

## 256b0a75 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:9,1': 2, 'keep': 68, 'move:7,5': 1, 'move:7,1': 2, 'move:7,0': 1}; cases: 74

## 2601afb7 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 15, 'move:1,-6': 1, 'move:0,-6': 1, 'move:2,2': 9, 'move:0,2': 18, 'move:3,-4': 1, 'move:1,-4': 2, 'move:0,-4': 1, 'move:4,2': 2, 'move:3,2': 1, 'move:1,-8': 3, 'move:0,-8': 1}; cases: 55

## 272f95fa (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:2': 1, 'move:3,0': 2, 'recolor:const:6': 1, 'recolor:const:1': 1, 'keep': 2, 'move:0,8': 2, 'move:6,0': 2, 'move:9,7': 1}; cases: 12

## 29623171 (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 20, 'keep': 10}; cases: 30
- same prior intent, different change: pair0@(9,10) color=2 size=1 -> ['move:-3,-10', 'move:-3,-8']  vs  pair0@(1,10) color=2 size=1 -> ['keep', 'move:-1,-1']

## 2a28add5 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 40, 'recolor:const:8': 19, 'keep': 1}; cases: 60

## 2de01db2 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 20, 'move:1,0': 1, 'move:1,5': 1, 'move:0,2': 1, 'move:0,8': 1, 'recolor:const:4': 3, 'recolor:const:0': 2, 'recolor:const:8': 3, 'move:0,-3': 1, 'recolor:largest': 2}; cases: 35

## 2e65ae53 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:6,0': 1, 'move:5,-9': 1, 'move:10,3': 1, 'recolor:const:9': 1, 'move:6,3': 1, 'move:5,6': 4, 'move:5,1': 1, 'move:1,6': 1, 'move:2,3': 1, 'move:0,8': 1, 'move:3,0': 1, 'keep': 16, 'move:7,5': 3, 'move:9,1': 1, 'move:8,9': 4, 'move:2,5': 2}; cases: 40

## 2f767503 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 44, 'remove': 6}; cases: 50

## 2faf500b (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,-1': 3, 'move:0,1': 3, 'move:1,-9': 1, 'move:1,0': 3, 'remove': 23, 'slide:up': 1, 'move:9,0': 1, 'move:-1,0': 1, 'move:6,0': 1, 'move:7,5': 1, 'move:0,8': 1}; cases: 39

## 31aa019c (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 53, 'recolor:const:2': 4, 'keep': 3}; cases: 60

## 32e9702f (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 15, 'move:0,-2': 2, 'move:3,-4': 1, 'move:0,-1': 1, 'move:2,0': 2}; cases: 21

## 3391f8c0 (nbccg) — indistinguishable_under_priors
- label classes: {'move:-4,4': 1, 'remove': 14, 'move:4,-4': 1, 'move:4,0': 2, 'move:0,3': 1, 'move:3,3': 1, 'move:3,6': 1, 'move:3,0': 1, 'move:0,-3': 1, 'move:0,-6': 1, 'move:2,3': 1, 'move:2,-3': 1, 'move:0,6': 2}; cases: 28
- same prior intent, different change: pair3@(3,4) color=8 size=4 -> ['move:2,3']  vs  pair3@(3,10) color=8 size=4 -> ['move:2,-3']

## 33b52de3 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 16, 'recolor:const:8': 4, 'recolor:const:1': 16, 'recolor:const:4': 3, 'recolor:const:2': 6, 'recolor:const:3': 2}; cases: 47
- same prior intent, different change: pair0@(5,10) color=5 size=7 -> ['recolor:const:8']  vs  pair0@(5,14) color=5 size=7 -> ['recolor:const:1']
- same prior intent, different change: pair0@(9,6) color=5 size=7 -> ['recolor:const:1']  vs  pair0@(9,14) color=5 size=7 -> ['recolor:const:4', 'recolor:least_common']

## 363442ee (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:3': 5, 'keep': 19, 'recolor:const:6': 3, 'recolor:const:8': 5}; cases: 32
- same prior intent, different change: pair0@(7,5) color=1 size=1 -> ['recolor:const:3']  vs  pair2@(4,8) color=1 size=1 -> ['recolor:const:8']
- same prior intent, different change: pair0@(7,5) color=1 size=1 -> ['recolor:const:3']  vs  pair2@(7,8) color=1 size=1 -> ['recolor:const:8']

## 37d3e8b2 (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:2': 5, 'recolor:const:3': 4, 'recolor:const:7': 3, 'recolor:const:1': 3}; cases: 15
- same prior intent, different change: pair1@(3,5) color=8 size=31 -> ['recolor:const:3']  vs  pair2@(7,2) color=8 size=38 -> ['recolor:const:7']

## 39e1d7f9 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 98, 'move:4,0': 6, 'move:0,8': 8, 'move:0,5': 1, 'move:-5,0': 1, 'move:8,0': 2}; cases: 116

## 3bd292e8 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 6, 'recolor:const:3': 4, 'recolor:const:5': 5}; cases: 15
- same prior intent, different change: pair0@(0,0) color=7 size=19 -> ['recolor:const:3']  vs  pair2@(0,0) color=7 size=20 -> ['recolor:const:5']

## 3bdb4ada (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 33, 'move:0,1': 29}; cases: 62
- same prior intent, different change: pair0@(1,2) color=1 size=3 -> ['move:0,-1', 'move:0,1']  vs  pair0@(1,3) color=1 size=3 -> ['keep', 'move:0,-2']
- same prior intent, different change: pair0@(1,2) color=1 size=3 -> ['move:0,-1', 'move:0,1']  vs  pair0@(1,5) color=1 size=3 -> ['keep', 'move:0,-2']

## 3c9b0459 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 9, 'slide:up': 1, 'keep': 4, 'move:0,1': 2}; cases: 16

## 3d588dc9 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 2, 'move:8,4': 2, 'move:5,3': 2, 'keep': 24, 'move:-5,0': 1, 'move:-6,-2': 1, 'move:-7,0': 1}; cases: 33

## 4093f84a (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 22, 'recolor:adj': 4, 'recolor:const:5': 1, 'keep': 3}; cases: 30
- same prior intent, different change: pair0@(12,10) color=3 size=1 -> ['recolor:const:0', 'remove']  vs  pair0@(6,10) color=3 size=1 -> ['recolor:const:5', 'recolor:largest']
- same prior intent, different change: pair0@(9,2) color=3 size=1 -> ['recolor:const:0', 'remove']  vs  pair0@(6,10) color=3 size=1 -> ['recolor:const:5', 'recolor:largest']

## 40f6cd08 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 116, 'move:3,0': 5, 'move:2,0': 6, 'move:6,0': 2, 'move:-1,0': 1, 'move:-2,0': 1, 'move:-4,0': 1, 'move:-5,0': 1, 'move:-6,0': 2, 'move:-8,0': 1, 'move:7,0': 1, 'move:5,0': 2, 'move:1,0': 1}; cases: 140
- same prior intent, different change: pair0@(9,19) color=2 size=9 -> ['keep', 'move:-1,0']  vs  pair0@(12,19) color=2 size=9 -> ['move:-1,-14', 'move:-1,-15']
- same prior intent, different change: pair0@(10,19) color=2 size=9 -> ['keep', 'move:-1,-14']  vs  pair0@(13,19) color=2 size=9 -> ['move:-10,-14', 'move:-10,-15']

## 41ace6b5 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:-4,8': 1, 'move:-7,6': 1, 'move:-5,4': 4, 'move:-6,2': 1, 'move:-3,0': 1, 'keep': 36, 'slide:up': 5, 'move:-2,6': 2, 'move:-1,0': 1, 'move:-2,2': 3, 'move:-2,0': 3, 'move:-3,4': 1, 'move:-1,4': 1, 'move:-2,8': 1, 'move:-4,4': 2, 'move:-4,0': 2, 'move:-3,8': 1}; cases: 66

## 423a55dc (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 25, 'keep': 7, 'move:3,1': 1, 'move:0,1': 1, 'move:1,0': 1, 'move:4,0': 1}; cases: 36

## 42a15761 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,4': 4, 'keep': 4, 'move:0,-12': 1, 'move:0,-4': 2}; cases: 11

## 4347f46a (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 14, 'move:0,3': 5, 'move:0,2': 6, 'move:0,1': 7, 'move:0,5': 3, 'move:0,4': 4, 'move:0,6': 1}; cases: 40
- same prior intent, different change: pair0@(1,2) color=2 size=4 -> ['move:0,-1', 'move:0,3']  vs  pair0@(1,3) color=2 size=4 -> ['move:0,-2', 'move:0,2']
- same prior intent, different change: pair0@(1,2) color=2 size=4 -> ['move:0,-1', 'move:0,3']  vs  pair0@(1,4) color=2 size=4 -> ['move:0,-3', 'move:0,1']

## 4364c1c4 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,1': 7, 'remove': 3, 'move:3,-4': 1, 'move:2,-1': 1, 'move:1,-1': 4, 'move:0,-1': 4, 'move:1,1': 4, 'move:3,1': 3, 'move:2,1': 1}; cases: 28

## 46c35fc7 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,2': 5, 'move:5,1': 1, 'move:2,0': 2, 'move:-1,-1': 2, 'move:-1,1': 3, 'keep': 7, 'move:-2,0': 3, 'move:0,-2': 2, 'move:1,1': 5, 'move:0,1': 2, 'move:1,0': 3, 'move:3,4': 1, 'move:1,-1': 3, 'move:2,1': 1}; cases: 40

## 470c91de (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:-1,1': 7, 'slide:up': 4, 'remove': 9, 'recolor:adj': 7, 'move:-1,0': 1, 'move:1,1': 3, 'move:2,1': 3, 'move:1,0': 1, 'move:1,-1': 1, 'recolor:const:9': 1}; cases: 37

## 48634b99 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 119, 'move:2,7': 3, 'move:0,-7': 1, 'move:-3,-7': 1, 'move:6,0': 2, 'move:-7,-12': 1, 'move:2,-5': 1, 'move:2,-2': 1, 'move:7,-9': 2, 'move:5,-9': 1, 'move:4,5': 2, 'move:3,5': 1, 'move:1,5': 1}; cases: 136
- same prior intent, different change: pair0@(1,2) color=8 size=1 -> ['move:-1,4', 'move:0,4']  vs  pair0@(7,6) color=8 size=1 -> ['keep', 'move:-1,-4']
- same prior intent, different change: pair0@(1,2) color=8 size=1 -> ['move:-1,4', 'move:0,4']  vs  pair0@(8,6) color=8 size=1 -> ['keep', 'move:-1,0']

## 494ef9d7 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 33, 'remove': 9}; cases: 42

## 4acc7107 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 10, 'keep': 1, 'move:3,1': 1, 'move:-3,-2': 1, 'move:4,3': 1, 'move:-3,-6': 1, 'move:3,2': 1}; cases: 16

## 4b6b68e5 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 21, 'remove': 7, 'move:-6,-3': 1, 'move:6,0': 1, 'move:9,0': 1, 'move:-9,0': 1, 'recolor:const:6': 4}; cases: 36

## 4e45f183 (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 23, 'keep': 26, 'move:6,-6': 2, 'move:12,0': 1, 'move:-6,12': 1, 'move:-12,-6': 2, 'move:6,-12': 1, 'move:0,-6': 3, 'move:12,-12': 1, 'move:6,6': 1, 'move:-12,0': 1, 'move:-6,6': 1, 'move:0,6': 3, 'move:12,6': 1, 'move:-6,0': 3, 'move:6,0': 4, 'move:9,0': 1}; cases: 75
- same prior intent, different change: pair0@(14,4) color=2 size=1 -> ['move:-12,-2', 'move:-12,12']  vs  pair0@(2,2) color=2 size=1 -> ['keep', 'move:-1,-1']
- same prior intent, different change: pair0@(7,5) color=2 size=1 -> ['move:-5,-3', 'move:-5,11']  vs  pair0@(11,7) color=2 size=1 -> ['keep', 'move:-1,1']

## 4e7e0eb9 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,4': 4, 'move:4,0': 5, 'keep': 10, 'move:0,-4': 3, 'recolor:const:6': 3, 'move:-4,0': 4, 'recolor:const:8': 3, 'move:14,0': 1, 'move:-6,-4': 1, 'move:-6,0': 1, 'move:10,0': 1, 'move:0,6': 1, 'move:0,-14': 1}; cases: 38

## 4ff4c9da (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 111, 'move:5,2': 2, 'move:4,5': 8, 'move:2,0': 1, 'move:0,8': 3, 'recolor:const:8': 3, 'move:0,4': 1, 'move:9,0': 1, 'move:6,0': 1}; cases: 131

## 5034a0b5 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 92, 'remove': 37, 'move:2,0': 1}; cases: 130

## 50cb2852 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 16, 'move:0,4': 3, 'move:0,3': 4, 'move:0,2': 7, 'move:0,1': 8, 'move:0,5': 2, 'move:0,6': 1}; cases: 41
- same prior intent, different change: pair0@(7,2) color=1 size=3 -> ['keep', 'move:0,5']  vs  pair0@(7,3) color=1 size=3 -> ['move:0,-1', 'move:0,4']
- same prior intent, different change: pair0@(7,2) color=1 size=3 -> ['keep', 'move:0,5']  vs  pair0@(7,4) color=1 size=3 -> ['move:0,-2', 'move:0,3']

## 516b51b7 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 14, 'move:0,6': 2, 'move:0,5': 3, 'move:0,4': 3, 'move:0,3': 4, 'move:0,2': 4, 'move:0,1': 7, 'move:6,0': 1}; cases: 38
- same prior intent, different change: pair0@(1,2) color=1 size=7 -> ['move:0,-1', 'move:0,6']  vs  pair0@(1,3) color=1 size=7 -> ['move:0,-2', 'move:0,5']
- same prior intent, different change: pair0@(1,2) color=1 size=7 -> ['move:0,-1', 'move:0,6']  vs  pair0@(1,4) color=1 size=7 -> ['move:0,-3', 'move:0,4']

## 52364a65 (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 16, 'keep': 20}; cases: 36
- same prior intent, different change: pair1@(5,2) color=2 size=1 -> ['move:0,1', 'move:0,2']  vs  pair1@(5,5) color=2 size=1 -> ['keep', 'move:0,-1']
- same prior intent, different change: pair1@(0,2) color=9 size=2 -> ['move:0,1', 'move:0,2']  vs  pair1@(0,5) color=9 size=2 -> ['keep', 'move:0,-1']

## 52df9849 (nbhcg) — indistinguishable_under_priors
- label classes: {'move:5,0': 1, 'move:3,0': 3, 'keep': 21, 'move:2,0': 1}; cases: 26
- same prior intent, different change: pair0@(6,4) color=1 size=5 -> ['move:4,0', 'move:5,0']  vs  pair0@(9,4) color=1 size=5 -> ['move:1,0', 'move:2,0']
- same prior intent, different change: pair0@(6,4) color=1 size=5 -> ['move:4,0', 'move:5,0']  vs  pair0@(10,4) color=1 size=5 -> ['keep', 'move:1,0']

## 538b439f (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 67, 'move:7,8': 1, 'move:8,4': 1, 'move:9,3': 1, 'move:8,0': 1, 'move:9,6': 1, 'move:9,4': 1, 'move:5,2': 1, 'move:2,5': 1, 'move:7,5': 1, 'move:4,3': 1, 'move:7,2': 1, 'move:2,6': 1, 'move:1,5': 1, 'move:4,5': 1}; cases: 81
- same prior intent, different change: pair0@(15,1) color=4 size=1 -> ['keep', 'move:-1,-1']  vs  pair0@(1,12) color=4 size=1 -> ['move:10,-7', 'move:10,2']
- same prior intent, different change: pair0@(18,6) color=4 size=1 -> ['keep', 'move:-1,-4']  vs  pair0@(3,7) color=4 size=1 -> ['move:11,-7', 'move:12,-6']

## 54d9e175 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:6': 7, 'recolor:const:8': 5, 'recolor:const:9': 3, 'keep': 7, 'recolor:const:7': 5}; cases: 27

## 54db823b (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 85, 'remove': 13}; cases: 98
- same prior intent, different change: pair0@(8,3) color=9 size=1 -> ['keep', 'move:-1,-2']  vs  pair1@(2,9) color=9 size=1 -> ['move:-1,-6', 'move:-1,-8']
- same prior intent, different change: pair0@(8,3) color=9 size=1 -> ['keep', 'move:-1,-2']  vs  pair2@(10,9) color=9 size=1 -> ['move:-1,-5', 'move:-1,-7']

## 54dc2872 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 7, 'remove': 5, 'move:1,1': 2, 'move:1,-1': 1, 'move:-1,-1': 1}; cases: 16

## 5623160b (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 8, 'remove': 18}; cases: 26

## 575b1a71 (nbvcg) — indistinguishable_under_priors
- label classes: {'recolor:const:1': 5, 'recolor:const:2': 8, 'recolor:const:3': 6, 'recolor:const:4': 4}; cases: 23
- same prior intent, different change: pair0@(4,4) color=0 size=1 -> ['recolor:const:2']  vs  pair0@(3,7) color=0 size=1 -> ['recolor:const:3']
- same prior intent, different change: pair0@(7,4) color=0 size=1 -> ['recolor:const:2']  vs  pair0@(3,7) color=0 size=1 -> ['recolor:const:3']

## 5792cb4d (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,3': 1, 'move:0,-5': 1, 'move:-2,-5': 1, 'move:2,5': 1, 'move:0,-1': 2, 'move:0,1': 1, 'move:0,5': 1, 'keep': 3, 'move:2,2': 2, 'move:-5,-4': 1, 'move:1,2': 1, 'move:-1,0': 1, 'move:-2,0': 1, 'move:3,2': 1, 'move:4,3': 1}; cases: 19

## 58743b76 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 15, 'move:9,5': 1, 'move:8,1': 1, 'move:8,8': 1, 'move:5,1': 1, 'recolor:const:1': 1, 'recolor:const:6': 1, 'move:4,6': 1, 'move:6,9': 1, 'move:0,5': 1, 'recolor:const:2': 1, 'move:-1,-6': 1, 'move:-9,-9': 1, 'move:-6,-4': 1, 'move:-5,0': 1, 'move:1,-3': 1, 'move:-5,-3': 1, 'move:-1,-4': 1}; cases: 32
- same prior intent, different change: pair0@(3,8) color=2 size=1 -> ['move:-2,3', 'move:6,-1']  vs  pair0@(3,1) color=2 size=1 -> ['move:-2,10', 'move:6,6']
- same prior intent, different change: pair0@(3,8) color=2 size=1 -> ['move:-2,3', 'move:6,-1']  vs  pair0@(9,7) color=2 size=1 -> ['keep', 'move:-8,4']

## 5a5a2103 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 84, 'move:0,4': 4, 'recolor:const:1': 4, 'move:0,1': 3, 'recolor:const:2': 5}; cases: 100
- same prior intent, different change: pair0@(16,1) color=1 size=2 -> ['keep', 'move:0,10']  vs  pair0@(16,2) color=1 size=2 -> ['move:0,-1', 'move:0,14']
- same prior intent, different change: pair0@(6,1) color=2 size=2 -> ['keep', 'move:0,10']  vs  pair0@(6,2) color=2 size=2 -> ['move:0,-1', 'move:0,14']

## 5b692c0f (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 50, 'move:6,0': 2, 'move:2,0': 2, 'move:-1,1': 2, 'remove': 2}; cases: 58

## 5e6bbc0b (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 27, 'remove': 16, 'move:1,3': 1, 'move:2,-5': 5, 'move:3,0': 2, 'move:1,0': 1, 'move:2,-2': 3, 'move:0,-1': 1, 'move:0,-5': 2, 'move:2,1': 1, 'slide:up': 1}; cases: 60
- same prior intent, different change: pair0@(3,1) color=1 size=1 -> ['move:-1,2', 'move:-1,3']  vs  pair1@(2,2) color=1 size=1 -> ['keep', 'move:-1,-1']
- same prior intent, different change: pair0@(1,1) color=1 size=1 -> ['move:-1,2', 'move:-1,3']  vs  pair1@(4,2) color=1 size=1 -> ['keep', 'move:-1,-1']

## 5ffb2104 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 20, 'keep': 2, 'move:0,1': 1}; cases: 23

## 62ab2642 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:6,0': 1, 'keep': 13, 'recolor:const:8': 1, 'move:3,1': 1}; cases: 16

## 6455b5f5 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:6,0': 2, 'move:0,5': 1, 'keep': 13, 'recolor:const:1': 1, 'move:0,-8': 1}; cases: 18

## 67a3c6ac (nbvcg) — indistinguishable_under_priors
- label classes: {'move:3,1': 1, 'keep': 13, 'remove': 15, 'move:1,1': 1, 'move:-1,1': 1, 'move:1,-4': 1, 'move:3,0': 2, 'move:0,1': 8, 'move:1,2': 1, 'move:0,4': 1, 'move:0,2': 3, 'move:2,2': 1, 'slide:up': 1, 'move:2,-1': 1, 'move:1,-3': 1, 'move:0,-3': 1, 'move:0,-5': 1}; cases: 53
- same prior intent, different change: pair0@(1,2) color=1 size=1 -> ['move:0,-2', 'move:0,1']  vs  pair0@(5,5) color=1 size=1 -> ['move:-1,-2', 'move:-3,-2']

## 68b16354 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 14, 'move:0,2': 3, 'move:0,1': 4, 'move:-1,0': 3, 'move:2,0': 5, 'keep': 12, 'move:4,1': 2, 'move:-2,0': 2, 'move:4,0': 2, 'move:-3,0': 1, 'move:1,0': 2, 'move:-2,2': 1, 'move:5,0': 2, 'move:0,4': 1, 'move:3,0': 1, 'move:-6,0': 2, 'move:1,-6': 1, 'move:4,5': 2, 'move:3,3': 1, 'move:6,0': 2, 'move:1,4': 1}; cases: 64

## 694f12f3 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 8, 'move:0,3': 2, 'move:0,2': 3, 'move:0,1': 3, 'move:5,1': 1, 'move:5,0': 1, 'move:0,4': 1}; cases: 19
- same prior intent, different change: pair0@(1,2) color=4 size=5 -> ['move:0,-1', 'move:0,3']  vs  pair0@(1,3) color=4 size=5 -> ['move:0,-2', 'move:0,2']
- same prior intent, different change: pair0@(1,2) color=4 size=5 -> ['move:0,-1', 'move:0,3']  vs  pair0@(1,4) color=4 size=5 -> ['move:0,-3', 'move:0,1']

## 6ad5bdfd (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 3, 'move:0,-2': 1, 'remove': 13, 'move:0,-1': 1, 'move:2,0': 1, 'move:0,1': 1}; cases: 20

## 6c434453 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 16, 'move:-2,7': 1, 'move:0,4': 1, 'move:3,5': 1, 'move:-2,5': 1, 'move:3,4': 1, 'move:1,3': 1, 'move:5,3': 1, 'move:3,2': 1, 'move:1,7': 1, 'move:2,7': 1, 'move:3,1': 1, 'move:1,5': 2, 'move:-5,4': 1, 'move:-7,3': 1, 'move:-5,2': 1}; cases: 32
- same prior intent, different change: pair0@(5,1) color=1 size=3 -> ['move:-2,7']  vs  pair0@(5,3) color=1 size=3 -> ['move:-2,5']
- same prior intent, different change: pair0@(5,1) color=1 size=3 -> ['move:-2,7']  vs  pair0@(3,8) color=1 size=3 -> ['keep']

## 6ca952ad (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 6, 'remove': 18, 'move:2,0': 1}; cases: 25
- same prior intent, different change: pair0@(1,2) color=6 size=2 -> ['keep', 'move:2,2']  vs  pair0@(1,4) color=6 size=2 -> ['move:0,-2', 'move:2,0']

## 6cdd2623 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 84, 'recolor:const:2': 2, 'keep': 12, 'recolor:const:3': 4, 'recolor:adj': 1}; cases: 103

## 6d0160f0 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 100, 'keep': 4, 'move:0,-1': 1, 'recolor:const:4': 2, 'move:1,0': 1, 'move:1,-2': 1}; cases: 109

## 72322fa7 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 34, 'move:1,5': 1}; cases: 35

## 7447852a (ccgbr) — indistinguishable_under_priors
- label classes: {'keep': 54, 'move:0,4': 3, 'move:0,-4': 2}; cases: 59
- same prior intent, different change: pair0@(0,1) color=0 size=4 -> ['keep', 'move:0,8']  vs  pair0@(0,5) color=0 size=4 -> ['move:0,-4', 'move:0,4']
- same prior intent, different change: pair0@(0,1) color=0 size=4 -> ['keep', 'move:0,8']  vs  pair1@(0,5) color=0 size=4 -> ['move:0,-4', 'recolor:const:4']

## 776ffc46 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 21, 'recolor:const:2': 2, 'recolor:const:3': 3, 'move:-6,3': 1, 'move:-14,0': 1}; cases: 28

## 782b5218 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 26, 'move:6,0': 9, 'move:2,7': 1, 'move:4,5': 2, 'remove': 10}; cases: 48
- same prior intent, different change: pair2@(1,5) color=8 size=1 -> ['move:2,-5', 'move:3,-4']  vs  pair2@(7,2) color=8 size=1 -> ['keep', 'move:-1,-1']

## 7c8af763 (ccgbr) — indistinguishable_under_priors
- label classes: {'recolor:const:1': 10, 'recolor:const:2': 11, 'keep': 65}; cases: 86
- same prior intent, different change: pair0@(6,8) color=0 size=6 -> ['recolor:const:1']  vs  pair2@(4,7) color=0 size=6 -> ['recolor:const:2', 'recolor:least_common']
- same prior intent, different change: pair0@(6,8) color=0 size=6 -> ['recolor:const:1']  vs  pair2@(1,7) color=0 size=6 -> ['recolor:const:2', 'recolor:least_common']

## 7d1f7ee8 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:2': 1, 'keep': 7, 'recolor:ctx': 6, 'recolor:adj': 1, 'recolor:const:8': 1, 'recolor:largest': 1}; cases: 17

## 7e02026e (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 93, 'move:2,4': 1, 'move:1,4': 1, 'move:0,6': 1, 'move:-3,5': 1, 'move:4,2': 1, 'move:3,1': 1, 'move:2,1': 1, 'move:1,3': 1, 'move:0,9': 1, 'move:-5,6': 1, 'move:4,1': 1, 'move:1,5': 1, 'move:-4,7': 1, 'move:-5,7': 1, 'move:-6,7': 1}; cases: 108
- same prior intent, different change: pair0@(1,2) color=0 size=3 -> ['keep', 'move:0,5']  vs  pair2@(1,8) color=0 size=3 -> ['move:-1,-2', 'move:-1,-6']
- same prior intent, different change: pair0@(1,2) color=0 size=3 -> ['keep', 'move:0,5']  vs  pair2@(2,7) color=0 size=3 -> ['move:-2,-1', 'move:-2,-5']

## 7e0986d6 (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 12, 'recolor:adj': 10, 'recolor:ctx': 6, 'keep': 7}; cases: 35
- same prior intent, different change: pair0@(5,5) color=1 size=1 -> ['recolor:const:0', 'remove']  vs  pair0@(9,9) color=1 size=1 -> ['recolor:adj', 'recolor:const:2']
- same prior intent, different change: pair0@(5,5) color=1 size=1 -> ['recolor:const:0', 'remove']  vs  pair0@(11,12) color=1 size=1 -> ['recolor:adj', 'recolor:const:2']

## 7ee1c6ea (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 53, 'recolor:const:6': 2, 'move:1,0': 1, 'move:7,1': 1, 'move:6,0': 2, 'remove': 12, 'move:4,0': 1, 'move:2,0': 2, 'move:3,0': 1, 'move:6,1': 1, 'move:2,4': 1, 'move:2,5': 1, 'recolor:const:2': 1, 'move:2,7': 1, 'move:0,1': 1}; cases: 81

## 817e6c09 (nbccg) — indistinguishable_under_priors
- label classes: {'move:2,2': 1, 'move:3,-3': 1, 'keep': 12, 'move:-2,6': 1, 'move:-2,2': 1, 'move:1,-8': 1, 'move:2,3': 1, 'move:1,6': 2, 'move:0,11': 1, 'move:4,-2': 1, 'move:-3,-3': 1, 'move:0,-9': 1, 'move:3,1': 1, 'move:4,2': 1, 'move:3,2': 1}; cases: 27
- same prior intent, different change: pair1@(1,4) color=2 size=4 -> ['keep', 'move:0,-3']  vs  pair2@(3,8) color=2 size=4 -> ['move:-1,-6', 'move:-3,-2']
- same prior intent, different change: pair1@(1,4) color=2 size=4 -> ['keep', 'move:0,-3']  vs  pair2@(4,5) color=2 size=4 -> ['move:-2,-3', 'move:-4,1']

## 825aa9e9 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 32, 'move:1,0': 4, 'remove': 7, 'move:3,1': 1, 'move:2,0': 1, 'move:0,1': 1}; cases: 46
- same prior intent, different change: pair1@(0,1) color=6 size=1 -> ['keep', 'move:0,1']  vs  pair1@(0,7) color=6 size=1 -> ['move:0,-5', 'move:0,-6']

## 833966f4 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 2, 'keep': 2, 'move:1,0': 4, 'move:-1,0': 2}; cases: 10

## 845d6e51 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 10, 'recolor:const:1': 8, 'recolor:const:4': 4, 'recolor:const:2': 10, 'recolor:const:7': 1}; cases: 33
- same prior intent, different change: pair0@(5,11) color=3 size=4 -> ['recolor:const:1']  vs  pair1@(10,10) color=3 size=4 -> ['recolor:const:2', 'recolor:same_shape']

## 84db8fc4 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 161, 'recolor:const:2': 15, 'recolor:const:5': 9}; cases: 185
- same prior intent, different change: pair1@(2,1) color=0 size=3 -> ['recolor:const:2']  vs  pair1@(4,7) color=0 size=3 -> ['recolor:const:5']
- same prior intent, different change: pair1@(8,1) color=0 size=1 -> ['recolor:const:2']  vs  pair1@(4,4) color=0 size=1 -> ['recolor:const:5']

## 85b81ff1 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,9': 4, 'move:0,3': 3, 'keep': 9, 'move:0,6': 3, 'move:0,-3': 1}; cases: 20

## 85c4e7cd (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:4': 1, 'recolor:const:2': 3, 'recolor:ctx': 2, 'remove': 4, 'keep': 2, 'recolor:const:6': 1, 'recolor:const:1': 1, 'recolor:const:3': 2, 'recolor:const:5': 1, 'recolor:const:8': 1}; cases: 18

## 85fa5666 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 9, 'move:0,1': 2, 'move:-6,0': 1, 'move:3,-6': 2, 'move:0,3': 4, 'move:1,9': 1, 'move:4,5': 1, 'move:2,7': 1, 'move:4,1': 3, 'move:1,-4': 3, 'move:9,4': 1, 'move:6,0': 1, 'slide:up': 1, 'move:3,-4': 1, 'move:4,2': 2, 'move:1,3': 1, 'move:-3,1': 1, 'move:3,0': 3, 'move:3,4': 1, 'move:0,-3': 1, 'move:1,6': 1, 'move:1,0': 1, 'move:-3,0': 2, 'move:6,3': 1}; cases: 45

## 868de0fa (ccgbr) — indistinguishable_under_priors
- label classes: {'move:2,7': 2, 'move:6,0': 3, 'move:1,7': 1, 'keep': 15, 'move:5,0': 1, 'move:4,5': 2, 'move:8,9': 1, 'move:1,-9': 1, 'recolor:const:7': 1, 'recolor:const:2': 1, 'move:-9,4': 1, 'move:0,4': 1}; cases: 30
- same prior intent, different change: pair1@(1,5) color=0 size=16 -> ['move:2,-5', 'move:3,-5']  vs  pair2@(10,3) color=0 size=25 -> ['recolor:const:7']

## 880c1354 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:3': 1, 'move:6,0': 1, 'recolor:const:2': 1, 'keep': 23, 'recolor:const:1': 2, 'move:4,6': 1, 'remove': 1, 'recolor:largest': 1, 'recolor:const:5': 1}; cases: 32

## 8886d717 (nbvcg) — indistinguishable_under_priors
- label classes: {'move:4,5': 2, 'move:1,7': 1, 'keep': 56, 'move:5,3': 1, 'move:2,-5': 1, 'move:5,4': 1, 'move:4,0': 1, 'move:5,1': 1}; cases: 64
- same prior intent, different change: pair0@(3,1) color=8 size=1 -> ['move:-1,6', 'move:-1,7']  vs  pair0@(8,5) color=8 size=1 -> ['keep', 'move:-3,1']
- same prior intent, different change: pair2@(2,2) color=8 size=1 -> ['keep', 'move:-1,5']  vs  pair2@(6,7) color=8 size=1 -> ['move:-4,-5', 'move:-4,-6']

## 8cb8642d (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 20, 'move:0,7': 2, 'move:0,6': 3, 'move:0,5': 4, 'move:0,4': 5, 'move:0,3': 5, 'move:0,2': 5, 'move:0,1': 5, 'move:2,9': 1, 'move:0,8': 1}; cases: 51
- same prior intent, different change: pair0@(1,3) color=3 size=10 -> ['move:0,-1', 'move:0,7']  vs  pair0@(1,4) color=3 size=10 -> ['move:0,-2', 'move:0,6']
- same prior intent, different change: pair0@(1,3) color=3 size=10 -> ['move:0,-1', 'move:0,7']  vs  pair0@(1,5) color=3 size=10 -> ['move:0,-3', 'move:0,5']

## 8dae5dfc (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:largest': 3, 'recolor:const:8': 5, 'recolor:const:3': 3, 'keep': 4, 'recolor:const:2': 3, 'recolor:const:1': 2, 'move:4,5': 1, 'recolor:ctx': 2, 'move:-7,1': 1, 'move:6,0': 1, 'recolor:const:4': 1}; cases: 26

## 8ee62060 (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 36, 'keep': 3}; cases: 39
- same prior intent, different change: pair2@(5,4) color=1 size=1 -> ['keep', 'move:-1,1']  vs  pair2@(2,3) color=1 size=1 -> ['move:-1,5', 'move:-2,6']
- same prior intent, different change: pair2@(5,4) color=1 size=1 -> ['keep', 'move:-1,1']  vs  pair2@(6,7) color=1 size=1 -> ['move:-1,-3', 'move:-2,-2']

## 902510d5 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 25, 'recolor:const:4': 1, 'remove': 16, 'recolor:const:2': 1, 'recolor:const:7': 1}; cases: 44

## 92e50de0 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:4,0': 23, 'keep': 112, 'move:0,4': 2, 'move:-4,0': 1}; cases: 138

## 93c31fbe (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 51, 'remove': 16}; cases: 67
- same prior intent, different change: pair1@(15,10) color=1 size=1 -> ['keep', 'move:-10,12']  vs  pair1@(14,3) color=1 size=1 -> ['move:-10,5', 'move:-10,6']

## 941d9a10 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 65, 'move:2,7': 2, 'move:0,8': 1, 'move:0,5': 1, 'move:0,4': 1, 'move:0,3': 1, 'move:0,2': 1, 'move:0,-5': 1, 'move:7,0': 1, 'move:3,0': 1, 'move:-7,0': 1}; cases: 76
- same prior intent, different change: pair0@(4,1) color=0 size=2 -> ['keep', 'move:0,-1']  vs  pair0@(4,4) color=0 size=2 -> ['move:0,-2', 'move:0,-3']
- same prior intent, different change: pair0@(4,1) color=0 size=2 -> ['keep', 'move:0,-1']  vs  pair0@(4,5) color=0 size=2 -> ['move:0,-3', 'move:0,-4']

## 9473c6fb (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:2': 8, 'recolor:const:5': 7, 'recolor:const:8': 7, 'keep': 3}; cases: 25
- same prior intent, different change: pair2@(4,4) color=9 size=1 -> ['recolor:const:2']  vs  pair2@(4,6) color=9 size=1 -> ['recolor:const:5']
- same prior intent, different change: pair2@(4,8) color=6 size=1 -> ['recolor:const:8']  vs  pair2@(2,2) color=6 size=1 -> ['recolor:const:5']

## 94be5b80 (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 7, 'remove': 5, 'move:6,0': 1, 'move:12,2': 1}; cases: 14

## 963c33f8 (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 17, 'keep': 51, 'move:0,3': 1, 'move:-2,1': 1}; cases: 70
- same prior intent, different change: pair0@(12,7) color=5 size=2 -> ['keep', 'move:-1,1']  vs  pair2@(13,12) color=5 size=2 -> ['move:-1,-10', 'move:-1,-6']

## 97239e3d (ccgbr) — indistinguishable_under_priors
- label classes: {'keep': 91, 'move:5,6': 10, 'move:8,0': 2, 'move:2,8': 1, 'move:2,5': 2}; cases: 106
- same prior intent, different change: pair0@(2,14) color=0 size=1 -> ['move:-1,-14', 'move:-1,-2']  vs  pair0@(14,2) color=0 size=1 -> ['move:-1,10', 'move:-1,14']
- same prior intent, different change: pair0@(14,2) color=0 size=1 -> ['move:-1,10', 'move:-1,14']  vs  pair1@(2,10) color=0 size=1 -> ['move:-1,-2', 'move:-1,-6']

## 985ae207 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 72, 'move:6,0': 4, 'move:2,0': 5, 'move:3,0': 3, 'move:1,0': 3, 'move:-2,0': 3, 'move:-1,0': 1, 'move:7,0': 1, 'move:5,0': 1}; cases: 93
- same prior intent, different change: pair1@(16,6) color=4 size=12 -> ['move:2,0', 'move:3,0']  vs  pair1@(18,6) color=4 size=12 -> ['keep', 'move:1,0']
- same prior intent, different change: pair2@(2,2) color=3 size=13 -> ['move:-1,0']  vs  pair2@(3,2) color=3 size=13 -> ['move:-2,0']

## 98c475bf (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 168, 'remove': 32}; cases: 200

## 9968a131 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 5, 'keep': 10, 'move:0,1': 2, 'move:2,1': 3}; cases: 20

## 99caaf76 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 35, 'keep': 3, 'move:-4,3': 1, 'move:0,2': 1, 'move:-3,2': 1, 'move:0,4': 1, 'move:-4,0': 1, 'move:-2,0': 1, 'move:3,9': 1, 'move:3,0': 2, 'move:3,4': 1, 'move:1,0': 2}; cases: 50

## 9b365c51 (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 10, 'recolor:const:1': 3, 'recolor:const:6': 2, 'recolor:const:7': 5, 'recolor:const:4': 6, 'recolor:const:3': 4, 'recolor:const:2': 6}; cases: 36
- same prior intent, different change: pair1@(1,8) color=8 size=4 -> ['recolor:const:4']  vs  pair1@(3,12) color=8 size=4 -> ['recolor:const:3']
- same prior intent, different change: pair1@(1,8) color=8 size=4 -> ['recolor:const:4']  vs  pair1@(3,13) color=8 size=4 -> ['recolor:const:3']

## 9b4c17c4 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 47, 'move:0,-4': 2, 'remove': 20, 'move:1,7': 1, 'move:0,5': 1, 'move:0,2': 1, 'move:0,4': 4, 'move:3,1': 1, 'move:0,-2': 2, 'move:0,-1': 2, 'move:0,-3': 2, 'move:5,2': 1, 'move:0,8': 1, 'move:2,0': 1, 'move:-9,7': 1, 'move:-6,6': 1, 'move:-9,5': 1}; cases: 89
- same prior intent, different change: pair1@(0,7) color=8 size=11 -> ['move:0,2', 'move:0,3']  vs  pair1@(0,11) color=8 size=11 -> ['keep', 'move:0,-1']
- same prior intent, different change: pair1@(6,4) color=2 size=2 -> ['keep', 'move:-3,1']  vs  pair3@(5,7) color=2 size=2 -> ['move:-3,6', 'move:-3,7']

## 9c56f360 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 44, 'remove': 7, 'move:0,-1': 1}; cases: 52
- same prior intent, different change: pair0@(1,7) color=3 size=1 -> ['move:-1,0', 'move:0,-2']  vs  pair0@(2,7) color=3 size=1 -> ['keep', 'move:-1,-2']
- same prior intent, different change: pair0@(1,7) color=3 size=1 -> ['move:-1,0', 'move:0,-2']  vs  pair2@(7,7) color=3 size=1 -> ['keep', 'move:-1,-5']

## 9f41bd9c (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 10, 'keep': 8, 'move:0,-2': 2, 'move:0,-5': 2, 'move:0,-8': 1, 'move:0,-9': 4, 'move:0,-11': 2, 'move:0,-14': 1, 'move:0,15': 1, 'move:0,12': 2, 'move:0,11': 1, 'move:0,9': 3, 'move:0,8': 1, 'move:0,5': 1, 'move:0,4': 3, 'move:0,1': 1}; cases: 43
- same prior intent, different change: pair0@(11,1) color=6 size=6 -> ['keep', 'move:0,-1']  vs  pair0@(11,6) color=6 size=6 -> ['move:0,-2', 'move:0,-3']
- same prior intent, different change: pair0@(11,1) color=6 size=6 -> ['keep', 'move:0,-1']  vs  pair0@(11,7) color=6 size=6 -> ['move:0,-3', 'move:0,-4']

## 9f8de559 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 137, 'remove': 1, 'move:0,1': 2, 'move:0,-1': 1}; cases: 141

## a096bf4d (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 98, 'move:-5,5': 2, 'move:5,5': 7, 'move:5,0': 1, 'move:5,10': 1}; cases: 109
- same prior intent, different change: pair0@(22,7) color=3 size=4 -> ['move:-10,-5', 'move:-10,10']  vs  pair0@(17,17) color=3 size=4 -> ['keep', 'move:-10,-15']
- same prior intent, different change: pair0@(12,7) color=3 size=4 -> ['move:-10,10', 'move:-5,-5']  vs  pair0@(17,12) color=3 size=4 -> ['keep', 'move:-10,-10']

## a5f85a15 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 11, 'move:1,1': 5, 'move:1,-5': 1, 'move:-3,3': 1, 'move:3,3': 1, 'move:0,-5': 1}; cases: 20
- same prior intent, different change: pair0@(2,4) color=9 size=1 -> ['keep', 'move:-2,-2']  vs  pair0@(3,5) color=9 size=1 -> ['move:-1,-1', 'move:-3,-3']
- same prior intent, different change: pair0@(6,2) color=9 size=1 -> ['keep', 'move:-2,-2']  vs  pair0@(5,1) color=9 size=1 -> ['move:-1,-1', 'move:-1,5']

## a834deea (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 35, 'move:4,5': 1, 'move:6,0': 1, 'move:0,3': 2, 'move:2,2': 1, 'move:0,2': 4, 'move:0,1': 3, 'move:2,0': 1, 'move:6,2': 1}; cases: 49
- same prior intent, different change: pair0@(7,4) color=0 size=5 -> ['keep', 'move:-6,-3']  vs  pair0@(7,5) color=0 size=5 -> ['move:-6,-4', 'move:-6,0']
- same prior intent, different change: pair0@(7,4) color=0 size=5 -> ['keep', 'move:-6,-3']  vs  pair0@(7,7) color=0 size=5 -> ['move:-6,-2', 'move:-6,-6']

## a85d4709 (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:4': 4, 'recolor:const:2': 3, 'recolor:const:3': 3}; cases: 10
- same prior intent, different change: pair0@(2,0) color=5 size=1 -> ['recolor:const:2']  vs  pair2@(2,1) color=5 size=1 -> ['recolor:const:4']
- same prior intent, different change: pair0@(0,0) color=5 size=1 -> ['recolor:const:2']  vs  pair2@(0,1) color=5 size=1 -> ['recolor:const:4']

## a934301b (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 39, 'keep': 16}; cases: 55
- same prior intent, different change: pair0@(10,11) color=8 size=1 -> ['move:-10,-5', 'move:-7,-10']  vs  pair1@(11,7) color=8 size=1 -> ['keep', 'move:-5,5']
- same prior intent, different change: pair0@(10,11) color=8 size=1 -> ['move:-10,-5', 'move:-7,-10']  vs  pair1@(2,11) color=8 size=1 -> ['keep', 'move:4,1']

## ac0c5833 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 56, 'move:2,0': 1, 'remove': 1}; cases: 58
- same prior intent, different change: pair2@(3,1) color=2 size=3 -> ['move:-1,12', 'move:12,13']  vs  pair2@(5,1) color=2 size=3 -> ['keep', 'move:-3,12']

## ac2e8ecf (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'slide:up': 2, 'move:8,0': 1, 'move:-9,0': 1, 'move:6,0': 1, 'remove': 8, 'move:10,0': 1, 'move:-3,0': 1, 'move:4,0': 1, 'move:11,0': 1}; cases: 17

## ad173014 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 20, 'move:-5,-9': 1, 'move:-6,-8': 1, 'move:-4,-8': 2, 'recolor:const:3': 3, 'recolor:const:6': 2, 'move:-6,9': 1, 'recolor:const:8': 2, 'move:-7,8': 1, 'move:-7,-9': 1, 'move:-7,-10': 1, 'recolor:const:4': 1}; cases: 36

## ad38a9d0 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:3': 2, 'recolor:const:9': 2, 'recolor:const:2': 3, 'recolor:const:8': 2, 'recolor:const:5': 2, 'recolor:const:4': 3, 'keep': 3}; cases: 17

## b548a754 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:3': 1, 'keep': 20, 'move:0,5': 1, 'move:4,0': 2, 'recolor:const:2': 1, 'move:0,6': 1, 'recolor:aligned': 1}; cases: 27

## b745798f (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 14, 'move:3,-2': 1, 'keep': 4, 'move:3,-3': 2, 'move:-3,-3': 1, 'move:-2,-4': 1, 'move:0,2': 1}; cases: 24

## b74ca5d1 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:-3,3': 1, 'move:-2,2': 2, 'move:-1,1': 4, 'move:1,1': 7, 'move:1,0': 5, 'recolor:const:5': 2, 'move:2,1': 3, 'keep': 7, 'recolor:const:9': 5, 'move:-1,-1': 3, 'move:-1,3': 1, 'move:-1,2': 1, 'move:-1,0': 3, 'move:5,2': 1, 'move:0,2': 3, 'move:0,1': 5, 'move:0,-1': 5, 'move:0,-2': 5, 'move:-3,2': 1, 'recolor:const:1': 2, 'move:-3,-2': 1, 'move:2,0': 12, 'move:2,3': 1, 'move:-2,3': 1, 'move:2,-1': 3, 'move:-2,-1': 2, 'move:-2,0': 2, 'recolor:const:3': 2, 'move:0,-3': 1, 'move:0,-4': 1, 'move:4,0': 1, 'move:3,1': 1, 'move:1,-1': 3, 'move:-1,-3': 1, 'move:0,4': 1, 'move:-4,4': 1, 'move:-4,0': 1, 'move:2,2': 2, 'move:2,-2': 2, 'move:-2,-2': 2, 'recolor:const:4': 3, 'recolor:adj': 1, 'recolor:const:7': 1, 'move:-2,1': 1}; cases: 113

## b9630600 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 144, 'move:7,1': 1, 'move:5,0': 2, 'remove': 26, 'move:-5,0': 1, 'move:6,0': 1, 'move:13,2': 1, 'move:-3,5': 1, 'move:7,0': 1, 'move:-6,8': 1, 'move:-8,9': 1, 'move:-9,7': 1, 'move:2,0': 1}; cases: 182
- same prior intent, different change: pair0@(10,15) color=3 size=8 -> ['keep', 'move:15,-1']  vs  pair0@(15,15) color=3 size=8 -> ['move:-5,0', 'move:0,-13']
- same prior intent, different change: pair0@(10,0) color=3 size=10 -> ['move:15,13', 'move:15,14']  vs  pair0@(15,0) color=3 size=10 -> ['keep', 'move:10,13']

## ba9d41b8 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 12, 'move:0,3': 6, 'move:0,2': 6, 'move:0,1': 6, 'move:0,8': 2, 'move:0,7': 2, 'move:0,6': 4, 'move:0,5': 4, 'move:0,4': 5}; cases: 47
- same prior intent, different change: pair0@(0,1) color=1 size=5 -> ['move:0,-1', 'move:0,3']  vs  pair0@(0,2) color=1 size=5 -> ['move:0,-2', 'move:0,2']
- same prior intent, different change: pair0@(0,1) color=1 size=5 -> ['move:0,-1', 'move:0,3']  vs  pair0@(0,3) color=1 size=5 -> ['move:0,-3', 'move:0,1']

## baf41dbf (nbvcg) — indistinguishable_under_priors
- label classes: {'move:4,2': 1, 'remove': 7, 'keep': 21, 'move:0,4': 1, 'move:2,7': 1, 'move:5,2': 1}; cases: 32
- same prior intent, different change: pair1@(1,3) color=3 size=4 -> ['keep', 'move:0,-2']  vs  pair1@(1,6) color=3 size=4 -> ['move:0,-3', 'move:0,-5']
- same prior intent, different change: pair2@(3,4) color=3 size=5 -> ['move:0,-2', 'move:0,3']  vs  pair2@(3,7) color=3 size=5 -> ['keep', 'move:0,-5']

## bb43febb (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 8, 'move:0,4': 1, 'move:0,3': 3, 'move:0,2': 3, 'move:0,1': 4}; cases: 19
- same prior intent, different change: pair0@(1,2) color=5 size=5 -> ['move:0,-1', 'move:0,4']  vs  pair0@(1,3) color=5 size=5 -> ['move:0,-2', 'move:0,3']
- same prior intent, different change: pair0@(1,2) color=5 size=5 -> ['move:0,-1', 'move:0,4']  vs  pair0@(1,4) color=5 size=5 -> ['move:0,-3', 'move:0,2']

## bc93ec48 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:-8,0': 1, 'move:0,1': 2, 'keep': 33, 'move:3,1': 1, 'move:6,0': 2, 'move:0,-8': 1, 'move:-5,0': 1, 'move:7,0': 1, 'move:0,-7': 1, 'move:1,7': 1}; cases: 44

## bcb3040b (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 112, 'move:2,7': 1, 'move:2,0': 2, 'move:5,6': 1, 'move:-4,4': 1, 'move:-6,1': 1, 'move:7,3': 1, 'move:5,1': 1, 'move:5,2': 1, 'move:2,2': 1, 'move:1,1': 1}; cases: 123
- same prior intent, different change: pair0@(1,8) color=1 size=2 -> ['keep', 'move:-1,-7']  vs  pair1@(13,12) color=1 size=2 -> ['move:-1,-2', 'move:-10,-1']
- same prior intent, different change: pair0@(3,9) color=1 size=2 -> ['keep', 'move:-1,-1']  vs  pair1@(4,4) color=1 size=2 -> ['move:-1,10', 'move:-1,6']

## bd14c3bf (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 13, 'recolor:const:2': 10, 'move:1,4': 1}; cases: 24
- same prior intent, different change: pair0@(14,2) color=1 size=7 -> ['keep']  vs  pair1@(5,1) color=1 size=7 -> ['move:1,4', 'move:7,1']

## bd283c4a (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 20, 'move:-7,0': 1, 'keep': 7, 'move:7,-1': 2, 'move:2,-2': 2, 'move:2,4': 1, 'move:0,2': 2, 'move:5,2': 1, 'move:-5,4': 1, 'move:-5,0': 1, 'move:0,-1': 1, 'move:1,3': 1, 'move:0,1': 1, 'move:3,1': 1}; cases: 42
- same prior intent, different change: pair0@(6,5) color=5 size=2 -> ['move:-1,3', 'move:-1,4']  vs  pair0@(4,8) color=5 size=2 -> ['keep', 'move:-1,0']
- same prior intent, different change: pair1@(1,2) color=2 size=2 -> ['move:-1,3', 'move:-1,4']  vs  pair1@(1,6) color=2 size=2 -> ['keep', 'move:-1,-1']

## beb8660c (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 6, 'move:0,1': 1, 'keep': 3, 'move:-1,0': 1, 'move:4,0': 1, 'move:1,2': 1, 'move:-1,1': 1}; cases: 14

## c35c1b4c (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 141, 'remove': 19, 'move:1,-6': 1, 'move:1,1': 1}; cases: 162
- same prior intent, different change: pair0@(7,6) color=9 size=2 -> ['move:-6,2', 'move:-7,2']  vs  pair0@(7,7) color=9 size=2 -> ['move:-6,1', 'move:-7,1']
- same prior intent, different change: pair1@(1,1) color=8 size=1 -> ['keep', 'move:-1,1']  vs  pair1@(7,5) color=8 size=1 -> ['move:-1,4', 'move:-3,-5']

## c6141b15 (nbhcg) — indistinguishable_under_priors
- label classes: {'remove': 28, 'move:-4,-6': 1, 'move:0,-11': 1, 'move:-8,-6': 1, 'move:-5,-5': 1, 'move:-10,-6': 1, 'move:9,1': 1, 'move:5,6': 1, 'move:3,3': 1, 'move:-2,6': 1, 'move:2,-7': 1, 'move:2,-3': 1, 'move:0,8': 1, 'move:1,7': 1, 'move:6,5': 1, 'move:5,4': 1, 'move:4,5': 1, 'move:2,7': 1, 'move:1,8': 1, 'move:2,-6': 1, 'move:-4,-7': 1}; cases: 48
- same prior intent, different change: pair2@(3,3) color=8 size=1 -> ['move:-1,7', 'move:-1,9']  vs  pair2@(5,7) color=8 size=1 -> ['move:-1,3', 'move:-1,5']
- same prior intent, different change: pair2@(3,3) color=8 size=1 -> ['move:-1,7', 'move:-1,9']  vs  pair2@(7,7) color=8 size=1 -> ['move:-3,3', 'move:-3,5']

## c7d4e6ad (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 15, 'recolor:const:9': 2, 'recolor:const:6': 4, 'recolor:const:4': 3, 'recolor:const:8': 3, 'recolor:const:2': 4}; cases: 31

## c9680e90 (nbhcg) — indistinguishable_under_priors
- label classes: {'remove': 18, 'recolor:adj': 4, 'recolor:const:2': 5, 'keep': 3}; cases: 30
- same prior intent, different change: pair0@(6,5) color=6 size=1 -> ['recolor:const:7', 'remove']  vs  pair2@(7,2) color=6 size=1 -> ['recolor:const:2']
- same prior intent, different change: pair2@(7,7) color=6 size=1 -> ['recolor:const:7', 'remove']  vs  pair2@(7,2) color=6 size=1 -> ['recolor:const:2']

## cbded52d (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 32, 'move:0,-3': 1, 'move:3,-6': 1, 'move:3,0': 2, 'move:3,3': 2, 'move:6,0': 1}; cases: 39

## ce9e57f2 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 34, 'move:0,4': 5, 'move:-1,0': 2, 'move:0,2': 3, 'move:0,-2': 1, 'move:-4,2': 1, 'move:-1,4': 2, 'move:-5,0': 1, 'move:-5,4': 2, 'move:0,6': 1, 'move:-2,6': 1, 'move:-2,2': 1, 'move:2,-4': 1, 'move:1,-4': 1, 'move:-6,2': 2, 'move:-6,0': 2, 'move:-7,6': 1}; cases: 61
- same prior intent, different change: pair0@(2,1) color=2 size=1 -> ['keep', 'move:-1,0']  vs  pair0@(6,1) color=2 size=1 -> ['move:-1,2', 'move:-1,4']
- same prior intent, different change: pair0@(2,1) color=2 size=1 -> ['keep', 'move:-1,0']  vs  pair2@(7,1) color=2 size=1 -> ['move:-1,2', 'move:-1,4']

## d07ae81c (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 52, 'move:2,0': 6, 'move:1,0': 1, 'move:5,0': 2, 'move:8,9': 1, 'move:0,8': 1, 'move:-2,0': 3, 'move:2,7': 3, 'move:-5,0': 2, 'move:-6,0': 2, 'move:-9,0': 1, 'move:-10,0': 1, 'move:-13,0': 1, 'move:6,0': 2, 'move:4,0': 1, 'move:-8,0': 1, 'move:1,7': 1, 'move:-3,0': 1}; cases: 82
- same prior intent, different change: pair0@(4,9) color=3 size=5 -> ['keep', 'move:-1,0']  vs  pair0@(10,9) color=3 size=5 -> ['move:-6,0', 'move:-7,0']
- same prior intent, different change: pair0@(4,0) color=3 size=3 -> ['keep', 'move:-1,0']  vs  pair0@(9,0) color=3 size=3 -> ['move:-5,0', 'move:-5,10']

## d23f8c26 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 8, 'remove': 16}; cases: 24

## d282b262 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 78, 'move:0,4': 2, 'keep': 2, 'move:1,3': 1, 'move:0,1': 1, 'move:4,1': 1, 'move:1,4': 1}; cases: 86

## d2acf2cb (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 56, 'recolor:largest': 6, 'remove': 6, 'move:1,6': 1, 'move:1,0': 1, 'move:1,1': 1, 'move:2,-6': 1, 'move:1,2': 1}; cases: 73

## d406998b (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 24, 'move:1,-9': 1, 'move:0,-9': 2, 'move:0,5': 2, 'move:1,7': 3, 'move:1,3': 2, 'move:0,3': 3, 'move:-1,1': 2, 'move:2,1': 3, 'move:-1,5': 1, 'move:1,1': 2, 'move:0,9': 1, 'move:0,-5': 1, 'move:2,7': 1, 'move:2,-1': 1}; cases: 49
- same prior intent, different change: pair0@(0,7) color=5 size=1 -> ['keep', 'move:0,-2']  vs  pair1@(0,1) color=5 size=1 -> ['move:0,5', 'move:0,7']
- same prior intent, different change: pair0@(0,7) color=5 size=1 -> ['keep', 'move:0,-2']  vs  pair1@(0,3) color=5 size=1 -> ['move:0,3', 'move:0,5']

## d6542281 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 31, 'remove': 1}; cases: 32

## d94c3b52 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 72, 'move:-8,8': 1, 'move:-4,4': 2, 'move:-8,0': 1, 'move:-4,8': 1, 'move:4,-8': 2, 'move:-8,4': 1, 'move:4,16': 1, 'move:0,-8': 1, 'move:0,8': 3, 'move:0,16': 1, 'move:-4,0': 1, 'move:-8,-4': 1, 'move:3,9': 1, 'recolor:const:8': 7, 'move:2,7': 1, 'move:0,7': 1, 'move:4,4': 3, 'move:4,0': 1, 'move:3,0': 2, 'move:2,9': 1, 'move:5,2': 1, 'move:6,8': 1, 'move:8,1': 1, 'move:9,0': 1, 'move:9,1': 1}; cases: 110
- same prior intent, different change: pair0@(5,17) color=1 size=7 -> ['keep', 'move:-4,-16']  vs  pair0@(5,5) color=1 size=7 -> ['move:-4,-4', 'move:0,-4']
- same prior intent, different change: pair0@(13,13) color=1 size=7 -> ['move:-12,-12', 'move:-8,-12']  vs  pair1@(13,9) color=1 size=7 -> ['keep', 'move:-4,-8']

## dc2aa30b (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 46, 'move:-4,4': 4, 'move:0,4': 4, 'move:1,9': 1, 'move:0,7': 1, 'move:-8,0': 2, 'move:0,1': 2, 'move:4,-8': 2, 'move:8,0': 4, 'remove': 12, 'move:8,4': 1, 'move:-8,4': 1, 'move:-8,-4': 1, 'move:1,0': 1, 'move:6,0': 1, 'move:4,0': 1, 'move:2,0': 1, 'move:-4,0': 1, 'move:-8,8': 1, 'move:3,0': 1, 'move:-8,5': 1, 'move:0,8': 2, 'move:8,-4': 1}; cases: 92
- same prior intent, different change: pair0@(0,1) color=2 size=4 -> ['move:4,0', 'move:8,0']  vs  pair0@(0,5) color=2 size=4 -> ['move:4,-4', 'move:8,-1']
- same prior intent, different change: pair2@(2,8) color=2 size=1 -> ['move:-1,-8', 'move:-2,-4']  vs  pair2@(9,1) color=2 size=1 -> ['keep', 'move:-1,-1']

## dce56571 (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 13, 'keep': 4}; cases: 17

## dd2401ed (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 29, 'remove': 4, 'move:3,2': 1, 'move:-4,7': 1, 'move:2,7': 1, 'move:1,3': 1, 'move:1,6': 2, 'move:-4,4': 1, 'move:2,6': 1, 'move:-5,3': 1, 'move:5,7': 1}; cases: 43
- same prior intent, different change: pair0@(2,9) color=2 size=1 -> ['keep', 'move:-1,-5']  vs  pair1@(2,9) color=2 size=1 -> ['move:0,4', 'move:1,3']
- same prior intent, different change: pair0@(5,6) color=2 size=1 -> ['keep', 'move:-3,-2']  vs  pair1@(2,9) color=2 size=1 -> ['move:0,4', 'move:1,3']

## ddf7fa4f (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 9, 'recolor:const:1': 2, 'recolor:const:7': 2, 'recolor:const:4': 1, 'recolor:const:6': 1, 'recolor:const:2': 1, 'recolor:const:8': 1, 'recolor:aligned': 1}; cases: 18

## e1d2900e (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 15, 'remove': 21}; cases: 36
- same prior intent, different change: pair0@(18,23) color=1 size=1 -> ['move:-11,-15', 'move:-11,-18']  vs  pair1@(23,13) color=1 size=1 -> ['keep', 'move:-13,13']
- same prior intent, different change: pair0@(10,7) color=1 size=1 -> ['move:-1,0', 'move:-3,-2']  vs  pair1@(23,13) color=1 size=1 -> ['keep', 'move:-13,13']

## e21a174a (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:4,0': 3, 'move:1,0': 1, 'move:-3,0': 1, 'move:9,0': 1, 'move:-2,0': 2, 'remove': 1, 'move:-6,0': 1, 'move:-9,0': 2, 'move:7,0': 1, 'move:10,0': 1}; cases: 14

## e41c6fd3 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 5, 'move:-2,0': 2, 'keep': 3, 'move:-3,0': 1, 'move:-1,0': 1}; cases: 12

## e48d4e1a (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 36, 'keep': 4, 'move:0,-3': 2, 'move:0,-1': 1, 'move:0,-2': 1}; cases: 44

## e5062a87 (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 74, 'move:2,0': 4, 'move:-2,-2': 1, 'move:3,0': 1, 'move:5,4': 1, 'recolor:const:2': 1, 'move:4,5': 1}; cases: 83
- same prior intent, different change: pair0@(8,8) color=0 size=1 -> ['keep', 'move:-1,-2']  vs  pair2@(4,2) color=0 size=1 -> ['move:-1,4', 'move:-1,5']
- same prior intent, different change: pair0@(8,8) color=0 size=1 -> ['keep', 'move:-1,-2']  vs  pair2@(4,4) color=0 size=1 -> ['move:-1,2', 'move:-1,3']

## e509e548 (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:6': 6, 'recolor:const:2': 4, 'recolor:const:1': 6}; cases: 16
- same prior intent, different change: pair1@(3,3) color=3 size=7 -> ['recolor:const:2']  vs  pair1@(13,6) color=3 size=7 -> ['recolor:const:1']

## e681b708 (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 60, 'move:2,4': 4, 'move:-7,0': 1, 'move:2,-5': 1, 'move:1,-7': 1, 'move:4,9': 2, 'move:3,0': 4, 'move:2,7': 3, 'move:4,5': 4, 'move:0,-3': 2, 'move:5,2': 4, 'move:0,4': 2, 'move:6,0': 2, 'move:1,6': 1, 'move:5,6': 6, 'move:5,-9': 2, 'move:4,0': 2, 'move:7,5': 2, 'move:9,1': 5, 'move:3,2': 2, 'move:1,5': 2, 'move:2,5': 4, 'move:0,3': 1, 'move:2,0': 2, 'move:0,-5': 1, 'move:5,9': 1, 'move:9,4': 1, 'move:5,8': 2, 'move:2,-4': 1, 'move:1,4': 2, 'move:5,1': 1, 'move:1,8': 1, 'move:3,7': 1, 'move:0,7': 1, 'move:-8,1': 1, 'move:0,2': 1, 'move:4,3': 1, 'move:-4,0': 1, 'move:1,7': 1, 'move:2,2': 1, 'move:3,-4': 1}; cases: 138
- same prior intent, different change: pair0@(17,3) color=1 size=1 -> ['move:-1,13', 'move:-1,4']  vs  pair0@(20,20) color=1 size=1 -> ['move:-1,-13', 'move:-1,-4']
- same prior intent, different change: pair0@(17,3) color=1 size=1 -> ['move:-1,13', 'move:-1,4']  vs  pair0@(10,22) color=1 size=1 -> ['move:-1,-15', 'move:-1,-6']

## e69241bd (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:6,5': 1, 'move:1,3': 1, 'keep': 71, 'recolor:const:3': 1, 'move:2,0': 1, 'move:6,0': 2, 'recolor:const:6': 1, 'recolor:const:8': 2, 'recolor:const:4': 2, 'move:0,2': 1, 'move:-1,1': 1}; cases: 84

## e734a0e8 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 21, 'move:6,6': 1, 'move:6,0': 1, 'move:-6,0': 1, 'move:0,6': 1, 'move:0,-6': 1, 'move:0,4': 1, 'move:-4,4': 1, 'move:-8,0': 1}; cases: 29

## e74e1818 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 27, 'keep': 37, 'move:1,4': 1, 'move:1,2': 1, 'move:1,0': 1, 'slide:up': 1}; cases: 68

## e7dd8335 (nbhcg) — indistinguishable_under_priors
- label classes: {'keep': 18, 'move:-1,0': 3, 'move:-1,3': 1, 'move:-3,3': 1, 'move:-3,0': 2, 'move:-5,0': 3, 'move:-1,4': 1, 'move:-2,2': 4, 'move:-4,4': 1, 'move:-4,1': 2}; cases: 36
- same prior intent, different change: pair0@(3,1) color=1 size=1 -> ['keep', 'move:-1,0']  vs  pair0@(6,1) color=1 size=1 -> ['move:-2,0', 'move:-2,3']
- same prior intent, different change: pair0@(3,1) color=1 size=1 -> ['keep', 'move:-1,0']  vs  pair1@(4,1) color=1 size=1 -> ['move:-2,0', 'move:-2,2']

## e8593010 (nbvcg) — indistinguishable_under_priors
- label classes: {'recolor:const:2': 24, 'recolor:const:1': 13, 'recolor:const:3': 23}; cases: 60
- same prior intent, different change: pair0@(6,1) color=0 size=1 -> ['recolor:const:2']  vs  pair0@(6,6) color=0 size=1 -> ['recolor:const:1']
- same prior intent, different change: pair0@(6,1) color=0 size=1 -> ['recolor:const:2']  vs  pair0@(8,6) color=0 size=1 -> ['recolor:const:3']

## e9afcf9a (nbvcg) — indistinguishable_under_priors
- label classes: {'keep': 6, 'remove': 6}; cases: 12
- same prior intent, different change: pair0@(1,1) color=8 size=1 -> ['move:-1,0', 'move:-1,2']  vs  pair0@(1,2) color=8 size=1 -> ['keep', 'move:-1,-1']
- same prior intent, different change: pair0@(1,1) color=8 size=1 -> ['move:-1,0', 'move:-1,2']  vs  pair0@(1,4) color=8 size=1 -> ['keep', 'move:-1,-1']

## e9bb6954 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 89, 'move:9,-4': 1, 'move:10,3': 1, 'move:-2,6': 1, 'move:7,2': 1, 'move:0,5': 1, 'move:-3,-8': 1, 'move:5,0': 1, 'move:-10,0': 1, 'remove': 1, 'move:6,0': 1, 'move:3,0': 1, 'move:4,1': 1, 'move:8,-3': 1, 'move:-2,5': 1, 'move:6,3': 1, 'move:2,-6': 1, 'recolor:const:7': 2}; cases: 107

## ecaa0ec1 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 14, 'move:0,-1': 2, 'remove': 16, 'move:0,2': 1, 'move:2,1': 1, 'move:-1,0': 1, 'recolor:adj': 1, 'move:1,0': 1, 'move:0,1': 2, 'move:0,-2': 2}; cases: 41

## ecb67b6d (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 24, 'move:1,-4': 2, 'recolor:const:8': 3, 'move:3,1': 2, 'move:9,0': 1, 'move:3,-4': 1, 'move:3,0': 1, 'move:4,0': 1}; cases: 35
- same prior intent, different change: pair0@(3,4) color=5 size=1 -> ['move:-1,-4', 'move:-2,-1']  vs  pair2@(10,5) color=5 size=1 -> ['keep', 'move:-1,-1']
- same prior intent, different change: pair0@(3,4) color=5 size=1 -> ['move:-1,-4', 'move:-2,-1']  vs  pair2@(10,7) color=5 size=1 -> ['keep', 'move:-1,-1']

## edcc2ff0 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'remove': 5, 'keep': 31, 'recolor:const:0': 1}; cases: 37

## ef26cbf6 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'recolor:const:3': 3, 'recolor:const:7': 2, 'recolor:const:8': 2, 'keep': 8, 'recolor:const:6': 3, 'recolor:const:2': 1}; cases: 19

## f0100645 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 9, 'move:0,-2': 2, 'remove': 15, 'move:0,1': 1, 'move:6,0': 1, 'move:3,-2': 1}; cases: 29

## f0f8a26d (nbvcg) — indistinguishable_under_priors
- label classes: {'remove': 22, 'move:3,1': 1, 'keep': 10, 'move:1,-1': 1, 'move:1,-4': 1, 'move:3,0': 1, 'move:4,0': 1, 'move:3,8': 1, 'move:0,3': 1}; cases: 39
- same prior intent, different change: pair2@(8,1) color=8 size=1 -> ['move:-1,1', 'move:-1,2']  vs  pair2@(5,9) color=8 size=1 -> ['keep', 'move:-1,-2']

## f18ec8cc (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:0,-11': 1, 'remove': 3, 'keep': 19, 'move:0,9': 2, 'move:1,-9': 1, 'move:0,-2': 1, 'move:2,4': 1, 'move:0,-3': 5, 'move:0,8': 2, 'move:1,5': 1, 'move:0,-5': 2, 'move:2,0': 1, 'move:4,5': 2, 'move:0,7': 1, 'move:1,1': 1}; cases: 43

## f1bcbc2c (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:8': 2, 'keep': 9}; cases: 11
- same prior intent, different change: pair0@(7,4) color=9 size=1 -> ['recolor:const:8']  vs  pair1@(6,4) color=9 size=1 -> ['keep']
- same prior intent, different change: pair1@(6,4) color=9 size=1 -> ['keep']  vs  pair2@(4,5) color=9 size=1 -> ['recolor:const:8']

## f21745ec (ccgbr) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'move:8,9': 1, 'move:9,1': 1, 'move:7,5': 1, 'keep': 28, 'remove': 4, 'move:6,0': 1, 'move:2,7': 1, 'move:5,6': 1, 'move:5,1': 1}; cases: 39

## f341894c (nbccg) — indistinguishable_under_priors
- label classes: {'keep': 37, 'move:2,5': 2, 'move:4,2': 1, 'move:2,1': 2, 'move:0,1': 2, 'move:1,0': 2, 'move:0,-1': 1, 'move:3,-2': 1, 'move:3,3': 1, 'move:-8,9': 1, 'move:6,0': 1}; cases: 51
- same prior intent, different change: pair0@(6,2) color=1 size=1 -> ['move:-1,0', 'move:-1,4']  vs  pair1@(3,1) color=1 size=1 -> ['keep', 'move:0,2']
- same prior intent, different change: pair0@(6,2) color=1 size=1 -> ['move:-1,0', 'move:-1,4']  vs  pair1@(3,3) color=1 size=1 -> ['keep', 'move:0,-2']

## f3cdc58f (nbccg) — indistinguishable_under_priors
- label classes: {'remove': 40, 'move:1,-3': 1, 'move:3,-2': 1, 'move:2,-1': 1, 'move:2,1': 1, 'move:4,2': 1, 'move:0,1': 2, 'keep': 4, 'move:0,-3': 1, 'move:0,-1': 2, 'move:4,1': 1}; cases: 55
- same prior intent, different change: pair1@(9,3) color=1 size=1 -> ['move:-1,-3', 'move:-2,-3']  vs  pair1@(9,1) color=1 size=1 -> ['move:-1,-1', 'move:-2,-1']

## f3e14006 (nbhcg) — indistinguishable_under_priors
- label classes: {'remove': 48, 'move:-1,1': 2, 'keep': 7, 'move:3,1': 3, 'move:2,-1': 1, 'move:3,0': 1, 'move:-1,0': 1, 'move:0,1': 3, 'move:1,3': 1}; cases: 67
- same prior intent, different change: pair3@(4,8) color=3 size=1 -> ['move:0,-1', 'move:0,-3']  vs  pair3@(4,3) color=3 size=1 -> ['keep', 'move:0,2']
- same prior intent, different change: pair3@(1,5) color=7 size=1 -> ['move:3,-1', 'move:3,1']  vs  pair3@(9,5) color=7 size=1 -> ['move:-1,-1', 'move:-1,1']

## fafd9572 (nbccg) — indistinguishable_under_priors
- label classes: {'recolor:const:3': 9, 'recolor:const:2': 5, 'recolor:const:4': 1, 'keep': 9}; cases: 24
- same prior intent, different change: pair1@(4,8) color=1 size=3 -> ['recolor:const:3']  vs  pair1@(1,1) color=1 size=3 -> ['recolor:const:2', 'recolor:least_common']
- same prior intent, different change: pair1@(5,9) color=1 size=3 -> ['recolor:const:3']  vs  pair1@(8,8) color=1 size=3 -> ['recolor:const:2', 'recolor:least_common']

## fe45cba4 (nbvcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 18, 'remove': 5}; cases: 23

## fea12743 (nbccg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 12, 'recolor:const:3': 3, 'recolor:const:8': 5, 'move:10,-5': 1}; cases: 21

## ff2825db (nbhcg) — needs_>2_attribute_or_>5_rule_concept
- label classes: {'keep': 39, 'remove': 8, 'recolor:const:5': 2, 'move:-2,-3': 1, 'move:-2,6': 1, 'move:-3,-3': 1, 'move:-3,7': 1, 'move:-4,-3': 1, 'move:-4,7': 1, 'move:-5,-3': 1, 'move:-5,7': 1, 'move:-6,-3': 1, 'move:-6,7': 1, 'move:-7,-3': 1, 'move:-7,7': 1, 'move:-8,-3': 1, 'move:-8,6': 1, 'move:6,0': 2, 'move:4,5': 3, 'move:2,0': 2, 'move:3,0': 2, 'move:-2,-1': 1, 'move:-3,0': 1, 'move:-4,1': 2, 'move:-5,3': 1, 'move:-5,-1': 1, 'move:-6,0': 2, 'move:-7,2': 1, 'move:-8,-1': 1, 'recolor:const:4': 2, 'move:-2,-8': 1, 'move:-2,0': 1, 'move:-3,-9': 1, 'move:-3,1': 1, 'move:-4,-8': 1, 'move:-5,-8': 1, 'move:-5,1': 1, 'move:-6,-9': 1, 'move:-7,-9': 1, 'move:-7,0': 1, 'move:-8,-9': 1, 'move:-8,0': 1}; cases: 96

