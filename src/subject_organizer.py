"""Subject classifier and organizer for ebooks.

Scans the root ``./ebooks/`` directory, uses an LLM (or keyword fallback) to
classify each book's subject, moves the book into a matching subdirectory, and
maintains an ``ebook_manifest.json`` that tracks all books, their subjects,
organisation status and classification confidence.

Books that are already inside a subdirectory are skipped automatically.

Example::

    organizer = SubjectOrganizer()
    organizer.run()
"""

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.loaders import EPUBLoader, PDFLoader

SUPPORTED_EXTENSIONS = {".pdf", ".epub"}
MANIFEST_FILENAME = "ebook_manifest.json"

# Words too generic to form a meaningful subject directory name.
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
    """Convert *text* to a snake_case slug suitable as a directory name."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text


def _keyword_subject(title: str, content_preview: str) -> Tuple[str, float]:
    """Derive a subject slug from keyword extraction.

    Returns a ``(slug, confidence)`` tuple where confidence is between 0 and 1.
    """
    combined = f"{content_preview} {title}"
    words = combined.split()
    seen: set = set()
    meaningful: List[str] = []
    for word in words:
        w = word.lower()
        w = re.sub(r"[^\w]", "", w)
        if w and w not in _STOP_WORDS and w.isalpha() and len(w) > 2 and w not in seen:
            seen.add(w)
            meaningful.append(w)
        if len(meaningful) == 2:
            break

    if meaningful:
        return "_".join(meaningful), 0.4

    slug = _slugify(title)
    return slug or "general", 0.3


def classify_subject(title: str, content_preview: str) -> Tuple[str, float, List[str]]:
    """Classify an ebook's primary subject using the LLM when available.

    Falls back to keyword extraction when no API key is configured.

    Returns:
        A tuple of ``(primary_subject, confidence, related_subjects)`` where
        *primary_subject* is a snake_case directory slug, *confidence* is a
        float between 0 and 1, and *related_subjects* is a list of related
        subject slugs suggested by the LLM.
    """
    # --- LLM path -----------------------------------------------------------
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
                max_tokens=200,
            )
            prompt = ChatPromptTemplate.from_template(
                "You are a librarian classifying ebooks. Given the title and a short "
                "content preview, return ONLY valid JSON (no markdown) with these keys:\n"
                "  primary: snake_case subject slug (2-3 words, e.g. machine_learning)\n"
                "  confidence: float 0-1 indicating classification confidence\n"
                "  related: list of up to 3 related snake_case subject slugs\n\n"
                "Title: {title}\n"
                "Content preview: {preview}\n\n"
                "JSON:"
            )
            chain = prompt | llm
            response = chain.invoke({"title": title, "preview": content_preview[:400]})
            raw = response.content.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```[a-z]*\n?", "", raw).strip("`").strip()
            parsed = json.loads(raw)

            primary = str(parsed.get("primary", "")).strip().lower()
            primary = re.sub(r"[^\w]", "_", primary).strip("_")
            primary = re.sub(r"_+", "_", primary)

            confidence = float(parsed.get("confidence", 0.7))
            confidence = max(0.0, min(1.0, confidence))

            related_raw = parsed.get("related", [])
            related: List[str] = []
            if isinstance(related_raw, list):
                for item in related_raw:
                    slug = re.sub(r"[^\w]", "_", str(item).lower()).strip("_")
                    slug = re.sub(r"_+", "_", slug)
                    if slug:
                        related.append(slug)

            if primary:
                return primary, confidence, related
    except Exception:
        pass

    # --- Keyword-extraction fallback ----------------------------------------
    slug, confidence = _keyword_subject(title, content_preview)
    return slug, confidence, []


class SubjectOrganizer:
    """Organise root-level ebooks in *ebooks_dir* into subject subdirectories.

    Books already inside a subdirectory are skipped.  Progress is tracked in a
    JSON manifest file so repeated runs only process new files.

    Args:
        ebooks_dir: Path to the root ebooks directory.  Defaults to
            ``./ebooks``.
        copy_files: When ``True`` files are *copied* instead of moved.
            Defaults to ``False`` (move).
    """

    def __init__(
        self,
        ebooks_dir: Path = Path("ebooks"),
        copy_files: bool = False,
    ) -> None:
        self.ebooks_dir = ebooks_dir
        self.copy_files = copy_files
        self.manifest_path = ebooks_dir / MANIFEST_FILENAME
        self._manifest: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Manifest helpers
    # ------------------------------------------------------------------

    def load_manifest(self) -> Dict[str, Any]:
        """Load (or initialise) the manifest from disk."""
        if self.manifest_path.exists():
            try:
                self._manifest = json.loads(
                    self.manifest_path.read_text(encoding="utf-8")
                )
            except Exception:
                self._manifest = {}
        if not self._manifest:
            self._manifest = {
                "books": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        return self._manifest

    def save_manifest(self) -> None:
        """Persist the manifest to disk."""
        self.ebooks_dir.mkdir(parents=True, exist_ok=True)
        self._manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.manifest_path.write_text(
            json.dumps(self._manifest, indent=2, default=str),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> List[Dict[str, Any]]:
        """Classify and organise all root-level ebooks.

        Returns:
            A list of result dicts, one per processed ebook, with keys:
            ``file``, ``title``, ``subject``, ``confidence``,
            ``related_subjects``, ``destination``, and ``status``
            (``"organized"``, ``"skipped"``, or ``"error"``).
        """
        self.ebooks_dir.mkdir(exist_ok=True)
        self.load_manifest()

        pdf_loader = PDFLoader()
        epub_loader = EPUBLoader()

        root_files = sorted(
            [
                f
                for f in self.ebooks_dir.iterdir()
                if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
            ],
            key=lambda p: p.name.lower(),
        )

        results: List[Dict[str, Any]] = []

        for ebook_file in root_files:
            result = self._process_file(ebook_file, pdf_loader, epub_loader)
            results.append(result)

        self.save_manifest()
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_file(
        self,
        ebook_file: Path,
        pdf_loader: PDFLoader,
        epub_loader: EPUBLoader,
    ) -> Dict[str, Any]:
        """Process a single ebook file and return a result dict."""
        try:
            if ebook_file.suffix.lower() == ".epub":
                content, metadata = epub_loader.load(str(ebook_file))
            else:
                content, metadata = pdf_loader.load(str(ebook_file))
                ebook_file = Path(metadata.get("file_path", str(ebook_file)))

            title = metadata.get("title") or ebook_file.stem
            content_preview = content[:500] if content else ""

            primary, confidence, related = classify_subject(title, content_preview)

            dest_dir = self.ebooks_dir / primary
            dest_dir.mkdir(parents=True, exist_ok=True)

            dest_file = dest_dir / ebook_file.name
            if self.copy_files:
                shutil.copy2(str(ebook_file), str(dest_file))
            else:
                ebook_file.rename(dest_file)

            # Handle matching zip supplement
            zip_file = ebook_file.with_suffix(".zip")
            if zip_file.exists():
                dest_zip = dest_dir / zip_file.name
                if self.copy_files:
                    shutil.copy2(str(zip_file), str(dest_zip))
                else:
                    zip_file.rename(dest_zip)

            # Update manifest
            books = self._manifest.setdefault("books", {})
            books[ebook_file.name] = {
                "title": title,
                "file": ebook_file.name,
                "subject": primary,
                "confidence": round(confidence, 3),
                "related_subjects": related,
                "destination": str(dest_dir),
                "status": "organized",
                "organized_at": datetime.now(timezone.utc).isoformat(),
            }

            return {
                "file": ebook_file.name,
                "title": title,
                "subject": primary,
                "confidence": round(confidence, 3),
                "related_subjects": related,
                "destination": str(dest_dir),
                "status": "organized",
            }

        except Exception as exc:
            return {
                "file": ebook_file.name,
                "title": ebook_file.stem,
                "subject": None,
                "confidence": 0.0,
                "related_subjects": [],
                "destination": None,
                "status": "error",
                "error": str(exc),
            }
