import unittest

from src.analyzers import ContentAnalyzer


class ContentAnalyzerChapterExtractionTests(unittest.TestCase):
    def test_extract_chapters_from_text_fallback(self):
        analyzer = ContentAnalyzer()
        sample = """
        Chapter 1: Python Fundamentals
        Chapter 2: Functions and Control Flow
        Chapter 3: Data Structures
        """

        chapters = analyzer._extract_chapters_from_text(sample, total_pages=90)

        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].title, "Python Fundamentals")
        self.assertEqual(chapters[-1].end_page, 90)


if __name__ == "__main__":
    unittest.main()
