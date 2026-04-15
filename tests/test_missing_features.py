import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.analyze_books import _fallback_groupings, _topic_overlap
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
            book_path.write_text("x")
            zip_path.write_text("x")

            supplement = find_matching_supplement(book_path)
            self.assertEqual(supplement, zip_path)

    def test_rename_matching_supplement_after_pdf_rename(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            old_pdf = Path(tmp_dir) / "old-name.pdf"
            new_pdf = Path(tmp_dir) / "New Name.pdf"
            old_zip = Path(tmp_dir) / "old-name.zip"
            old_pdf.write_text("x")
            new_pdf.write_text("x")
            old_zip.write_text("x")

            renamed_zip = rename_matching_supplement_if_needed(old_pdf, new_pdf)

            self.assertEqual(renamed_zip, Path(tmp_dir) / "New Name.zip")
            self.assertTrue((Path(tmp_dir) / "New Name.zip").exists())
            self.assertFalse(old_zip.exists())

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
        self.assertAlmostEqual(_topic_overlap(["Python"], ["python", "ML"]), 0.5)


if __name__ == "__main__":
    unittest.main()
