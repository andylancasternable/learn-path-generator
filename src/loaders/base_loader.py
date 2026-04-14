from abc import ABC, abstractmethod
from src.models import Ebook


class BaseLoader(ABC):
    """Base class for ebook loaders"""
    
    @abstractmethod
    def load(self, file_path: str) -> tuple[str, dict]:
        """
        Load and extract text from ebook
        Returns: (text_content, metadata)
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> list[str]:
        """Return list of supported file formats"""
        pass
