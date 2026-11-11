#!/usr/bin/env python3
"""Deck text-fidelity diff (QA gate evidence tool).

Converts a finished .pptx to Markdown text (Microsoft MarkItDown)
and diffs its non-empty lines against the LOCKED slides_markdown
source the deck was built from. Any line present in only one side
is reported: lines in the deck but not the source are possible
AI-added claims; lines in the source but not the deck are dropped
content. The gate requires 0 unexplained diffs.

Usage: deck_text_diff.py deck.pptx locked_slides.md
Exit code 0 if the line sets match exactly, 1 otherwise.
Requires: markitdown[pptx].
"""
import sys

from markitdown import MarkItDown


def lines_of(text: str):
    out = []
    for raw in text.splitlines():
        stripped = raw.strip()
        # Skip converter artefacts, not content: MarkItDown's slide
        # separator comments and image-reference lines.
        if stripped.startswith("<!--") or stripped.startswith("!["):
            continue
        line = " ".join(raw.replace("#", " ").split())
        if line:
            out.append(line)
    return out


def main(argv) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    deck_path, locked_path = argv[1], argv[2]
    md = MarkItDown(enable_plugins=False)
    deck_text = md.convert(deck_path).markdown
    with open(locked_path, encoding="utf-8") as f:
        locked_text = f.read()
    deck_lines = lines_of(deck_text)
    locked_lines = lines_of(locked_text)
    deck_set, locked_set = set(deck_lines), set(locked_lines)
    only_deck = [l for l in deck_lines if l not in locked_set]
    only_locked = [l for l in locked_lines if l not in deck_set]
    print(f"Deck lines: {len(deck_lines)}  Locked-source lines: {len(locked_lines)}")
    for l in only_deck:
        print(f"  IN DECK ONLY (possible added content): {l}")
    for l in only_locked:
        print(f"  IN SOURCE ONLY (possible dropped content): {l}")
    if only_deck or only_locked:
        print(f"\nFAIL: {len(only_deck)} deck-only, {len(only_locked)} source-only lines.")
        return 1
    print("\nPASS: deck text matches the locked source line for line.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
