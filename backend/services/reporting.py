import hashlib
import io
import json
from datetime import UTC, datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#16212B")
TEAL = colors.HexColor("#17766F")
MUTED = colors.HexColor("#5D6B73")
PALE = colors.HexColor("#EFF6F4")
BORDER = colors.HexColor("#DDE5E2")


def _safe(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _collect_citations(value: Any, result: dict[str, dict[str, Any]] | None = None):
    found = result if result is not None else {}
    if isinstance(value, dict):
        if {"id", "title", "url", "excerpt"}.issubset(value):
            found[value["id"]] = value
        for nested in value.values():
            _collect_citations(nested, found)
    elif isinstance(value, list):
        for nested in value:
            _collect_citations(nested, found)
    return list(found.values())


def build_pdf_report(case: Any, run: Any, disclaimer: str) -> bytes:
    buffer = io.BytesIO()
    generated_at = datetime.now(UTC)
    payload_hash = hashlib.sha256(
        json.dumps(run.result, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=18 * mm,
        title=f"IP-SAKTI Innovation Intelligence Report — {case.title}",
        author="IP-SAKTI Sahayak 360",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleNavy", parent=styles["Title"], textColor=NAVY, fontSize=22, leading=28))
    styles.add(ParagraphStyle(name="Eyebrow", parent=styles["Normal"], textColor=TEAL, fontSize=8, leading=10, spaceAfter=5))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], textColor=NAVY, fontSize=14, leading=18, spaceBefore=12, spaceAfter=7))
    styles.add(ParagraphStyle(name="BodyMuted", parent=styles["BodyText"], textColor=MUTED, fontSize=9, leading=14))
    styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], textColor=MUTED, fontSize=7.5, leading=11))
    styles.add(ParagraphStyle(name="Score", parent=styles["BodyText"], textColor=TEAL, fontSize=18, leading=20, alignment=TA_CENTER))

    story = [
        Paragraph("IP-SAKTI SAHAYAK 360 / CONTROLLED DECISION RECORD", styles["Eyebrow"]),
        Paragraph("Innovation Intelligence Report", styles["TitleNavy"]),
        Spacer(1, 4 * mm),
        Paragraph(_safe(case.title), styles["Heading2"]),
        Paragraph(_safe(run.result["executive_summary"]), styles["BodyMuted"]),
        Spacer(1, 6 * mm),
        Table(
            [
                ["Case", f"CASE-{case.id:05d}"],
                ["Generated", generated_at.isoformat()],
                ["Corpus", run.corpus_version],
                ["Analysis run", str(run.id)],
                ["Record hash", payload_hash],
            ],
            colWidths=[34 * mm, 122 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), PALE),
                    ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
                    ("TEXTCOLOR", (1, 0), (1, -1), MUTED),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        ),
        Paragraph("Risk and opportunity signals", styles["Section"]),
    ]

    risk_cells = []
    for risk in run.result["risk_cards"]:
        risk_cells.append(
            [
                Paragraph(str(risk["score"]), styles["Score"]),
                Paragraph(f"<b>{_safe(risk['title'])}</b><br/>{_safe(risk['level'])}", styles["Small"]),
                Paragraph(_safe(risk["summary"]), styles["Small"]),
            ]
        )
    risk_table = Table(risk_cells, colWidths=[18 * mm, 44 * mm, 94 * mm])
    risk_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("BACKGROUND", (0, 0), (0, -1), PALE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(risk_table)

    story.extend([Paragraph("Recommended protection strategy", styles["Section"])])
    for item in run.result["ip_strategy"]["recommended_strategy"]:
        story.append(Paragraph(f"• {_safe(item)}", styles["BodyMuted"]))

    story.extend([Paragraph("Regulatory and ABS pathway", styles["Section"])])
    for step in run.result["regulatory_abs"]["steps"]:
        story.append(
            KeepTogether(
                [
                    Paragraph(f"<b>{step['order']}. {_safe(step['name'])}</b> — {_safe(step['status'])}", styles["BodyMuted"]),
                    Paragraph(_safe(step["detail"]), styles["Small"]),
                    Spacer(1, 2 * mm),
                ]
            )
        )

    story.extend([PageBreak(), Paragraph("Challenge My Innovation", styles["Section"])])
    for reviewer, objections in run.result["challenges"].items():
        story.append(Paragraph(_safe(reviewer.replace("_", " ").title()), styles["Heading3"]))
        for objection in objections:
            story.append(
                Paragraph(
                    f"<b>{_safe(objection['severity'].upper())}:</b> {_safe(objection['objection'])}<br/>"
                    f"<b>Missing:</b> {_safe(objection['missing'])}<br/>"
                    f"<b>Next step:</b> {_safe(objection['next_step'])}",
                    styles["Small"],
                )
            )
            story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Next actions", styles["Section"]))
    for index, item in enumerate(run.result["next_actions"], start=1):
        story.append(Paragraph(f"{index}. {_safe(item)}", styles["BodyMuted"]))

    citations = _collect_citations(run.result)
    story.extend([PageBreak(), Paragraph("Evidence register", styles["Section"])])
    if citations:
        for index, citation in enumerate(citations, start=1):
            locator = f" · {citation['locator']}" if citation.get("locator") else ""
            story.append(
                Paragraph(
                    f"<b>[{index}] {_safe(citation['title'])}</b><br/>"
                    f"{_safe(citation['authority'])} · {_safe(citation['jurisdiction'])}{_safe(locator)}<br/>"
                    f"Status: {_safe(citation['support_status'])} · Date: {_safe(citation['effective_date'])}<br/>"
                    f"{_safe(citation['excerpt'])}<br/><link href=\"{_safe(citation['url'])}\" color=\"#17766F\">{_safe(citation['url'])}</link>",
                    styles["Small"],
                )
            )
            story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("No evidence citations were recorded.", styles["BodyMuted"]))

    story.extend(
        [
            Paragraph("Limitations and decision boundary", styles["Section"]),
            Paragraph(_safe(disclaimer), styles["BodyMuted"]),
            Paragraph(
                "User-supplied documents are integrity-hashed and retrieved as evidence, but their authenticity, completeness, legal status and scientific quality are not independently verified by the system.",
                styles["BodyMuted"],
            ),
        ]
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 8 * mm, f"CASE-{case.id:05d} · {payload_hash[:16]}")
        canvas.drawRightString(192 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
