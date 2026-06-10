"""PDF report generator using ReportLab."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from continuum.database.repository import NoteRepository
from continuum.models.entities import ReportData


class ReportGenerator:
    """Generates professional PDF activity reports."""

    BRAND_COLOR = colors.HexColor("#4F46E5")
    ACCENT_COLOR = colors.HexColor("#818CF8")
    TEXT_COLOR = colors.HexColor("#1E1B4B")
    MUTED_COLOR = colors.HexColor("#6B7280")

    def __init__(self, repository: NoteRepository) -> None:
        self._repo = repository

    def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        output_path: Path,
    ) -> Path:
        """Generate a PDF report for the given date range."""
        notes = self._repo.get_notes_by_date_range(start_date, end_date)
        stats = self._repo.get_activity_stats(start_date, end_date)

        cat_counter: Counter[str] = Counter()
        tag_counter: Counter[str] = Counter()
        for note in notes:
            cat_counter.update(note.categories)
            tag_counter.update(note.tags)

        connections: list[tuple[str, str, float]] = []
        for note in notes:
            assert note.id is not None
            for related, strength, _ in self._repo.get_backlinks_for_note(note.id):
                connections.append((note.title, related.title, strength))

        data = ReportData(
            start_date=start_date,
            end_date=end_date,
            notes=notes,
            stats=stats,
            category_breakdown=dict(cat_counter),
            tag_breakdown=dict(tag_counter),
            connections=connections,
        )

        return self._render_pdf(data, output_path)

    def _render_pdf(self, data: ReportData, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=28,
            textColor=self.BRAND_COLOR,
            spaceAfter=6,
            alignment=TA_CENTER,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=12,
            textColor=self.MUTED_COLOR,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=16,
            textColor=self.BRAND_COLOR,
            spaceBefore=16,
            spaceAfter=8,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10,
            textColor=self.TEXT_COLOR,
            leading=14,
        )
        note_title_style = ParagraphStyle(
            "NoteTitle",
            parent=styles["Normal"],
            fontSize=12,
            textColor=self.BRAND_COLOR,
            fontName="Helvetica-Bold",
            spaceBefore=8,
        )

        story: list = []

        # Cover
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph("continuum", title_style))
        story.append(Paragraph("Activity Report", subtitle_style))
        date_range = (
            f"{data.start_date.strftime('%B %d, %Y')} — {data.end_date.strftime('%B %d, %Y')}"
        )
        story.append(Paragraph(date_range, subtitle_style))
        story.append(Spacer(1, 0.5 * inch))
        story.append(HRFlowable(width="60%", thickness=2, color=self.ACCENT_COLOR, spaceAfter=20))
        story.append(PageBreak())

        # Summary statistics
        story.append(Paragraph("Summary", heading_style))
        stat_data = [
            ["Metric", "Value"],
            ["Notes Created", str(data.stats.notes_in_period)],
            ["Categories Involved", str(len(data.category_breakdown))],
            ["Tags Generated", str(len(data.tag_breakdown))],
            ["Related Connections", str(len(data.connections))],
            ["Total Notes (All Time)", str(data.stats.total_notes)],
        ]
        stat_table = Table(stat_data, colWidths=[3 * inch, 2 * inch])
        stat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.5, self.ACCENT_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(stat_table)
        story.append(Spacer(1, 16))

        # Category breakdown
        if data.category_breakdown:
            story.append(Paragraph("Categories", heading_style))
            cat_data = [["Category", "Notes"]] + [
                [cat, str(count)] for cat, count in sorted(
                    data.category_breakdown.items(), key=lambda x: x[1], reverse=True
                )
            ]
            cat_table = Table(cat_data, colWidths=[3 * inch, 2 * inch])
            cat_table.setStyle(self._table_style())
            story.append(cat_table)
            story.append(Spacer(1, 16))

        # Tag breakdown
        if data.tag_breakdown:
            story.append(Paragraph("Tags", heading_style))
            tag_data = [["Tag", "Occurrences"]] + [
                [tag, str(count)] for tag, count in sorted(
                    data.tag_breakdown.items(), key=lambda x: x[1], reverse=True
                )[:20]
            ]
            tag_table = Table(tag_data, colWidths=[3 * inch, 2 * inch])
            tag_table.setStyle(self._table_style())
            story.append(tag_table)
            story.append(Spacer(1, 16))

        # Notes detail
        story.append(PageBreak())
        story.append(Paragraph("Notes", heading_style))
        if not data.notes:
            story.append(Paragraph("No notes were created during this period.", body_style))
        else:
            for note in data.notes:
                story.append(Paragraph(note.title or "Untitled", note_title_style))
                meta = f"Created: {note.created_at.strftime('%b %d, %Y at %H:%M')}"
                if note.categories:
                    meta += f"  |  Categories: {', '.join(note.categories)}"
                if note.tags:
                    meta += f"  |  Tags: {', '.join(note.tags[:5])}"
                story.append(Paragraph(meta, ParagraphStyle(
                    "Meta", parent=body_style, fontSize=8, textColor=self.MUTED_COLOR
                )))
                preview = note.content[:300] + ("…" if len(note.content) > 300 else "")
                story.append(Paragraph(preview.replace("\n", "<br/>"), body_style))
                story.append(Spacer(1, 8))

        # Connections
        if data.connections:
            story.append(PageBreak())
            story.append(Paragraph("Related Connections", heading_style))
            conn_data = [["Note A", "Note B", "Strength"]] + [
                [a, b, f"{s:.0%}"] for a, b, s in data.connections[:30]
            ]
            conn_table = Table(conn_data, colWidths=[2.2 * inch, 2.2 * inch, 1 * inch])
            conn_table.setStyle(self._table_style())
            story.append(conn_table)

        doc.build(story)
        return output_path

    def _table_style(self) -> TableStyle:
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_COLOR),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("GRID", (0, 0), (-1, -1), 0.5, self.ACCENT_COLOR),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F3FF")]),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ])
