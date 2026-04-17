import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.loaders import EPUBLoader, PDFLoader

SUPPORTED_EXTENSIONS = {".pdf", ".epub"}

# Words that are too generic to form meaningful subject directory names.
_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "need",
        "programming",
        "development",
        "introduction",
        "guide",
        "using",
        "course",
        "tutorial",
        "handbook",
        "edition",
        "volume",
        "practical",
    }
)


def _slugify(text: str) -> str:
    """Convert text to a snake_case slug suitable as a directory name."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def _subject_with_claude(title: str, content_preview: str) -> Optional[str]:
    """Determine a subject directory name from ebook title and content.

    Tries the configured LLM when an API key is available; otherwise falls
    back to keyword extraction from the provided text.
    """
    # --- LLM path -------------------------------------------------------
    try:
        from src.config import settings  # noqa: PLC0415

        api_key = os.getenv("ANTHROPIC_API_KEY") or getattr(
            settings, "anthropic_api_key", None
        )
        if api_key:
            from langchain_anthropic import ChatAnthropic  # noqa: PLC0415
            from langchain_core.prompts import ChatPromptTemplate  # noqa: PLC0415

            llm = ChatAnthropic(
                api_key=api_key,
                model_name=getattr(settings, "model_name", "claude-3-haiku-20240307"),
                temperature=0.1,
                max_tokens=50,
            )
            prompt = ChatPromptTemplate.from_template(
                "Given this ebook title and a short content preview, return ONLY a "
                "concise snake_case directory name (2-3 words max) that describes the "
                "subject area. Examples: python_fundamentals, machine_learning, "
                "data_science, web_development.\n\n"
                "Title: {title}\n"
                "Content preview: {preview}\n\n"
                "Directory name:"
            )
            chain = prompt | llm
            response = chain.invoke({"title": title, "preview": content_preview[:300]})
            raw = response.content.strip().lower()
            # Keep only word characters and underscores
            slug = re.sub(r"[^\w]", "_", raw).strip("_")
            slug = re.sub(r"_+", "_", slug)
            if slug:
                return slug
    except Exception:
        pass

    # --- Keyword-extraction fallback ------------------------------------
    combined = f"{content_preview} {title}"
    words = combined.split()
    seen: set = set()
    meaningful: List[str] = []
    for word in words:
        w = word.lower()
        # Strip punctuation
        w = re.sub(r"[^\w]", "", w)
        if w and w not in _STOP_WORDS and w.isalpha() and len(w) > 2 and w not in seen:
            seen.add(w)
            meaningful.append(w)
        if len(meaningful) == 2:
            break

    if meaningful:
        return "_".join(meaningful)

    return _slugify(title) or None


def organize_books(
    ebooks_dir: Path, copy_files: bool = True
) -> List[Dict[str, Any]]:
    """Organize ebooks in the root of *ebooks_dir* into subject subdirectories.

    Each ebook (and any matching ``.zip`` supplement) is moved or copied into a
    subdirectory whose name is derived from the ebook's subject.

    Args:
        ebooks_dir: Directory that contains the ebooks to organize.
        copy_files: When *True* files are copied; when *False* they are moved.

    Returns:
        A list of result dicts, one per organized ebook, with keys
        ``ebook`` (title), ``file`` (filename only), ``subject`` (directory
        name), and ``destination`` (full path to the subject directory).
    """
    pdf_loader = PDFLoader()
    epub_loader = EPUBLoader()

    results: List[Dict[str, Any]] = []

    ebook_files = sorted(
        [
            f
            for f in ebooks_dir.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ],
        key=lambda p: p.name.lower(),
    )

    for ebook_file in ebook_files:
        try:
            if ebook_file.suffix.lower() == ".epub":
                content, metadata = epub_loader.load(str(ebook_file))
            else:
                content, metadata = pdf_loader.load(str(ebook_file))
                ebook_file = Path(metadata.get("file_path", str(ebook_file)))

            title = metadata.get("title") or ebook_file.stem
            content_preview = content[:500] if content else ""

            subject = _subject_with_claude(title, content_preview) or _slugify(title)

            dest_dir = ebooks_dir / subject
            dest_dir.mkdir(parents=True, exist_ok=True)

            dest_file = dest_dir / ebook_file.name
            if copy_files:
                shutil.copy2(str(ebook_file), str(dest_file))
            else:
                ebook_file.rename(dest_file)

            # Handle matching zip supplement
            zip_file = ebook_file.with_suffix(".zip")
            if zip_file.exists():
                dest_zip = dest_dir / zip_file.name
                if copy_files:
                    shutil.copy2(str(zip_file), str(dest_zip))
                else:
                    zip_file.rename(dest_zip)

            results.append(
                {
                    "ebook": title,
                    "file": ebook_file.name,
                    "subject": subject,
                    "destination": str(dest_dir),
                }
            )

        except Exception as exc:
            print(f"⚠️  Could not organize {ebook_file.name}: {exc}")

    return results
