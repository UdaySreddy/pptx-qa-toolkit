#!/usr/bin/env python3
"""PPTX structure scan (QA gate evidence tool).

For a .pptx file, reports per slide: shape inventory (types),
whether the slide is FLATTENED (its only content shape is one
picture covering >=90% of the slide and it carries no text),
the font inventory across the deck, and the file's core
properties (author/title/etc. — the metadata identity sweep).

Usage: pptx_scan.py deck.pptx
Exit code 0 if no slide is flattened, 1 if any is, 2 on error.
Requires: python-pptx.
"""
import sys

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE


def main(argv) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    path = argv[1]
    prs = Presentation(path)
    slide_w, slide_h = prs.slide_width, prs.slide_height
    slide_area = slide_w * slide_h
    fonts = set()
    flattened = []
    print(f"File: {path}")
    print(f"Slides: {len(prs.slides)}  Size: {slide_w} x {slide_h} EMU")
    for i, slide in enumerate(prs.slides, 1):
        shapes = list(slide.shapes)
        pics = [s for s in shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE]
        text_shapes = [s for s in shapes if s.has_text_frame and s.text_frame.text.strip()]
        for s in shapes:
            if s.has_text_frame:
                for para in s.text_frame.paragraphs:
                    for run in para.runs:
                        if run.font.name:
                            fonts.add(run.font.name)
        is_flat = False
        if len(shapes) == 1 and len(pics) == 1 and not text_shapes:
            pic = pics[0]
            if (pic.width * pic.height) / slide_area >= 0.90:
                is_flat = True
                flattened.append(i)
        kinds = {}
        for s in shapes:
            kinds[str(s.shape_type)] = kinds.get(str(s.shape_type), 0) + 1
        print(f"  Slide {i}: {len(shapes)} shapes {kinds}"
              f"{'  <-- FLATTENED' if is_flat else ''}")
    cp = prs.core_properties
    print("Fonts used:", ", ".join(sorted(fonts)) or "(none named)")
    print("Core properties: "
          f"author={cp.author!r} last_modified_by={cp.last_modified_by!r} "
          f"title={cp.title!r}")
    if flattened:
        print(f"\nFAIL: flattened slide(s): {flattened}")
        return 1
    print("\nPASS: no flattened slides.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
