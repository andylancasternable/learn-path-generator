import tempfile
import unittest
from pathlib import Path

from src.book_discovery import discover_subject_ebooks, find_empty_subject_directories, list_ebook_files


class BookDiscoveryTests(unittest.TestCase):
    def test_list_ebook_files_filters_supported_extensions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            directory = Path(tmp_dir)
            (directory / "a.pdf").write_text("pdf")
            (directory / "b.epub").write_text("epub")
            (directory / "c.txt").write_text("txt")

            ebook_names = [path.name for path in list_ebook_files(directory)]
            self.assertEqual(ebook_names, ["a.pdf", "b.epub"])

    def test_discover_subject_ebooks_supports_general_and_subdirs(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ebooks_dir = Path(tmp_dir)
            (ebooks_dir / "root_book.pdf").write_text("root")

            python_dir = ebooks_dir / "python"
            python_dir.mkdir()
            (python_dir / "python_book.epub").write_text("python")

            empty_dir = ebooks_dir / "empty_subject"
            empty_dir.mkdir()

            subjects = discover_subject_ebooks(ebooks_dir)

            self.assertEqual(sorted(subjects.keys()), ["General", "python"])
            self.assertEqual([path.name for path in subjects["General"]], ["root_book.pdf"])
            self.assertEqual([path.name for path in subjects["python"]], ["python_book.epub"])
            self.assertEqual(find_empty_subject_directories(ebooks_dir), ["empty_subject"])


if __name__ == "__main__":
    unittest.main()
