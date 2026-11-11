#!/usr/bin/env python3
"""pptx_strict.py — PresentationML schema-order guard for PPTX files.

Catches the defect class that LibreOffice tolerates but PowerPoint rejects
with "cannot open": elements written in schema-invalid child order.

Checks, per slide:
  1. <p:sld> children follow the CT_Slide sequence:
     cSld, clrMapOvr, transition, timing, extLst (present ones, in order).
  2. Every <p:cTn>'s element children are a subsequence of the
     CT_TLCommonTimeNodeData sequence:
     stCondLst, endCondLst, childTnLst, subTnLst, prevCondLst, nextCondLst.
     (Anything else inside cTn — e.g. attrNameLst — is a FAIL.)
  3. Every <p:cBhvr>'s children follow CT_TLCommonBehaviourData order:
     cTn, tgtEl, attrNameLst (cTn required; the rest optional).
  4. Every <p:seq>'s children follow: cTn, prevCondLst, nextCondLst.
  5. Every animation target (spTgt spid) resolves to a real shape id
     in the same slide's spTree.

Canonical timing-anatomy checks (PowerPoint's grammar; LibreOffice
tolerates all of these, which is how they shipped once):
  6. cTn id values are unique within each slide's timing tree.
  7. Preset attributes never nest: no cTn carrying presetID/presetClass
     may have a descendant cTn carrying them. (The original injector put
     presets on BOTH a group par and the branch par inside it.)
  8. A preset par's childTnLst holds ONLY leaf behaviour elements
     (set, anim, animClr, animEffect, animMotion, animRot, animScale) —
     never another p:par.
  9. Step anatomy under mainSeq is exactly 3 par levels:
     step par (click steps: stCondLst cond evt=onClick with sldTgt) >
     group par (plain cTn, NO preset attrs; first group of a click step
     binds the click: cond evt=onClick with spTgt of a real shape) >
     preset par(s). Any extra/missing level is a FAIL.
 10. nodeType discipline per step: a click step has exactly one preset
     par with nodeType=clickEffect and none with afterEffect; an auto
     step has exactly one afterEffect (when it has effects) and no
     clickEffect; all other preset pars are withEffect.
 11. grpId discipline: preset pars under one group par share a single
     grpId; different group pars in a slide never reuse a grpId.

Usage: pptx_strict.py <file.pptx> [more.pptx ...]
Exit 0 = PASS (all files), 1 = FAIL.
"""
import sys, zipfile
from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"

def q(t):
    return f"{{{P}}}{t}"

def lname(e):
    return etree.QName(e).localname

def check_seq(kids, order, ctx, problems):
    idx = []
    for k in kids:
        if k not in order:
            problems.append(f"{ctx}: unexpected child <p:{k}> (allowed: {order})")
            return
        idx.append(order.index(k))
    if idx != sorted(idx):
        problems.append(f"{ctx}: children out of schema order: {kids}")

SLD_ORDER = ["cSld", "clrMapOvr", "transition", "timing", "extLst"]
CTN_ORDER = ["stCondLst", "endCondLst", "childTnLst", "subTnLst",
             "prevCondLst", "nextCondLst"]
CBHVR_ORDER = ["cTn", "tgtEl", "attrNameLst"]
SEQ_ORDER = ["cTn", "prevCondLst", "nextCondLst"]

def check_file(path):
    problems = []
    z = zipfile.ZipFile(path)
    slides = sorted(n for n in z.namelist()
                    if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
    for name in slides:
        root = etree.fromstring(z.read(name))
        kids = [lname(c) for c in root if isinstance(c.tag, str)]
        if not kids or kids[0] != "cSld":
            problems.append(f"{name}: first child of <p:sld> is not cSld: {kids}")
        check_seq(kids, SLD_ORDER, f"{name} <p:sld>", problems)
        shape_ids = set()
        for sp in root.iter(q("cxnSp")):
            pass
        for e in root.iter():
            if lname(e) in ("sp", "cxnSp", "pic", "graphicFrame", "grpSp"):
                nv = e.find(f".//{q('cNvPr')}")
                if nv is not None:
                    shape_ids.add(nv.get("id"))
        for e in root.iter(q("cTn")):
            ck = [lname(c) for c in e if isinstance(c.tag, str)]
            check_seq(ck, CTN_ORDER, f"{name} <p:cTn id={e.get('id')}>", problems)
        for e in root.iter(q("cBhvr")):
            ck = [lname(c) for c in e if isinstance(c.tag, str)]
            if not ck or ck[0] != "cTn":
                problems.append(f"{name} <p:cBhvr>: first child is not cTn: {ck}")
            check_seq(ck, CBHVR_ORDER, f"{name} <p:cBhvr>", problems)
        for e in root.iter(q("seq")):
            ck = [lname(c) for c in e if isinstance(c.tag, str)]
            check_seq(ck, SEQ_ORDER, f"{name} <p:seq>", problems)
        for e in root.iter(q("spTgt")):
            if e.get("spid") not in shape_ids:
                problems.append(f"{name}: spTgt spid={e.get('spid')} "
                                f"does not resolve to a shape id")
        timing = root.find(q("timing"))
        if timing is not None:
            check_timing(timing, name, shape_ids, problems)
    return slides, problems

LEAF_BEHAVIOURS = ("set", "anim", "animClr", "animEffect", "animMotion",
                   "animRot", "animScale")

def _kids(e, tag):
    return [c for c in e if isinstance(c.tag, str) and lname(c) == tag]

def _first(e, tag):
    k = _kids(e, tag)
    return k[0] if k else None

def _ctn_of(par):
    return _first(par, "cTn")

def _child_pars(ctn):
    lst = _first(ctn, "childTnLst") if ctn is not None else None
    return _kids(lst, "par") if lst is not None else []

def _conds(ctn):
    st = _first(ctn, "stCondLst") if ctn is not None else None
    return _kids(st, "cond") if st is not None else []

def check_timing(timing, name, shape_ids, problems):
    ctx = f"{name} <p:timing>"
    # 6. cTn id uniqueness
    ids = [e.get("id") for e in timing.iter(q("cTn"))]
    seen, dups = set(), set()
    for i in ids:
        if i in seen:
            dups.add(i)
        seen.add(i)
    if dups:
        problems.append(f"{ctx}: duplicate cTn id(s): {sorted(dups)}")
    # 7+8. preset nesting / preset-par leaf purity
    for e in timing.iter(q("cTn")):
        if e.get("presetID") is None:
            continue
        for d in e.iter(q("cTn")):
            if d is not e and d.get("presetID") is not None:
                problems.append(
                    f"{ctx}: nested preset cTn — preset id={e.get('id')} "
                    f"contains preset id={d.get('id')} (presets must not nest)")
                break
        lst = _first(e, "childTnLst")
        if lst is not None:
            for c in lst:
                if isinstance(c.tag, str) and lname(c) not in LEAF_BEHAVIOURS:
                    problems.append(
                        f"{ctx}: preset cTn id={e.get('id')} childTnLst "
                        f"holds <p:{lname(c)}> (leaf behaviours only)")
                    break
    # locate mainSeq
    main_seq = None
    for e in timing.iter(q("cTn")):
        if e.get("nodeType") == "mainSeq":
            main_seq = e
            break
    if main_seq is None:
        problems.append(f"{ctx}: no cTn with nodeType=mainSeq")
        return
    grp_owner = {}   # grpId -> id(group par) for check 11
    for step_par in _child_pars(main_seq):
        sctn = _ctn_of(step_par)
        sconds = _conds(sctn)
        is_click = any(c.get("evt") == "onClick" for c in sconds)
        if is_click and not any(
                _first(c, "tgtEl") is not None
                and _first(_first(c, "tgtEl"), "sldTgt") is not None
                for c in sconds if c.get("evt") == "onClick"):
            problems.append(
                f"{ctx}: click step cTn id={sctn.get('id')} onClick cond "
                f"lacks tgtEl/sldTgt")
        groups = _child_pars(sctn)
        n_click_eff = n_after_eff = 0
        for gi, gpar in enumerate(groups):
            gctn = _ctn_of(gpar)
            if gctn is None:
                problems.append(f"{ctx}: group par without cTn in step "
                                f"id={sctn.get('id')}")
                continue
            if gctn.get("presetID") is not None:
                problems.append(
                    f"{ctx}: group par cTn id={gctn.get('id')} carries "
                    f"presetID (group pars must be plain)")
            if is_click and gi == 0:
                bound = False
                for c in _conds(gctn):
                    if c.get("evt") == "onClick":
                        t = _first(c, "tgtEl")
                        sp = _first(t, "spTgt") if t is not None else None
                        if sp is not None and sp.get("spid") in shape_ids:
                            bound = True
                if not bound:
                    problems.append(
                        f"{ctx}: first group of click step id="
                        f"{sctn.get('id')} lacks onClick cond bound to a "
                        f"shape spTgt")
            grp_ids_here = set()
            for ppar in _child_pars(gctn):
                pctn = _ctn_of(ppar)
                if pctn is None or pctn.get("presetID") is None:
                    problems.append(
                        f"{ctx}: par under group cTn id={gctn.get('id')} "
                        f"is not a preset par (extra/missing level)")
                    continue
                nt = pctn.get("nodeType")
                if nt == "clickEffect":
                    n_click_eff += 1
                elif nt == "afterEffect":
                    n_after_eff += 1
                elif nt != "withEffect":
                    problems.append(
                        f"{ctx}: preset cTn id={pctn.get('id')} has "
                        f"nodeType={nt!r} (clickEffect/withEffect/"
                        f"afterEffect only)")
                gid = pctn.get("grpId")
                grp_ids_here.add(gid)
                owner = grp_owner.setdefault(gid, gpar)
                if owner is not gpar:
                    problems.append(
                        f"{ctx}: grpId={gid} reused by two different "
                        f"group pars")
            if len(grp_ids_here) > 1:
                problems.append(
                    f"{ctx}: group par cTn id={gctn.get('id')} preset "
                    f"pars disagree on grpId: {sorted(grp_ids_here)}")
        if is_click:
            if n_click_eff != 1:
                problems.append(
                    f"{ctx}: click step id={sctn.get('id')} has "
                    f"{n_click_eff} clickEffect preset pars (exactly 1)")
            if n_after_eff:
                problems.append(
                    f"{ctx}: click step id={sctn.get('id')} contains "
                    f"afterEffect preset par(s)")
        else:
            if n_click_eff:
                problems.append(
                    f"{ctx}: auto step id={sctn.get('id')} contains "
                    f"clickEffect preset par(s)")
            if (n_click_eff + n_after_eff) and n_after_eff != 1:
                problems.append(
                    f"{ctx}: auto step id={sctn.get('id')} has "
                    f"{n_after_eff} afterEffect preset pars (exactly 1)")

def main():
    ok = True
    for path in sys.argv[1:]:
        slides, problems = check_file(path)
        if problems:
            ok = False
            print(f"FAIL {path} ({len(slides)} slides, {len(problems)} problems)")
            for p in problems[:20]:
                print(f"  - {p}")
            if len(problems) > 20:
                print(f"  ... and {len(problems) - 20} more")
        else:
            print(f"PASS {path} ({len(slides)} slides: order + targets strict-clean)")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
