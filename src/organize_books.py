import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from src.book_discovery import list_ebook_files
from src.config import settings
from src.loaders import EPUBLoader, PDFLoader

DEFAULT_SUBJECT = "general_studies"
MAX_DUPLICATE_ATTEMPTS = 100
CONTENT_PREVIEW_LENGTH = 2000
SUBJECT_KEYWORDS = {
    "python_fundamentals": {"python", "programming", "oop"},
    "machine_learning": {"machine learning", "ml", "neural", "deep learning"},
    "data_science": {"data science", "data analysis", "analytics", "statistics"},
    "web_development": {"web", "django", "flask", "api"},
}


def _slugify_subject(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().casefold()).strip("_")
    return normalized or DEFAULT_SUBJECT


def _subject_from_keywords(title: str, content_preview: str) -> str:
    haystack = f"{title}\n{content_preview}".casefold()
    for subject, keywords in SUBJECT_KEYWORDS.items():
        for keyword in keywords:
            if keyword.casefold() in haystack:
                return subject
    return DEFAULT_SUBJECT


def _subject_with_claude(title: str, content_preview: str) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
    if not api_key:
        return None

    prompt = ChatPromptTemplate.from_template(
        """Identify the primary subject category for this ebook.

Title: {title}
Content preview:
{content_preview}

Return ONLY valid JSON:
{{"subject": "short subject label"}}
"""
    )

    llm = ChatAnthropic(
        api_key=api_key,
        model_name=settings.model_name,
        temperature=0.1,
        max_tokens=256,
    )

    try:
        chain = prompt | llm
        response = chain.invoke({"title": title, "content_preview": content_preview[:1500]})
        json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
        if not json_match:
            return None
        parsed = json.loads(json_match.group(0))
        subject = parsed.get("subject")
        return _slugify_subject(subject) if isinstance(subject, str) else None
    except Exception:
        return None


def _resolve_destination(source: Path, destination_dir: Path) -> Path:
    destination = destination_dir / source.name
    if not destination.exists():
        return destination
    for index in range(2, MAX_DUPLICATE_ATTEMPTS + 2):
        candidate = destination_dir / f"{source.stem}_{index}{source.suffix}"
        if not candidate.exists():
            return candidate
    raise OSError(f"Could not resolve unique destination for {source.name} in {destination_dir}")


def _transfer_file(source: Path, destination: Path, copy_files: bool) -> None:
    if copy_files:
        shutil.copy2(source, destination)
    else:
        source.rename(destination)


def organize_books(ebooks_dir: Path, copy_files: bool = False) -> List[dict]:
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()
    results: List[dict] = []

    root_books = list_ebook_files(ebooks_dir)
    for ebook_path in root_books:
        original_path = ebook_path
        if ebook_path.suffix.lower() == ".pdf":
            content, metadata = pdf_loader.load(str(ebook_path))
            ebook_path = Path(metadata.get("file_path", str(ebook_path)))
        else:
            content, metadata = epub_loader.load(str(ebook_path))

        if not content:
            continue

        title = metadata.get("title") or ebook_path.stem
        content_preview = content[:CONTENT_PREVIEW_LENGTH]
        subject = _subject_with_claude(title, content_preview) or _subject_from_keywords(title, content_preview)
        destination_dir = ebooks_dir / _slugify_subject(subject)
        destination_dir.mkdir(exist_ok=True)

        # PDF loader may rename ebook_path, so check both original and current stems for supplements.
        old_supplement = original_path.with_suffix(".zip")
        current_supplement = ebook_path.with_suffix(".zip")
        supplement_file = None
        if current_supplement.exists():
            supplement_file = current_supplement
        elif old_supplement.exists():
            supplement_file = old_supplement

        try:
            destination_file = _resolve_destination(ebook_path, destination_dir)
        except OSError as error:
            print(f"⚠️  {error}")
            continue
        _transfer_file(ebook_path, destination_file, copy_files)

        if supplement_file:
            destination_supplement = destination_dir / f"{destination_file.stem}.zip"
            if not destination_supplement.exists():
                _transfer_file(supplement_file, destination_supplement, copy_files)

        results.append(
            {
                "title": title,
                "subject": destination_dir.name,
                "file": destination_file.name,
                "mode": "copied" if copy_files else "moved",
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-organize root ebooks into subject directories.")
    parser.add_argument("--copy", action="store_true", help="Copy files instead of moving them.")
    args = parser.parse_args()

    ebooks_dir = Path("ebooks")
    ebooks_dir.mkdir(exist_ok=True)
    books = organize_books(ebooks_dir, copy_files=args.copy)

    if not books:
        print("⚠️  No root-level ebooks found to organize.")
        return

    print(f"✅ Organized {len(books)} ebook(s):")
    for book in books:
        print(f"- {book['title']} → {book['subject']}/{book['file']} ({book['mode']})")


if __name__ == "__main__":
    main()
