"""Flask web dashboard for learning path progress tracking."""

import json
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for, abort

from src import progress_tracker as pt
from src.models import PathStatus

app = Flask(__name__)

EBOOKS_DIR = Path("ebooks")
BATCH_OUTPUT_DIR = Path("output") / "subject_learning_paths"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_module_detail(progress, module_id):
    """Return (ModuleProgress, original Module) for a given module_id."""
    mod_progress = next((m for m in progress.modules if m.module_id == module_id), None)
    orig_module = None
    if progress.original_path:
        orig_module = next(
            (m for m in progress.original_path.modules if m.module_id == module_id), None
        )
    return mod_progress, orig_module


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    paths = pt.list_paths()
    user_stats = pt.get_user_progress()
    return render_template("dashboard.html", paths=paths, user_stats=user_stats)


@app.route("/path/<path_id>")
def path_detail(path_id):
    progress = pt.load_path(path_id)
    if progress is None:
        abort(404)

    # Build enriched module list: merge ModuleProgress with original Module data
    modules_enriched = []
    for mod in progress.modules:
        orig = None
        if progress.original_path:
            orig = next(
                (m for m in progress.original_path.modules if m.module_id == mod.module_id),
                None,
            )
        total_lessons = len(orig.lessons) if orig else 0
        lessons_done = len(mod.completed_lessons)
        lesson_pct = round(lessons_done / total_lessons * 100) if total_lessons else 0
        modules_enriched.append(
            {
                "progress": mod,
                "original": orig,
                "total_lessons": total_lessons,
                "lessons_done": lessons_done,
                "lesson_pct": lesson_pct,
            }
        )

    return render_template(
        "path_detail.html",
        progress=progress,
        modules_enriched=modules_enriched,
    )


@app.route("/path/<path_id>/module/<module_id>")
def module_detail(path_id, module_id):
    progress = pt.load_path(path_id)
    if progress is None:
        abort(404)

    mod_progress, orig_module = _get_module_detail(progress, module_id)
    if mod_progress is None:
        abort(404)

    return render_template(
        "module_detail.html",
        progress=progress,
        mod_progress=mod_progress,
        orig_module=orig_module,
    )


@app.route("/subjects")
def subjects():
    """Display all subject subdirectories with ebook counts and build status."""
    EBOOKS_DIR.mkdir(exist_ok=True)

    subject_list = []
    for item in sorted(EBOOKS_DIR.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir():
            continue
        ebook_files = [
            f for f in item.iterdir()
            if f.is_file() and f.suffix.lower() in {".pdf", ".epub"}
        ]
        subject_list.append({
            "name": item.name,
            "display_name": item.name.replace("_", " ").title(),
            "ebook_count": len(ebook_files),
        })

    # Load batch processor manifest to get completion status per subject
    manifest: dict = {}
    manifest_path = BATCH_OUTPUT_DIR / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    manifest_subjects = manifest.get("subjects", {})

    # Enrich subject list with build status and path_id
    for subj in subject_list:
        name = subj["name"]
        display = subj["display_name"]
        entry = manifest_subjects.get(name) or manifest_subjects.get(display, {})
        subj["build_status"] = entry.get("status", "pending")
        # Check if a progress path already exists for this subject
        existing_paths = pt.list_paths()
        matched = next(
            (p for p in existing_paths if name.lower() in p.goal.lower() or
             display.lower() in p.goal.lower()),
            None,
        )
        subj["path_id"] = matched.path_id if matched else None
        subj["completion_percentage"] = matched.completion_percentage if matched else 0.0

    # Load manifest ebook counts (books already processed)
    ebook_manifest: dict = {}
    ebook_manifest_path = EBOOKS_DIR / "ebook_manifest.json"
    if ebook_manifest_path.exists():
        try:
            ebook_manifest = json.loads(ebook_manifest_path.read_text(encoding="utf-8"))
        except Exception:
            ebook_manifest = {}

    books_in_manifest = ebook_manifest.get("books", {})
    for subj in subject_list:
        subj["processed_count"] = sum(
            1 for b in books_in_manifest.values()
            if b.get("subject") == subj["name"]
        )

    return render_template("subjects.html", subjects=subject_list)


# ---------------------------------------------------------------------------
# Subject build-path API endpoint
# ---------------------------------------------------------------------------

@app.route("/api/subject/<subject>/build-path", methods=["POST"])
def api_build_subject_path(subject):
    """Trigger learning path generation for a subject directory.

    Returns JSON with keys: ``status``, ``path_id`` (on success), and
    ``message`` describing the outcome.  Rate-limit errors from the LLM are
    handled gracefully and surfaced as a 429 response.
    """
    print(f"DEBUG: Starting build-path for subject: {subject}")
    import re as _re
    safe_subject = _re.sub(r"[^a-zA-Z0-9_\-]", "", subject)
    print(f"DEBUG: safe_subject = {safe_subject}")
    if not safe_subject:
        return jsonify({"error": "Invalid subject name"}), 400

    subject_dir = EBOOKS_DIR / safe_subject
    print(f"DEBUG: subject_dir = {subject_dir}, exists = {subject_dir.is_dir()}")
    if not subject_dir.is_dir():
        return jsonify({"error": f"Subject directory not found: {safe_subject}"}), 404

    ebook_files = [
        f for f in subject_dir.iterdir()
        if f.is_file() and f.suffix.lower() in {".pdf", ".epub"}
    ]
    print(f"DEBUG: Found {len(ebook_files)} ebook files")
    if not ebook_files:
        return jsonify({"error": f"No ebooks found in subject: {safe_subject}"}), 404

    try:
        print("DEBUG: About to import modules...")
        from src.analyzers import ContentAnalyzer  # noqa: PLC0415
        print("DEBUG: ContentAnalyzer imported")
        from src.graph import KnowledgeGraph, PathGenerator  # noqa: PLC0415
        print("DEBUG: KnowledgeGraph and PathGenerator imported")
        from src.loaders import EPUBLoader, PDFLoader  # noqa: PLC0415
        print("DEBUG: EPUBLoader and PDFLoader imported")
        from src.models import Ebook  # noqa: PLC0415
        print("DEBUG: Ebook imported")
        from src.batch_processor import BatchProcessor, SubjectStatus  # noqa: PLC0415
        print("DEBUG: BatchProcessor and SubjectStatus imported")

        processor = BatchProcessor(output_dir=BATCH_OUTPUT_DIR)
        processor.load_manifest()

        display_name = safe_subject.replace("_", " ").title()
        processor.mark_subject_in_progress(safe_subject)

        pdf_loader = PDFLoader()
        epub_loader = EPUBLoader()
        analyzer = ContentAnalyzer()

        print(f"DEBUG: About to process {len(ebook_files)} ebooks...")
        loaded_ebooks = []
        for ebook_path in ebook_files:
            try:
                if ebook_path.suffix.lower() == ".epub":
                    content, metadata = epub_loader.load(str(ebook_path))
                else:
                    content, metadata = pdf_loader.load(str(ebook_path))
                    ebook_path = Path(metadata.get("file_path", str(ebook_path)))

                if not content:
                    continue

                ebook = Ebook(
                    title=metadata.get("title") or ebook_path.stem,
                    author=metadata.get("author", "Unknown"),
                    file_path=str(ebook_path),
                    difficulty_level="intermediate",
                    total_pages=metadata.get("pages"),
                )
                ebook = analyzer.analyze(ebook, content)
                loaded_ebooks.append(ebook)
            except Exception:
                continue

        if not loaded_ebooks:
            processor.mark_subject_failed(safe_subject, "No ebooks could be loaded")
            return jsonify({"error": "No ebooks could be loaded for this subject"}), 500

        print(f"DEBUG: Building knowledge graph from {len(loaded_ebooks)} loaded ebooks...")
        kg = KnowledgeGraph(subject=safe_subject)
        kg.build_from_ebooks(loaded_ebooks)

        goal = f"Master {display_name}"
        print(f"DEBUG: Generating learning path for goal: {goal}")
        path_generator = PathGenerator(kg)
        learning_path = path_generator.generate(goal)

        progress = pt.save_path(learning_path)

        result = {
            "subject": safe_subject,
            "ebook_count": len(loaded_ebooks),
            "paths": [learning_path.model_dump()],
        }
        processor.mark_subject_completed(safe_subject, result)

        return jsonify({
            "status": "completed",
            "path_id": progress.path_id,
            "message": f"Learning path generated for '{display_name}'",
            "ebook_count": len(loaded_ebooks),
            "modules": len(learning_path.modules),
            "estimated_hours": learning_path.estimated_total_hours,
        })

    except Exception as exc:
        import traceback
        error_msg = str(exc)
        print("=" * 80)
        print("TRACEBACK:")
        print(traceback.format_exc())
        print("=" * 80)
        # Detect rate-limit errors from various LLM providers
        if any(kw in error_msg.lower() for kw in ("rate limit", "rate_limit", "429", "too many")):
            try:
                processor.mark_subject_failed(safe_subject, error_msg)
            except Exception:
                pass
            return jsonify({
                "error": "Rate limit reached. Please wait a moment and try again.",
                "detail": error_msg,
            }), 429
        try:
            processor.mark_subject_failed(safe_subject, error_msg)
        except Exception:
            pass
        return jsonify({"error": error_msg}), 500


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/path/<path_id>/start", methods=["POST"])
def api_start_path(path_id):
    progress = pt.set_path_status(path_id, PathStatus.active)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404
    return jsonify({"status": "ok", "path_status": progress.status.value})


@app.route("/api/path/<path_id>/pause", methods=["POST"])
def api_pause_path(path_id):
    progress = pt.set_path_status(path_id, PathStatus.paused)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404
    return jsonify({"status": "ok", "path_status": progress.status.value})


@app.route("/api/path/<path_id>/complete", methods=["POST"])
def api_complete_path(path_id):
    progress = pt.set_path_status(path_id, PathStatus.completed)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404
    return jsonify({"status": "ok", "path_status": progress.status.value})


@app.route("/api/path/<path_id>/module/<module_id>/start", methods=["POST"])
def api_start_module(path_id, module_id):
    progress = pt.start_module(path_id, module_id)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404
    mod = next((m for m in progress.modules if m.module_id == module_id), None)
    return jsonify(
        {
            "status": "ok",
            "module_status": mod.status.value if mod else None,
            "completion_percentage": progress.completion_percentage,
        }
    )


@app.route("/api/path/<path_id>/module/<module_id>/complete", methods=["POST"])
def api_complete_module(path_id, module_id):
    progress = pt.complete_module(path_id, module_id)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404
    return jsonify(
        {
            "status": "ok",
            "completion_percentage": progress.completion_percentage,
        }
    )


@app.route(
    "/api/path/<path_id>/module/<module_id>/lesson/<lesson_id>/complete",
    methods=["POST"],
)
def api_complete_lesson(path_id, module_id, lesson_id):
    data = request.get_json(silent=True) or {}
    notes = data.get("notes")
    minutes = data.get("minutes")
    if minutes is not None:
        try:
            minutes = int(minutes)
        except (TypeError, ValueError):
            minutes = None

    progress = pt.complete_lesson(
        path_id, module_id, lesson_id, notes=notes, actual_minutes=minutes
    )
    if progress is None:
        return jsonify({"error": "Path not found"}), 404

    mod = next((m for m in progress.modules if m.module_id == module_id), None)
    return jsonify(
        {
            "status": "ok",
            "module_status": mod.status.value if mod else None,
            "completion_percentage": progress.completion_percentage,
        }
    )


@app.route("/api/path/<path_id>/module/<module_id>/notes", methods=["POST"])
def api_module_notes(path_id, module_id):
    data = request.get_json(silent=True) or {}
    notes = data.get("notes", "")
    progress = pt.add_module_notes(path_id, module_id, notes)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404
    return jsonify({"status": "ok"})


@app.route("/api/path/<path_id>/module/<module_id>/time", methods=["POST"])
def api_add_time(path_id, module_id):
    data = request.get_json(silent=True) or {}
    try:
        minutes = int(data.get("minutes", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid minutes value"}), 400
    if minutes <= 0:
        return jsonify({"error": "Minutes must be positive"}), 400

    progress = pt.add_module_time(path_id, module_id, minutes)
    if progress is None:
        return jsonify({"error": "Path not found"}), 404

    mod = next((m for m in progress.modules if m.module_id == module_id), None)
    return jsonify(
        {
            "status": "ok",
            "actual_hours": round(mod.actual_hours, 2) if mod else None,
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5000)
