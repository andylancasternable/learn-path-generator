import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.organize_books import organize_books


class OrganizeBooksTests(unittest.TestCase):
    def test_organize_books_moves_ebook_and_matching_zip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ebooks_dir = Path(tmp_dir)
            ebook_path = ebooks_dir / "python_basics.epub"
            zip_path = ebooks_dir / "python_basics.zip"
            ebook_path.write_text("x")
            zip_path.write_text("zip")

            with patch(
                "src.organize_books.EPUBLoader.load",
                return_value=("Python programming fundamentals", {"title": "Python Basics", "author": "Author"}),
            ):
                results = organize_books(ebooks_dir, copy_files=False)

            self.assertEqual(len(results), 1)
            destination_dir = ebooks_dir / "python_fundamentals"
            self.assertTrue((destination_dir / "python_basics.epub").exists())
            self.assertTrue((destination_dir / "python_basics.zip").exists())
            self.assertFalse(ebook_path.exists())
            self.assertFalse(zip_path.exists())


if __name__ == "__main__":
    unittest.main()
