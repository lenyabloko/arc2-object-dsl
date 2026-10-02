#!/usr/bin/env python3
"""T58 (Fable guidance v10a): export the ontology layers as one OWL 2 EL TBox for a single ELK classification run.

Inputs (read only):
  1. codex/ontology/concept_hierarchy.ttl  classes, rdfs:subClassOf, object properties, rdfs:subPropertyOf and the 11
     owl:propertyChainAxiom ("the 11 existing chains"). Four of those chains use rdfs:subClassOf as a chain link; an
     OWL 2 DL chain may only contain object properties, so that link is exported as the object property
     t58:subClassOfRel (stand-in, see its rdfs:comment). Datatype properties and the punned concept->feature
     assertions (an ABox about classes-as-individuals) are not exported.
  2. results/ontology/ontology_links.ttl    classes and rdfs:subClassOf (annotations are not exported).
  3. tools/dream/o0/items/*.py              each ITEM -> ObjectProperty (role) or Class (concept) at its declared IRI,
     one sub-property per parameter setting, the declared subsumptions, and the deterministic RCC-8 / RCC-5 / Allen
     compositions as property chains (single-relation table entries only, each sound in the O0 grounding).
  4. tools/m1b/v34/occupancy2.py            lattice concept names as classes, with the subsumptions / equivalences /
     disjointness that hold by definition in that code (justification on each axiom).
  5. results/m1b/c2_train.jsonl.txt, c2_deval.jsonl.txt  every lattice rule with exactly two attributes gives
     Pair_<a>_<b> == ObjectIntersectionOf(A B). Tasks listed in tools/m1b/novel_N2.txt are skipped; no task id is
     printed or written anywhere.
  6. tools/owl/lattice_parents.json        G71 (Fable v12): every emitted lattice name -> one of five parent classes
     (t58:ShapeProperty, PositionProperty, ColourRole, ScaleProperty, Relation) -> image-schema top(s) (t58:PART_WHOLE,
     NEAR_FAR, CONTAINMENT, MATCHING, SCALE, CONTACT). Names it lists are declared as lattice classes too.
Outputs: results/o0/t58_tbox.ofn (OWL 2 Functional Syntax), results/o0/t58_tbox.ttl (same axioms, rdflib) and
results/o0/t58_export_summary.json (counts, OWL 2 EL self-check, RBox regularity check (OWL 2 spec section 11.2),
structural check of the .ofn, round-trip check of the .ttl, and the classification ELK is expected to report).
Justifications are rdfs:comment axiom annotations (ASCII), so they survive the OWL API round trip.
usage: python3 tools/owl/t58_export.py [--concept-hierarchy PATH] [--all-runs]
"""
import sys

sys.dont_write_bytecode = True  # never write into tools/dream/o0/items/__pycache__

import argparse, glob, importlib.util, json, os, re, unicodedata  # noqa: E402
from collections import defaultdict  # noqa: E402

import rdflib  # noqa: E402
from rdflib import RDF, RDFS, OWL, BNode, Literal, URIRef  # noqa: E402
from rdflib.collection import Collection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DEF_CH = "/home/claude/work/codex/ontology/concept_hierarchy.ttl"
LINKS = os.path.join(ROOT, "results", "ontology", "ontology_links.ttl")
ITEMS = os.path.join(ROOT, "tools", "dream", "o0", "items")
OCC = os.path.join(ROOT, "tools", "m1b", "v34", "occupancy2.py")
N2 = os.path.join(ROOT, "tools", "m1b", "novel_N2.txt")
RUNS = [os.path.join(ROOT, "results", "m1b", f) for f in ("c2_train.jsonl.txt", "c2_deval.jsonl.txt")]
PARENTS = os.path.join(HERE, "lattice_parents.json")
OUT = os.path.join(ROOT, "results", "o0")

ONT = "https://github.com/lenyabloko/arc2-object-dsl/ontology/t58"
PREFIXES = [  # one Prefix block; order = output order
    ("owl", "http://www.w3.org/2002/07/owl#"),
    ("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"),
    ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
    ("xsd", "http://www.w3.org/2001/XMLSchema#"),
    ("t58", ONT + "#"),
    ("arga", "https://arc-arga.example/arga#"),
    ("arcm", "https://github.com/lenyabloko/arc2-object-dsl/ontology/mechanism#"),
    ("dul", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#"),
    # O0 item IRIs are written qsr:<x> / allen:<x>; no namespace is declared for them in the repo, so the export
    # binds them here (local namespaces of this project).
    ("qsr", "https://github.com/lenyabloko/arc2-object-dsl/ontology/qsr#"),
    ("allen", "https://github.com/lenyabloko/arc2-object-dsl/ontology/allen#"),
    ("lat", "https://github.com/lenyabloko/arc2-object-dsl/ontology/lattice#"),
]
NS = dict(PREFIXES)
RDFS_LABEL = NS["rdfs"] + "label"
RDFS_COMMENT = NS["rdfs"] + "comment"
SUBCLASS_REL = NS["t58"] + "subClassOfRel"
BUILTIN = {NS["owl"] + x for x in ("Thing", "Nothing", "topObjectProperty", "bottomObjectProperty")} | {
    RDFS_LABEL, RDFS_COMMENT}


def ascii_text(s):
    """ASCII-only annotation text (the OWL API reads .ofn as UTF-8, but ASCII avoids any encoding question)."""
    for a, b in (("⊑", "<="), ("⊓", " and "), ("∪", " | "), ("∘", " o "), ("≥", ">="), ("≤", "<="), ("≠", "!="),
                 ("–", "-"), ("—", "-"), ("→", "->"), ("×", "x"), ("’", "'"), ("“", '"'), ("”", '"')):
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "replace").decode("ascii")
    return " ".join(s.split())


# ------------------------------------------------------------------------------------------------ axiom store
class TBox:
    def __init__(self):
        self.ent = {}          # iri -> "Class" | "ObjectProperty"
        self.ax = []           # logical axioms (dicts)
        self.ann = []          # (subject iri, annotation property iri, text)
        self.src = defaultdict(lambda: defaultdict(int))

    def declare(self, iri, kind):
        if iri in BUILTIN: return iri
        old = self.ent.get(iri)
        if old and old != kind:
            raise ValueError(f"{iri} declared as {old} and {kind}")
        self.ent[iri] = kind
        return iri

    def add(self, src, kind, comment=None, **kw):
        a = dict(kind=kind, comment=ascii_text(comment) if comment else None, src=src, **kw)
        self.ax.append(a)
        self.src[src][kind] += 1
        return a

    def label(self, iri, text): self.ann.append((iri, RDFS_LABEL, ascii_text(text)))

    def note(self, iri, text): self.ann.append((iri, RDFS_COMMENT, ascii_text(text)))


# ------------------------------------------------------------------------------------------------ 1 + 2: TTL sources
def ttl_classes(path):
    g = rdflib.Graph(); g.parse(path)
    cls = set(g.subjects(RDF.type, OWL.Class)) | set(g.subjects(RDFS.subClassOf)) | set(g.objects(None, RDFS.subClassOf))
    cls = {c for c in cls if isinstance(c, URIRef)}
    sub = sorted((str(s), str(o)) for s, o in g.subject_objects(RDFS.subClassOf)
                 if isinstance(s, URIRef) and isinstance(o, URIRef))
    nonatomic = [1 for s, o in g.subject_objects(RDFS.subClassOf) if not (isinstance(s, URIRef) and isinstance(o, URIRef))]
    return g, sorted(map(str, cls)), sub, len(nonatomic)


def export_concept_hierarchy(T, path):
    g, cls, sub, nonatomic = ttl_classes(path)
    for c in cls: T.declare(c, "Class")
    for s, o in sub: T.add("concept_hierarchy", "SubClassOf", sub=s, sup=o)
    props = sorted(str(p) for p in g.subjects(RDF.type, OWL.ObjectProperty))
    for p in props: T.declare(p, "ObjectProperty")
    for s, o in sorted((str(s), str(o)) for s, o in g.subject_objects(RDFS.subPropertyOf)):
        T.declare(s, "ObjectProperty"); T.declare(o, "ObjectProperty")
        T.add("concept_hierarchy", "SubObjectPropertyOf", sub=s, sup=o, comment="rdfs:subPropertyOf in concept_hierarchy.ttl")
    chains = []
    for sup, lst in g.subject_objects(OWL.propertyChainAxiom):
        links = [str(x) for x in Collection(g, lst)]
        chains.append((str(sup), links))
    used_subclass = False
    for sup, links in sorted(chains):
        orig = " o ".join(l.split("#")[-1] for l in links)
        if str(RDFS.subClassOf) in links:
            used_subclass = True
            links = [SUBCLASS_REL if l == str(RDFS.subClassOf) else l for l in links]
            note = (f"owl:propertyChainAxiom from concept_hierarchy.ttl: {orig} <= {sup.split('#')[-1]}; the rdfs:subClassOf "
                    "link is written as t58:subClassOfRel because an OWL 2 DL property chain admits only object properties")
        else:
            note = f"owl:propertyChainAxiom from concept_hierarchy.ttl: {orig} <= {sup.split('#')[-1]}"
        for l in links + [sup]: T.declare(l, "ObjectProperty")
        T.add("concept_hierarchy", "Chain", chain=links, sup=sup, comment=note)
    if used_subclass:
        T.declare(SUBCLASS_REL, "ObjectProperty")
        T.label(SUBCLASS_REL, "subClassOf (as an object property)")
        T.note(SUBCLASS_REL, "Stand-in for rdfs:subClassOf inside the concept_hierarchy.ttl property chains (C subClassOfRel D "
                             "reads: concept C, taken as an individual, is a subclass of concept D). Introduced by T58 because "
                             "rdfs:subClassOf is not an OWL 2 DL object property.")
    dps = sum(1 for _ in g.subjects(RDF.type, OWL.DatatypeProperty))
    abox = sum(1 for p in ("requiresFeature", "impliesFeature", "requiresConstraint", "impliesConstraint")
               for _ in g.subject_objects(URIRef(NS["arga"] + p)))
    return dict(path=path, classes=len(cls), subclassof=len(sub), nonatomic_subclassof=nonatomic,
                object_properties=len(props), subpropertyof=sum(1 for _ in g.subject_objects(RDFS.subPropertyOf)),
                chains=len(chains), chains_using_rdfs_subClassOf=sum(1 for _, l in chains if str(RDFS.subClassOf) in l),
                datatype_properties_not_exported=dps, concept_feature_assertions_not_exported=abox)


def export_links(T, path):
    g, cls, sub, nonatomic = ttl_classes(path)
    for c in cls: T.declare(c, "Class")
    for s, o in sub: T.add("ontology_links", "SubClassOf", sub=s, sup=o)
    return dict(path=path, classes=len(cls), subclassof=len(sub), nonatomic_subclassof=nonatomic)


# ------------------------------------------------------------------------------------------------ 3: O0 items
def load_items():
    items = {}
    for f in sorted(glob.glob(os.path.join(ITEMS, "*.py"))):
        n = os.path.basename(f)[:-3]
        s = importlib.util.spec_from_file_location("t58_o0_" + n, f)
        m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
        it = m.ITEM
        if it["name"] != n: raise ValueError(f"item file {n}.py declares name {it['name']}")
        items[n] = it
    return items


def curie_to_iri(c):
    p, l = c.split(":", 1)
    return NS[p] + l


def settings(item):
    ps = item.get("params") or {}
    out = [{}]
    for k in sorted(ps):
        out = [dict(o, **{k: v}) for o in out for v in ps[k]]
    return out


def setting_iri(items, name, prm):
    it = items[name]
    base = curie_to_iri(it["iri"])
    ps = it.get("params") or {}
    if not ps:
        if prm: raise ValueError(f"{name} has no params but setting {prm} was given")
        return base
    if sorted(prm) != sorted(ps) or any(prm[k] not in ps[k] for k in prm):
        raise ValueError(f"bad setting {prm} for {name}")
    return base + "".join(f"__{k}_{prm[k]}" for k in sorted(prm))


def setting_label(name, prm):
    return name + ("[" + ",".join(f"{k}={prm[k]}" for k in sorted(prm)) + "]" if prm else "")


# Deterministic compositions. Each entry (r1, r2, r): r1 o r2 <= r, i.e. x r1 y and y r2 z imply x r z.
# RCC-8: Randell, Cui & Cohn (1992); composition table as tabulated in Cohn, Bennett, Gooday & Gotts (1997),
# "Qualitative spatial representation and reasoning with the region connection calculus", GeoInformatica 1, Table 1.
RCC8_SINGLE = [
    ("DC", "TPPi", "DC"), ("DC", "NTPPi", "DC"), ("TPP", "DC", "DC"), ("NTPP", "DC", "DC"),
    ("TPP", "NTPP", "NTPP"), ("NTPP", "TPP", "NTPP"), ("NTPP", "NTPP", "NTPP"),
    ("TPPi", "NTPPi", "NTPPi"), ("NTPPi", "TPPi", "NTPPi"), ("NTPPi", "NTPPi", "NTPPi"),
]
# EQ is the identity of the table (r o EQ = EQ o r = {r}); EQ o EQ is left out (O0 relations are irreflexive, x != y,
# so x EQ y EQ x would give EQ(x, x)). RCC-5 (same paper; Bennett 1994): PP o PP = {PP}, PPi o PPi = {PPi}.
RCC_EQ_FOR = ["DC", "PO", "TPP", "NTPP", "TPPi", "NTPPi", "PP", "PPi"]
RCC5_SINGLE = [("PP", "PP", "PP"), ("PPi", "PPi", "PPi")]
# Excluded on purpose: every entry with EC (rcc8_EC is grounded on raw cells, not on filled regions, so it can
# co-occur with NTPP / PO; the table assumes the region grounding), EQ o EQ (irreflexivity), and derived entries such
# as PP o NTPP <= NTPP (true, but NTPP <= PP makes it non-regular, OWL 2 section 11.2).
# Allen (1983), "Maintaining knowledge about temporal intervals", CACM 26(11), Fig. 4 transitivity table; only the
# 7 declared base relations (no inverses in EL), same axis on both links; eq o eq left out (irreflexive).
AB = {"b": "before", "m": "meets", "o": "overlaps", "s": "starts", "d": "during", "f": "finishes", "eq": "equals"}
ALLEN_SINGLE = [
    ("b", "b", "b"), ("b", "m", "b"), ("b", "o", "b"), ("b", "s", "b"),
    ("m", "b", "b"), ("m", "m", "b"), ("m", "o", "b"), ("m", "s", "m"),
    ("o", "b", "b"), ("o", "m", "b"), ("o", "s", "o"),
    ("s", "b", "b"), ("s", "m", "b"), ("s", "s", "s"), ("s", "d", "d"), ("s", "f", "d"),
    ("d", "b", "b"), ("d", "m", "b"), ("d", "s", "d"), ("d", "d", "d"), ("d", "f", "d"),
    ("f", "b", "b"), ("f", "m", "m"), ("f", "s", "d"), ("f", "d", "d"), ("f", "f", "f"),
] + [(r, "eq", r) for r in "bmosdf"] + [("eq", r, r) for r in "bmosdf"]


def export_o0(T, items):
    st = dict(items=len(items), roles=0, concepts=0, setting_properties=0, subsumptions=0, chains_rcc=0, chains_allen=0,
              not_exported=[])
    kind_of = {}
    for n, it in sorted(items.items()):
        kind = "ObjectProperty" if it["kind"] == "role" else "Class"
        kind_of[n] = kind
        st["roles" if kind == "ObjectProperty" else "concepts"] += 1
        base = T.declare(curie_to_iri(it["iri"]), kind)
        T.label(base, n)
        T.note(base, it.get("definition", ""))
        for prm in settings(it):
            if not prm: continue
            s = T.declare(setting_iri(items, n, prm), kind)
            T.label(s, setting_label(n, prm))
            T.add("o0", "SubObjectPropertyOf" if kind == "ObjectProperty" else "SubClassOf", sub=s, sup=base,
                  comment=f"parameter setting of O0 item {n} (the item is the union of its settings)")
            st["setting_properties"] += 1

    def sub(a, b, why):
        if kind_of[a[0]] != kind_of[b[0]]: raise ValueError(f"subsumption across kinds {a} {b}")
        x, y = setting_iri(items, *a), setting_iri(items, *b)
        T.add("o0", "SubObjectPropertyOf" if kind_of[a[0]] == "ObjectProperty" else "SubClassOf", sub=x, sup=y,
              comment=f"{setting_label(*a)} <= {setting_label(*b)}: {why}")
        st["subsumptions"] += 1

    for n, it in sorted(items.items()):
        ss, ps = it.get("subsumes_settings") or [], it.get("param_subsumes") or []
        for o in it.get("subsumes") or []:
            if o not in items: raise ValueError(f"{n} subsumes unknown item {o}")
            if it.get("params") or items[o].get("params"):
                if not ss:
                    st["not_exported"].append(f"{n} subsumes {o}: declared at the default setting only, no per-setting form")
                continue          # the per-setting forms in subsumes_settings are exported instead (exact)
            sub((n, {}), (o, {}), "declared in ITEM['subsumes']")
        for a, o, b in ss:
            if o not in items: raise ValueError(f"{n} subsumes_settings unknown item {o}")
            sub((n, a), (o, b), "declared in ITEM['subsumes_settings']")
        for x, a, o, b in ps:
            if x != n or o not in items: raise ValueError(f"bad param_subsumes in {n}")
            sub((n, a), (o, b), "declared in ITEM['param_subsumes']")
        if it.get("chains"):
            st["not_exported"].append(f"{n} ITEM['chains'] (transformation compositions): they hold only under x != z, which "
                                      "an OWL property chain cannot state")
        # item level: X <= Y when every setting of X is declared below some setting of Y (X is the union of its settings)
        cover = defaultdict(set)
        for a, o, b in ss: cover[o].add(json.dumps(a, sort_keys=True))
        for _x, a, o, b in ps: cover[o].add(json.dumps(a, sort_keys=True))
        if it.get("params"):
            alls = {json.dumps(s, sort_keys=True) for s in settings(it)}
            for o in sorted(cover):
                if o == n: continue
                if cover[o] >= alls:
                    T.add("o0", "SubObjectPropertyOf" if kind_of[n] == "ObjectProperty" else "SubClassOf",
                          sub=curie_to_iri(it["iri"]), sup=curie_to_iri(items[o]["iri"]),
                          comment=f"{n} <= {o} at item level: every setting of {n} is declared below a setting of {o}, and "
                                  f"{n} is the union of its settings")
                    st["subsumptions"] += 1; st.setdefault("item_level_from_settings", []).append(f"{n} <= {o}")
                elif o in (it.get("subsumes") or []):
                    st["not_exported"].append(f"{n} <= {o} at item level (ITEM['subsumes'], checked by the harness at the "
                                              f"default setting only): false for settings not covered, so only the "
                                              f"per-setting axioms are exported")

    rcc = lambda r: setting_iri(items, "rcc8_" + r, {})  # noqa: E731
    for r in [x for t in RCC8_SINGLE + RCC5_SINGLE for x in t] + RCC_EQ_FOR + ["EQ"]:
        if "rcc8_" + r not in items: raise ValueError(f"missing O0 item rcc8_{r}")
    for a, b, c in RCC8_SINGLE:
        T.add("o0", "Chain", chain=[rcc(a), rcc(b)], sup=rcc(c),
              comment=f"RCC-8 composition table (Randell, Cui & Cohn 1992; Cohn et al. 1997, Table 1): {a} o {b} = {{{c}}}. "
                      "Sound in the O0 grounding (filled regions, 4-adjacency, boundary = region cells with an outside "
                      "4-neighbour or on the grid border).")
        st["chains_rcc"] += 1
    for r in RCC_EQ_FOR:
        tab = "RCC-5" if r in ("PP", "PPi") else "RCC-8"
        for a, b in ((r, "EQ"), ("EQ", r)):
            T.add("o0", "Chain", chain=[rcc(a), rcc(b)], sup=rcc(r),
                  comment=f"{tab} composition table: EQ is the identity, {a} o {b} = {{{r}}} (EQ o EQ omitted: O0 roles are "
                          "irreflexive)")
            st["chains_rcc"] += 1
    for a, b, c in RCC5_SINGLE:
        T.add("o0", "Chain", chain=[rcc(a), rcc(b)], sup=rcc(c),
              comment=f"RCC-5 composition table (Randell, Cui & Cohn 1992; Bennett 1994): {a} o {b} = {{{c}}} (proper part "
                      "is transitive; region(x) < region(y) < region(z))")
        st["chains_rcc"] += 1
    al = items["allen"]
    for axis in al["params"]["axis"]:
        for a, b, c in ALLEN_SINGLE:
            for r in (a, b, c):
                if AB[r] not in al["params"]["rel"]: raise ValueError(f"allen rel {AB[r]} not declared")
            sa = lambda r: setting_iri(items, "allen", {"axis": axis, "rel": AB[r]})  # noqa: E731
            T.add("o0", "Chain", chain=[sa(a), sa(b)], sup=sa(c),
                  comment=f"Allen (1983) transitivity table, Fig. 4: {AB[a]} o {AB[b]} = {{{AB[c]}}}, same axis ({axis}); the "
                          "discrete reading [min, max+1) embeds exactly into Allen's real intervals")
            st["chains_allen"] += 1
    st["not_exported"].append("RCC-8 entries involving EC: rcc8_EC is grounded on raw cells (not filled regions), so the "
                              "region composition table does not apply to it")
    st["not_exported"].append("EQ o EQ <= EQ and allen equals o equals <= equals: unsound for irreflexive relations (x != y)")
    st["not_exported"].append("multi-relation table entries (disjunctive results, not EL) and derived PP o NTPP <= NTPP style "
                              "entries (non-regular together with NTPP <= PP)")
    return st


# ------------------------------------------------------------------------------------------------ 4 + 5: lattice
def lat_local(name):
    s = name.replace(">", "_gt_").replace("=", "_eq_").replace(":", "_")
    s = re.sub(r"[^A-Za-z0-9_]", "_", s)
    if not re.match(r"[A-Za-z_]", s): s = "a_" + s
    return s


COLOURS = range(10)
# attributes() vocabulary (occupancy2.py); every name / f-string stem is checked against the source below.
ATTR_LITERAL = ["multicolor", "size>12", "largest", "smallest", "size_unique", "single_pixel", "hline", "vline",
                "filled_rect", "square_bbox", "hollow_rect", "has_hole", "sym_lr", "sym_ud", "shape_unique",
                "shape_shared", "color_unique", "color_most_common", "color_least_common", "touches_border", "topmost",
                "bottommost", "leftmost", "rightmost", "touches_other", "isolated", "inside_other", "contains_other"]
ATTR_TEMPLATE = {"color=": [str(c) for c in COLOURS], "size=": [str(k) for k in range(1, 13)],
                 "adjColor=": [str(c) for c in COLOURS], "contextColor=": [str(c) for c in COLOURS],
                 "alignedColor=": [str(c) for c in COLOURS]}
# extra names (extra_attrs) added only to state a definitional equivalence
EXTRA_NAMES = ["D1:size_rank=0", "D1:size_rank_asc=0"]


def lattice_axioms(names):
    """(kind, members, justification) for definitional facts of occupancy2.attributes() / extra_attrs(); only facts
    whose classes are all exported are kept."""
    F = []
    F.append(("Eq", ["single_pixel", "size=1"],
              "attributes(): 'single_pixel' is added iff sizes[i] == 1, and 'size=<n>' is added with n = sizes[i] when "
              "sizes[i] <= 12, so size=1 holds iff sizes[i] == 1"))
    F.append(("Eq", ["D1:size_rank=0", "largest"],
              "extra_attrs(): ranks = distinct sizes sorted descending, so rank 0 means sizes[i] == max(sizes), which is "
              "exactly the test for 'largest' in attributes()"))
    F.append(("Eq", ["D1:size_rank_asc=0", "smallest"],
              "extra_attrs(): ascending rank 0 means sizes[i] == min(sizes), the test for 'smallest' in attributes()"))
    F.append(("Sub", ["hollow_rect", "has_hole"],
              "hollow_rect requires has_hole(pix); has_hole(pix) floods the free cells of the bbox plus a one-cell margin "
              "from the corner exactly as interior(pix) does (its early False is for bboxes thinner than 3, where nothing "
              "can be enclosed), so it is true iff interior(pix) is non-empty, the test for 'has_hole'"))
    F.append(("Sub", ["contains_other", "has_hole"],
              "contains_other: some other node's pixel set (non-empty: bbox() of every node is taken) is a subset of "
              "inner[i], so inner[i] is non-empty, the test for 'has_hole'"))
    for c in COLOURS:
        F.append(("Sub", [f"contextColor={c}", "inside_other"],
                  "'contextColor=<c>' is added only inside the 'if containers:' branch that adds 'inside_other'"))
        F.append(("Sub", [f"adjColor={c}", "touches_other"],
                  "'adjColor=<c>' ranges over colours of the touch set; a non-empty touch set adds 'touches_other'"))
    F.append(("Sub", ["color_unique", "color_least_common"],
              "color_unique: ccount[c] == 1; every count of a present colour is >= 1, so ccount[c] == min(ccount.values())"))
    F.append(("Sub", ["single_pixel", "smallest"], "every node has >= 1 pixel, so a size-1 node has the minimum size"))
    F.append(("Sub", ["single_pixel", "square_bbox"], "size 1 gives h == w == 1"))
    F.append(("Sub", ["single_pixel", "sym_lr"], "the one-cell normalised shape equals its left-right mirror"))
    F.append(("Sub", ["single_pixel", "sym_ud"], "the one-cell normalised shape equals its up-down mirror"))
    F.append(("Sub", ["hline", "sym_ud"], "hline has h == 1, so the up-down mirror r -> h-1-r is the identity"))
    F.append(("Sub", ["vline", "sym_lr"], "vline has w == 1, so the left-right mirror c -> w-1-c is the identity"))
    F.append(("Sub", ["filled_rect", "sym_lr"], "filled_rect: the shape is the full h x w box, which is mirror-symmetric"))
    F.append(("Sub", ["filled_rect", "sym_ud"], "filled_rect: the shape is the full h x w box, which is mirror-symmetric"))
    for k in range(1, 6):
        F.append(("Sub", [f"D12:n_holes={k}", "has_hole"],
                  "extra_attrs(): n_holes counts the 4-connected components of interior(pix); >= 1 means interior(pix) is "
                  "non-empty, the test for 'has_hole'"))
    for k in range(1, 5):
        F.append(("Sub", [f"D4:n_touch={k}", "touches_other"],
                  "extra_attrs(): n_touch >= 1 means a 4-neighbour is owned by another node; attributes() tests the "
                  "8-neighbourhood, which contains it"))
    F.append(("Disj", [f"color={c}" for c in COLOURS] + ["multicolor"],
              "attributes() adds exactly one of 'color=<c>' (c = the node colour) or 'multicolor'"))
    F.append(("Disj", [f"size={k}" for k in range(1, 13)] + ["size>12"],
              "attributes() adds exactly one of 'size=<n>' (n <= 12) or 'size>12'"))
    F.append(("Disj", ["touches_other", "isolated"], "attributes() adds exactly one of 'touches_other' / 'isolated'"))
    F.append(("Disj", ["shape_unique", "shape_shared"], "attributes() adds exactly one of 'shape_unique' / 'shape_shared'"))
    F.append(("Disj", ["single_pixel", "hline", "vline"],
              "hline: h == 1 and w > 1; vline: w == 1 and h > 1; single_pixel: h == w == 1"))
    F.append(("Disj", ["single_pixel", "filled_rect"], "filled_rect requires h*w > 1 cells"))
    F.append(("Disj", ["filled_rect", "has_hole"], "a full h x w box encloses no cell"))
    F.append(("Disj", ["has_hole", "single_pixel"], "interior(pix) is empty unless the bbox is at least 3 x 3"))
    F.append(("Disj", ["has_hole", "hline"], "interior(pix) is empty unless the bbox is at least 3 x 3"))
    F.append(("Disj", ["has_hole", "vline"], "interior(pix) is empty unless the bbox is at least 3 x 3"))
    F.append(("Disj", ["inside_other", "touches_border"],
              "inside_other: pix is inside inner[j], whose cells lie strictly inside bbox(j) (bbox edge cells reach the "
              "margin), so no cell of the node is on the grid border"))
    F.append(("Disj", [f"D12:n_holes={k}" for k in range(6)], "extra_attrs() adds one value min(n_holes, 5)"))
    F.append(("Disj", ["D12:n_holes=0", "has_hole"], "n_holes == 0 iff interior(pix) is empty"))
    F.append(("Disj", [f"D4:n_touch={k}" for k in range(5)], "extra_attrs() adds one value min(n_touch, 4)"))
    F.append(("Disj", [f"D1:size_rank={k}" for k in range(4)] + ["D1:size_rank>3"], "extra_attrs() adds one size rank"))
    F.append(("Disj", [f"D1:size_rank_asc={k}" for k in range(64)], "extra_attrs() adds one ascending size rank"))
    out = []
    for kind, mem, why in F:
        mem2 = [m for m in mem if m in names]
        if kind == "Disj":
            if len(mem2) >= 2: out.append((kind, mem2, why))
        elif len(mem2) == len(mem):
            out.append((kind, mem, why))
    return out


def export_lattice_parents(T, path=PARENTS):
    """G71: SubClassOf(lat:<name> t58:<Class>) for every name of the mapping, SubClassOf(t58:<Class> t58:<TOP>) for
    every class and image-schema top; parent classes and tops live in the t58 namespace (no recogniser name added)."""
    if not os.path.exists(path): return dict(skipped="no " + os.path.relpath(path, ROOT))
    M = json.load(open(path))
    tops = {k: T.declare(NS["t58"] + v.split(":", 1)[1], "Class") for k, v in M["schema_tops"].items()}
    for k, iri in tops.items():
        T.label(iri, k); T.note(iri, f"image-schema top {k} (v10 schema vocabulary); G71 root")
    cls = {}
    for c, d in M["classes"].items():
        cls[c] = T.declare(NS["t58"] + c, "Class"); T.label(cls[c], c); T.note(cls[c], "G71 lattice parent class: " + d["comment"])
        for t in d["tops"]:
            T.add("lattice_parents", "SubClassOf", sub=cls[c], sup=tops[t], comment=f"G71: {c} <= {t} (lattice_parents.json)")
    lat = {n: NS["lat"] + lat_local(n) for n in M["names"]}
    missing = [n for n in lat if lat[n] not in T.ent]
    if missing: raise ValueError("G71 names not declared as lattice classes: %s" % missing[:5])
    why = {f["regex"]: f["why"] for f in M["families"]}
    for n, c in sorted(M["names"].items()):
        w = next((why[f["regex"]] for f in M["families"] if re.match(f["regex"], n)), "")
        T.add("lattice_parents", "SubClassOf", sub=lat[n], sup=cls[c], comment=f"G71: {n} <= {c}: {w}")
    return dict(names=len(M["names"]), classes=len(cls), tops=len(tops), counts=M.get("counts"),
                not_placed=[x["family"] for x in M.get("not_placed", [])])


def name_in_source(name, src):
    if name.startswith("exists_"):
        return "exists_{key}" in src and f'"{name[7:]}"' in src
    if name.startswith("px:") or name.startswith("obj:") or name.startswith("cx:") or name.startswith("at:"):
        return name.split(":")[0] + ":" in src
    if f'"{name}"' in src: return True
    stem = re.split(r"(?<=[=>])", name)[0]           # 'color=3' -> 'color=', 'size>12' -> 'size>'
    return f'f"{stem}' in src or f'"{stem}' in src


def export_lattice(T, runs):
    src = open(OCC).read()
    a0, a1 = src.index("def attributes("), src.index("\ndef slide_distance(")
    attr_src = src[a0:a1]
    unverified = []
    for n in ATTR_LITERAL:
        if f'"{n}"' not in attr_src: unverified.append(n)
    for stem in ATTR_TEMPLATE:
        if f'f"{stem}' not in attr_src: unverified.append(stem)
    vocab = list(ATTR_LITERAL) + [s + v for s, vs in ATTR_TEMPLATE.items() for v in vs]
    n2 = set(re.findall(r"[0-9a-f]{8}", open(N2).read()))
    pairs, rule_names = {}, set()
    n_tasks, n_skipped, n_two = 0, 0, 0

    def rules_of(R):
        out = []

        def walk(x):
            if (isinstance(x, list) and len(x) == 2 and isinstance(x[0], list) and isinstance(x[1], str)
                    and all(isinstance(a, str) for a in x[0])):
                out.append(x); return
            if isinstance(x, list):
                for y in x: walk(y)
        walk(R)
        return out

    for f in runs:
        for line in open(f):
            d = json.loads(line)
            if "rules" not in d: continue
            if d.get("task") in n2:
                n_skipped += 1; continue
            n_tasks += 1
            for attrs, _label in rules_of(d["rules"]):
                rule_names.update(attrs)
                if len(attrs) == 2:
                    n_two += 1
                    key = tuple(sorted(attrs))
                    pairs[key] = pairs.get(key, 0) + 1
    extra = sorted(n for n in rule_names if n not in vocab)
    names = vocab + [n for n in extra] + [n for n in EXTRA_NAMES if n not in vocab and n not in extra]
    emitted = sorted(n for n in json.load(open(PARENTS))["names"] if n not in names) if os.path.exists(PARENTS) else []
    names += emitted                                    # G71: every emitted name the mapping places
    for n in names[len(vocab):]:
        if not name_in_source(n, src): unverified.append(n)
    iri = {}
    for n in names:
        iri[n] = T.declare(NS["lat"] + lat_local(n), "Class")
        T.label(iri[n], n)
    if len(set(iri.values())) != len(iri): raise ValueError("lattice name collision after IRI sanitising")
    nsub = neq = ndisj = 0
    for kind, mem, why in lattice_axioms(set(names)):
        if kind == "Sub":
            T.add("lattice", "SubClassOf", sub=iri[mem[0]], sup=iri[mem[1]], comment=f"{mem[0]} <= {mem[1]}: {why}"); nsub += 1
        elif kind == "Eq":
            T.add("lattice", "EquivalentClasses", members=[iri[m] for m in mem], comment=f"{mem[0]} == {mem[1]}: {why}"); neq += 1
        else:
            T.add("lattice", "DisjointClasses", members=[iri[m] for m in mem], comment=f"pairwise disjoint: {why}"); ndisj += 1
    seen = {}
    for (a, b), cnt in sorted(pairs.items()):
        p = NS["lat"] + f"Pair_{lat_local(a)}_{lat_local(b)}"
        if p in seen or p in iri.values(): raise ValueError("pair name collision")
        seen[p] = (a, b)
        T.declare(p, "Class")
        T.label(p, f"Pair({a}, {b})")
        T.add("pairs", "EquivalentClasses", members=[p, ("and", [iri[a], iri[b]])],
              comment=f"lattice rule conjunction {a} and {b} (two-attribute rule in {cnt} rule occurrence(s) of the "
                      "exported lattice programs)")
    return dict(attribute_vocabulary=len(vocab), names_from_rules_added=len(extra), extra_names=EXTRA_NAMES,
                names_from_g71_mapping_added=len(emitted),
                lattice_classes=len(names), subclassof=nsub, equivalentclasses=neq, disjointclasses=ndisj,
                runs=[os.path.relpath(f, ROOT) for f in runs], tasks_with_rules_used=n_tasks, tasks_skipped_n2=n_skipped,
                two_attribute_rule_occurrences=n_two, distinct_pairs=len(pairs), unverified_names=unverified,
                pairs=[f"{a} & {b}" for a, b in sorted(pairs)])


# ------------------------------------------------------------------------------------------------ serialisers
def short(iri):
    for p, ns in PREFIXES:
        if iri.startswith(ns):
            loc = iri[len(ns):]
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", loc): return f"{p}:{loc}"
    return f"<{iri}>"


def lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def ce(x):
    if isinstance(x, tuple):
        return "ObjectIntersectionOf(" + " ".join(ce(y) for y in x[1]) + ")"
    return short(x)


def write_ofn(T, path, header):
    L = [f"Prefix({p}:=<{ns}>)" for p, ns in PREFIXES]
    L.append("")
    L.append(f"Ontology(<{ONT}>")
    L.append(f"Annotation(rdfs:comment {lit(ascii_text(header))})")
    L.append("")
    for kind in ("Class", "ObjectProperty"):
        for iri in sorted(i for i, k in T.ent.items() if k == kind):
            L.append(f"Declaration({kind}({short(iri)}))")
    L.append("")
    for a in T.ax:
        an = f"Annotation(rdfs:comment {lit(a['comment'])}) " if a["comment"] else ""
        k = a["kind"]
        if k == "SubClassOf": L.append(f"SubClassOf({an}{short(a['sub'])} {short(a['sup'])})")
        elif k == "SubObjectPropertyOf": L.append(f"SubObjectPropertyOf({an}{short(a['sub'])} {short(a['sup'])})")
        elif k == "Chain":
            L.append(f"SubObjectPropertyOf({an}ObjectPropertyChain({' '.join(short(x) for x in a['chain'])}) {short(a['sup'])})")
        elif k == "EquivalentClasses": L.append(f"EquivalentClasses({an}{' '.join(ce(x) for x in a['members'])})")
        elif k == "DisjointClasses": L.append(f"DisjointClasses({an}{' '.join(short(x) for x in a['members'])})")
        else: raise ValueError(k)
    L.append("")
    for s, p, t in T.ann:
        L.append(f"AnnotationAssertion({short(p)} {short(s)} {lit(t)})")
    L.append(")")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")


def build_graph(T, header):
    g = rdflib.Graph()
    for p, ns in PREFIXES: g.bind(p, ns)
    o = URIRef(ONT)
    g.add((o, RDF.type, OWL.Ontology)); g.add((o, RDFS.comment, Literal(ascii_text(header))))
    for iri, k in T.ent.items():
        g.add((URIRef(iri), RDF.type, OWL.Class if k == "Class" else OWL.ObjectProperty))

    def node(x):
        if isinstance(x, tuple):
            b = BNode(); g.add((b, RDF.type, OWL.Class))
            lst = BNode(); Collection(g, lst, [node(y) for y in x[1]]); g.add((b, OWL.intersectionOf, lst))
            return b
        return URIRef(x)

    def annotate(s, p, t, comment):
        if not comment: return
        ax = BNode()
        g.add((ax, RDF.type, OWL.Axiom)); g.add((ax, OWL.annotatedSource, s)); g.add((ax, OWL.annotatedProperty, p))
        g.add((ax, OWL.annotatedTarget, t)); g.add((ax, RDFS.comment, Literal(comment)))

    for a in T.ax:
        k, c = a["kind"], a["comment"]
        if k in ("SubClassOf", "SubObjectPropertyOf"):
            p = RDFS.subClassOf if k == "SubClassOf" else RDFS.subPropertyOf
            s, t = URIRef(a["sub"]), URIRef(a["sup"])
            g.add((s, p, t)); annotate(s, p, t, c)
        elif k == "Chain":
            lst = BNode(); Collection(g, lst, [URIRef(x) for x in a["chain"]])
            s = URIRef(a["sup"]); g.add((s, OWL.propertyChainAxiom, lst)); annotate(s, OWL.propertyChainAxiom, lst, c)
        elif k == "EquivalentClasses":
            m = [node(x) for x in a["members"]]
            if len(m) != 2: raise ValueError("n-ary EquivalentClasses not used")
            g.add((m[0], OWL.equivalentClass, m[1])); annotate(m[0], OWL.equivalentClass, m[1], c)
        elif k == "DisjointClasses":
            m = [URIRef(x) for x in a["members"]]
            if len(m) == 2:
                g.add((m[0], OWL.disjointWith, m[1])); annotate(m[0], OWL.disjointWith, m[1], c)
            else:
                b = BNode(); lst = BNode(); Collection(g, lst, m)
                g.add((b, RDF.type, OWL.AllDisjointClasses)); g.add((b, OWL.members, lst))
                if c: g.add((b, RDFS.comment, Literal(c)))
    for s, p, t in T.ann:
        g.add((URIRef(s), URIRef(p), Literal(t)))
    return g


# ------------------------------------------------------------------------------------------------ checks on the files
TOK = re.compile(r'\s+|(?P<lp>\()|(?P<rp>\))|(?P<iri><[^<>"{}|^`\\\s]*>)|(?P<str>"(?:[^"\\]|\\.)*")'
                 r'(?P<suf>\^\^[^\s()]+|@[A-Za-z0-9-]+)?|(?P<word>[^\s()<>"]+)')
EL_AXIOMS = {"Declaration", "SubClassOf", "EquivalentClasses", "DisjointClasses", "SubObjectPropertyOf",
             "EquivalentObjectProperties", "TransitiveObjectProperty", "ReflexiveObjectProperty", "ObjectPropertyDomain",
             "ObjectPropertyRange", "DisjointObjectProperties", "SubDataPropertyOf", "EquivalentDataProperties",
             "DisjointDataProperties", "DataPropertyDomain", "DataPropertyRange", "FunctionalDataProperty",
             "DatatypeDefinition", "HasKey", "ClassAssertion", "ObjectPropertyAssertion", "DataPropertyAssertion",
             "NegativeObjectPropertyAssertion", "NegativeDataPropertyAssertion", "SameIndividual", "DifferentIndividuals",
             "AnnotationAssertion", "SubAnnotationPropertyOf", "AnnotationPropertyDomain", "AnnotationPropertyRange"}
EL_INNER = {"Class", "ObjectProperty", "DataProperty", "AnnotationProperty", "NamedIndividual", "Datatype", "Annotation",
            "ObjectIntersectionOf", "ObjectSomeValuesFrom", "ObjectHasValue", "ObjectHasSelf", "ObjectOneOf",
            "DataSomeValuesFrom", "DataHasValue", "DataIntersectionOf", "DataOneOf", "ObjectPropertyChain"}
NOT_EL = {"ObjectInverseOf": "inverse property", "InverseObjectProperties": "inverse property",
          "ObjectAllValuesFrom": "universal restriction", "DataAllValuesFrom": "universal restriction",
          "ObjectComplementOf": "negation", "DataComplementOf": "negation", "ObjectUnionOf": "disjunction",
          "DataUnionOf": "disjunction", "DisjointUnion": "disjunction", "ObjectMinCardinality": "cardinality",
          "ObjectMaxCardinality": "cardinality", "ObjectExactCardinality": "cardinality", "DataMinCardinality": "cardinality",
          "DataMaxCardinality": "cardinality", "DataExactCardinality": "cardinality",
          "FunctionalObjectProperty": "functional object property", "InverseFunctionalObjectProperty": "inverse property",
          "SymmetricObjectProperty": "symmetric property (inverse)", "AsymmetricObjectProperty": "asymmetric property",
          "IrreflexiveObjectProperty": "irreflexive property"}


def parse_ofn(path):
    text = open(path, encoding="utf-8").read()
    toks, pos, depth, err = [], 0, 0, []
    while pos < len(text):
        m = TOK.match(text, pos)
        if not m:
            err.append(f"untokenisable text at offset {pos}"); break
        pos = m.end()
        if m.group("lp"): depth += 1; toks.append(("(", None))
        elif m.group("rp"):
            depth -= 1; toks.append((")", None))
            if depth < 0: err.append(f"unbalanced ')' at offset {m.start()}"); depth = 0
        elif m.group("iri"): toks.append(("iri", m.group("iri")[1:-1]))
        elif m.group("str") is not None: toks.append(("lit", m.group("str")))
        elif m.group("word"): toks.append(("word", m.group("word")))
    if depth: err.append(f"{depth} unclosed '('")

    def expr(i):
        t, v = toks[i]
        if t == "word" and i + 1 < len(toks) and toks[i + 1][0] == "(":
            kids, j = [], i + 2
            while j < len(toks) and toks[j][0] != ")":
                k, j = expr(j); kids.append(k)
            return (v, kids), j + 1
        return (t, v), i + 1

    top, i = [], 0
    if not err:
        while i < len(toks):
            e, i = expr(i); top.append(e)
    return top, err


def check_ofn(path):
    top, err = parse_ofn(path)
    res = dict(file=os.path.relpath(path, ROOT), balanced_parentheses=not any("nbalanced" in e or "unclosed" in e for e in err),
               errors=list(err))
    if err: return res, None
    prefixes, onts = {}, []
    for e in top:
        if e[0] == "Prefix":
            k = e[1]
            if len(k) != 2 or k[0][0] != "word" or not k[0][1].endswith(":=") or k[1][0] != "iri":
                err.append(f"bad Prefix declaration {k}"); continue
            p = k[0][1][:-2]
            if p in prefixes: err.append(f"prefix {p} declared twice")
            prefixes[p] = k[1][1]
        elif e[0] == "Ontology": onts.append(e)
        else: err.append(f"unexpected top-level element {e[0]}")
    if len(onts) != 1:
        err.append(f"{len(onts)} Ontology(...) blocks"); res["errors"] = err; return res, None

    def expand(atom):
        t, v = atom
        if t == "iri": return v
        if t == "word" and ":" in v:
            p, loc = v.split(":", 1)
            if p not in prefixes: err.append(f"undeclared prefix in {v}"); return None
            return prefixes[p] + loc
        return None

    body = onts[0][1]
    if not body or body[0][0] != "iri": err.append("ontology IRI missing")
    declared, used, axioms = {}, defaultdict(set), []
    heads = defaultdict(int)
    notel = []

    def walk(node, ax):
        if node[0] in ("iri", "word", "lit"):
            if node[0] == "word" and ":" not in node[1]:
                err.append(f"stray keyword {node[1]}")
            iri = expand(node) if node[0] != "lit" else None
            if iri: used[iri].add(ax)
            return
        head, kids = node
        heads[head] += 1
        if head in NOT_EL: notel.append(dict(construct=head, kind=NOT_EL[head], axiom=ax))
        elif head not in EL_INNER and head not in EL_AXIOMS: notel.append(dict(construct=head, kind="not in OWL 2 EL", axiom=ax))
        if head in ("ObjectOneOf", "DataOneOf") and len(kids) != 1:
            notel.append(dict(construct=head, kind="enumeration of more than one element", axiom=ax))
        for k in kids: walk(k, ax)

    for n, e in enumerate(body[1:]):
        if e[0] in ("iri", "word", "lit"):
            err.append(f"stray token in ontology body: {e[1]}"); continue
        head, kids = e
        if head == "Annotation" and not axioms: continue   # ontology annotation
        if head == "Declaration":
            (kind, inner), = kids
            iri = expand(inner[0])
            if iri in declared and declared[iri] != kind:
                err.append(f"{iri} declared as {declared[iri]} and {kind}")
            declared[iri] = kind
            heads["Declaration"] += 1
            continue
        axioms.append(e)
        walk(e, n)
    annot_props = {RDFS_LABEL, RDFS_COMMENT}
    undeclared = sorted(i for i in used if i not in declared and i not in BUILTIN and i not in annot_props)
    res.update(prefixes=len(prefixes), ontology_iri=body[0][1] if body and body[0][0] == "iri" else None,
               declarations=sum(1 for _ in declared), declared_classes=sum(1 for k in declared.values() if k == "Class"),
               declared_object_properties=sum(1 for k in declared.values() if k == "ObjectProperty"),
               axioms=len(axioms), undeclared_iris=undeclared[:20], n_undeclared=len(undeclared),
               unused_declarations=sum(1 for i in declared if i not in used),
               constructs={k: v for k, v in sorted(heads.items())}, errors=err)
    res["ok"] = not err and not undeclared and res["balanced_parentheses"]
    return res, dict(axioms=axioms, expand=expand, notel=notel, declared=declared)


def classify_counts(parsed):
    c = defaultdict(int)
    for head, kids in parsed["axioms"]:
        k = [x for x in kids if x[0] != "Annotation"]
        if head == "SubObjectPropertyOf" and k[0][0] == "ObjectPropertyChain": c["property_chains"] += 1
        else: c[head] += 1
    return dict(c)


def rbox_regularity(parsed):
    """OWL 2 Structural Specification section 11.2: a strict order < on object property expressions such that
    (i) OPE1 -> OPE2 and not OPE2 ->* OPE1 imply OPE1 < OPE2, and (ii) every chain axiom ObjectPropertyChain(P1..Pn) <= P
    is of one of the forms: P = owl:topObjectProperty; n = 2 and P1 = P2 = P; Pi < P for all i; P1 = P and Pi < P for
    i >= 2; Pn = P and Pi < P for i <= n-1. With no inverse expressions the order extends to INV(.) by INV(X) ~ X, so
    the 'regular order' condition (OPE1 < OPE2 iff INV(OPE1) < OPE2) holds automatically."""
    ex = parsed["expand"]
    arrow, chains, viol, inverse = defaultdict(set), [], [], []
    for head, kids in parsed["axioms"]:
        k = [x for x in kids if x[0] != "Annotation"]
        if head == "SubObjectPropertyOf":
            if k[0][0] == "ObjectPropertyChain":
                chains.append(([ex(x) for x in k[0][1]], ex(k[1])))
            elif k[0][0] in ("iri", "word") and k[1][0] in ("iri", "word"):
                arrow[ex(k[0])].add(ex(k[1]))
            else: inverse.append(head)
        elif head == "EquivalentObjectProperties":
            ps = [ex(x) for x in k]
            for a in ps:
                for b in ps:
                    if a != b: arrow[a].add(b)
        elif head in ("InverseObjectProperties", "SymmetricObjectProperty"):
            inverse.append(head)
        elif head == "TransitiveObjectProperty":
            chains.append(([ex(k[0]), ex(k[0])], ex(k[0])))

    def reach(a):
        seen, st = {a}, [a]
        while st:
            x = st.pop()
            for y in arrow.get(x, ()):
                if y not in seen: seen.add(y); st.append(y)
        return seen

    R = {}
    less = defaultdict(set)          # a < b
    why = defaultdict(list)
    for a in list(arrow):
        for b in arrow[a]:
            R.setdefault(b, reach(b))
            if a not in R[b]:
                less[a].add(b); why[(a, b)].append(f"SubObjectPropertyOf({short(a)} {short(b)})")
    top = NS["owl"] + "topObjectProperty"
    for links, sup in chains:
        name = f"{' o '.join(short(x) for x in links)} <= {short(sup)}"
        if sup == top: continue
        if len(links) == 2 and links[0] == links[1] == sup: continue
        pos = [i for i, x in enumerate(links) if x == sup]
        n = len(links)
        if any(0 < i < n - 1 for i in pos) or (0 in pos and n - 1 in pos):
            viol.append(dict(chain=name, reason="super-property occurs inside the chain (not first/last only)")); continue
        for i, x in enumerate(links):
            if x != sup:
                less[x].add(sup); why[(x, sup)].append(name)
    # strict order exists iff the constraint graph is acyclic: report every strongly connected component
    nodes = set(less) | {b for s in less.values() for b in s}
    idx, low, onst, st, comps, counter = {}, {}, set(), [], [], [0]
    sys.setrecursionlimit(10000)

    def sc(v):
        idx[v] = low[v] = counter[0]; counter[0] += 1; st.append(v); onst.add(v)
        for w in less.get(v, ()):
            if w not in idx: sc(w); low[v] = min(low[v], low[w])
            elif w in onst: low[v] = min(low[v], idx[w])
        if low[v] == idx[v]:
            comp = []
            while True:
                w = st.pop(); onst.discard(w); comp.append(w)
                if w == v: break
            if len(comp) > 1 or v in less.get(v, ()): comps.append(comp)
    for v in sorted(nodes):
        if v not in idx: sc(v)
    for comp in comps:
        cs = set(comp)
        viol.append(dict(cycle=sorted(short(x) for x in comp),
                         because=sorted({w for (a, b), ws in why.items() if a in cs and b in cs for w in ws})))
    depth = {}

    def d(v):
        if v not in depth:
            depth[v] = 0
            depth[v] = 1 + max((d(w) for w in less.get(v, ())), default=-1)
        return depth[v]
    longest = max((d(v) for v in nodes), default=0) if not comps else None
    return dict(regular=not viol, violations=viol, chain_axioms=len(chains), order_constraints=sum(map(len, less.values())),
                properties_in_order=len(nodes), longest_strict_path=longest,
                inverse_or_symmetric_axioms=inverse,
                note="OWL 2 spec section 11.2; no inverse property expressions occur, so INV(X) is ordered like X")


def check_ttl(path, counts):
    g = rdflib.Graph(); g.parse(path, format="turtle")
    uri = lambda x: isinstance(x, URIRef)  # noqa: E731
    got = dict(
        classes=sum(1 for s in g.subjects(RDF.type, OWL.Class) if uri(s)),
        object_properties=sum(1 for s in g.subjects(RDF.type, OWL.ObjectProperty) if uri(s)),
        SubClassOf=sum(1 for s, o in g.subject_objects(RDFS.subClassOf)),
        SubObjectPropertyOf=sum(1 for s, o in g.subject_objects(RDFS.subPropertyOf)),
        property_chains=sum(1 for _ in g.subject_objects(OWL.propertyChainAxiom)),
        EquivalentClasses=sum(1 for _ in g.subject_objects(OWL.equivalentClass)),
        DisjointClasses=sum(1 for _ in g.subject_objects(OWL.disjointWith)) + sum(1 for _ in g.subjects(RDF.type, OWL.AllDisjointClasses)))
    forbidden = [str(p) for p in (OWL.inverseOf, OWL.allValuesFrom, OWL.complementOf, OWL.unionOf, OWL.cardinality,
                                  OWL.minCardinality, OWL.maxCardinality, OWL.qualifiedCardinality, OWL.oneOf,
                                  OWL.disjointUnionOf) if any(True for _ in g.subject_objects(p))]
    mism = {k: (got[k], counts.get(k)) for k in got if got[k] != counts.get(k)}
    return dict(file=os.path.relpath(path, ROOT), triples=len(g), counts=got, mismatches_vs_ofn=mism,
                non_el_vocabulary=forbidden, ok=not mism and not forbidden)


# ------------------------------------------------------------------------------------------------ expected answer
def expected_classification(T):
    """Classification of this TBox by EL saturation restricted to what it contains (atomic SubClassOf, atomic
    EquivalentClasses, Pair == A and B, DisjointClasses; no existential restriction occurs on the class side, so the
    property chains do not affect class subsumption). This is the answer ELK should reproduce."""
    classes = sorted(i for i, k in T.ent.items() if k == "Class")
    sup, conj, disj = defaultdict(set), [], []
    for a in T.ax:
        if a["kind"] == "SubClassOf": sup[a["sub"]].add(a["sup"])
        elif a["kind"] == "EquivalentClasses":
            m = a["members"]
            named = [x for x in m if not isinstance(x, tuple)]
            for x in named:
                for y in named:
                    if x != y: sup[x].add(y)
            for x in m:
                if isinstance(x, tuple):
                    for p in named:
                        sup[p].update(x[1]); conj.append((frozenset(x[1]), p))
        elif a["kind"] == "DisjointClasses": disj.append(set(a["members"]))
    S, unsat = {}, set()
    for c in classes:
        s, todo = {c}, [c]
        while todo:
            while todo:
                x = todo.pop()
                for y in sup.get(x, ()):
                    if y not in s: s.add(y); todo.append(y)
            for need, p in conj:
                if p not in s and need <= s: s.add(p); todo.append(p)
        S[c] = s
        if any(len(s & d) >= 2 for d in disj): unsat.add(c)
    changed = True
    while changed:                         # a class with an unsatisfiable subsumer is unsatisfiable
        changed = False
        for c in classes:
            if c not in unsat and S[c] & unsat: unsat.add(c); changed = True
    sat = [c for c in classes if c not in unsat]
    groups, seen = [], set()
    for c in sat:
        if c in seen: continue
        g = sorted(x for x in sat if x in S[c] and c in S[x])
        seen.update(g); groups.append(g)
    return dict(named_classes=len(classes), satisfiable=len(sat), distinct_after_classification=len(groups),
                equivalence_sets=[[short(x) for x in g] for g in groups if len(g) >= 2],
                unsatisfiable=sorted(short(x) for x in unsat))


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--concept-hierarchy", default=DEF_CH)
    ap.add_argument("--all-runs", action="store_true",
                    help="also read every other results/m1b/*_train / *_deval lattice run (default: c2 only)")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    runs = list(RUNS)
    if args.all_runs:
        runs = sorted(glob.glob(os.path.join(ROOT, "results", "m1b", "*_train.jsonl.txt"))
                      + glob.glob(os.path.join(ROOT, "results", "m1b", "*_deval.jsonl.txt")))
    os.makedirs(args.out, exist_ok=True)
    ofn, ttl, js = (os.path.join(args.out, f) for f in ("t58_tbox.ofn", "t58_tbox.ttl", "t58_export_summary.json"))

    T = TBox()
    src = {}
    src["concept_hierarchy"] = export_concept_hierarchy(T, args.concept_hierarchy)
    src["ontology_links"] = export_links(T, LINKS)
    items = load_items()
    src["o0_items"] = export_o0(T, items)
    src["lattice"] = export_lattice(T, runs)
    src["lattice_parents"] = export_lattice_parents(T)
    header = ("T58 (Fable guidance v10a) OWL 2 EL TBox generated by tools/owl/t58_export.py: concept_hierarchy.ttl classes, "
              "subclass axioms and its 11 property chains; ontology_links.ttl classes and subclass axioms; the O0 spatial "
              "roles with their declared subsumptions and deterministic RCC-8/RCC-5/Allen compositions; the lattice concept "
              "names of occupancy2.py with definitional axioms; and the lattice rules' two-attribute conjunctions as "
              "Pair_<a>_<b> classes; and (G71, Fable v12) the lattice names' parent classes under image-schema tops "
              "(tools/owl/lattice_parents.json). Axiom annotations give the source or justification of each axiom.")
    write_ofn(T, ofn, header)
    g = build_graph(T, header)
    g.serialize(ttl, format="turtle")

    ofn_res, parsed = check_ofn(ofn)
    counts = dict(classes=ofn_res.get("declared_classes"), object_properties=ofn_res.get("declared_object_properties"))
    if parsed:
        cc = classify_counts(parsed)
        counts.update(SubClassOf=cc.get("SubClassOf", 0), EquivalentClasses=cc.get("EquivalentClasses", 0),
                      DisjointClasses=cc.get("DisjointClasses", 0), SubObjectPropertyOf=cc.get("SubObjectPropertyOf", 0),
                      property_chains=cc.get("property_chains", 0), AnnotationAssertion=cc.get("AnnotationAssertion", 0))
        counts["logical_axioms"] = sum(v for k, v in counts.items() if k not in ("classes", "object_properties",
                                                                                 "AnnotationAssertion"))
    bysrc = {s: dict(v) for s, v in T.src.items()}
    el = dict(profile="OWL 2 EL", violations=parsed["notel"] if parsed else ["file did not parse"],
              checked="every constructor of every axiom in the written .ofn against the OWL 2 EL grammar (whitelist); "
                      "flags inverse properties, universal restrictions, negation, disjunction, cardinality, "
                      "functional/symmetric/asymmetric/irreflexive properties and enumerations of more than one element")
    reg = rbox_regularity(parsed) if parsed else dict(regular=False, violations=["file did not parse"])
    ttl_res = check_ttl(ttl, counts)
    exp = expected_classification(T)
    pairs_equiv = [s for s in exp["equivalence_sets"] if any("Pair_" in x for x in s)]
    summary = dict(
        test="T58", guidance="Fable guidance v10a", ontology_iri=ONT,
        files=dict(ofn=os.path.relpath(ofn, ROOT), ttl=os.path.relpath(ttl, ROOT), summary=os.path.relpath(js, ROOT)),
        counts=counts, axioms_by_source=bysrc, sources=src, el_profile=el, rbox_regularity=reg,
        ofn_structural_check=ofn_res, ttl_roundtrip_check=ttl_res,
        expected_classification=dict(exp, equivalence_sets_with_pairs=len(pairs_equiv)),
        left_out=[
            "concept_hierarchy.ttl: datatype properties, rdfs:domain/rdfs:range, and the punned concept->feature/constraint "
            "assertions (requiresFeature etc. between classes-as-individuals: ABox metamodelling, not TBox)",
            "concept_hierarchy.ttl: rdfs:subClassOf inside 4 chains replaced by the object property t58:subClassOfRel",
            "ontology_links.ttl: annotation properties (groundedIn, skos mappings, labels)",
        ] + src["o0_items"]["not_exported"] + [
            "lattice: subsumptions that need disjunction or negation (e.g. D14:dense_full == filled_rect or single_pixel) "
            "and links between lattice attributes and O0 roles (not definitional in the code)"],
    )
    with open(js, "w") as fh:
        json.dump(summary, fh, indent=1)
    c = counts
    print(f"T58 export -> {os.path.relpath(ofn, ROOT)}, {os.path.relpath(ttl, ROOT)}")
    print(f"  classes {c['classes']}  object properties {c['object_properties']}  SubClassOf {c.get('SubClassOf')}  "
          f"EquivalentClasses {c.get('EquivalentClasses')}  DisjointClasses {c.get('DisjointClasses')}  "
          f"SubObjectPropertyOf {c.get('SubObjectPropertyOf')}  property chains {c.get('property_chains')}")
    L = src["lattice"]
    print(f"  chains: concept_hierarchy {src['concept_hierarchy']['chains']}, RCC {src['o0_items']['chains_rcc']}, "
          f"Allen {src['o0_items']['chains_allen']}")
    print(f"  lattice: {L['lattice_classes']} concept classes, {L['distinct_pairs']} distinct pair classes from "
          f"{L['two_attribute_rule_occurrences']} two-attribute rules ({L['tasks_with_rules_used']} tasks used, "
          f"{L['tasks_skipped_n2']} N2 tasks skipped); unverified names: {L['unverified_names'] or 'none'}")
    print(f"  EL profile violations: {len(el['violations'])}   RBox regular: {reg['regular']} "
          f"({len(reg['violations'])} violations, {reg.get('order_constraints')} order constraints)")
    print(f"  .ofn structural check ok: {ofn_res.get('ok')} (balanced {ofn_res.get('balanced_parentheses')}, undeclared IRIs "
          f"{ofn_res.get('n_undeclared')})   .ttl reload ok: {ttl_res['ok']} ({ttl_res['triples']} triples)")
    print(f"  expected ELK result: {exp['named_classes']} named classes, {exp['distinct_after_classification']} distinct, "
          f"{len(exp['equivalence_sets'])} equivalence sets (size >= 2), {len(exp['unsatisfiable'])} unsatisfiable")
    for s in exp["equivalence_sets"]:
        print("    " + " == ".join(s))
    print(f"  summary -> {os.path.relpath(js, ROOT)}")
    ok = ofn_res.get("ok") and ttl_res["ok"] and not el["violations"] and reg["regular"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
