import unittest

from src.graph import KnowledgeGraph
from src.models import Ebook


class KnowledgeGraphSubjectTests(unittest.TestCase):
    def test_knowledge_graph_sets_subject_on_ebook_nodes(self):
        kg = KnowledgeGraph(subject="python")
        ebook = Ebook(
            title="Python Basics",
            author="Author",
            file_path="ebooks/python/python_basics.pdf",
            difficulty_level="beginner",
        )

        kg.add_ebook(ebook)

        self.assertEqual(kg.subject, "python")
        self.assertEqual(kg.graph.nodes["Python Basics"]["subject"], "python")


if __name__ == "__main__":
    unittest.main()
