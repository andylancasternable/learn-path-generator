import json
import os
import re
from typing import List

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from src.config import settings
from src.models import Chapter, Ebook, Lesson, Module, RecommendedResource


class ModuleGenerator:
    """Break down ebooks into coherent module/lesson plans."""

    def __init__(self):
        self.llm = None
        api_key = os.getenv("ANTHROPIC_API_KEY") or settings.anthropic_api_key
        if api_key:
            self.llm = ChatAnthropic(
                api_key=api_key,
                model_name=settings.model_name,
                temperature=0.3,
                max_tokens=settings.max_tokens,
            )
            self.prompt = ChatPromptTemplate.from_template(
                """You are creating a granular learning plan from ebook chapters.

Ebook title: {ebook_title}
Chapters:
{chapters_json}

Return ONLY valid JSON:
{{
  "modules": [
    {{
      "title": "Module title",
      "description": "short description",
      "lessons": [
        {{
          "title": "Lesson title",
          "chapter_reference": "Chapter 1, pages 1-20",
          "estimated_minutes": 45,
          "concepts": ["concept A", "concept B"]
        }}
      ]
    }}
  ]
}}
"""
            )

    def generate_for_ebook(self, ebook: Ebook) -> List[Module]:
        if self.llm and ebook.chapters:
            modules = self._generate_with_claude(ebook)
            if modules:
                return modules
        return self._generate_fallback_modules(ebook)

    def _generate_with_claude(self, ebook: Ebook) -> List[Module]:
        try:
            chain = self.prompt | self.llm
            response = chain.invoke(
                {
                    "ebook_title": ebook.title,
                    "chapters_json": json.dumps([chapter.model_dump() for chapter in ebook.chapters], indent=2),
                }
            )
            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if not json_match:
                return []
            parsed = json.loads(json_match.group(0))
            modules: List[Module] = []
            for index, module_data in enumerate(parsed.get("modules", []), start=1):
                lessons: List[Lesson] = []
                for lesson_index, lesson_data in enumerate(module_data.get("lessons", []), start=1):
                    lessons.append(
                        Lesson(
                            lesson_id=f"{index}.{lesson_index}",
                            title=lesson_data.get("title", f"Lesson {index}.{lesson_index}"),
                            chapter_reference=lesson_data.get("chapter_reference", ""),
                            estimated_minutes=int(lesson_data.get("estimated_minutes", 45)),
                            concepts=lesson_data.get("concepts", []),
                        )
                    )
                module_concepts = sorted({concept for lesson in lessons for concept in lesson.concepts})
                estimated_hours = round(sum(lesson.estimated_minutes for lesson in lessons) / 60.0, 2)
                modules.append(
                    Module(
                        module_id=f"M{index}",
                        title=module_data.get("title", f"Module {index}"),
                        description=module_data.get("description", ""),
                        lessons=lessons,
                        estimated_hours=estimated_hours,
                        concepts=module_concepts,
                        ebook_title=ebook.title,
                        resources=self._recommended_resources(module_data.get("title", ""), module_concepts),
                    )
                )
            return modules
        except Exception:
            return []

    def _generate_fallback_modules(self, ebook: Ebook) -> List[Module]:
        chapters = ebook.chapters or self._chapters_from_topics(ebook)
        if not chapters:
            return []

        module_size = 2
        modules: List[Module] = []
        for index in range(0, len(chapters), module_size):
            chunk = chapters[index : index + module_size]
            module_number = (index // module_size) + 1
            title = self._derive_module_title(module_number, chunk)
            lessons: List[Lesson] = []
            for lesson_index, chapter in enumerate(chunk, start=1):
                start_page = chapter.start_page or 1
                end_page = chapter.end_page or start_page + 20
                estimated_minutes = max(30, min(90, (end_page - start_page + 1) * 2))
                chapter_ref = f"Chapter {chapter.chapter_number or '?'}"
                if chapter.start_page and chapter.end_page:
                    chapter_ref = f"{chapter_ref}, pages {chapter.start_page}-{chapter.end_page}"
                lessons.append(
                    Lesson(
                        lesson_id=f"{module_number}.{lesson_index}",
                        title=chapter.title,
                        chapter_reference=chapter_ref,
                        estimated_minutes=estimated_minutes,
                        concepts=chapter.concepts or chapter.sections[:3],
                    )
                )

            concepts = sorted(
                {
                    concept
                    for lesson in lessons
                    for concept in lesson.concepts
                    if concept and concept.strip()
                }
            )
            estimated_hours = round(sum(lesson.estimated_minutes for lesson in lessons) / 60.0, 2)
            modules.append(
                Module(
                    module_id=f"M{module_number}",
                    title=title,
                    description=f"Focused study module based on {ebook.title}.",
                    lessons=lessons,
                    estimated_hours=estimated_hours,
                    concepts=concepts,
                    ebook_title=ebook.title,
                    resources=self._recommended_resources(title, concepts),
                )
            )

        return modules

    def _chapters_from_topics(self, ebook: Ebook) -> List[Chapter]:
        chapters: List[Chapter] = []
        for index, topic in enumerate(ebook.topics, start=1):
            chapters.append(
                Chapter(
                    title=topic.name,
                    chapter_number=index,
                    sections=[concept.name for concept in topic.concepts],
                    concepts=[concept.name for concept in topic.concepts],
                )
            )
        return chapters

    def _derive_module_title(self, module_number: int, chapters: List[Chapter]) -> str:
        if not chapters:
            return f"Module {module_number}"
        return f"Module {module_number}: {chapters[0].title}"

    def _recommended_resources(self, module_title: str, concepts: List[str]) -> List[RecommendedResource]:
        query = module_title.replace(" ", "+")
        resources = [
            RecommendedResource(
                title=f"LinkedIn Learning: {module_title}",
                url=f"https://www.linkedin.com/learning/search?keywords={query}",
                resource_type="linkedin_learning",
            ),
            RecommendedResource(
                title=f"YouTube tutorials: {module_title}",
                url=f"https://www.youtube.com/results?search_query={query}",
                resource_type="youtube",
            ),
        ]

        docs_url = "https://docs.python.org/3/" if any("python" in c.casefold() for c in concepts + [module_title]) else ""
        if docs_url:
            resources.append(
                RecommendedResource(
                    title="Official documentation",
                    url=docs_url,
                    resource_type="docs",
                )
            )
        return resources
