from pathlib import Path
from typing import Dict, List


SUPPORTED_EBOOK_SUFFIXES = {".pdf", ".epub"}


def list_ebook_files(directory: Path) -> List[Path]:
    """List ebook files (non-recursive) from a directory."""
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(
        [
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EBOOK_SUFFIXES
        ],
        key=lambda path: path.name.lower(),
    )


def discover_subject_ebooks(ebooks_dir: Path) -> Dict[str, List[Path]]:
    """
    Discover ebook collections by subject.

    - Root-level ebooks are grouped under "General".
    - Each immediate subdirectory is treated as a subject.
    """
    ebooks_dir.mkdir(exist_ok=True)
    subjects: Dict[str, List[Path]] = {}

    root_ebooks = list_ebook_files(ebooks_dir)
    if root_ebooks:
        subjects["General"] = root_ebooks

    for subdir in sorted([path for path in ebooks_dir.iterdir() if path.is_dir()], key=lambda path: path.name.lower()):
        subject_ebooks = list_ebook_files(subdir)
        if subject_ebooks:
            subjects[subdir.name] = subject_ebooks

    return subjects


def find_empty_subject_directories(ebooks_dir: Path) -> List[str]:
    """Find immediate subject directories that contain no supported ebook files."""
    if not ebooks_dir.exists() or not ebooks_dir.is_dir():
        return []

    empty_subjects: List[str] = []
    for subdir in sorted([path for path in ebooks_dir.iterdir() if path.is_dir()], key=lambda path: path.name.lower()):
        if not list_ebook_files(subdir):
            empty_subjects.append(subdir.name)
    return empty_subjects
