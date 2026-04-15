from .base_loader import BaseLoader
import PyPDF2
from pathlib import Path
import re


class PDFLoader(BaseLoader):
    """Loads and extracts text from PDF files"""

    INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

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
