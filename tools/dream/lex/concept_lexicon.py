"""Interim concept lexicon for mining shared prior concepts across solution texts (Len, Oct 1 2026: "find common
prior concepts that span multiple text lines using synonyms from WordNet and VerbNet").
The cloud session cannot reach PyPI or the WordNet/VerbNet downloads (egress policy, Oct 1), so this lexicon is
hand-written: each class groups words the way a WordNet synset/hypernym or a VerbNet class would. It is replaced by
real WordNet 3.0 synsets/hypernyms and VerbNet classes once the WSL session delivers the NLTK data
(cloud_outbox/wsl_results/nltk). Classes: ACT_* = actions (verb classes), ENT_* = participants (noun hypernyms),
REL_* = relations / stop conditions."""
LEX = {
 'ACT_RECOLOUR': 'recolour recoloured recolor recolored repaint repainted recolouring colouring painted paint paints swap swaps swapped turns turn becomes become takes take carries tinted',
 'ACT_FILL': 'fill filled fills filling flood flooded cover covered covers',
 'ACT_EXTEND': 'ray rays shoot shoots extend extended extends extending beam beams emit emits emitter draw drawn draws drawing trail trails continue continued continues continuation projection project casts cast casting',
 'ACT_CONNECT': 'connect connects connected join joins joined joining bridge bridges link links chain chained corridor corridors connector connectors attached',
 'ACT_MOVE': 'move moves moved moving slide slides sliding slid shift shifted shifts offset translation translated fall falls drop drops dropped gravity pushed push glide travel travels lands',
 'ACT_REFLECT': 'mirror mirrored mirroring mirrors reflection reflect reflected reflects symmetric symmetry mirror-symmetric flip flipped fold folded',
 'ACT_ROTATE': 'rotate rotated rotation rotations clockwise anticlockwise counter-clockwise',
 'ACT_SCALE': 'scale scaled scaling enlarged enlarge upscale upscaled downscaled downscale shrink shrunk stretch stretched stretches k-by-k kronecker blown blow factor doubled magnified',
 'ACT_COPY': 'copy copies copied stamp stamped stamps stamping replicate replicated duplicate duplicated template templates motif stencil glyph glyphs exemplar clone',
 'ACT_TILE': 'tile tiled tiles tiling repeat repeated repeats repeating periodic period periodically lattice cycle cycles cyclically alternating alternate progression sequence wallpaper',
 'ACT_CROP': 'crop cropped crops extract extracted cut window windows select selects selected bbox bounding pick picked',
 'ACT_COUNT': 'count counts counted number histogram tally statistics frequency frequent majority rank ranked',
 'ACT_REMOVE': 'erase erased erases remove removed removes clear cleared delete deleted noise stray denoise vanish disappear disappears',
 'ACT_COMPLETE': 'complete completed completes completion missing restore restored repair repaired hidden occluded occluder heal',
 'ACT_SURROUND': 'frame frames framed outline outlined ring rings halo border bordered surround surrounded around decorate decorated decoration concentric nested encircle',
 'ACT_PARTITION': 'separator separators divider dividers split splits partition partitioned divided panel panels band bands quadrant quadrants rooms compartment',
 'ACT_COMBINE': 'overlay overlaid union intersection xor combine combined mask masks and-ing superimpose differs difference compare',
 'ACT_SORT': 'sort sorted order ordered ordering arranged arrange stacked stack stacks restacked aligned',
 'ACT_GROW': 'grow grows growth spread spreads expand expands staircase spiral spirals pyramid',
 'ACT_MAP': 'legend key keys mapping mapped map maps lookup table learned palette indicator',
 'ENT_OBJECT': 'object objects shape shapes piece pieces blob blobs component components figure figures',
 'ENT_MARKER': 'marker markers dot dots seed seeds pixel pixels point points mark marks anchor anchors single cell-marker',
 'ENT_LINE': 'line lines bar bars segment segments stripe stripes strip strips row rows column columns arm arms',
 'ENT_AREA': 'rectangle rectangles square squares box boxes region regions area areas block blocks',
 'ENT_GRID': 'grid canvas board output input',
 'REL_INSIDE': 'inside interior enclosed hole holes cavity cup contains inner within',
 'REL_STOP': 'until reaches reach wall walls obstacle contact touches touching touch edge edges blocked hit hits border',
 'REL_DIAG': 'diagonal diagonals diagonally anti-diagonal',
 'REL_NEAR': 'nearest adjacent neighbour neighbours beside next touching closest',
 'REL_SIZE': 'largest smallest biggest longest shortest largest larger smaller size sizes',
}
WORD2CLASS = {}
for k, v in LEX.items():
    for w in v.split():
        WORD2CLASS.setdefault(w, []).append(k)
