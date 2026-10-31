"""Professional server-side PDF payslips, built with ReportLab.

The payslip is rendered entirely from ``PayrollRecord`` snapshot fields, so it
never changes when the employee's current salary structure is revised.
"""

import calendar
from decimal import Decimal
from html import escape
from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

from apps.organization.models import CompanyProfile

from .models import PayrollRecord

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#d8dee8")
HEADER_BG = colors.HexColor("#0f172a")
SOFT_BG = colors.HexColor("#f4f7fb")
ACCENT = colors.HexColor("#1d4ed8")
ACCENT_SOFT = colors.HexColor("#e8efff")

EARNING_LABELS = {
    "basic_salary": "Basic salary",
    "hra": "House rent allowance (HRA)",
    "conveyance_allowance": "Conveyance allowance",
    "medical_allowance": "Medical allowance",
    "special_allowance": "Special allowance",
    "other_allowances": "Other allowances",
}
DEDUCTION_LABELS = {
    "provident_fund": "Provident fund (PF)",
    "professional_tax": "Professional tax",
    "income_tax": "Income tax / TDS",
    "other_deductions": "Other deductions",
}


def _money(amount: Decimal | None, currency: str) -> str:
    value = amount if amount is not None else Decimal("0.00")
    return f"{currency} {value:,.2f}"


def _date(value) -> str:
    return value.strftime("%d %b %Y") if value else "—"


def _company() -> tuple[str, CompanyProfile | None, list[str]]:
    profile = CompanyProfile.load()
    name = (
        profile.name if profile else getattr(settings, "PAYROLL_COMPANY_NAME", "HRMS")
    )
    lines: list[str] = []
    if profile:
        if profile.address:
            lines.extend(
                line.strip() for line in profile.address.splitlines() if line.strip()
            )
        contact = " · ".join(
            part for part in (profile.email, profile.phone, profile.website) if part
        )
        if contact:
            lines.append(contact)
    return name, profile, lines


def _logo(profile: CompanyProfile | None, max_width: float, max_height: float):
    if profile is None or not profile.logo:
        return None
    try:
        path = profile.logo.path
        reader = ImageReader(path)
        width, height = reader.getSize()
    except Exception:  # noqa: BLE001 - a missing/broken logo must not break a payslip
        return None

    scale = min(max_width / width, max_height / height)
    return Image(path, width=width * scale, height=height * scale)


def _header(story: list, record: PayrollRecord) -> None:
    name, profile, contact_lines = _company()
    currency = getattr(settings, "PAYROLL_CURRENCY", "INR")

    logo = _logo(profile, max_width=38 * mm, max_height=16 * mm)
    company_bits = [Paragraph(f"<b>{escape(name)}</b>", _styles()["company"])]
    for line in contact_lines[:2]:
        company_bits.append(Paragraph(escape(line), _styles()["meta"]))
    if logo is not None:
        left = Table([[logo, company_bits]], colWidths=[42 * mm, 76 * mm])
        left.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
    else:
        left = company_bits

    right = [
        Paragraph("PAYSLIP", _styles()["payslip"]),
        Paragraph(
            f"<b>{calendar.month_name[record.payroll_month]} {record.payroll_year}</b>",
            _styles()["meta"],
        ),
        Paragraph(f"Payslip no. {record.payslip_number}", _styles()["meta"]),
        Paragraph(f"Status: {record.get_status_display()}", _styles()["meta"]),
    ]

    header = Table([[left, right]], colWidths=[120 * mm, 60 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header)
    story.append(HRFlowable(width="100%", thickness=1.2, color=INK, spaceAfter=8))

    if record.status != PayrollRecord.Status.FINALIZED:
        story.append(
            Paragraph(
                "DRAFT — not a finalized payslip",
                _styles()["draft"],
            )
        )
        story.append(Spacer(1, 5))

    story.append(Paragraph("EMPLOYEE DETAILS", _styles()["section"]))
    details = [
        ("Employee name", record.employee_name, "Employee ID", record.employee_code),
        (
            "Designation",
            record.designation or "—",
            "Department",
            record.department or "—",
        ),
        (
            "Date of joining",
            _date(record.date_of_joining),
            "Pay period",
            f"{calendar.month_name[record.payroll_month]} {record.payroll_year}",
        ),
        (
            "Payslip number",
            record.payslip_number,
            "Payment status",
            record.get_payment_status_display(),
        ),
    ]
    detail_rows = [
        [
            Paragraph(f"<b>{label}</b>", _styles()["label"]),
            Paragraph(escape(str(value)), _styles()["value"]),
            Paragraph(f"<b>{right_label}</b>", _styles()["label"]),
            Paragraph(escape(str(right_value)), _styles()["value"]),
        ]
        for label, value, right_label, right_value in details
    ]
    table = Table(detail_rows, colWidths=[32 * mm, 58 * mm, 32 * mm, 58 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("SALARY BREAKDOWN", _styles()["section"]))
    _salary_table(story, record, currency)
    story.append(Spacer(1, 10))
    _net_pay(story, record, currency)
    story.append(Spacer(1, 10))
    _payment_details(story, record)


def _salary_table(story: list, record: PayrollRecord, currency: str) -> None:
    earning_rows = [
        (label, _money(getattr(record, field), currency))
        for field, label in EARNING_LABELS.items()
    ]
    deduction_rows = [
        (label, _money(getattr(record, field), currency))
        for field, label in DEDUCTION_LABELS.items()
    ]

    rows = [
        [
            Paragraph("EARNINGS", _styles()["table_head"]),
            Paragraph("AMOUNT", _styles()["table_head_right"]),
            Paragraph("DEDUCTIONS", _styles()["table_head"]),
            Paragraph("AMOUNT", _styles()["table_head_right"]),
        ]
    ]
    for index in range(max(len(earning_rows), len(deduction_rows))):
        earning = earning_rows[index] if index < len(earning_rows) else ("", "")
        deduction = deduction_rows[index] if index < len(deduction_rows) else ("", "")
        rows.append(
            [
                Paragraph(earning[0], _styles()["cell"]),
                Paragraph(earning[1], _styles()["cell_right"]),
                Paragraph(deduction[0], _styles()["cell"]),
                Paragraph(deduction[1], _styles()["cell_right"]),
            ]
        )
    rows.append(
        [
            Paragraph("<b>Gross earnings</b>", _styles()["cell"]),
            Paragraph(
                f"<b>{_money(record.gross_salary, currency)}</b>",
                _styles()["cell_right"],
            ),
            Paragraph("<b>Total deductions</b>", _styles()["cell"]),
            Paragraph(
                f"<b>{_money(record.total_deductions, currency)}</b>",
                _styles()["cell_right"],
            ),
        ]
    )

    table = Table(rows, colWidths=[62 * mm, 28 * mm, 62 * mm, 28 * mm], repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("BACKGROUND", (0, -1), (-1, -1), SOFT_BG),
        ("LINEABOVE", (0, -1), (-1, -1), 0.8, INK),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]
    table.setStyle(TableStyle(style))
    story.append(table)


def _net_pay(story: list, record: PayrollRecord, currency: str) -> None:
    adjustment = record.adjustment_amount or Decimal("0.00")
    rows = []
    if adjustment != 0:
        label = "Adjustment (addition)" if adjustment > 0 else "Adjustment (deduction)"
        rows.append(
            [
                Paragraph(label, _styles()["cell"]),
                Paragraph(_money(adjustment, currency), _styles()["cell_right"]),
            ]
        )
        if record.adjustment_note:
            rows.append(
                [
                    Paragraph(escape(record.adjustment_note), _styles()["note"]),
                    Paragraph("", _styles()["cell"]),
                ]
            )

    rows.append(
        [
            Paragraph("NET SALARY PAYABLE", _styles()["net_label"]),
            Paragraph(_money(record.net_salary, currency), _styles()["net_value"]),
        ]
    )

    table = Table(rows, colWidths=[130 * mm, 50 * mm])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, -1), (-1, -1), ACCENT_SOFT),
                ("BOX", (0, -1), (-1, -1), 1, ACCENT),
                ("LINEABOVE", (0, -1), (-1, -1), 1, ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)


def _payment_details(story: list, record: PayrollRecord) -> None:
    payment_date = _date(record.payment_date) if record.payment_date else "—"
    reference = record.payment_reference or "—"
    rows = [
        [
            Paragraph("Payment status", _styles()["label"]),
            Paragraph(record.get_payment_status_display(), _styles()["value"]),
            Paragraph("Payment date", _styles()["label"]),
            Paragraph(payment_date, _styles()["value"]),
        ],
        [
            Paragraph("Payment reference", _styles()["label"]),
            Paragraph(escape(reference), _styles()["value"]),
            Paragraph("Finalized on", _styles()["label"]),
            Paragraph(_date(record.finalized_at), _styles()["value"]),
        ],
    ]
    table = Table(rows, colWidths=[34 * mm, 56 * mm, 34 * mm, 56 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(Paragraph("PAYMENT DETAILS", _styles()["section"]))
    story.append(table)


def _styles() -> dict:
    styles = getSampleStyleSheet()
    return {
        "company": ParagraphStyle(
            "Company",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=19,
            textColor=INK,
            alignment=0,
            spaceAfter=2,
        ),
        "payslip": ParagraphStyle(
            "Payslip",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=23,
            textColor=INK,
            alignment=2,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=11,
            textColor=MUTED,
            alignment=2,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=ACCENT,
            spaceBefore=2,
            spaceAfter=5,
        ),
        "label": ParagraphStyle(
            "Label",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=MUTED,
        ),
        "value": ParagraphStyle(
            "Value",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11.5,
            textColor=INK,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.5,
            textColor=INK,
        ),
        "cell_right": ParagraphStyle(
            "CellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.5,
            textColor=INK,
            alignment=2,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=colors.white,
        ),
        "table_head_right": ParagraphStyle(
            "TableHeadRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
            textColor=colors.white,
            alignment=2,
        ),
        "net_label": ParagraphStyle(
            "NetLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=13,
            textColor=ACCENT,
        ),
        "net_value": ParagraphStyle(
            "NetValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=ACCENT,
            alignment=2,
        ),
        "note": ParagraphStyle(
            "Note",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=10.5,
            textColor=MUTED,
            alignment=0,
        ),
        "draft": ParagraphStyle(
            "Draft",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#b91c1c"),
            alignment=1,
        ),
    }


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _height = A4
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.6)
    canvas.line(15 * mm, 15 * mm, width - 15 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(15 * mm, 10.5 * mm, "This is a computer-generated payslip.")
    canvas.drawRightString(width - 15 * mm, 10.5 * mm, "Page 1 of 1")
    canvas.restoreState()


def render_payslip(record: PayrollRecord) -> bytes:
    """Render one payroll record as PDF bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title=f"Payslip {record.payslip_number}",
        author="HRMS",
        subject=f"Payslip for {record.employee_name} · {record.pay_period_label}",
    )
    story: list = []
    _header(story, record)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
