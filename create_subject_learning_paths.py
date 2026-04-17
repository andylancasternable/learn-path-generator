#!/usr/bin/env python3
"""Generate learning paths for each subject subdirectory under ebooks/.

Supports incremental processing with checkpoint/resume so that large ebook
collections can be handled across multiple runs without repeating work.

Example usage::

    # Process all subjects (pauses gracefully on rate-limit)
    python create_subject_learning_paths.py

    # Resume from where a previous run left off
    python create_subject_learning_paths.py --resume

    # Process only a specific subject
    python create_subject_learning_paths.py --subject machine_learning
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

from src.analyzers import ContentAnalyzer
from src.batch_processor import BatchProcessor, SubjectStatus
from src.book_discovery import list_ebook_files
from src.graph import KnowledgeGraph, PathGenerator
from src.loaders import EPUBLoader, PDFLoader
from src.main import (
    discover_subject_folders,
    display_subject_name,
    rename_matching_supplement_if_needed,
)
from src.models import Ebook

OUTPUT_DIR = Path("output") / "subject_learning_paths"
EBOOKS_DIR = Path("ebooks")

# Seconds to wait before retrying after a rate-limit error.
_RATE_LIMIT_PAUSE = 60


def _load_ebooks_for_subject(
    subject_dir: Path,
    ebook_files: list,
) -> tuple:
    """Load and analyse ebooks for a single subject.

    Returns ``(loaded_ebooks, supplements_by_title)``.
    """
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()

    loaded_ebooks = []
    supplements_by_title = {}

    for ebook_path in ebook_files:
        original_ebook_path = ebook_path
        try:
            if ebook_path.suffix.lower() == ".pdf":
                content, metadata = pdf_loader.load(str(ebook_path))
                renamed_path = Path(metadata.get("file_path", str(ebook_path)))
                if renamed_path != ebook_path:
                    print(f"  📝 Renamed PDF to: {renamed_path.name}")
                ebook_path = renamed_path
            else:
                content, metadata = epub_loader.load(str(ebook_path))

            if not content:
                print(f"  ⚠️  Failed to load {ebook_path.name}")
                continue

            ebook = Ebook(
                title=metadata.get("title") or ebook_path.stem,
                author=metadata.get("author", "Unknown"),
                file_path=str(ebook_path),
                difficulty_level="intermediate",
                total_pages=metadata.get("pages"),
            )

            supplement = rename_matching_supplement_if_needed(
                original_ebook_path, ebook_path
            )
            if supplement:
                supplements_by_title[ebook.title] = supplement.name
                print(f"  📎 Supplementary materials: {supplement.name}")

            print(f"  🔍 Analysing {ebook_path.name} …")
            ebook = analyzer.analyze(ebook, content)
            print(
                f"  ✅ {len(ebook.topics)} topics, "
                f"{sum(len(t.concepts) for t in ebook.topics)} concepts"
            )
            loaded_ebooks.append(ebook)

        except Exception as exc:
            print(f"  ❌ Error loading {ebook_path.name}: {exc}")

    return loaded_ebooks, supplements_by_title


def _generate_paths_for_subject(
    subject_name: str,
    subject_dir: Path,
    ebook_files: list,
    goals: list,
) -> dict:
    """Load ebooks for *subject_name* and generate learning paths for each goal.

    Returns a serialisable dict with all paths and metadata.
    """
    loaded_ebooks, supplements_by_title = _load_ebooks_for_subject(
        subject_dir, ebook_files
    )
    if not loaded_ebooks:
        raise ValueError(f"No ebooks could be loaded for subject '{subject_name}'")

    kg = KnowledgeGraph(subject=subject_name)
    print("\n  🔗 Building knowledge graph …")
    kg.build_from_ebooks(loaded_ebooks)
    print(
        f"  ✅ Graph: {len(kg.get_all_ebooks())} ebooks, "
        f"{len(kg.get_all_concepts())} concepts\n"
    )

    path_generator = PathGenerator(kg)
    paths = []
    for goal in goals:
        print(f"  🎯 Generating path: {goal}")
        path = path_generator.generate(goal)
        if path.steps or path.modules:
            print(
                f"     📖 {path.ebooks_count} ebook(s) · "
                f"⏱️  {path.estimated_total_hours}h · "
                f"📦 {len(path.modules)} module(s)"
            )
            paths.append(path.model_dump())
        else:
            print("     ⚠️  Could not generate path")

    return {
        "subject": subject_name,
        "ebook_count": len(loaded_ebooks),
        "paths": paths,
        "supplements": supplements_by_title,
    }


def _build_subject_goals(subject_name: str) -> list:
    """Return learning goals tailored to the given subject."""
    goal_map = {
        "machine_learning": [
            "Master machine learning concepts and algorithms",
            "Apply machine learning to real-world problems",
        ],
        "data_science": [
            "Become proficient in data science and analytics",
            "Master data wrangling and visualization",
        ],
        "python_fundamentals": [
            "Master Python programming fundamentals",
            "Build Python applications and scripts",
        ],
        "general_studies": [
            "Comprehensive understanding of AI and computing",
        ],
        "web_development": [
            "Build full-stack web applications",
            "Master front-end and back-end web development",
        ],
    }
    return goal_map.get(
        subject_name,
        [f"Master {subject_name.replace('_', ' ')}"],
    )


def _print_separator(title: str = "") -> None:
    line = "=" * 70
    if title:
        print(f"\n{line}")
        print(f"  {title}")
        print(f"{line}")
    else:
        print(f"\n{line}")


def process_all_subjects(
    ebooks_dir: Path,
    processor: BatchProcessor,
    target_subject: Optional[str] = None,
    resume: bool = False,
) -> None:
    """Discover subjects and process each one, saving results incrementally."""
    subjects = discover_subject_folders(ebooks_dir)
    if not subjects:
        print("⚠️  No ebooks found in ./ebooks directory")
        return

    all_subject_names = [display_subject_name(name) for name, _, _ in subjects]

    if target_subject:
        # Validate the requested subject exists
        if target_subject not in all_subject_names:
            print(
                f"❌ Subject '{target_subject}' not found. "
                f"Available: {', '.join(all_subject_names)}"
            )
            sys.exit(1)
        subjects_to_process = [
            (name, path, files)
            for name, path, files in subjects
            if display_subject_name(name) == target_subject
        ]
    elif resume:
        pending = set(processor.get_pending_subjects(all_subject_names))
        subjects_to_process = [
            (name, path, files)
            for name, path, files in subjects
            if display_subject_name(name) in pending
        ]
        if not subjects_to_process:
            print("✅ All subjects already completed — nothing to resume.")
            _print_final_summary(processor)
            return
        completed_count = len(all_subject_names) - len(subjects_to_process)
        print(
            f"▶️  Resuming: {completed_count} already done, "
            f"{len(subjects_to_process)} remaining\n"
        )
    else:
        subjects_to_process = subjects

    total = len(subjects_to_process)
    print(f"📋 Subjects to process: {total}\n")

    for idx, (subject_name, subject_dir, ebook_files) in enumerate(
        subjects_to_process, 1
    ):
        resolved = display_subject_name(subject_name)
        _print_separator(f"[{idx}/{total}] SUBJECT: {resolved.upper()}")

        if not ebook_files:
            print(f"⚠️  No ebooks in this subject — skipping")
            continue

        print(f"📚 {len(ebook_files)} ebook(s) in {subject_dir}\n")

        processor.mark_subject_in_progress(resolved)
        goals = _build_subject_goals(resolved)

        try:
            result = _generate_paths_for_subject(
                resolved, subject_dir, ebook_files, goals
            )
            processor.mark_subject_completed(resolved, result)
            print(
                f"\n  ✅ Saved results for '{resolved}' → "
                f"{processor.output_dir / (resolved + '.json')}"
            )

        except Exception as exc:
            error_msg = str(exc)
            processor.mark_subject_failed(resolved, error_msg)

            if "rate limit" in error_msg.lower() or "429" in error_msg:
                print(
                    f"\n  ⏸️  Rate limit reached after subject '{resolved}'.\n"
                    f"      Wait ~{_RATE_LIMIT_PAUSE}s then run:\n"
                    f"      python create_subject_learning_paths.py --resume"
                )
                time.sleep(_RATE_LIMIT_PAUSE)
            else:
                print(f"\n  ❌ Failed for '{resolved}': {error_msg}")

    _print_final_summary(processor)


def _print_final_summary(processor: BatchProcessor) -> None:
    """Print a summary table and write combined output JSON."""
    summary = processor.get_summary()
    _print_separator("SUMMARY")
    print(f"  Total subjects : {summary['total']}")
    print(f"  ✅ Completed   : {summary['completed']}")
    print(f"  ❌ Failed      : {summary['failed']}")
    print(f"  ⏳ Pending     : {summary['pending']}")

    completed = processor.get_completed_subjects()
    if completed:
        all_results = {}
        for subject in completed:
            data = processor.load_subject_result(subject)
            if data:
                all_results[subject] = data

        combined_path = processor.output_dir / "subject_learning_paths.json"
        combined_path.write_text(
            json.dumps(all_results, indent=2, default=str), encoding="utf-8"
        )
        print(f"\n  📄 Combined output: {combined_path}")

    failed = processor.get_failed_subjects()
    if failed:
        print(
            f"\n  ⚠️  Failed subjects: {', '.join(failed)}\n"
            "      Re-run with --resume once the rate limit resets."
        )
    print()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate subject-based learning paths from your ebook library.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all subjects
  python create_subject_learning_paths.py

  # Resume from where a previous run left off
  python create_subject_learning_paths.py --resume

  # Process only one subject
  python create_subject_learning_paths.py --subject machine_learning
""",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip subjects that have already been completed.",
    )
    parser.add_argument(
        "--subject",
        metavar="NAME",
        default=None,
        help="Process only this subject (use the directory name, e.g. machine_learning).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    print("🚀 Subject Learning Path Generator\n")

    ebooks_dir = EBOOKS_DIR
    ebooks_dir.mkdir(exist_ok=True)

    processor = BatchProcessor(output_dir=OUTPUT_DIR)
    processor.load_manifest()

    process_all_subjects(
        ebooks_dir=ebooks_dir,
        processor=processor,
        target_subject=args.subject,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
