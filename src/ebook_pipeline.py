from pathlib import Path
from typing import List

from src.analyzers import ContentAnalyzer
from src.loaders import EPUBLoader, PDFLoader
from src.models import Ebook


def load_and_analyze_ebooks(
    ebook_paths: List[Path],
    pdf_loader: PDFLoader,
    epub_loader: EPUBLoader,
    analyzer: ContentAnalyzer,
) -> List[Ebook]:
    """Load and analyze ebook files."""
    loaded_ebooks: List[Ebook] = []

    for ebook_path in ebook_paths:
        print(f"Processing: {ebook_path.name}")

        if ebook_path.suffix.lower() == ".pdf":
            content, metadata = pdf_loader.load(str(ebook_path))
        else:
            content, metadata = epub_loader.load(str(ebook_path))

        if not content:
            print(f"  ⚠️  Failed to load {ebook_path.name}")
            continue

        pages_raw = metadata.get("pages")
        try:
            pages = int(pages_raw) if pages_raw is not None else None
        except (TypeError, ValueError):
            pages = None
        ebook = Ebook(
            title=metadata.get("title") or ebook_path.stem,
            author=metadata.get("author", "Unknown"),
            file_path=str(ebook_path),
            difficulty_level="intermediate",
            total_pages=pages,
        )

        print("  🔍 Analyzing content...")
        ebook = analyzer.analyze(ebook, content)
        concepts_count = sum(len(topic.concepts) for topic in ebook.topics)
        print(f"  ✅ Extracted {len(ebook.topics)} topics, {concepts_count} concepts")

        loaded_ebooks.append(ebook)

    return loaded_ebooks
