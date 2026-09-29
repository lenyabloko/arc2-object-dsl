"""Bind Codex's grid-level DSL (extended_transformations/*_grid_based) into the verified G-DSL search.

Parameter domains are read from each function's own source (string enums) and from the task's
training pairs (colours present, size ratios). Nothing task-specific: every value is either an
enum the function declares, a colour seen in the task's training grids, or a small integer.
"""
from __future__ import annotations
import glob, importlib, inspect, os, re, sys

_OPS = None
SKIP = {"fill_grid_based"}          # needs an object argument, not a grid-level op
ENUM_HINT = ("type", "axis", "corner", "mirror_grid", "combine_pattern", "concat_axis", "fill_direction",
             "shifting_direction", "direction", "connect_mode", "component_mode", "selection", "output_mode",
             "mirror_axis", "center_mode", "duplicate_mode", "split_axis", "fold", "overlay")
INTS = {"factor": (2, 3, 4), "grid_size": (2, 3, 4, 5), "output_width": (1, 2, 3), "degrees": (90, 180, 270),
        "duplicate": (2, 3), "duplicate_arbitrary": (2, 3), "connectivity": (4, 8)}


def _root():
    for r in (os.environ.get("CODEX_DSL_ROOT", ""), "/home/claude/work/cand2", "/kaggle/working/cand"):
        if r and os.path.isdir(os.path.join(r, "extended_transformations")): return r
    return None


def load():
    global _OPS
    if _OPS is not None: return _OPS
    _OPS = []
    root = _root()
    if not root: return _OPS
    for p in (root, os.path.join(root, "extended_transformations")):
        if p not in sys.path: sys.path.append(p)
    for f in sorted(glob.glob(os.path.join(root, "extended_transformations", "*_grid.py"))):
        name = os.path.basename(f)[:-3]
        try:
            mod = importlib.import_module("extended_transformations." + name)
            src = inspect.getsource(mod)
        except Exception:
            continue
        for fn in sorted(n for n in dir(mod) if n.endswith("_grid_based")):
            if fn in SKIP: continue
            f_ = getattr(mod, fn)
            try: sig = inspect.signature(f_)
            except Exception: continue
            params = []
            for pn, p in list(sig.parameters.items())[1:]:
                d = p.default if p.default is not inspect.Parameter.empty else None
                if pn == "classifier_params": continue
                kind, vals = "fixed", [d]
                if any(pn.endswith(h) or pn == h for h in ENUM_HINT) and (isinstance(d, str) or d is None):
                    vs = set(re.findall(rf'\b{pn}\s*==\s*["\']([^"\']+)["\']', src))
                    for grp in re.findall(rf'\b{pn}\s+in\s*[\(\[\{{]([^\)\]\}}]+)[\)\]\}}]', src):
                        vs |= set(re.findall(r'["\']([^"\']+)["\']', grp))
                    if vs: kind, vals = "enum", ([d] if d is not None else []) + sorted(vs - {d})
                elif "color" in pn:
                    kind = "colour"
                elif isinstance(d, bool):
                    kind, vals = "bool", [d, not d]
                elif pn in INTS:
                    kind, vals = "int", [d] + [v for v in INTS[pn] if v != d]
                params.append((pn, kind, vals, d))
            _OPS.append((fn, f_, params))
    return _OPS


_WL = None
def whitelist():
    global _WL
    if _WL is None:
        import json
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "codex_types_general.json")
        _WL = {tuple(x) for x in json.load(open(p))["types"]} if os.path.exists(p) and os.environ.get("CODEX_ALL_TYPES") != "1" else None
    return _WL

def programs(train, per_op=70):
    """Yield (name, cost, fn) for Codex ops: enum type values x (default colours, then one colour varied)."""
    ops = load()
    if not ops: return
    cols = sorted({v for p in train[:1] for g in (p["input"], p["output"]) for r in g for v in r})
    for fn, f_, params in ops:
        n = 0
        enum_ps = [p for p in params if p[1] == "enum"]
        main = enum_ps[0] if enum_ps else None
        others = [p for p in params if p is not main]
        base = {pn: d for pn, _, _, d in params}
        wl = whitelist()
        for tv in (main[2] if main else [None]):
            if n > per_op: break
            if wl is not None and (fn.replace("_grid_based", ""), str(tv)) not in wl: continue
            kw = dict(base)
            if main: kw[main[0]] = tv
            variants = [dict(kw)]
            for pn, kind, vals, d in others:
                opts = cols if kind == "colour" else vals[1:] if kind in ("enum", "bool", "int") else []
                for v in opts:
                    if v == d: continue
                    k2 = dict(kw); k2[pn] = v; variants.append(k2)
            # two colour params varied together over induced colours (e.g. colour1 -> colour2)
            cps = [p for p in others if p[1] == "colour"]
            if len(cps) >= 2:
                for a in cols:
                    for b in cols:
                        if a != b:
                            k2 = dict(kw); k2[cps[0][0]] = a; k2[cps[1][0]] = b; variants.append(k2)
            for k2 in variants:
                n += 1
                if n > per_op: break
                nd = sum(1 for pn, _, _, d in params if k2.get(pn) != d and (not main or pn != main[0]))
                label = f"codex:{fn.replace('_grid_based', '')}[{tv}]" + ("" if not nd else "(" + ",".join(f"{pn}={k2[pn]}" for pn, _, _, d in params if k2.get(pn) != d and (not main or pn != main[0])) + ")")
                yield (label, 3 + nd, (lambda g, f_=f_, k2=k2: f_([list(r) for r in g], **k2)))
