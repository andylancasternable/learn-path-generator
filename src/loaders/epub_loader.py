from .base_loader import BaseLoader
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from pathlib import Path


class EPUBLoader(BaseLoader):
    """Loads and extracts text from EPUB files"""
    
    def load(self, file_path: str) -> tuple[str, dict]:
        """Extract text and metadata from EPUB"""
        try:
            book = epub.read_epub(file_path)
            
            # Extract metadata
            metadata = {
                "title": book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else "",
                "author": book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else "",
                "pages": "Unknown"
            }
            
            # Extract text content
            text_content = []
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text_content.append(soup.get_text())
            
            full_text = "\n".join(text_content)
            return full_text, metadata
        
        except Exception as e:
            print(f"Error loading EPUB {file_path}: {e}")
            return "", {}
    
    def get_supported_formats(self) -> list[str]:
        return [".epub"]
