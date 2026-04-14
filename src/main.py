import os
from pathlib import Path
from src.loaders import PDFLoader, EPUBLoader
from src.analyzers import ContentAnalyzer
from src.graph import KnowledgeGraph, PathGenerator
from src.models import Ebook


def main():
    """Main execution function"""
    print("🚀 Learning Path Generator Initialized\n")
    
    # Initialize components
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    analyzer = ContentAnalyzer()
    kg = KnowledgeGraph()
    
    # Find and load ebooks
    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)
    
    ebooks_files = list(ebooks_dir.glob("*.pdf")) + list(ebooks_dir.glob("*.epub"))
    
    if not ebooks_files:
        print("⚠️  No ebooks found in ./ebooks directory")
        print("Please add PDF or EPUB files to get started.\n")
        return
    
    print(f"📚 Found {len(ebooks_files)} ebook(s)\n")
    
    loaded_ebooks = []
    
    # Load and analyze ebooks
    for ebook_path in ebooks_files:
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
        print("❌ No ebooks could be loaded")
        return
    
    # Build knowledge graph
    print(f"\n🔗 Building knowledge graph...")
    kg.build_from_ebooks(loaded_ebooks)
    print(f"✅ Knowledge graph built with {len(kg.get_all_ebooks())} ebooks and {len(kg.get_all_concepts())} concepts\n")
    
    # Generate learning paths
    path_generator = PathGenerator(kg)
    
    # Example learning goals
    goals = [
        "Master Python programming fundamentals",
        "Learn data science and machine learning basics",
        "Understand web development with Python"
    ]
    
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


if __name__ == "__main__":
    main()
