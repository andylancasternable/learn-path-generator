#!/usr/bin/env python3
"""CLI script to classify and organise ebooks by subject.

Scans all PDFs and EPUBs in the ``./ebooks/`` root directory, uses an LLM
(or keyword-extraction fallback) to determine each book's subject, and moves
the file into the appropriate subdirectory:

* ``./ebooks/<subject>/`` is created if it does not already exist.
* Books that are already inside a subdirectory are skipped.
* Progress is saved in ``./ebooks/ebook_manifest.json``.

Usage::

    # Move files into subject subdirectories (default)
    python organize_ebooks.py

    # Copy instead of move (safe to run multiple times)
    python organize_ebooks.py --copy

    # Use a different ebooks directory
    python organize_ebooks.py --dir /path/to/ebooks
"""

import argparse
from pathlib import Path

from src.subject_organizer import SubjectOrganizer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify and organise ebooks by subject.",
    )
    parser.add_argument(
        "--dir",
        default="ebooks",
        metavar="PATH",
        help="Root ebooks directory (default: ./ebooks)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy files instead of moving them",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    ebooks_dir = Path(args.dir)

    print("📚 Ebook Subject Organiser\n")
    print(f"📁 Scanning: {ebooks_dir.resolve()}")
    print(f"📦 Mode: {'copy' if args.copy else 'move'}\n")

    organizer = SubjectOrganizer(ebooks_dir=ebooks_dir, copy_files=args.copy)
    results = organizer.run()

    if not results:
        print("⚠️  No ebooks found in the root of the ebooks directory.")
        print("    (Books already in subdirectories are skipped.)")
        return

    organized = [r for r in results if r["status"] == "organized"]
    errors = [r for r in results if r["status"] == "error"]

    print(f"✅ Processed {len(results)} ebook(s):\n")

    for r in results:
        if r["status"] == "organized":
            conf_pct = int(r["confidence"] * 100)
            related = (
                f"  (related: {', '.join(r['related_subjects'])})"
                if r["related_subjects"]
                else ""
            )
            print(
                f"  📖 {r['file']}\n"
                f"     → {r['subject']}/ (confidence {conf_pct}%){related}"
            )
        else:
            print(f"  ❌ {r['file']}: {r.get('error', 'unknown error')}")

    print(f"\n📊 Summary:")
    print(f"   Organised: {len(organized)}")
    if errors:
        print(f"   Errors:    {len(errors)}")
    print(f"\n💾 Manifest saved to: {ebooks_dir / 'ebook_manifest.json'}\n")


if __name__ == "__main__":
    main()
