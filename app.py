"""Flask web dashboard for learning path progress tracking."""

from flask import Flask, render_template, request, jsonify, redirect, url_for, abort

from src import progress_tracker as pt
from src.models import PathStatus

app = Flask(__name__)


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
