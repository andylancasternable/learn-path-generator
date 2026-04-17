"""Batch processing with checkpoint/resume support for learning path generation."""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class SubjectStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"


class BatchProcessor:
    """Handles batched processing of subjects with checkpoint/resume support.

    Progress is persisted to a *manifest* JSON file so that a long-running
    generation job can be interrupted and resumed without repeating work
    that has already been completed.

    Per-subject results are also written to individual JSON files inside
    *output_dir* so they can be inspected or loaded independently.

    Example::

        processor = BatchProcessor(output_dir=Path("output"))
        processor.load_manifest()

        for subject in processor.get_pending_subjects(all_subjects):
            processor.mark_subject_in_progress(subject)
            try:
                result = expensive_generate(subject)
                processor.mark_subject_completed(subject, result)
            except RateLimitError:
                processor.mark_subject_failed(subject, "rate limit")
                break
    """

    def __init__(self, output_dir: Path = Path("output")) -> None:
        self.output_dir = output_dir
        self.manifest_path = output_dir / "manifest.json"
        self._manifest: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Manifest management
    # ------------------------------------------------------------------

    def load_manifest(self) -> Dict[str, Any]:
        """Load the processing manifest from disk.

        If no manifest file exists yet an empty one is initialised in memory
        (nothing is written to disk until :py:meth:`save_manifest` is called).
        """
        if self.manifest_path.exists():
            self._manifest = json.loads(
                self.manifest_path.read_text(encoding="utf-8")
            )
        else:
            self._manifest = {
                "subjects": {},
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        return self._manifest

    def save_manifest(self) -> None:
        """Persist the current manifest to disk."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        self.manifest_path.write_text(
            json.dumps(self._manifest, indent=2, default=str), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Subject status tracking
    # ------------------------------------------------------------------

    def get_subject_status(self, subject: str) -> SubjectStatus:
        """Return the current processing status for *subject*."""
        subjects = self._manifest.get("subjects", {})
        entry = subjects.get(subject, {})
        raw = entry.get("status", SubjectStatus.pending)
        try:
            return SubjectStatus(raw)
        except ValueError:
            return SubjectStatus.pending

    def mark_subject_in_progress(self, subject: str) -> None:
        """Record that *subject* is currently being processed."""
        self._ensure_subject_entry(subject)
        self._manifest["subjects"][subject]["status"] = SubjectStatus.in_progress
        self._manifest["subjects"][subject]["started_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        self.save_manifest()

    def mark_subject_completed(
        self, subject: str, result: Optional[Any] = None
    ) -> None:
        """Record that *subject* has been successfully processed.

        If *result* is provided it is also saved to a per-subject JSON file.
        """
        self._ensure_subject_entry(subject)
        entry = self._manifest["subjects"][subject]
        entry["status"] = SubjectStatus.completed
        entry["completed_at"] = datetime.now(timezone.utc).isoformat()
        if result is not None:
            result_path = self.save_subject_result(subject, result)
            entry["result_file"] = str(result_path)
        self.save_manifest()

    def mark_subject_failed(self, subject: str, error: str) -> None:
        """Record that processing *subject* failed with *error*."""
        self._ensure_subject_entry(subject)
        entry = self._manifest["subjects"][subject]
        entry["status"] = SubjectStatus.failed
        entry["failed_at"] = datetime.now(timezone.utc).isoformat()
        entry["error"] = error
        self.save_manifest()

    # ------------------------------------------------------------------
    # Result persistence
    # ------------------------------------------------------------------

    def save_subject_result(self, subject: str, data: Any) -> Path:
        """Write *data* as JSON to a per-subject file and return the path."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        result_path = self.output_dir / f"{subject}.json"
        result_path.write_text(
            json.dumps(data, indent=2, default=str), encoding="utf-8"
        )
        return result_path

    def load_subject_result(self, subject: str) -> Optional[Any]:
        """Load a previously saved per-subject result, or *None* if not found."""
        result_path = self.output_dir / f"{subject}.json"
        if result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
        return None

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_pending_subjects(self, all_subjects: List[str]) -> List[str]:
        """Return the subset of *all_subjects* that have not yet completed."""
        return [
            s
            for s in all_subjects
            if self.get_subject_status(s) != SubjectStatus.completed
        ]

    def get_completed_subjects(self) -> List[str]:
        """Return all subjects recorded as completed in the manifest."""
        return [
            subject
            for subject, entry in self._manifest.get("subjects", {}).items()
            if entry.get("status") == SubjectStatus.completed
        ]

    def get_failed_subjects(self) -> List[str]:
        """Return all subjects recorded as failed in the manifest."""
        return [
            subject
            for subject, entry in self._manifest.get("subjects", {}).items()
            if entry.get("status") == SubjectStatus.failed
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Return a human-readable summary of processing status."""
        subjects = self._manifest.get("subjects", {})
        counts: Dict[str, int] = {s.value: 0 for s in SubjectStatus}
        for entry in subjects.values():
            status = entry.get("status", SubjectStatus.pending.value)
            if status in counts:
                counts[status] += 1
            else:
                counts[SubjectStatus.pending.value] += 1
        return {
            "total": len(subjects),
            "completed": counts.get(SubjectStatus.completed.value, 0),
            "failed": counts.get(SubjectStatus.failed.value, 0),
            "in_progress": counts.get(SubjectStatus.in_progress.value, 0),
            "pending": counts.get(SubjectStatus.pending.value, 0),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_subject_entry(self, subject: str) -> None:
        if "subjects" not in self._manifest:
            self._manifest["subjects"] = {}
        if subject not in self._manifest["subjects"]:
            self._manifest["subjects"][subject] = {
                "status": SubjectStatus.pending,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
