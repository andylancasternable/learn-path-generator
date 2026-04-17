from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


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
    tools_technologies: List[str] = []
    deliverables: List[str] = []


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


# ---------------------------------------------------------------------------
# Progress tracking models
# ---------------------------------------------------------------------------

class ModuleStatus(str, Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"


class PathStatus(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"


class CompletedLesson(BaseModel):
    lesson_id: str
    module_id: str
    path_id: str
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
    actual_minutes: Optional[int] = None


class ModuleProgress(BaseModel):
    module_id: str
    title: str
    status: ModuleStatus = ModuleStatus.not_started
    completed_lessons: List[str] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None
    estimated_hours: float = 0.0
    actual_hours: float = 0.0


class LearningPathProgress(BaseModel):
    path_id: str
    goal: str
    status: PathStatus = PathStatus.active
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completion_percentage: float = 0.0
    modules: List[ModuleProgress] = []
    notes: Optional[str] = None
    estimated_total_hours: float = 0.0
    actual_total_hours: float = 0.0
    original_path: Optional[LearningPath] = None


class UserProgress(BaseModel):
    total_hours_spent: float = 0.0
    total_modules_completed: int = 0
    total_lessons_completed: int = 0
    active_paths: List[str] = []
    completed_paths: List[str] = []
    paused_paths: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    stats_by_subject: Dict[str, float] = {}
