import io
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab import rl_config
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import ChangeType, Comparison, ImpactFinding, ImportBatch, Project, RequirementChange, ReviewStatus, Severity


BLUE = colors.HexColor("#2563eb")
NAVY = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
LINE = colors.HexColor("#d8e0ea")
PANEL = colors.HexColor("#f8fafc")
HIGH = colors.HexColor("#dc2626")
MEDIUM = colors.HexColor("#d97706")
LOW = colors.HexColor("#0284c7")
GREEN = colors.HexColor("#16a34a")

SEVERITY_ORDER = [Severity.HIGH, Severity.MEDIUM, Severity.LOW]
REVIEW_ORDER = [ReviewStatus.CONFIRMED, ReviewStatus.DISMISSED, ReviewStatus.UNREVIEWED]
rl_config.useA85 = 0


def draw_radar_logo(canvas: Canvas, x: float, y: float, size: float) -> None:
    canvas.saveState()
    canvas.setFillColor(BLUE)
    canvas.roundRect(x, y, size, size, size * 0.25, fill=1, stroke=0)

    center_x = x + size / 2
    center_y = y + size / 2
    outer_radius = size * 0.31
    inner_radius = size * 0.18
    canvas.setStrokeColor(colors.white)
    canvas.setLineCap(1)
    canvas.setLineWidth(size * 0.075)
    canvas.arc(
        center_x - outer_radius,
        center_y - outer_radius,
        center_x + outer_radius,
        center_y + outer_radius,
        25,
        255,
    )
    canvas.arc(
        center_x - outer_radius,
        center_y - outer_radius,
        center_x + outer_radius,
        center_y + outer_radius,
        315,
        50,
    )
    canvas.setLineWidth(size * 0.068)
    canvas.arc(
        center_x - inner_radius,
        center_y - inner_radius,
        center_x + inner_radius,
        center_y + inner_radius,
        150,
        255,
    )
    canvas.setLineWidth(size * 0.085)
    canvas.line(center_x, center_y, x + size * 0.32, y + size * 0.72)

    canvas.setFillColor(colors.white)
    canvas.circle(center_x, center_y, size * 0.065, fill=1, stroke=0)
    canvas.circle(x + size * 0.72, y + size * 0.65, size * 0.058, fill=1, stroke=0)
    canvas.circle(x + size * 0.43, y + size * 0.23, size * 0.052, fill=1, stroke=0)
    canvas.restoreState()


class RadarLogoFlowable(Flowable):
    def __init__(self, size: float):
        super().__init__()
        self.width = size
        self.height = size
        self.size = size

    def draw(self) -> None:
        draw_radar_logo(self.canv, 0, 0, self.size)


@dataclass(frozen=True)
class ReportStats:
    modified: int
    added: int
    removed: int
    unchanged: int
    total_findings: int
    severity_counts: Counter
    review_counts: Counter

    @property
    def changed_total(self) -> int:
        return self.modified + self.added + self.removed

    @property
    def reviewed_total(self) -> int:
        return self.review_counts[ReviewStatus.CONFIRMED] + self.review_counts[ReviewStatus.DISMISSED]


class ReportCanvas(Canvas):
    def __init__(self, *args, project_name: str, generated_at: datetime, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_name = project_name
        self.generated_at = generated_at
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_furniture(page_count)
            super().showPage()
        super().save()

    def _draw_page_furniture(self, page_count: int):
        width, height = letter
        self.saveState()
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(0.6 * inch, height - 0.55 * inch, width - 0.6 * inch, height - 0.55 * inch)
        logo_size = 0.18 * inch
        logo_x = 0.6 * inch
        logo_y = height - 0.47 * inch
        draw_radar_logo(self, logo_x, logo_y, logo_size)
        self.setFillColor(NAVY)
        self.setFont("Helvetica-Bold", 8.5)
        self.drawString(logo_x + logo_size + 0.08 * inch, height - 0.38 * inch, "ReqRadar | Requirements Impact Analysis")
        self.setFont("Helvetica", 8)
        self.setFillColor(MUTED)
        self.drawRightString(width - 0.6 * inch, height - 0.38 * inch, self.project_name[:70])
        self.line(0.6 * inch, 0.55 * inch, width - 0.6 * inch, 0.55 * inch)
        self.drawString(0.6 * inch, 0.35 * inch, f"Generated {self.generated_at.strftime('%Y-%m-%d %H:%M UTC')}")
        self.drawRightString(width - 0.6 * inch, 0.35 * inch, f"Page {self._pageNumber} / {page_count}")
        self.restoreState()


def build_requirements_impact_pdf(project: Project, comparison: Comparison, imports: list[ImportBatch], changes: list[RequirementChange], findings: list[ImpactFinding]) -> bytes:
    generated_at = datetime.now(UTC)
    stats = calculate_stats(comparison, findings)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.78 * inch,
        bottomMargin=0.72 * inch,
        title=f"ReqRadar Requirements Impact Analysis - {project.name}",
        author="ReqRadar",
        subject="Requirements Impact Analysis",
        pageCompression=0,
    )
    styles = report_styles()
    story: list = []
    baseline, target = comparison_versions(comparison, imports)
    story.extend(executive_summary(project, comparison, baseline, target, generated_at, stats, changes, findings, styles))
    story.extend(change_overview(changes, findings, styles))
    for severity in SEVERITY_ORDER:
        section = severity_section(severity, findings, styles)
        if section:
            story.extend(section)
    review_section = reviewed_findings(findings, styles)
    if review_section:
        story.extend(review_section)
    story.extend(methodology_section(baseline, target, styles))

    doc.build(story, canvasmaker=lambda *args, **kwargs: ReportCanvas(*args, project_name=project.name, generated_at=generated_at, **kwargs))
    return buffer.getvalue()


def report_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=19, leading=23, textColor=NAVY, spaceAfter=5),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontSize=10, leading=14, textColor=MUTED, spaceAfter=12),
        "section": ParagraphStyle("section", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=16, spaceAfter=8),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontSize=8.5, leading=12, textColor=NAVY),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontSize=7.5, leading=10, textColor=MUTED),
        "table_header": ParagraphStyle("table_header", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.white, alignment=TA_CENTER),
        "table_cell": ParagraphStyle("table_cell", parent=base["BodyText"], fontSize=7.2, leading=9.2, textColor=NAVY),
        "kpi_value": ParagraphStyle("kpi_value", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=16, leading=18, textColor=NAVY, alignment=TA_CENTER),
        "kpi_label": ParagraphStyle("kpi_label", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=6.8, leading=8, textColor=MUTED, alignment=TA_CENTER),
        "finding_title": ParagraphStyle("finding_title", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=NAVY),
        "finding_body": ParagraphStyle("finding_body", parent=base["BodyText"], fontSize=7.8, leading=10.5, textColor=NAVY),
    }


def calculate_stats(comparison: Comparison, findings: list[ImpactFinding]) -> ReportStats:
    summary = comparison.summary_json or {}
    severity_counts = Counter(finding.severity for finding in findings)
    review_counts = Counter(finding.review_status for finding in findings)
    return ReportStats(
        modified=int(summary.get(ChangeType.MODIFIED.value, summary.get("MODIFIED", 0)) or 0),
        added=int(summary.get(ChangeType.ADDED.value, summary.get("ADDED", 0)) or 0),
        removed=int(summary.get(ChangeType.REMOVED.value, summary.get("REMOVED", 0)) or 0),
        unchanged=int(summary.get(ChangeType.UNCHANGED.value, summary.get("UNCHANGED", 0)) or 0),
        total_findings=len(findings),
        severity_counts=severity_counts,
        review_counts=review_counts,
    )


def comparison_versions(comparison: Comparison, imports: list[ImportBatch]) -> tuple[str, str]:
    by_id = {item.id: item for item in imports}
    baseline = by_id.get(comparison.baseline_import_id)
    target = by_id.get(comparison.comparison_import_id)
    return format_import_label(baseline), format_import_label(target)


def format_import_label(batch: ImportBatch | None) -> str:
    if batch is None:
        return ""
    if batch.filename:
        return f"{batch.version_label} ({batch.filename})"
    return batch.version_label


def executive_summary(project: Project, comparison: Comparison, baseline: str, target: str, generated_at: datetime, stats: ReportStats, changes: list[RequirementChange], findings: list[ImpactFinding], styles: dict[str, ParagraphStyle]) -> list:
    elements = [
        brand_title(styles),
        Paragraph("Requirements Impact Analysis", styles["subtitle"]),
        meta_table(
            [
                ("Project", project.name),
                ("Comparison", f"{baseline} \u2192 {target}" if baseline or target else "Not available"),
                ("Generated", generated_at.strftime("%Y-%m-%d %H:%M UTC")),
            ],
            styles,
        ),
        Paragraph("Executive Summary", styles["section"]),
        Paragraph(executive_assessment(stats), styles["body"]),
        Spacer(1, 8),
        kpi_grid(
            [
                ("Modified", stats.modified),
                ("Added", stats.added),
                ("Removed", stats.removed),
                ("Unchanged", stats.unchanged),
                ("Potential Impacts", stats.total_findings),
                ("High Impact", stats.severity_counts[Severity.HIGH]),
                ("Medium Impact", stats.severity_counts[Severity.MEDIUM]),
                ("Low Impact", stats.severity_counts[Severity.LOW]),
            ],
            styles,
        ),
    ]
    if stats.total_findings:
        elements.extend([Spacer(1, 8), review_progress(stats, styles)])
    ranked = highest_impact_requirements(changes, findings)
    if ranked:
        elements.extend([Paragraph("Highest Impact Requirements", styles["section"]), highest_impact_table(ranked, styles)])
    return elements


def brand_title(styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[RadarLogoFlowable(0.32 * inch), Paragraph("ReqRadar", styles["title"])]],
        colWidths=[0.4 * inch, 1.55 * inch],
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def executive_assessment(stats: ReportStats) -> str:
    priority = ""
    if stats.severity_counts[Severity.HIGH]:
        priority = f" {stats.severity_counts[Severity.HIGH]} findings are classified as high impact and should receive priority review."
    elif stats.total_findings:
        priority = " No high-impact findings were identified in the current report state."
    return f"This comparison identified {stats.changed_total} changed requirements and {stats.total_findings} potential downstream impacts.{priority}"


def meta_table(rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[Paragraph(label, styles["small"]), Paragraph(value or "Not available", styles["body"])] for label, value in rows]
    table = Table(data, colWidths=[1.05 * inch, 5.75 * inch])
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    return table


def kpi_grid(items: list[tuple[str, int]], styles: dict[str, ParagraphStyle]) -> Table:
    rows = []
    for start in range(0, len(items), 4):
        row = []
        for label, value in items[start : start + 4]:
            row.append([Paragraph(str(value), styles["kpi_value"]), Paragraph(label.upper(), styles["kpi_label"])])
        rows.append(row)
    table = Table(rows, colWidths=[1.65 * inch] * 4, hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return table


def review_progress(stats: ReportStats, styles: dict[str, ParagraphStyle]) -> Table:
    pct = stats.reviewed_total / stats.total_findings if stats.total_findings else 0
    progress_width = 3.8 * inch
    bar = Table([["", ""]], colWidths=[max(progress_width * pct, 0.01 * inch), max(progress_width * (1 - pct), 0.01 * inch)], rowHeights=[0.12 * inch])
    bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), BLUE), ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#e2e8f0")), ("BOX", (0, 0), (-1, -1), 0.4, LINE)]))
    table = Table(
        [
            [Paragraph("Review Progress", styles["section"])],
            [Paragraph(f"Reviewed: {stats.reviewed_total} / {stats.total_findings}   Confirmed: {stats.review_counts[ReviewStatus.CONFIRMED]}   Dismissed: {stats.review_counts[ReviewStatus.DISMISSED]}   Unreviewed: {stats.review_counts[ReviewStatus.UNREVIEWED]}", styles["body"])],
            [bar],
        ],
        colWidths=[6.8 * inch],
    )
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return table


def highest_impact_requirements(changes: list[RequirementChange], findings: list[ImpactFinding], limit: int = 6) -> list[tuple[str, int, int]]:
    by_change = {change.id: change.external_id for change in changes}
    totals: dict[str, int] = defaultdict(int)
    highs: dict[str, int] = defaultdict(int)
    for finding in findings:
        external_id = by_change.get(finding.requirement_change_id)
        if not external_id:
            continue
        totals[external_id] += 1
        if finding.severity == Severity.HIGH:
            highs[external_id] += 1
    ranked = sorted(((req, totals[req], highs[req]) for req in totals), key=lambda item: (-item[2], -item[1], item[0]))
    return ranked[:limit]


def highest_impact_table(rows: list[tuple[str, int, int]], styles: dict[str, ParagraphStyle]) -> Table:
    data = [[Paragraph("Requirement", styles["table_header"]), Paragraph("Findings", styles["table_header"]), Paragraph("High", styles["table_header"])]]
    data.extend([[table_cell(req, styles), table_cell(count, styles), table_cell(high, styles)] for req, count, high in rows])
    return styled_table(data, [4.8 * inch, 1 * inch, 1 * inch])


def change_overview(changes: list[RequirementChange], findings: list[ImpactFinding], styles: dict[str, ParagraphStyle]) -> list:
    changed = [change for change in changes if change.change_type != ChangeType.UNCHANGED]
    if not changed:
        return []
    by_change: dict[object, list[ImpactFinding]] = defaultdict(list)
    for finding in findings:
        by_change[finding.requirement_change_id].append(finding)
    ranked = sorted(changed, key=lambda change: (-sum(1 for item in by_change[change.id] if item.severity == Severity.HIGH), -len(by_change[change.id]), change.external_id))
    data = [[Paragraph("Requirement ID", styles["table_header"]), Paragraph("Change Type", styles["table_header"]), Paragraph("Impact Findings", styles["table_header"]), Paragraph("High", styles["table_header"]), Paragraph("Review Status", styles["table_header"])]]
    for change in ranked:
        related = by_change[change.id]
        high_count = sum(1 for item in related if item.severity == Severity.HIGH)
        status = review_summary(related)
        data.append([table_cell(change.external_id, styles), table_cell(change.change_type.value, styles), table_cell(len(related), styles), table_cell(high_count, styles), table_cell(status, styles)])
    return [Paragraph("Change Overview", styles["section"]), styled_table(data, [1.65 * inch, 1.05 * inch, 1.15 * inch, 0.65 * inch, 2.3 * inch])]


def review_summary(findings: list[ImpactFinding]) -> str:
    if not findings:
        return "No findings"
    counts = Counter(finding.review_status for finding in findings)
    if counts[ReviewStatus.UNREVIEWED]:
        return f"Needs review ({counts[ReviewStatus.UNREVIEWED]} unreviewed)"
    return f"Reviewed ({counts[ReviewStatus.CONFIRMED]} confirmed, {counts[ReviewStatus.DISMISSED]} dismissed)"


def styled_table(data: list, col_widths: list[float]) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.35, LINE), ("BACKGROUND", (0, 1), (-1, -1), colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    return table


def table_cell(value: object, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(value), styles["table_cell"])


def severity_section(severity: Severity, findings: list[ImpactFinding], styles: dict[str, ParagraphStyle]) -> list:
    section_findings = sorted((finding for finding in findings if finding.severity == severity), key=lambda item: (review_sort(item.review_status), item.change.external_id, item.impacted_requirement_external_id))
    if not section_findings:
        return []
    elements = [Paragraph(f"{severity.value.title()} Impact Findings", styles["section"])]
    for finding in section_findings:
        elements.append(finding_block(finding, styles))
    return elements


def review_sort(status: ReviewStatus) -> int:
    try:
        return REVIEW_ORDER.index(status)
    except ValueError:
        return len(REVIEW_ORDER)


def finding_block(finding: ImpactFinding, styles: dict[str, ParagraphStyle]) -> KeepTogether:
    accent = severity_color(finding.severity)
    status_color = review_color(finding.review_status)
    severity_badge = badge(finding.severity.value, accent)
    review_badge = badge(finding.review_status.value, status_color)
    title = Table([[severity_badge, review_badge]], colWidths=[1 * inch, 1.3 * inch], hAlign="LEFT")
    title.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    rows = [
        [title],
        [Paragraph(f"<b>{escape(finding.change.external_id)}</b> \u2192 impacts \u2192 <b>{escape(finding.impacted_requirement_external_id)}</b>", styles["finding_title"])],
        [Paragraph("<b>Why this was flagged</b>", styles["small"])],
        [Paragraph(escape(finding.reason), styles["finding_body"])],
        [Paragraph(f"Confidence: {finding.confidence * 100:.0f}% &nbsp;&nbsp; Detection: {escape(finding.detection_method)} &nbsp;&nbsp; Relationship: {escape(finding.relationship_type)}", styles["small"])],
    ]
    if finding.manually_adjusted_severity:
        rows.append([Paragraph("Severity was manually adjusted in review.", styles["small"])])
    if finding.reviewer_note:
        rows.extend([[Paragraph("<b>Reviewer note</b>", styles["small"])], [Paragraph(escape(finding.reviewer_note), styles["finding_body"])]])
    table = Table(rows, colWidths=[6.8 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.white), ("BOX", (0, 0), (-1, -1), 0.5, LINE), ("LINEBEFORE", (0, 0), (0, -1), 3, accent), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return KeepTogether([table, Spacer(1, 6)])


def badge(text: str, color: colors.Color) -> Table:
    style = ParagraphStyle("badge", fontName="Helvetica-Bold", fontSize=6.5, leading=8, textColor=colors.white, alignment=TA_CENTER)
    table = Table([[Paragraph(text, style)]], colWidths=[0.95 * inch], rowHeights=[0.18 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), color), ("BOX", (0, 0), (-1, -1), 0, color), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return table


def severity_color(severity: Severity) -> colors.Color:
    return {Severity.HIGH: HIGH, Severity.MEDIUM: MEDIUM, Severity.LOW: LOW}[severity]


def review_color(status: ReviewStatus) -> colors.Color:
    return {ReviewStatus.CONFIRMED: GREEN, ReviewStatus.DISMISSED: MUTED, ReviewStatus.UNREVIEWED: MEDIUM}[status]


def reviewed_findings(findings: list[ImpactFinding], styles: dict[str, ParagraphStyle]) -> list:
    reviewed = [finding for finding in findings if finding.review_status != ReviewStatus.UNREVIEWED]
    if not reviewed:
        return []
    data = [[Paragraph("Requirement", styles["table_header"]), Paragraph("Impacted", styles["table_header"]), Paragraph("Severity", styles["table_header"]), Paragraph("Review", styles["table_header"]), Paragraph("Reviewer Note", styles["table_header"])]]
    for finding in sorted(reviewed, key=lambda item: (item.review_status.value, item.change.external_id, item.impacted_requirement_external_id)):
        data.append([table_cell(finding.change.external_id, styles), table_cell(finding.impacted_requirement_external_id, styles), table_cell(finding.severity.value, styles), table_cell(finding.review_status.value, styles), table_cell(finding.reviewer_note or "", styles)])
    return [Paragraph("Reviewed Findings", styles["section"]), styled_table(data, [1.25 * inch, 1.25 * inch, 0.8 * inch, 0.95 * inch, 2.55 * inch])]


def methodology_section(baseline: str, target: str, styles: dict[str, ParagraphStyle]) -> list:
    body = [
        "This report is generated deterministically from the selected ReqRadar comparison.",
        "Findings are grouped by effective severity and show the review state at export time.",
        "Counts are calculated from the comparison summary and associated impact findings.",
    ]
    if baseline or target:
        body.append(f"Compared versions: {baseline or 'Not available'} \u2192 {target or 'Not available'}.")
    return [Paragraph("Methodology / Report Information", styles["section"]), Paragraph(" ".join(body), styles["body"])]


def escape(value: object) -> str:
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
