import json
import os
import re
from typing import List, Optional

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
                """Design one practical, hands-on project for this module. The project must be specific to the module's concepts — not a generic template — and must produce tangible, verifiable results.

Module title: {module_title}
Module concepts: {concepts}
Module lessons: {lessons}
Estimated module hours: {estimated_hours}

Requirements:
- Give the project a concrete, descriptive title (e.g. "Build a binary classifier with Scikit-learn on the Iris dataset", not "Module Project")
- Scope the work so it fits within the estimated module hours
- Every requirement and success metric must reference at least one module concept by name
- List specific tools and technologies the learner should use
- List tangible deliverables (code files, outputs, reports) the learner will produce

Return ONLY valid JSON:
{{
  "title": "Concrete project title",
  "duration": "X-Y hours",
  "difficulty": "beginner|intermediate|advanced",
  "brief": "One-paragraph description of what the learner will build and why it matters",
  "tools_technologies": ["tool or library name", "..."],
  "requirements": ["Specific requirement referencing a concept", "..."],
  "deliverables": ["Concrete artifact the learner produces", "..."],
  "learning_outcomes": ["Outcome tied to a specific concept", "..."],
  "evaluation_checklist": ["Verifiable check tied to a concept", "..."],
  "success_metrics": ["Measurable criterion that proves concept mastery", "..."]
}}
"""
            )

    def generate_for_module(self, module: Module) -> Project:
        if self.llm:
            project = self._generate_with_claude(module)
            if project:
                return project
        return self._generate_fallback_project(module)

    def _generate_with_claude(self, module: Module) -> Optional[Project]:
        try:
            chain = self.prompt | self.llm
            response = chain.invoke(
                {
                    "module_title": module.title,
                    "concepts": ", ".join(module.concepts),
                    "lessons": json.dumps([lesson.model_dump() for lesson in module.lessons], indent=2),
                    "estimated_hours": module.estimated_hours,
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
                tools_technologies=parsed.get("tools_technologies", []),
                requirements=parsed.get("requirements", []),
                deliverables=parsed.get("deliverables", []),
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
        concepts = module.concepts[:4] if module.concepts else []
        concept_text = ", ".join(concepts) if concepts else "core module concepts"
        primary_concept = concepts[0] if concepts else module.title
        secondary_concepts = concepts[1:] if len(concepts) > 1 else []

        tools = self._infer_tools(module.concepts)

        requirements = [
            f"Apply {primary_concept} to solve a realistic problem",
        ]
        if secondary_concepts:
            requirements.append(
                f"Integrate {' and '.join(secondary_concepts)} into the solution"
            )
        requirements += [
            "Provide runnable code with clear input/output behavior",
            "Handle at least two edge cases or error conditions",
        ]

        deliverables = [
            f"Working implementation demonstrating {primary_concept}",
            "README or inline comments explaining key decisions",
        ]
        if tools:
            deliverables.append(f"Code using {tools[0]}")

        success_metrics = [
            f"Implementation correctly applies {primary_concept}",
            "All stated requirements are met and verifiable",
            "At least one improvement or extension beyond minimum scope",
        ]

        return Project(
            title=f"{primary_concept} in Practice: {module.title}",
            concepts_covered=module.concepts,
            duration=self._duration_for_module(module.estimated_hours),
            difficulty=difficulty,
            brief=(
                f"Build a practical project that applies {concept_text} from the "
                f"{module.title} module. The project must produce runnable code that "
                "solves a real-world problem and demonstrates mastery of the module concepts."
            ),
            tools_technologies=tools,
            requirements=requirements,
            deliverables=deliverables,
            learning_outcomes=[
                f"Demonstrate practical use of {primary_concept} in a working programme",
                "Translate lesson concepts into verifiable, runnable code",
                "Connect theory from lessons to observable results",
            ],
            evaluation_checklist=[
                f"{primary_concept} is applied correctly and intentionally",
                "Solution meets all stated requirements",
                "Code is organised, readable, and well-commented",
                "Deliverables are present and verifiable",
            ],
            reference_chapters=chapter_refs,
            success_metrics=success_metrics,
        )

    def _infer_tools(self, concepts: List[str]) -> List[str]:
        """Return a short list of plausible tools based on concept keywords."""
        concept_str = " ".join(concepts).lower()
        tools: List[str] = []
        if any(kw in concept_str for kw in ("machine learning", "classification", "regression", "neural", "deep learning", "model", "training")):
            tools += ["Python", "Scikit-learn", "NumPy", "pandas"]
        elif any(kw in concept_str for kw in ("data", "dataframe", "csv", "analysis", "statistics", "pandas")):
            tools += ["Python", "pandas", "matplotlib"]
        elif any(kw in concept_str for kw in ("web", "http", "api", "rest", "flask", "django", "fastapi")):
            tools += ["Python", "Flask" if "flask" in concept_str else "FastAPI"]
        elif any(kw in concept_str for kw in ("sql", "database", "query", "relational")):
            tools += ["Python", "SQLite", "SQLAlchemy"]
        elif any(kw in concept_str for kw in ("javascript", "typescript", "node", "react", "frontend")):
            tools += ["Node.js", "JavaScript"]
        elif any(kw in concept_str for kw in ("java", "spring", "maven")):
            tools += ["Java", "Maven"]
        else:
            tools += ["Python"]
        return tools

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
