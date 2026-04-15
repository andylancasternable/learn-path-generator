"""Command-line interface for learning path progress tracking.

Usage:
    python -m src.cli <command> [options]
"""

import sys
from pathlib import Path
from typing import Optional

import click

from src.exporters import export_to_file
from src.models import PathStatus
from src import progress_tracker as pt


def _require_path(path_id: str):
    """Load a path or exit with an error."""
    progress = pt.load_path(path_id)
    if progress is None:
        click.echo(f"❌ Learning path not found: {path_id}", err=True)
        sys.exit(1)
    return progress


@click.group()
def cli():
    """Learning Path Generator – progress tracking CLI."""


@cli.command("list")
def list_paths():
    """List all saved learning paths."""
    paths = pt.list_paths()
    if not paths:
        click.echo("No saved learning paths found.")
        return
    click.echo(f"{'ID':<55} {'Status':<12} {'Progress':>8}  Goal")
    click.echo("-" * 100)
    for p in paths:
        click.echo(
            f"{p.path_id:<55} {p.status.value:<12} {p.completion_percentage:>7.1f}%  {p.goal}"
        )


@cli.command("view")
@click.argument("path_id")
def view_path(path_id: str):
    """View detailed progress for a learning path."""
    progress = _require_path(path_id)
    click.echo(f"\n📚 {progress.goal}")
    click.echo(f"   ID:         {progress.path_id}")
    click.echo(f"   Status:     {progress.status.value}")
    click.echo(f"   Created:    {progress.created_at.strftime('%Y-%m-%d')}")
    click.echo(f"   Updated:    {progress.updated_at.strftime('%Y-%m-%d')}")
    click.echo(
        f"   Completion: {progress.completion_percentage:.1f}%  "
        f"({progress.actual_total_hours:.1f}h actual / {progress.estimated_total_hours:.1f}h est.)"
    )
    if progress.notes:
        click.echo(f"   Notes:      {progress.notes}")

    # ASCII progress bar
    filled = int(progress.completion_percentage / 5)
    bar = "█" * filled + "░" * (20 - filled)
    click.echo(f"\n   [{bar}] {progress.completion_percentage:.1f}%\n")

    click.echo("Modules:")
    for mod in progress.modules:
        icons = {"not_started": "⬜", "in_progress": "🔄", "completed": "✅"}
        icon = icons.get(mod.status.value, "⬜")
        lessons_done = len(mod.completed_lessons)
        total_lessons = 0
        if progress.original_path:
            orig = next(
                (m for m in progress.original_path.modules if m.module_id == mod.module_id),
                None,
            )
            if orig:
                total_lessons = len(orig.lessons)
        lesson_info = f"{lessons_done}/{total_lessons}" if total_lessons else str(lessons_done)
        click.echo(
            f"  {icon} [{mod.module_id}] {mod.title} — {mod.status.value} "
            f"({mod.actual_hours:.1f}h/{mod.estimated_hours:.1f}h est., lessons {lesson_info})"
        )
        if mod.notes:
            click.echo(f"       Notes: {mod.notes}")


@cli.command("complete-lesson")
@click.argument("path_id")
@click.argument("module_id")
@click.argument("lesson_id")
@click.option("--notes", default=None, help="Notes about this lesson")
@click.option("--minutes", default=None, type=int, help="Actual minutes spent")
def complete_lesson(
    path_id: str,
    module_id: str,
    lesson_id: str,
    notes: Optional[str],
    minutes: Optional[int],
):
    """Mark a lesson as complete."""
    progress = pt.complete_lesson(path_id, module_id, lesson_id, notes=notes, actual_minutes=minutes)
    if progress is None:
        click.echo(f"❌ Path not found: {path_id}", err=True)
        sys.exit(1)
    click.echo(
        f"✅ Lesson {lesson_id} in module {module_id} marked complete. "
        f"Overall progress: {progress.completion_percentage:.1f}%"
    )


@cli.command("complete-module")
@click.argument("path_id")
@click.argument("module_id")
def complete_module(path_id: str, module_id: str):
    """Mark an entire module as complete."""
    progress = pt.complete_module(path_id, module_id)
    if progress is None:
        click.echo(f"❌ Path not found: {path_id}", err=True)
        sys.exit(1)
    click.echo(
        f"✅ Module {module_id} marked complete. "
        f"Overall progress: {progress.completion_percentage:.1f}%"
    )


@cli.command("status")
@click.argument("path_id")
def show_status(path_id: str):
    """Show overall completion status for a path."""
    progress = _require_path(path_id)
    completed = sum(1 for m in progress.modules if m.status.value == "completed")
    in_progress = sum(1 for m in progress.modules if m.status.value == "in_progress")
    not_started = sum(1 for m in progress.modules if m.status.value == "not_started")
    click.echo(f"\n📊 Status for: {progress.goal}")
    click.echo(f"   Status:      {progress.status.value}")
    click.echo(f"   Completion:  {progress.completion_percentage:.1f}%")
    click.echo(f"   Modules:     {completed} completed, {in_progress} in progress, {not_started} not started")
    click.echo(
        f"   Time:        {progress.actual_total_hours:.1f}h actual / {progress.estimated_total_hours:.1f}h estimated"
    )


@cli.command("export")
@click.argument("path_id")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "csv", "markdown", "pdf"], case_sensitive=False),
    default="markdown",
    show_default=True,
    help="Export format",
)
@click.option("--output", default=None, help="Output file path (default: <path_id>.<ext>)")
def export_path(path_id: str, fmt: str, output: Optional[str]):
    """Export a learning path progress to a file."""
    progress = _require_path(path_id)
    ext_map = {"json": "json", "csv": "csv", "markdown": "md", "pdf": "pdf"}
    ext = ext_map[fmt.lower()]
    out_file = Path(output) if output else Path(f"{path_id}.{ext}")
    export_to_file(progress, out_file, fmt)
    click.echo(f"✅ Exported to {out_file}")


@cli.command("new-path")
@click.argument("goal")
def new_path(goal: str):
    """Create a new learning path stub for manual tracking (no ebook analysis)."""
    from src.models import LearningPath

    path = LearningPath(goal=goal, ebooks_count=0, estimated_total_hours=0.0)
    progress = pt.save_path(path)
    click.echo(f"✅ Created new learning path: {progress.path_id}")
    click.echo(f"   Goal: {progress.goal}")
    click.echo(f"   Use 'python -m src.cli view {progress.path_id}' to view it.")


@cli.command("pause")
@click.argument("path_id")
def pause_path(path_id: str):
    """Pause a learning path."""
    progress = pt.set_path_status(path_id, PathStatus.paused)
    if progress is None:
        click.echo(f"❌ Path not found: {path_id}", err=True)
        sys.exit(1)
    click.echo(f"⏸️  Path {path_id} paused.")


@cli.command("resume")
@click.argument("path_id")
def resume_path(path_id: str):
    """Resume a paused learning path."""
    progress = pt.set_path_status(path_id, PathStatus.active)
    if progress is None:
        click.echo(f"❌ Path not found: {path_id}", err=True)
        sys.exit(1)
    click.echo(f"▶️  Path {path_id} resumed.")


@cli.command("stats")
def show_stats():
    """Show aggregate learning statistics."""
    up = pt.get_user_progress()
    paths = pt.list_paths()
    click.echo("\n📈 Learning Statistics")
    click.echo(f"   Total hours spent:      {up.total_hours_spent:.1f}h")
    click.echo(f"   Total modules completed: {up.total_modules_completed}")
    click.echo(f"   Total lessons completed: {up.total_lessons_completed}")
    click.echo(f"   Active paths:           {len(up.active_paths)}")
    click.echo(f"   Paused paths:           {len(up.paused_paths)}")
    click.echo(f"   Completed paths:        {len(up.completed_paths)}")
    if paths:
        avg_completion = sum(p.completion_percentage for p in paths) / len(paths)
        click.echo(f"   Avg. completion:        {avg_completion:.1f}%")


if __name__ == "__main__":
    cli()
