#!/usr/bin/env python3
"""N-gram overlap audit for source-copying detection (QA gate evidence tool).

Purpose: the house rule is that deliverable text is never copied
from the sources it was grounded in (NCERT / OpenStax / Siyavula —
learn from them, never lift their sentences). This script makes
that rule measurable: it reports how much of a deliverable's text
appears verbatim in a source corpus, and shows the longest
verbatim passages it finds.

Method: both sides are normalised (lowercase, non-alphanumerics
collapsed to spaces) into word tokens; the sources' word n-grams
(default n=8) form one combined set; the overlap is the share of
the deliverable's n-gram occurrences present in that set.

Usage:
  ngram_overlap.py DELIVERABLE.txt SOURCE.txt [SOURCE2.txt ...]
                   [--n 8] [--threshold 0.02]

Threshold: overlap fraction <= threshold passes (default 0.02 = 2%).
Exit code 0 on PASS, 1 on FAIL, 2 on usage error.
Stdlib only.
"""
import re
import sys


def tokens_of(text: str):
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).split()


def ngrams(tokens, n):
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def longest_matches(del_tokens, matched, n, limit=10):
    """Reconstruct the longest verbatim passages from matched n-gram runs.

    `matched[i]` is True when the n-gram starting at token i is in the
    source set. A run of consecutive matched n-grams starting at i and
    ending at j covers tokens i .. j+n-1.
    """
    passages = []
    i = 0
    total = len(matched)
    while i < total:
        if not matched[i]:
            i += 1
            continue
        j = i
        while j + 1 < total and matched[j + 1]:
            j += 1
        passages.append(" ".join(del_tokens[i:j + n]))
        i = j + 1
    passages.sort(key=lambda p: len(p.split()), reverse=True)
    return passages[:limit]


def main(argv) -> int:
    n = 8
    threshold = 0.02
    files = []
    args = argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--n" and i + 1 < len(args):
            try:
                n = int(args[i + 1])
            except ValueError:
                print(__doc__)
                return 2
            i += 2
        elif a == "--threshold" and i + 1 < len(args):
            try:
                threshold = float(args[i + 1])
            except ValueError:
                print(__doc__)
                return 2
            i += 2
        elif a.startswith("--"):
            print(__doc__)
            return 2
        else:
            files.append(a)
            i += 1
    if len(files) < 2 or n < 1:
        print(__doc__)
        return 2

    deliverable_path, source_paths = files[0], files[1:]
    try:
        with open(deliverable_path, encoding="utf-8") as f:
            del_tokens = tokens_of(f.read())
        source_set = set()
        source_words = 0
        for path in source_paths:
            with open(path, encoding="utf-8") as f:
                toks = tokens_of(f.read())
            source_words += len(toks)
            source_set.update(ngrams(toks, n))
    except OSError as e:
        print(f"ERROR: cannot read input: {e}")
        return 2

    del_grams = ngrams(del_tokens, n)
    print(f"Deliverable: {deliverable_path} ({len(del_tokens)} words, "
          f"{len(del_grams)} {n}-grams)")
    print(f"Sources: {len(source_paths)} file(s), {source_words} words, "
          f"{len(source_set)} unique source {n}-grams")

    if not del_grams:
        print(f"\nDeliverable has fewer than {n} words — no {n}-grams to check.")
        print(f"PASS  overlap 0.00% <= threshold {threshold * 100:.2f}%.")
        return 0

    matched = [g in source_set for g in del_grams]
    hits = sum(matched)
    overlap = hits / len(del_grams)
    print(f"Matched {n}-grams: {hits}/{len(del_grams)}")
    print(f"Overlap: {overlap * 100:.2f}%")

    if hits:
        print("\nLongest verbatim matches (words):")
        for p in longest_matches(del_tokens, matched, n):
            print(f"  [{len(p.split())} words] {p}")

    ok = overlap <= threshold
    print(f"\n{'PASS' if ok else 'FAIL'}  overlap {overlap * 100:.2f}% "
          f"{'<=' if ok else '>'} threshold {threshold * 100:.2f}%.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
