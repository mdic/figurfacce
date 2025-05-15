"""
inline_tag_into_main.py
-----------------------
• clones every source XML into xml_out/
• drops <comments>
• renames root <doc>  →  <text>
• rewrites *every direct child* of <main> (head, p, etc.) into a stream of
  <w pos="…" wclass="…" hw="…" usas="…">token</w> elements
• chooses the pipeline with --lang  (it|en, or any key you map)
"""

from __future__ import annotations
import argparse, pathlib, sys
from lxml import etree
from tqdm import tqdm
import spacy


# ──────────────── 1.  PIPELINE BUILDERS ──────────────────────────────────────
def build_it_pipeline():
    """Italian: default model + PyMUSAS tagger."""
    nlp = spacy.load("it_core_news_sm", exclude=["parser", "ner"])
    dual = spacy.load("it_dual_upos2usas_contextual")
    nlp.add_pipe("pymusas_rule_based_tagger", source=dual)
    return nlp


def build_en_pipeline():
    """English: small model + PyMUSAS tagger."""
    nlp = spacy.load("en_core_web_sm", exclude=["parser", "ner"])
    dual = spacy.load("en_dual_none_contextual")
    nlp.add_pipe("pymusas_rule_based_tagger", source=dual)
    return nlp


LANG2BUILDER = {
    "it": build_it_pipeline,
    "en": build_en_pipeline,
    # add more:  "es": build_es_pipeline,
}
# ─────────────────────────────────────────────────────────────────────────────

SKIP_TAGS = {"graphic"}  # <main> children you don’t want to touch
# TOKEN_ATTRS = ("lemma_", "pos_", "tag_", "dep_")  # still available if needed


# ──────────────── 2.  XML HELPERS ────────────────────────────────────────────
def drop_comments(root: etree._Element) -> None:
    for c in root.xpath(".//comments"):
        p = c.getparent()
        if p is not None:
            p.remove(c)


# ──────────────── 3.  ANNOTATION ─────────────────────────────────────────────
def annotate_block(elem: etree._Element, nlp) -> None:
    """Replace elem’s text with inline <w …> tokens, keeping attributes."""
    text = " ".join(t.strip() for t in elem.itertext() if t.strip())
    if not text:
        return

    doc = nlp(text)
    elem.clear()  # keep elem.attrib
    for i, tok in enumerate(doc, 1):
        w = etree.SubElement(elem, "w")
        w.attrib["pos"] = tok.pos_
        w.attrib["wclass"] = tok.tag_
        w.attrib["hw"] = tok.lemma_
        # PyMUSAS tag list may be empty → safeguard
        w.attrib["usas"] = tok._.pymusas_tags[0] if tok._.get("pymusas_tags") else ""
        w.text = tok.text_with_ws
        # w.text = tok.text
        # w.tail = tok.whitespace_


# ──────────────── 4.  FILE PROCESSING ────────────────────────────────────────
def process_one(src: pathlib.Path, dst: pathlib.Path, nlp) -> None:
    tree = etree.parse(str(src), etree.XMLParser(recover=True))
    root = tree.getroot()

    root.tag = "text"  # rename <doc> → <text>
    drop_comments(root)

    main = root.find(".//main")
    if main is not None:
        for child in main:
            if child.tag not in SKIP_TAGS:
                annotate_block(child, nlp)

    dst.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(dst), encoding="utf-8", pretty_print=True)


# ──────────────── 5.  PIPELINE LOADER ───────────────────────────────────────
def load_pipeline(lang_key: str):
    builder = LANG2BUILDER.get(lang_key)
    if builder:
        try:
            return builder()
        except Exception as e:
            sys.exit(f"❌  Failed building pipeline for '{lang_key}': {e}")
    # fallback: treat key as a model name or path
    try:
        return spacy.load(lang_key)
    except OSError as e:
        sys.exit(f"❌  Cannot load SpaCy model '{lang_key}': {e}")


# ──────────────── 6.  CLI ───────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser(description="Inline token tagging inside <main>")
    ap.add_argument("xml_in", type=pathlib.Path, help="Directory with source XMLs")
    ap.add_argument("xml_out", type=pathlib.Path, help="Directory for tagged XMLs")
    ap.add_argument(
        "-l", "--lang", default="it", help="Language code or model name (default 'it')"
    )
    args = ap.parse_args()

    if not args.xml_in.exists():
        sys.exit(f"Input dir {args.xml_in} does not exist")
    args.xml_out.mkdir(parents=True, exist_ok=True)

    nlp = load_pipeline(args.lang)

    files = sorted(args.xml_in.glob("**/*.xml"))
    if not files:
        sys.exit(f"No .xml files found in {args.xml_in}")

    for src in tqdm(files, desc=f"Annotating ({args.lang})"):
        dst = args.xml_out / src.relative_to(args.xml_in)
        process_one(src, dst, nlp)

    print("✅  Tagged XMLs written to", args.xml_out)


if __name__ == "__main__":
    main()
