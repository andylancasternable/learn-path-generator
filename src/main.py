from pathlib import Path
from typing import List, Optional, Tuple

from src.analyzers import ContentAnalyzer
from src.book_discovery import list_ebook_files
from src.ebook_pipeline import load_and_analyze_ebooks
from src.graph import KnowledgeGraph, PathGenerator
from src.loaders import EPUBLoader, PDFLoader


def find_ebook_files(directory: Path) -> List[Path]:
    """Find supported ebook files in a directory."""
    return list_ebook_files(directory)


def discover_subject_folders(ebooks_dir: Path) -> List[Tuple[Optional[str], Path, List[Path]]]:
    """
    Discover subject folders and root-level ebooks.

    Returns tuples of: (subject_name, folder_path, ebook_files)
    subject_name is None for root-level ebooks in ./ebooks.
    """
    subjects: List[Tuple[Optional[str], Path, List[Path]]] = []
    root_files = find_ebook_files(ebooks_dir)
    if root_files:
        subjects.append((None, ebooks_dir, root_files))

    for subdir in sorted((path for path in ebooks_dir.iterdir() if path.is_dir()), key=lambda path: path.name.lower()):
        subjects.append((subdir.name, subdir, find_ebook_files(subdir)))

    return subjects


def display_subject_name(subject_name: Optional[str]) -> str:
    return subject_name or "general"


def main():
    """Main execution function."""
    print("🚀 Learning Path Generator Initialized\n")

    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()

    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)

    subjects = discover_subject_folders(ebooks_dir)
    if not subjects:
        print("⚠️  No ebooks found in ./ebooks directory")
        print("Please add PDF or EPUB files to get started.\n")
        return

    total_ebooks = sum(len(ebook_files) for _, _, ebook_files in subjects)
    print(f"📚 Found {total_ebooks} ebook(s) across {len(subjects)} subject group(s)\n")

    goals = [
        "Master Python programming fundamentals",
        "Learn data science and machine learning basics",
        "Understand web development with Python",
    ]

    for subject_name, _subject_dir, ebook_files in subjects:
        resolved_subject = display_subject_name(subject_name)
        print(f"\n📂 Subject: {resolved_subject}")
        print(f"📚 Found {len(ebook_files)} ebook(s)\n")

        if not ebook_files:
            print(f"⚠️  No ebooks found for subject '{resolved_subject}'")
            continue

        loaded_ebooks = load_and_analyze_ebooks(
            ebook_paths=ebook_files,
            pdf_loader=pdf_loader,
            epub_loader=epub_loader,
            analyzer=analyzer,
        )
        if not loaded_ebooks:
            print(f"❌ No ebooks could be loaded for subject '{resolved_subject}'\n")
            continue

        kg = KnowledgeGraph(subject=resolved_subject)
        print("\n🔗 Building knowledge graph...")
        kg.build_from_ebooks(loaded_ebooks)
        print(
            f"✅ Knowledge graph built with {len(kg.get_all_ebooks())} ebooks and {len(kg.get_all_concepts())} concepts\n"
        )

        path_generator = PathGenerator(kg)
        for goal in goals:
            print(f"🎯 Generating learning path for: {goal}")
            path = path_generator.generate(goal)
            if path.steps:
                print(f"  📖 Recommended {path.ebooks_count} ebook(s)")
                print(f"  ⏱️  Estimated {path.estimated_total_hours} hours\n")
                for step in path.steps:
                    print(f"    Step {step.order}: {step.ebook_title}")
                    print(f"      Topics: {', '.join(step.topics)}")
                    print(f"      Why: {step.rationale}\n")
            else:
                print("  ⚠️  Could not generate path\n")


if __name__ == "__main__":
    main()
