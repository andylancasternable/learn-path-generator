from .base_loader import BaseLoader
import PyPDF2
from pathlib import Path


class PDFLoader(BaseLoader):
    """Loads and extracts text from PDF files"""
    
    def load(self, file_path: str) -> tuple[str, dict]:
        """Extract text and metadata from PDF"""
        try:
            text_content = []
            metadata = {}
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                if pdf_reader.metadata:
                    metadata = {
                        "title": pdf_reader.metadata.get("/Title", ""),
                        "author": pdf_reader.metadata.get("/Author", ""),
                        "pages": len(pdf_reader.pages)
                    }
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf_reader.pages):
                    text_content.append(page.extract_text())
            
            full_text = "\n".join(text_content)
            return full_text, metadata
        
        except Exception as e:
            print(f"Error loading PDF {file_path}: {e}")
            return "", {}
    
    def get_supported_formats(self) -> list[str]:
        return [".pdf"]
