# PPTX QA Toolkit

A small set of command-line quality-assurance tools for PowerPoint (`.pptx`)
decks, built for teachers and content creators who ship editable slides and
need to be sure a deck will actually open in PowerPoint and read well in a
classroom.

These tools were developed and are used in a real lesson-production pipeline.
Each script is standalone Python 3 and reports a clear PASS/FAIL with reasons.

## Tools

| Script | What it checks |
|---|---|
| `pptx_strict.py` | PresentationML schema-order guard. Catches the defect class that LibreOffice tolerates but PowerPoint rejects with "cannot open": elements written in schema-invalid child order (including animation `<p:timing>` structure, preset nesting, and target resolution). |
| `pptx_scan.py` | Native-shape inventory of a deck: confirms slides are built from native, editable shapes rather than flattened images. |
| `contrast_audit.py` | Colour-contrast audit of slide text/background pairs against WCAG ratios, so text stays readable for every student. |
| `deck_text_diff.py` | Diffs the text of two deck versions (or a deck against a locked script) so no teaching line is silently lost or altered between revisions. |
| `ngram_overlap.py` | N-gram overlap check between a deliverable and its source material, to verify content is original work grounded in — not copied from — the source. |

## Usage

```bash
python3 pptx_strict.py my-deck.pptx
python3 pptx_scan.py my-deck.pptx
python3 contrast_audit.py --help
python3 deck_text_diff.py script.md my-deck.pptx
python3 ngram_overlap.py deliverable.txt source.txt
```

## Requirements

- Python 3.9+
- `python-pptx` for the deck-inspection tools (`pip install python-pptx`)

## Why this exists

A deck that opens in one renderer can still fail in PowerPoint, read poorly
for colour-blind students, or quietly drift away from the approved script.
This toolkit turns those failure modes into automated gates that run before
a deck reaches a classroom.

## License

MIT — see `LICENSE`.
