"""Export learning path progress to various formats."""

import csv
import io
import json
from pathlib import Path
from typing import Union

from src.models import LearningPathProgress, ModuleStatus


def export_json(progress: LearningPathProgress) -> str:
    """Return a JSON string of the full progress object."""
    return progress.model_dump_json(indent=2)


def export_csv(progress: LearningPathProgress) -> str:
    """Return a CSV string with one row per module."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "path_id",
        "goal",
        "module_id",
        "module_title",
        "status",
        "estimated_hours",
        "actual_hours",
        "completed_lessons",
        "started_at",
        "completed_at",
        "notes",
    ])
    for mod in progress.modules:
        writer.writerow([
            progress.path_id,
            progress.goal,
            mod.module_id,
            mod.title,
            mod.status.value,
            mod.estimated_hours,
            round(mod.actual_hours, 2),
            ";".join(mod.completed_lessons),
            mod.started_at.isoformat() if mod.started_at else "",
            mod.completed_at.isoformat() if mod.completed_at else "",
            mod.notes or "",
        ])
    return output.getvalue()


def export_markdown(progress: LearningPathProgress) -> str:
    """Return a Markdown-formatted progress report."""
    lines = []
    lines.append(f"# Learning Path: {progress.goal}")
    lines.append("")
    lines.append(f"**Path ID:** {progress.path_id}  ")
    lines.append(f"**Status:** {progress.status.value}  ")
    lines.append(f"**Created:** {progress.created_at.strftime('%Y-%m-%d')}  ")
    lines.append(f"**Last updated:** {progress.updated_at.strftime('%Y-%m-%d')}  ")
    lines.append(f"**Completion:** {progress.completion_percentage:.1f}%  ")
    lines.append(
        f"**Time:** {progress.actual_total_hours:.1f}h actual / "
        f"{progress.estimated_total_hours:.1f}h estimated  "
    )
    if progress.notes:
        lines.append(f"**Notes:** {progress.notes}  ")
    lines.append("")

    # Progress bar (simple ASCII)
    filled = int(progress.completion_percentage / 5)
    bar = "█" * filled + "░" * (20 - filled)
    lines.append(f"`{bar}` {progress.completion_percentage:.1f}%")
    lines.append("")

    lines.append("## Modules")
    lines.append("")

    status_icons = {
        ModuleStatus.not_started: "⬜",
        ModuleStatus.in_progress: "🔄",
        ModuleStatus.completed: "✅",
    }

    for mod in progress.modules:
        icon = status_icons.get(mod.status, "⬜")
        lines.append(f"### {icon} {mod.title}")
        lines.append("")
        lines.append(f"- **Module ID:** `{mod.module_id}`")
        lines.append(f"- **Status:** {mod.status.value}")
        lines.append(f"- **Estimated hours:** {mod.estimated_hours:.1f}")
        lines.append(f"- **Actual hours:** {mod.actual_hours:.1f}")
        if mod.completed_lessons:
            lines.append(f"- **Completed lessons:** {', '.join(mod.completed_lessons)}")
        if mod.started_at:
            lines.append(f"- **Started:** {mod.started_at.strftime('%Y-%m-%d')}")
        if mod.completed_at:
            lines.append(f"- **Completed:** {mod.completed_at.strftime('%Y-%m-%d')}")
        if mod.notes:
            lines.append(f"- **Notes:** {mod.notes}")
        lines.append("")

    if progress.original_path and progress.original_path.recommendations:
        lines.append("## Recommendations")
        lines.append("")
        for rec in progress.original_path.recommendations:
            lines.append(f"- {rec}")
        lines.append("")

    return "\n".join(lines)


def export_pdf(progress: LearningPathProgress) -> bytes:
    """Return PDF bytes of the progress report using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF export. Install it with: pip install reportlab"
        ) from exc

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        fontSize=18,
        spaceAfter=12,
    )
    story.append(Paragraph(f"Learning Path: {progress.goal}", title_style))
    story.append(Spacer(1, 0.2 * inch))

    # Metadata table
    meta_data = [
        ["Path ID", progress.path_id],
        ["Status", progress.status.value],
        ["Created", progress.created_at.strftime("%Y-%m-%d")],
        ["Last updated", progress.updated_at.strftime("%Y-%m-%d")],
        ["Completion", f"{progress.completion_percentage:.1f}%"],
        [
            "Time",
            f"{progress.actual_total_hours:.1f}h actual / {progress.estimated_total_hours:.1f}h estimated",
        ],
    ]
    meta_table = Table(meta_data, colWidths=[2 * inch, 4 * inch])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 0.3 * inch))

    # Modules section
    story.append(Paragraph("Modules", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))

    module_rows = [["Module", "Status", "Est. hrs", "Actual hrs", "Lessons done"]]
    for mod in progress.modules:
        module_rows.append([
            mod.title,
            mod.status.value,
            f"{mod.estimated_hours:.1f}",
            f"{mod.actual_hours:.1f}",
            str(len(mod.completed_lessons)),
        ])

    mod_table = Table(
        module_rows,
        colWidths=[2.5 * inch, 1 * inch, 0.8 * inch, 0.8 * inch, 1 * inch],
    )
    mod_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
        ])
    )
    story.append(mod_table)

    doc.build(story)
    return buffer.getvalue()


def export_to_file(
    progress: LearningPathProgress,
    output_path: Union[str, Path],
    fmt: str,
) -> Path:
    """Write exported progress to a file and return the path."""
    output_path = Path(output_path)
    fmt = fmt.lower()

    if fmt == "json":
        output_path.write_text(export_json(progress), encoding="utf-8")
    elif fmt == "csv":
        output_path.write_text(export_csv(progress), encoding="utf-8")
    elif fmt == "markdown":
        output_path.write_text(export_markdown(progress), encoding="utf-8")
    elif fmt == "pdf":
        output_path.write_bytes(export_pdf(progress))
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}. Choose from: json, csv, markdown, pdf")

    return output_path
