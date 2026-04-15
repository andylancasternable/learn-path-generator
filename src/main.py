from pathlib import Path
from typing import List, Optional, Tuple
from src.loaders import PDFLoader, EPUBLoader
from src.analyzers import ContentAnalyzer
from src.graph import KnowledgeGraph, PathGenerator
from src.models import Ebook


SUPPORTED_FORMATS = (".pdf", ".epub")


def find_ebook_files(directory: Path) -> List[Path]:
    """Find supported ebook files in a directory"""
    ebook_files = []
    for extension in SUPPORTED_FORMATS:
        ebook_files.extend(directory.glob(f"*{extension}"))
    return sorted(ebook_files)


def discover_subject_folders(ebooks_dir: Path) -> List[Tuple[Optional[str], Path, List[Path]]]:
    """Discover subject folders and root-level ebooks.
    
    Returns tuples of: (subject_name, folder_path, ebook_files)
    subject_name is None for root-level ebooks in ./ebooks.
    """
    subjects = []
    root_files = find_ebook_files(ebooks_dir)
    if root_files:
        subjects.append((None, ebooks_dir, root_files))
    
    for subdir in sorted([path for path in ebooks_dir.iterdir() if path.is_dir()]):
        subject_files = find_ebook_files(subdir)
        subjects.append((subdir.name, subdir, subject_files))
    
    return subjects


def display_subject_name(subject_name: Optional[str]) -> str:
    return subject_name or "general"


def main():
    """Main execution function"""
    print("🚀 Learning Path Generator Initialized\n")
    
    # Initialize components
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()
    
    # Find and load ebooks
    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)
    
    subjects = discover_subject_folders(ebooks_dir)

    if not subjects:
        print("⚠️  No ebooks found in ./ebooks directory")
        print("Please add PDF or EPUB files to get started.\n")
        return
    
    # Example learning goals
    goals = [
        "Master Python programming fundamentals",
        "Learn data science and machine learning basics",
        "Understand web development with Python"
    ]

    any_successful_subject = False

    for subject_name, subject_dir, ebook_files in subjects:
        print(f"\n📂 Subject: {display_subject_name(subject_name)}")

        subject_location = "./ebooks" if subject_name is None else f"./ebooks/{subject_name}"

        if not ebook_files:
            print(f"⚠️  No ebooks found in {subject_location} directory")
            continue

        print(f"📚 Found {len(ebook_files)} ebook(s) in {subject_location}")

        loaded_ebooks = []

        # Load and analyze ebooks
        for ebook_path in ebook_files:
            print(f"Processing: {ebook_path.name}")
            
            # Load content based on file type
            if ebook_path.suffix.lower() == ".pdf":
                content, metadata = pdf_loader.load(str(ebook_path))
            else:  # EPUB
                content, metadata = epub_loader.load(str(ebook_path))
            
            if not content:
                print(f"  ⚠️  Failed to load {ebook_path.name}")
                continue
            
            # Create ebook model
            ebook = Ebook(
                title=metadata.get("title") or ebook_path.stem,
                author=metadata.get("author", "Unknown"),
                file_path=str(ebook_path),
                difficulty_level="intermediate",
                total_pages=metadata.get("pages")
            )
            
            # Analyze content
            print(f"  🔍 Analyzing content...")
            ebook = analyzer.analyze(ebook, content)
            print(f"  ✅ Extracted {len(ebook.topics)} topics, {sum(len(t.concepts) for t in ebook.topics)} concepts")
            
            loaded_ebooks.append(ebook)

        if not loaded_ebooks:
            print("❌ No ebooks could be loaded for this subject")
            continue

        any_successful_subject = True
        
        # Build knowledge graph
        print(f"\n🔗 Building knowledge graph...")
        kg = KnowledgeGraph(subject_name=subject_name)
        kg.build_from_ebooks(loaded_ebooks)
        print(f"✅ Knowledge graph built with {len(kg.get_all_ebooks())} ebooks and {len(kg.get_all_concepts())} concepts\n")
        
        # Generate learning paths
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
                print(f"  ⚠️  Could not generate path\n")

    if not any_successful_subject:
        print("❌ No subject had loadable ebooks")


if __name__ == "__main__":
    main()
