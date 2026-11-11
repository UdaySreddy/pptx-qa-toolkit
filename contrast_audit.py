#!/usr/bin/env python3
"""WCAG contrast audit for slide palettes (QA gate evidence tool).

Usage:
  contrast_audit.py FG,BG[,label] [FG,BG[,label] ...]
  contrast_audit.py --large FG,BG[,label] ...   # judge pairs as large text

Thresholds (WCAG 2.x): normal text >= 4.5:1, large text >= 3.0:1.
Exit code 0 if every pair passes its threshold, 1 otherwise.
Stdlib only.
"""
import sys


def _lum(hexv: str) -> float:
    h = hexv.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    la, lb = _lum(fg), _lum(bg)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def main(argv) -> int:
    large = "--large" in argv
    pairs = [a for a in argv[1:] if not a.startswith("--")]
    if not pairs:
        print(__doc__)
        return 2
    threshold = 3.0 if large else 4.5
    kind = "large" if large else "normal"
    failed = 0
    for spec in pairs:
        parts = spec.split(",")
        fg, bg = parts[0], parts[1]
        label = parts[2] if len(parts) > 2 else f"{fg} on {bg}"
        r = ratio(fg, bg)
        ok = r >= threshold
        failed += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {r:5.2f}:1  ({kind} text, needs "
              f"{threshold}:1)  {label}")
    print(f"\n{len(pairs) - failed}/{len(pairs)} pairs pass ({kind} text).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
