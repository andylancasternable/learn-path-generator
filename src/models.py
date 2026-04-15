from pydantic import BaseModel
from typing import List, Optional


class Concept(BaseModel):
    name: str
    difficulty_level: str  # beginner, intermediate, advanced
    prerequisites: List[str] = []
    description: Optional[str] = None


class Topic(BaseModel):
    name: str
    concepts: List[Concept] = []
    description: Optional[str] = None


class Ebook(BaseModel):
    title: str
    author: str
    file_path: str
    difficulty_level: str  # beginner, intermediate, advanced
    topics: List[Topic] = []
    total_pages: Optional[int] = None
    summary: Optional[str] = None
    chapters: List["Chapter"] = []


class PathStep(BaseModel):
    order: int
    ebook_title: str
    topics: List[str]
    estimated_hours: float
    rationale: str


class RecommendedResource(BaseModel):
    title: str
    url: str
    resource_type: str  # linkedin_learning, youtube, docs


class Chapter(BaseModel):
    title: str
    chapter_number: Optional[int] = None
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    sections: List[str] = []
    concepts: List[str] = []


class Lesson(BaseModel):
    lesson_id: str
    title: str
    chapter_reference: str
    estimated_minutes: int
    concepts: List[str] = []


class Project(BaseModel):
    title: str
    concepts_covered: List[str]
    duration: str
    difficulty: str  # beginner, intermediate, advanced
    brief: str
    requirements: List[str] = []
    learning_outcomes: List[str] = []
    evaluation_checklist: List[str] = []
    reference_chapters: List[str] = []
    success_metrics: List[str] = []


class Module(BaseModel):
    module_id: str
    title: str
    description: str
    lessons: List[Lesson] = []
    estimated_hours: float
    concepts: List[str] = []
    ebook_title: Optional[str] = None
    resources: List[RecommendedResource] = []
    project: Optional[Project] = None


class LearningPath(BaseModel):
    goal: str
    ebooks_count: int
    estimated_total_hours: float
    steps: List[PathStep] = []
    modules: List[Module] = []
    recommendations: List[str] = []
