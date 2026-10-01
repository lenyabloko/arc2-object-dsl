"""T59 (Fable v10a): engine parity between the Datalog fixpoint (o0_rules.dl.txt via engine.py) and the Dream-side
O0 materialisation (tools/dream/o0/items/*.py through harness.py), per design grid.

Design grids: inputs (train and test) of the design tasks = training challenges minus novel_N2, plus the evaluation
tasks in deval_a / deval_b. Individuals: harness.individuals(P, grid, 'nbccg') with probe tools/m1b/v34. For every
grid, both sides produce {item + json(params): sorted [[i, j], ...]} for every item and parameter setting; canonical
JSON -> sha256; equal / not, W_mat, seconds per side. No outputs, no solutions files are read.
usage: python3 t59_parity.py [--limit N] [--part K --parts P]      one part -> results/o0/t59_parity.partK.json
       python3 t59_parity.py --merge P                             parts -> results/o0/t59_parity.json + summary
"""
import argparse, hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
O0 = os.path.join(ROOT, 'tools', 'dream', 'o0')
M1B = os.path.join(ROOT, 'tools', 'm1b')
OUT = os.path.join(ROOT, 'results', 'o0')
sys.path[:0] = [HERE, O0]
import engine  # noqa: E402
import harness as Hn  # noqa: E402

CAP = 200000                                               # G63 cap on derived facts per grid


def design_grids():
    tr = json.load(open(Hn.B + 'arc-agi_training_challenges.json'))
    ev = json.load(open(Hn.B + 'arc-agi_evaluation_challenges.json'))
    n2 = set(open(os.path.join(M1B, 'novel_N2.txt')).read().split())
    dv = []
    for f in ('deval_a.txt', 'deval_b.txt'):
        dv += [k for k in re.split(r'[,\s]+', open(os.path.join(M1B, f)).read()) if k]
    tasks = [(k, tr[k]) for k in sorted(tr) if k not in n2] + [(k, ev[k]) for k in sorted(set(dv)) if k not in n2]
    out = []
    for k, t in tasks:
        for i, g in enumerate([p['input'] for p in t['train']] + [p['input'] for p in t['test']]):
            out.append(("%s:%d" % (k, i), g))
    return out, n2


def edb(grid, inds, bg):
    """primitive facts only: grid size, cells with colour, background colour, individuals' kind and cells"""
    H, W = len(grid), len(grid[0])
    return {"size": [(H, W)], "cell": [(y, x, grid[y][x]) for y in range(H) for x in range(W)], "bg": [(bg,)],
            "ind": [(i, x["kind"]) for i, x in enumerate(inds)],
            "pix": [(i, y, x) for i, ind in enumerate(inds) for (y, x) in ind["pix"]]}


def skey(it, prm):
    return it["name"] + (json.dumps(prm, sort_keys=True) if prm else "")


def py_side(items, grid, inds, bg):
    ext, err = {}, {}
    for it in items:
        for prm in Hn.settings(it):
            try: ext[skey(it, prm)] = sorted([int(i), int(j)] for i, j in Hn.extension(it, grid, inds, bg, prm))
            except Exception as e: err[skey(it, prm)] = repr(e)[:200]
    return ext, err


def dl_side(items, res):
    ext = {}
    for it in items:
        rel = res.relations.get(it["name"], [])
        keys = sorted(it.get("params") or {})
        by = {}
        for t in rel: by.setdefault(tuple(t[2:]), []).append([t[0], t[1]])
        for prm in Hn.settings(it):
            ext[skey(it, prm)] = sorted(by.get(tuple(prm[k] for k in keys), []))
    return ext


def digest(ext):
    return hashlib.sha256(json.dumps(ext, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(part, parts, limit):
    P = Hn.setup(os.path.join(M1B, 'v34'))
    items = Hn.load_items()
    prog = engine.Program(open(os.path.join(HERE, 'o0_rules.dl.txt')).read())
    grids, n2 = design_grids()
    grids = grids[part::parts][:limit] if limit else grids[part::parts]
    rows = []
    for n, (key, g) in enumerate(grids):
        assert key.split(":")[0] not in n2
        row = {"key": key, "H": len(g), "W": len(g[0])}
        try: inds, names, bg = Hn.individuals(P, g, 'nbccg')
        except Exception as e:
            row["skip"] = repr(e)[:80]; rows.append(row); continue
        row["n_ind"] = len(inds); row["n_obj"] = sum(x["kind"] == "object" for x in inds)
        t0 = time.time(); pe, perr = py_side(items, g, inds, bg); t1 = time.time()
        try:
            res = prog.run(edb(g, inds, bg)); de = dl_side(items, res); derr = None
        except Exception as e:
            res, de, derr = None, {}, repr(e)[:200]
        t2 = time.time()
        row.update(py_s=round(t1 - t0, 4), dl_s=round(t2 - t1, 4), n_ext=sum(len(v) for v in pe.values()))
        if perr: row["py_err"] = perr
        if derr: row["dl_err"] = derr
        row["eq"] = (not perr and not derr and digest(pe) == digest(de))
        row["mismatch"] = sorted({k.split("{")[0] for k in set(pe) | set(de) if pe.get(k) != de.get(k)})
        if not row["eq"] and res is not None:
            row["diff"] = {k: [len(set(map(tuple, pe.get(k, []))) - set(map(tuple, de.get(k, [])))),
                               len(set(map(tuple, de.get(k, []))) - set(map(tuple, pe.get(k, []))))]
                           for k in set(pe) | set(de) if pe.get(k) != de.get(k)}
        if res is not None:
            row["wmat"] = res.wmat
            row["top_rule"] = max(res.by_rule.items(), key=lambda kv: kv[1])
            row["top_pred"] = sorted(res.by_pred.items(), key=lambda kv: -kv[1])[:5]
        rows.append(row)
        if n % 50 == 0:
            print(json.dumps({q: row.get(q) for q in ("key", "eq", "wmat", "py_s", "dl_s", "mismatch")}), file=sys.stderr, flush=True)
    return rows


def rule_stats():
    """G62 shape of the rule file: relational body atoms (negated included) and distinct variables per rule"""
    prog = engine.Program(open(os.path.join(HERE, 'o0_rules.dl.txt')).read())
    st = []
    for h, b in prog.rules:
        vs = {a[1] for a in h[1] if a[0] == "v"} | {v for a in h[1] if a[0] == "agg" for v in a[2]}
        for l in b: vs |= engine.lvars(l)
        st.append((sum(l[0] == "atom" for l in b), len(vs)))
    return {"rules": len(st), "facts": sum(len(v) for v in prog.facts.values()), "strata": len(prog.strata),
            "recursive_strata": sum(any(r for _, r, _ in rs) for _, rs in prog.compiled),
            "atoms_le4": sum(a <= 4 for a, v in st), "vars_le4": sum(v <= 4 for a, v in st),
            "both_le4": sum(a <= 4 and v <= 4 for a, v in st), "max_atoms": max(a for a, v in st),
            "max_vars": max(v for a, v in st)}


def summarise(rows, n2):
    done = [r for r in rows if "skip" not in r]
    eq = sum(r["eq"] for r in done)
    per_item, ex = {}, {}
    for r in done:
        for it in r["mismatch"]:
            per_item[it] = per_item.get(it, 0) + 1
            if len(ex.setdefault(it, [])) < 5 and r["key"].split(":")[0] not in n2: ex[it].append(r["key"])
    w = [r["wmat"] for r in done if "wmat" in r]
    dl = [r["dl_s"] for r in done]; py = [r["py_s"] for r in done]
    wmax = max(done, key=lambda r: r.get("wmat", 0)) if done else {}
    rule_tot = {}
    for r in done:
        for p, c in r.get("top_pred", []): rule_tot[p] = rule_tot.get(p, 0) + c
    return {"grids_total": len(rows), "grids_skipped_segmentation": len(rows) - len(done), "grids_compared": len(done),
            "grids_hash_equal": eq, "parity_pct": round(100.0 * eq / max(1, len(done)), 3),
            "items_with_mismatch": per_item, "mismatch_examples": ex,
            "wmat_max": max(w) if w else 0, "wmat_mean": round(sum(w) / max(1, len(w)), 1),
            "wmat_max_grid": wmax.get("key"), "wmat_max_top_rule": wmax.get("top_rule"), "wmat_max_top_preds": wmax.get("top_pred"),
            "grids_over_cap": sum(x > CAP for x in w), "cap": CAP,
            "ext_max": max((r["n_ext"] for r in done), default=0),
            "ext_mean": round(sum(r["n_ext"] for r in done) / max(1, len(done)), 1),
            "dl_s_max": max(dl, default=0), "dl_s_mean": round(sum(dl) / max(1, len(dl)), 4),
            "py_s_max": max(py, default=0), "py_s_mean": round(sum(py) / max(1, len(py)), 4),
            "pred_totals_from_grid_top5": sorted(rule_tot.items(), key=lambda kv: -kv[1])[:10],
            "py_errors": sum(bool(r.get("py_err")) for r in done), "dl_errors": sum(bool(r.get("dl_err")) for r in done),
            "rule_file": rule_stats()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0); ap.add_argument("--part", type=int, default=0)
    ap.add_argument("--parts", type=int, default=1); ap.add_argument("--merge", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    n2 = set(open(os.path.join(M1B, 'novel_N2.txt')).read().split())
    if a.merge:
        rows = []
        for k in range(a.merge): rows += json.load(open(os.path.join(OUT, "t59_parity.part%d.json" % k)))["rows"]
    else:
        rows = run(a.part, a.parts, a.limit)
        if a.parts > 1:
            json.dump({"rows": rows}, open(os.path.join(OUT, "t59_parity.part%d.json" % a.part), "w"))
            print(json.dumps(summarise(rows, n2), indent=1)); sys.exit(0)
    S = summarise(rows, n2)
    for r in rows:
        r.pop("diff", None) if r.get("eq") else None
    json.dump({"summary": S, "rows": rows}, open(os.path.join(OUT, "t59_parity.limit.json" if a.limit else "t59_parity.json"), "w"), indent=0)   # smoke runs never overwrite the full result
    print(json.dumps(S, indent=1))
