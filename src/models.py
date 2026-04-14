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


class PathStep(BaseModel):
    order: int
    ebook_title: str
    topics: List[str]
    estimated_hours: float
    rationale: str


class LearningPath(BaseModel):
    goal: str
    ebooks_count: int
    estimated_total_hours: float
    steps: List[PathStep] = []
