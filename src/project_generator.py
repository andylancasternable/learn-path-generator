import json
import os
import re

from langchain_core.prompts import ChatPromptTemplate

from src.config import settings
from src.llm_factory import get_llm
from src.models import Module, Project


class ProjectGenerator:
    """Create practical module projects that act as final exams."""
    MIN_PROJECT_HOURS = 2

    def __init__(self):
        self.llm = get_llm(temperature=0.4, max_tokens=settings.max_tokens)
        if self.llm:
            self.prompt = ChatPromptTemplate.from_template(
                """Design one hands-on project for this module.

Module title: {module_title}
Module concepts: {concepts}
Module lessons: {lessons}

Return ONLY valid JSON:
{{
  "title": "Project title",
  "duration": "2-3 hours",
  "difficulty": "beginner|intermediate|advanced",
  "brief": "Project brief",
  "requirements": ["..."],
  "learning_outcomes": ["..."],
  "evaluation_checklist": ["..."],
  "success_metrics": ["..."]
}}
"""
            )

    def generate_for_module(self, module: Module) -> Project:
        if self.llm:
            project = self._generate_with_claude(module)
            if project:
                return project
        return self._generate_fallback_project(module)

    def _generate_with_claude(self, module: Module) -> Project | None:
        try:
            chain = self.prompt | self.llm
            response = chain.invoke(
                {
                    "module_title": module.title,
                    "concepts": ", ".join(module.concepts),
                    "lessons": json.dumps([lesson.model_dump() for lesson in module.lessons], indent=2),
                }
            )
            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if not json_match:
                return None
            parsed = json.loads(json_match.group(0))
            chapter_refs = [lesson.chapter_reference for lesson in module.lessons if lesson.chapter_reference]
            return Project(
                title=parsed.get("title", f"Project: {module.title}"),
                concepts_covered=module.concepts,
                duration=parsed.get("duration", "2-3 hours"),
                difficulty=parsed.get("difficulty", self._difficulty_for_module(module.estimated_hours)),
                brief=parsed.get("brief", ""),
                requirements=parsed.get("requirements", []),
                learning_outcomes=parsed.get("learning_outcomes", []),
                evaluation_checklist=parsed.get("evaluation_checklist", []),
                reference_chapters=chapter_refs,
                success_metrics=parsed.get("success_metrics", []),
            )
        except Exception:
            return None

    def _generate_fallback_project(self, module: Module) -> Project:
        difficulty = self._difficulty_for_module(module.estimated_hours)
        chapter_refs = [lesson.chapter_reference for lesson in module.lessons if lesson.chapter_reference]
        concept_text = ", ".join(module.concepts[:4]) if module.concepts else "core module concepts"

        return Project(
            title=f"Project: {module.title} Application",
            concepts_covered=module.concepts,
            duration=self._duration_for_module(module.estimated_hours),
            difficulty=difficulty,
            brief=(
                f"Build a practical project that applies {concept_text}. "
                "The project should solve a real workflow problem and include runnable code."
            ),
            requirements=[
                "Implement core module concepts in working code",
                "Provide clear input/output behavior",
                "Persist or process data in a realistic way",
                "Include basic error handling and edge-case validation",
            ],
            learning_outcomes=[
                "Apply module concepts in a realistic scenario",
                "Improve implementation and debugging skills",
                "Connect theory from lessons to practical results",
            ],
            evaluation_checklist=[
                "Concepts from module are used correctly",
                "Solution meets stated requirements",
                "Code is organized and understandable",
                "Project output is verifiable",
            ],
            reference_chapters=chapter_refs,
            success_metrics=[
                "All functional requirements completed",
                "At least one extension/improvement beyond minimum scope",
            ],
        )

    def _difficulty_for_module(self, estimated_hours: float) -> str:
        if estimated_hours <= 3:
            return "beginner"
        if estimated_hours <= 6:
            return "intermediate"
        return "advanced"

    def _duration_for_module(self, estimated_hours: float) -> str:
        lower = max(self.MIN_PROJECT_HOURS, int(round(estimated_hours)))
        upper = lower + 1
        return f"{lower}-{upper} hours"
