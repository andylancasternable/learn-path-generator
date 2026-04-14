from pathlib import Path
from src.loaders import PDFLoader, EPUBLoader
from src.analyzers import ContentAnalyzer
from src.graph import KnowledgeGraph, PathGenerator
from src.book_discovery import discover_subject_ebooks, find_empty_subject_directories
from src.ebook_pipeline import load_and_analyze_ebooks


def main():
    """Main execution function"""
    print("🚀 Learning Path Generator Initialized\n")
    
    # Initialize components
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()
    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)

    subject_ebooks = discover_subject_ebooks(ebooks_dir)
    empty_subjects = find_empty_subject_directories(ebooks_dir)

    if not subject_ebooks:
        print("⚠️  No ebooks found in ./ebooks directory")
        print("Please add PDF or EPUB files to get started.\n")
        return

    total_ebooks = sum(len(ebooks) for ebooks in subject_ebooks.values())
    print(f"📚 Found {total_ebooks} ebook(s) across {len(subject_ebooks)} subject group(s)\n")

    if empty_subjects:
        print(f"⚠️  Empty subject folders skipped: {', '.join(empty_subjects)}\n")

    # Example learning goals
    goals = [
        "Master Python programming fundamentals",
        "Learn data science and machine learning basics",
        "Understand web development with Python"
    ]

    for subject_name, ebook_paths in subject_ebooks.items():
        print(f"\n📂 Subject: {subject_name}")
        print(f"📚 Found {len(ebook_paths)} ebook(s)\n")

        loaded_ebooks = load_and_analyze_ebooks(
            ebook_paths=ebook_paths,
            pdf_loader=pdf_loader,
            epub_loader=epub_loader,
            analyzer=analyzer,
        )

        if not loaded_ebooks:
            print(f"❌ No ebooks could be loaded for subject '{subject_name}'\n")
            continue

        kg = KnowledgeGraph(subject=subject_name)
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
