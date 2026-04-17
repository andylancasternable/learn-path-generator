import unittest

from src.models import Chapter, Ebook, Lesson, Module
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

    def test_fallback_project_includes_new_fields(self):
        """Fallback project should populate tools_technologies and deliverables."""
        module = Module(
            module_id="1",
            title="Machine Learning Fundamentals",
            description="Intro to ML",
            lessons=[
                Lesson(
                    lesson_id="1.1",
                    title="Supervised Learning",
                    chapter_reference="Chapter 1, pages 1-20",
                    estimated_minutes=45,
                    concepts=["supervised learning", "classification"],
                )
            ],
            estimated_hours=4,
            concepts=["supervised learning", "classification", "regression"],
        )

        project_generator = ProjectGenerator()
        project_generator.llm = None
        project = project_generator.generate_for_module(module)

        self.assertTrue(project.tools_technologies, "tools_technologies should be non-empty")
        self.assertTrue(project.deliverables, "deliverables should be non-empty")
        self.assertTrue(project.success_metrics, "success_metrics should be non-empty")

    def test_fallback_project_title_references_primary_concept(self):
        """Fallback title should include the primary concept, not be a generic placeholder."""
        module = Module(
            module_id="2",
            title="Data Analysis",
            description="Working with data",
            lessons=[],
            estimated_hours=3,
            concepts=["dataframe", "csv", "analysis"],
        )

        project_generator = ProjectGenerator()
        project_generator.llm = None
        project = project_generator.generate_for_module(module)

        # Title should not be the old generic "Project: <title> Application" pattern
        self.assertNotIn("Application", project.title)
        # Should reference the primary concept
        self.assertIn("dataframe", project.title.lower())

    def test_fallback_requirements_reference_concepts(self):
        """Fallback requirements should reference specific module concepts."""
        module = Module(
            module_id="3",
            title="SQL Basics",
            description="Intro to SQL",
            lessons=[],
            estimated_hours=2,
            concepts=["sql", "query", "relational"],
        )

        project_generator = ProjectGenerator()
        project_generator.llm = None
        project = project_generator.generate_for_module(module)

        combined = " ".join(project.requirements).lower()
        self.assertIn("sql", combined, "Requirements should reference the primary concept")

    def test_infer_tools_machine_learning(self):
        generator = ProjectGenerator()
        generator.llm = None
        tools = generator._infer_tools(["supervised learning", "classification", "machine learning"])
        self.assertIn("Scikit-learn", tools)

    def test_infer_tools_web(self):
        generator = ProjectGenerator()
        generator.llm = None
        tools = generator._infer_tools(["REST api", "http", "web"])
        self.assertTrue(len(tools) > 0)
        self.assertIn("Python", tools)

    def test_infer_tools_fallback_to_python(self):
        generator = ProjectGenerator()
        generator.llm = None
        tools = generator._infer_tools(["some unknown concept"])
        self.assertEqual(tools, ["Python"])


if __name__ == "__main__":
    unittest.main()
