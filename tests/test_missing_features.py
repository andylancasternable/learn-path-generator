import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analyze_books import _fallback_groupings
from src.loaders.pdf_loader import PDFLoader
from src.main import find_matching_supplement, rename_matching_supplement_if_needed


class FakePage:
    def extract_text(self):
        return "example text"


class FakePdfReader:
    metadata = {
        "/Title": "AI and Business Rule Engines for Excel Power Users",
        "/Author": "Example Author",
    }
    pages = [FakePage()]


class FakePdfReaderNoMetadata:
    metadata = {}
    pages = [FakePage()]


class MissingFeatureTests(unittest.TestCase):
    def test_pdf_loader_renames_pdf_using_metadata_title(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "aiandbusinessruleenginesforexcelpowerusers.pdf"
            pdf_path.write_bytes(b"fake")

            loader = PDFLoader()
            with patch("src.loaders.pdf_loader.PyPDF2.PdfReader", return_value=FakePdfReader()):
                _content, metadata = loader.load(str(pdf_path))

            expected_name = "AI and Business Rule Engines for Excel Power Users.pdf"
            self.assertEqual(Path(metadata["file_path"]).name, expected_name)
            self.assertTrue((Path(tmp_dir) / expected_name).exists())
            self.assertFalse(pdf_path.exists())
            self.assertEqual(metadata["title"], "AI and Business Rule Engines for Excel Power Users")

    def test_find_matching_supplement_by_filename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            book_path = Path(tmp_dir) / "My Book.pdf"
            zip_path = Path(tmp_dir) / "My Book.zip"
            book_path.touch()
            zip_path.touch()

            supplement = find_matching_supplement(book_path)
            self.assertEqual(supplement, zip_path)

    def test_rename_matching_supplement_after_pdf_rename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            old_pdf = Path(tmp_dir) / "old-name.pdf"
            new_pdf = Path(tmp_dir) / "New Name.pdf"
            old_zip = Path(tmp_dir) / "old-name.zip"
            old_pdf.touch()
            new_pdf.touch()
            old_zip.touch()

            renamed_zip = rename_matching_supplement_if_needed(old_pdf, new_pdf)

            self.assertEqual(renamed_zip, Path(tmp_dir) / "New Name.zip")
            self.assertTrue((Path(tmp_dir) / "New Name.zip").exists())
            self.assertFalse(old_zip.exists())

    def test_pdf_loader_parses_concatenated_filename_when_metadata_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "aiproductmanagershandbook.pdf"
            pdf_path.write_bytes(b"fake")

            loader = PDFLoader()
            with patch("src.loaders.pdf_loader.PyPDF2.PdfReader", return_value=FakePdfReaderNoMetadata()):
                _content, metadata = loader.load(str(pdf_path))

            expected_name = "AI Product Managers Handbook.pdf"
            self.assertEqual(Path(metadata["file_path"]).name, expected_name)
            self.assertEqual(metadata["title"], "AI Product Managers Handbook")
            self.assertTrue((Path(tmp_dir) / expected_name).exists())
            self.assertFalse(pdf_path.exists())

    def test_pdf_loader_parses_camel_case_filename_when_metadata_missing(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            pdf_path = Path(tmp_dir) / "practicalDeepLearning.pdf"
            pdf_path.write_bytes(b"fake")

            loader = PDFLoader()
            with patch("src.loaders.pdf_loader.PyPDF2.PdfReader", return_value=FakePdfReaderNoMetadata()):
                _content, metadata = loader.load(str(pdf_path))

            expected_name = "Practical Deep Learning.pdf"
            self.assertEqual(Path(metadata["file_path"]).name, expected_name)
            self.assertEqual(metadata["title"], "Practical Deep Learning")

    def test_fallback_groupings_uses_topic_overlap(self):
        books = [
            {"title": "Book A", "topics": ["Python", "Data"]},
            {"title": "Book B", "topics": ["python", "ML"]},
            {"title": "Book C", "topics": ["Excel"]},
        ]

        groups = _fallback_groupings(books)
        grouped_titles = [tuple(group["books"]) for group in groups]

        self.assertIn(("Book A", "Book B"), grouped_titles)
        self.assertIn(("Book C",), grouped_titles)


if __name__ == "__main__":
    unittest.main()
