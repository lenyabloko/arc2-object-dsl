"""Machine profiles for the review page (engine v4, training pairs only): each dev task's first fitted situation tree,
in the page's words. Dev = design minus the T86 14 minus the sealed T90 draws, i.e. only tasks Len has already seen on
the pages (no new task is shown). Input: results/o0/v4_design_depth2.json. Output: a dict embedded as D['machine']."""
import json, os, re
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ROW = {'markers': 'markers', 'marks': 'marks (legend marks left out)', 'fg': 'foreground cells', 'bg': 'background',
       'objects': 'each object', 'grid_corners': 'grid corners', 'obj_corners': 'object corners', 'centre': 'centres',
       'across': 'across panels', 'train': 'the same in all examples', 'exemplar': 'the exemplar shape', 'input': 'the input',
       'own': 'own colour', 'hit': 'colour of what it hits', 'key': 'the colour key', 'nearest': 'nearest object’s colour',
       'largest': 'largest object', 'smallest': 'smallest object', 'odd': 'odd one out', 'segments': 'line segments',
       'obstacle': 'first obstacle', 'border': 'grid border', 'frame': 'the frame', 'between': 'between objects',
       'region': 'enclosed region', 'panels': 'panels', 'axis': 'symmetry axis', 'pixel_count': 'pixel count',
       'object_count': 'object count', 'target': 'the target', 'kept': 'kept', 'cleared': 'cleared',
       'topleft': 'copy’s top-left on the mark', 'nearest_place': 'around the anchor'}
ARG = {'anchors': 'where copies go', 'unit': 'what is copied', 'rest': 'rest of input', 'place': 'placement',
       'source': 'what is extended', 'stop': 'stops at', 'colour': 'colour', 'subject': 'what', 'key': 'colour rule',
       'region': 'region', 'target': 'to', 'extent': 'how far', 'axis': 'axis'}


def flat(k):
    m = re.match(r'([a-z]+)\((.*)\)$', k)
    if not m: return k
    how, args = m.group(1), m.group(2)
    parts = []
    for a in [x for x in args.split(', ') if x]:
        n, v = a.split(':=')
        if n == 'place' and v == 'nearest': continue
        if n == 'rest' and v == 'kept': continue
        parts.append('%s = %s' % (ARG.get(n, n), ROW.get(v, v)))
    return how + ' (' + ', '.join(parts) + ')'


def human(k):
    m = re.match(r'paste\(input:=(.*)@([a-z]+)\)$', k)
    if m: return 'on each %s: %s' % (m.group(2), flat(m.group(1)))
    m = re.match(r'(.*)\[input:=(.*)@grid\]$', k)
    if m: return 'first %s, then %s' % (flat(m.group(2)), flat(m.group(1)))
    return flat(k)


def build():
    d = json.load(open(os.path.join(REPO, 'results/o0/v4_design_depth2.json')))
    tasks = {k: {'tree': human(v['fits'][0]), 'key': v['fits'][0], 'depth': min(v['depths']), 'n_fits': len(v['fits'])}
             for k, v in d['tasks'].items() if v.get('fits')}
    s = d['summary']
    return {'summary': {'n': s['n'], 'depth1': s['fit_depth1'], 'depth2': s['fit_depth_le2'], 'only2': s['only_depth2']},
            'tasks': tasks, 'parts': list(s['R_part'].items())[:25],
            'len_parts': {k: '%d (needed by %d)' % (v, s.get('len_parts_necessary', {}).get(k, 0)) for k, v in s['len_parts'].items()}}


if __name__ == '__main__':
    M = build(); print(json.dumps(M['summary'])); print(list(M['tasks'].items())[:3])
