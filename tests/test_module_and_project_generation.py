import unittest

from src.models import Chapter, Ebook
from src.module_generator import ModuleGenerator
from src.project_generator import ProjectGenerator


class ModuleAndProjectGenerationTests(unittest.TestCase):
    def test_module_generator_builds_lessons_from_chapters(self):
        ebook = Ebook(
            title="Python Basics",
            author="Author",
            file_path="ebooks/python_basics.pdf",
            difficulty_level="beginner",
            total_pages=120,
            chapters=[
                Chapter(title="Variables and Types", chapter_number=1, start_page=1, end_page=20, concepts=["Variables"]),
                Chapter(title="Functions", chapter_number=2, start_page=21, end_page=45, concepts=["Functions"]),
                Chapter(title="Data Structures", chapter_number=3, start_page=46, end_page=80, concepts=["Lists", "Dicts"]),
            ],
        )

        generator = ModuleGenerator()
        generator.llm = None
        modules = generator.generate_for_ebook(ebook)

        self.assertGreaterEqual(len(modules), 2)
        self.assertEqual(modules[0].lessons[0].lesson_id, "1.1")
        self.assertTrue(modules[0].resources)

    def test_project_generator_creates_project_from_module(self):
        ebook = Ebook(
            title="Python Basics",
            author="Author",
            file_path="ebooks/python_basics.pdf",
            difficulty_level="beginner",
            chapters=[Chapter(title="Variables", chapter_number=1, start_page=1, end_page=20, concepts=["Variables"])],
        )
        module_generator = ModuleGenerator()
        module_generator.llm = None
        module = module_generator.generate_for_ebook(ebook)[0]

        project_generator = ProjectGenerator()
        project_generator.llm = None
        project = project_generator.generate_for_module(module)

        self.assertTrue(project.title.strip())
        self.assertTrue(project.requirements)
        self.assertTrue(project.evaluation_checklist)


if __name__ == "__main__":
    unittest.main()
