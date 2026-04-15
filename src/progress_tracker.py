"""Persist learning paths and track user progress using JSON files."""

import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from src.models import (
    CompletedLesson,
    LearningPath,
    LearningPathProgress,
    ModuleProgress,
    ModuleStatus,
    PathStatus,
    UserProgress,
)

PROGRESS_DIR = Path("progress")
PATHS_DIR = PROGRESS_DIR / "paths"
BACKUPS_DIR = PROGRESS_DIR / "backups"
USER_PROGRESS_FILE = PROGRESS_DIR / "user_progress.json"


def _slugify(text: str) -> str:
    """Convert a string to a safe filename slug."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s_-]", "", slug)
    slug = re.sub(r"\s+", "_", slug.strip())
    return slug[:60]


def _path_id(goal: str, created_at: Optional[datetime] = None) -> str:
    ts = (created_at or datetime.now(timezone.utc)).strftime("%Y_%m_%d")
    return f"{_slugify(goal)}_{ts}"


def _ensure_dirs() -> None:
    PATHS_DIR.mkdir(parents=True, exist_ok=True)
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


def _load_user_progress() -> UserProgress:
    if USER_PROGRESS_FILE.exists():
        data = json.loads(USER_PROGRESS_FILE.read_text(encoding="utf-8"))
        return UserProgress.model_validate(data)
    return UserProgress()


def _save_user_progress(up: UserProgress) -> None:
    _ensure_dirs()
    up.updated_at = datetime.now(timezone.utc)
    USER_PROGRESS_FILE.write_text(
        up.model_dump_json(indent=2), encoding="utf-8"
    )


def save_path(learning_path: LearningPath) -> LearningPathProgress:
    """Persist a newly generated LearningPath and return its LearningPathProgress."""
    _ensure_dirs()
    path_id = _path_id(learning_path.goal)

    modules: List[ModuleProgress] = []
    for mod in learning_path.modules:
        modules.append(
            ModuleProgress(
                module_id=mod.module_id,
                title=mod.title,
                status=ModuleStatus.not_started,
                estimated_hours=mod.estimated_hours,
            )
        )

    progress = LearningPathProgress(
        path_id=path_id,
        goal=learning_path.goal,
        status=PathStatus.active,
        modules=modules,
        estimated_total_hours=learning_path.estimated_total_hours,
        original_path=learning_path,
    )

    file_path = PATHS_DIR / f"{path_id}.json"
    file_path.write_text(progress.model_dump_json(indent=2), encoding="utf-8")

    # Update user progress index
    up = _load_user_progress()
    if path_id not in up.active_paths:
        up.active_paths.append(path_id)
    _save_user_progress(up)

    return progress


def load_path(path_id: str) -> Optional[LearningPathProgress]:
    """Load a saved LearningPathProgress by its ID."""
    file_path = PATHS_DIR / f"{path_id}.json"
    if not file_path.exists():
        return None
    data = json.loads(file_path.read_text(encoding="utf-8"))
    return LearningPathProgress.model_validate(data)


def _write_path(progress: LearningPathProgress) -> None:
    _ensure_dirs()
    progress.updated_at = datetime.now(timezone.utc)
    file_path = PATHS_DIR / f"{progress.path_id}.json"
    file_path.write_text(progress.model_dump_json(indent=2), encoding="utf-8")


def list_paths() -> List[LearningPathProgress]:
    """Return all saved learning path progress records."""
    _ensure_dirs()
    paths = []
    for file_path in sorted(PATHS_DIR.glob("*.json")):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            paths.append(LearningPathProgress.model_validate(data))
        except Exception:
            pass
    return paths


def complete_lesson(
    path_id: str,
    module_id: str,
    lesson_id: str,
    notes: Optional[str] = None,
    actual_minutes: Optional[int] = None,
) -> Optional[LearningPathProgress]:
    """Mark a lesson as complete and update progress."""
    progress = load_path(path_id)
    if progress is None:
        return None

    completed = CompletedLesson(
        lesson_id=lesson_id,
        module_id=module_id,
        path_id=path_id,
        notes=notes,
        actual_minutes=actual_minutes,
    )

    for mod in progress.modules:
        if mod.module_id == module_id:
            if lesson_id not in mod.completed_lessons:
                mod.completed_lessons.append(lesson_id)
            if mod.status == ModuleStatus.not_started:
                mod.status = ModuleStatus.in_progress
                mod.started_at = datetime.now(timezone.utc)
            if actual_minutes:
                mod.actual_hours += actual_minutes / 60.0

            # Check if all lessons are completed
            if progress.original_path:
                orig_module = next(
                    (m for m in progress.original_path.modules if m.module_id == module_id),
                    None,
                )
                if orig_module and len(mod.completed_lessons) >= len(orig_module.lessons):
                    mod.status = ModuleStatus.completed
                    mod.completed_at = datetime.now(timezone.utc)
            break

    # Recalculate completion percentage
    progress.completion_percentage = _calc_completion(progress)
    progress.actual_total_hours = sum(m.actual_hours for m in progress.modules)
    _write_path(progress)

    # Update user-level stats
    up = _load_user_progress()
    up.total_lessons_completed += 1
    if actual_minutes:
        up.total_hours_spent += actual_minutes / 60.0
    _save_user_progress(up)

    return progress


def complete_module(path_id: str, module_id: str) -> Optional[LearningPathProgress]:
    """Mark an entire module as complete."""
    progress = load_path(path_id)
    if progress is None:
        return None

    for mod in progress.modules:
        if mod.module_id == module_id:
            if progress.original_path:
                orig_module = next(
                    (m for m in progress.original_path.modules if m.module_id == module_id),
                    None,
                )
                if orig_module:
                    mod.completed_lessons = [les.lesson_id for les in orig_module.lessons]
            mod.status = ModuleStatus.completed
            if mod.started_at is None:
                mod.started_at = datetime.now(timezone.utc)
            mod.completed_at = datetime.now(timezone.utc)
            break

    progress.completion_percentage = _calc_completion(progress)
    progress.actual_total_hours = sum(m.actual_hours for m in progress.modules)
    _write_path(progress)

    up = _load_user_progress()
    up.total_modules_completed += 1
    _save_user_progress(up)

    return progress


def _calc_completion(progress: LearningPathProgress) -> float:
    if not progress.modules:
        return 0.0
    completed = sum(1 for m in progress.modules if m.status == ModuleStatus.completed)
    return round(completed / len(progress.modules) * 100, 1)


def set_path_status(path_id: str, status: PathStatus) -> Optional[LearningPathProgress]:
    """Pause, resume, or complete a learning path."""
    progress = load_path(path_id)
    if progress is None:
        return None

    old_status = progress.status
    progress.status = status
    _write_path(progress)

    up = _load_user_progress()
    for lst in [up.active_paths, up.paused_paths, up.completed_paths]:
        if path_id in lst:
            lst.remove(path_id)

    if status == PathStatus.active:
        up.active_paths.append(path_id)
    elif status == PathStatus.paused:
        up.paused_paths.append(path_id)
    else:
        up.completed_paths.append(path_id)

    _save_user_progress(up)
    return progress


def get_user_progress() -> UserProgress:
    return _load_user_progress()


def backup_progress() -> Path:
    """Create a timestamped backup of the progress directory."""
    _ensure_dirs()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUPS_DIR / f"backup_{ts}.json"
    data: dict = {"paths": {}, "user_progress": None}

    for path_file in PATHS_DIR.glob("*.json"):
        data["paths"][path_file.stem] = json.loads(path_file.read_text(encoding="utf-8"))

    if USER_PROGRESS_FILE.exists():
        data["user_progress"] = json.loads(USER_PROGRESS_FILE.read_text(encoding="utf-8"))

    backup_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return backup_file
