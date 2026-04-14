import tempfile
import unittest
from pathlib import Path
import sys
import types


if "langchain.prompts" not in sys.modules:
    prompts_module = types.ModuleType("langchain.prompts")

    class ChatPromptTemplate:
        @staticmethod
        def from_template(_template):
            return object()

    prompts_module.ChatPromptTemplate = ChatPromptTemplate
    sys.modules["langchain.prompts"] = prompts_module

if "langchain_anthropic" not in sys.modules:
    anthropic_module = types.ModuleType("langchain_anthropic")

    class ChatAnthropic:
        def __init__(self, *args, **kwargs):
            pass

    anthropic_module.ChatAnthropic = ChatAnthropic
    sys.modules["langchain_anthropic"] = anthropic_module

from src.graph.knowledge_graph import KnowledgeGraph
from src.main import discover_subject_folders, display_subject_name, find_ebook_files


class SubjectDiscoveryTests(unittest.TestCase):
    def test_find_ebook_files_only_supported_formats(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            (base / "book1.pdf").write_text("x")
            (base / "book2.epub").write_text("x")
            (base / "notes.txt").write_text("x")

            found = find_ebook_files(base)

            self.assertEqual([path.name for path in found], ["book1.pdf", "book2.epub"])

    def test_discover_subject_folders_includes_root_for_backward_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ebooks_dir = Path(tmp_dir)
            (ebooks_dir / "root_book.pdf").write_text("x")

            subjects = discover_subject_folders(ebooks_dir)

            self.assertEqual(len(subjects), 1)
            subject_name, subject_path, files = subjects[0]
            self.assertIsNone(subject_name)
            self.assertEqual(subject_path, ebooks_dir)
            self.assertEqual([file.name for file in files], ["root_book.pdf"])

    def test_discover_subject_folders_includes_subdirectories_even_when_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ebooks_dir = Path(tmp_dir)
            python_dir = ebooks_dir / "python"
            empty_dir = ebooks_dir / "data_science"
            python_dir.mkdir()
            empty_dir.mkdir()
            (python_dir / "intro.pdf").write_text("x")

            subjects = discover_subject_folders(ebooks_dir)

            self.assertEqual(len(subjects), 2)
            self.assertEqual(subjects[0][0], "data_science")
            self.assertEqual([path.name for path in subjects[0][2]], [])
            self.assertEqual(subjects[1][0], "python")
            self.assertEqual([path.name for path in subjects[1][2]], ["intro.pdf"])

    def test_display_subject_name_defaults_to_general(self):
        self.assertEqual(display_subject_name(None), "general")
        self.assertEqual(display_subject_name("python"), "python")

    def test_knowledge_graph_accepts_subject_name(self):
        graph = KnowledgeGraph(subject_name="python")
        self.assertEqual(graph.subject_name, "python")


if __name__ == "__main__":
    unittest.main()
