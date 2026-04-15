from .base_loader import BaseLoader
import PyPDF2
from pathlib import Path
import re


class PDFLoader(BaseLoader):
    """Loads and extracts text from PDF files"""

    INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
    TITLE_ACRONYMS = {"ai", "api", "aws", "cpu", "css", "html", "http", "https", "json", "ml", "nlp", "pdf", "sql", "ui", "ux"}
    TITLE_WORD_HINTS = {
        "advanced", "algorithms", "analysis", "analytics", "and", "api", "applied", "art", "basics", "beginner",
        "business", "code", "coding", "data", "deep", "design", "development", "engines", "excel", "for",
        "fundamentals", "guide", "handbook", "hands", "in", "introduction", "learning", "low", "machine", "managers",
        "models", "on", "patterns", "power", "practical", "processing", "product", "programming", "python", "rule",
        "science", "scikit", "tensorflow", "the", "to", "users", "with",
    }

    def _normalize_title(self, title: str) -> str:
        """Normalize PDF metadata title to a readable string."""
        if not title:
            return ""
        return " ".join(str(title).replace("\x00", " ").split()).strip()

    def _safe_filename(self, title: str) -> str:
        """Convert a title into a safe filename."""
        safe_title = re.sub(self.INVALID_FILENAME_CHARS, "", title)
        safe_title = re.sub(r"\s+", " ", safe_title).strip().rstrip(".")
        return safe_title

    def _split_concatenated_word(self, token: str) -> list[str]:
        """Split a concatenated lowercase token into likely words."""
        lower_token = token.casefold()
        if len(lower_token) <= 3:
            return [token]

        length = len(lower_token)
        best: list[tuple[int, list[str]]] = [(-10**9, []) for _ in range(length + 1)]
        best[0] = (0, [])

        for start in range(length):
            score, words = best[start]
            if score < -10**8:
                continue
            for end in range(start + 1, min(length, start + 20) + 1):
                piece = lower_token[start:end]
                next_score = score - 6 - len(piece)
                if piece in self.TITLE_WORD_HINTS:
                    next_score = score + 14 - max(0, len(piece) - 6)
                elif piece in self.TITLE_ACRONYMS:
                    next_score = score + 10
                elif len(piece) <= 2:
                    next_score = score - 3

                if next_score > best[end][0]:
                    best[end] = (next_score, words + [piece])

        split_words = best[length][1]
        return split_words if len(split_words) > 1 else [token]

    def _format_title_word(self, word: str) -> str:
        lower_word = word.casefold()
        if lower_word in self.TITLE_ACRONYMS:
            return lower_word.upper()
        return lower_word.capitalize()

    def _title_from_filename(self, file_path: str) -> str:
        """Build a readable title from filename when metadata is missing."""
        stem = Path(file_path).stem
        if not stem:
            return ""

        normalized = re.sub(r"[_\-\.]+", " ", stem)
        normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", normalized)
        raw_tokens = [token for token in normalized.split() if token]
        if not raw_tokens:
            return ""

        split_tokens: list[str] = []
        for token in raw_tokens:
            if token.islower() and len(token) > 8:
                split_tokens.extend(self._split_concatenated_word(token))
            else:
                split_tokens.append(token)

        safe_tokens = [self._safe_filename(token) for token in split_tokens]
        formatted_tokens = [self._format_title_word(token) for token in safe_tokens if token]
        return " ".join(formatted_tokens).strip()

    def _rename_file_to_title(self, file_path: str, title: str) -> str:
        """Rename PDF file to metadata title when possible."""
        current_path = Path(file_path)
        normalized_title = self._normalize_title(title)
        if not normalized_title:
            return str(current_path)

        safe_title = self._safe_filename(normalized_title)
        if not safe_title:
            return str(current_path)

        target_path = current_path.with_name(f"{safe_title}{current_path.suffix}")
        if target_path == current_path or target_path.exists():
            return str(current_path)

        try:
            current_path.rename(target_path)
            return str(target_path)
        except OSError as error:
            print(f"Warning: Could not rename PDF {current_path.name}: {error}")
            return str(current_path)

    def load(self, file_path: str) -> tuple[str, dict]:
        """Extract text and metadata from PDF"""
        try:
            text_content = []
            metadata = {"file_path": file_path}
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                title = ""
                author = ""
                if pdf_reader.metadata:
                    title = self._normalize_title(pdf_reader.metadata.get("/Title", ""))
                    author = self._normalize_title(pdf_reader.metadata.get("/Author", ""))

                metadata.update({
                    "title": title,
                    "author": author,
                    "pages": len(pdf_reader.pages)
                })
                
                # Extract text from all pages
                for page in pdf_reader.pages:
                    page_text = page.extract_text() or ""
                    text_content.append(page_text)
            
            full_text = "\n".join(text_content)

            resolved_title = metadata.get("title", "") or self._title_from_filename(file_path)
            if resolved_title:
                metadata["title"] = resolved_title
            else:
                print(f"Warning: Could not extract title for PDF {Path(file_path).name}; keeping original filename.")

            renamed_path = self._rename_file_to_title(file_path, metadata.get("title", ""))
            metadata["file_path"] = renamed_path
            if renamed_path != file_path:
                metadata["renamed_from"] = file_path
                metadata["renamed_to"] = renamed_path

            return full_text, metadata
        
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
            return "", {}
    
    def get_supported_formats(self) -> list[str]:
        return [".pdf"]
