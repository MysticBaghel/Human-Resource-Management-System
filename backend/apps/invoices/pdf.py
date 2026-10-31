"""Server-side PDF invoices, built with ReportLab.

Everything is rendered from snapshot fields on the invoice and its line items,
so a later client edit or payment never changes an already-issued PDF.
"""

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

from apps.organization.models import CompanyProfile

from .models import Invoice

INK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#64748b")
BORDER = colors.HexColor("#d8dee8")
HEADER_BG = colors.HexColor("#0f172a")
SOFT_BG = colors.HexColor("#f4f7fb")
ACCENT = colors.HexColor("#1d4ed8")
ACCENT_SOFT = colors.HexColor("#e8efff")
DANGER = colors.HexColor("#b91c1c")


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
    except Exception:  # noqa: BLE001 - a broken logo must not break the invoice
        return None
    scale = min(max_width / width, max_height / height)
    return Image(path, width=width * scale, height=height * scale)


def _header(story: list, invoice: Invoice) -> None:
    name, profile, contact_lines = _company()
    logo = _logo(profile, max_width=38 * mm, max_height=16 * mm)

    company_bits = [Paragraph(f"<b>{escape(name)}</b>", _styles()["company"])]
    for line in contact_lines[:3]:
        company_bits.append(Paragraph(escape(line), _styles()["meta"]))
    if logo is not None:
        left = Table([[logo, company_bits]], colWidths=[42 * mm, 80 * mm])
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
        Paragraph("INVOICE", _styles()["invoice"]),
        Paragraph(f"<b>{escape(invoice.invoice_number)}</b>", _styles()["number"]),
        Paragraph(f"Status: {invoice.get_status_display()}", _styles()["meta"]),
        Paragraph(f"Issued: {_date(invoice.issue_date)}", _styles()["meta"]),
        Paragraph(f"Due: {_date(invoice.due_date)}", _styles()["meta"]),
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
    story.append(Spacer(1, 2))
    story.append(
        Table(
            [[""]],
            colWidths=[180 * mm],
            rowHeights=[1.4],
            style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK)]),
        )
    )
    story.append(Spacer(1, 10))

    if invoice.status == Invoice.Status.CANCELLED:
        story.append(
            Paragraph(
                "CANCELLED — this invoice is not payable.",
                _styles()["status_bad"],
            )
        )
        story.append(Spacer(1, 6))
    elif invoice.status == Invoice.Status.DRAFT:
        story.append(
            Paragraph(
                "DRAFT — not yet issued to the client.",
                _styles()["status_draft"],
            )
        )
        story.append(Spacer(1, 6))


def _parties(story: list, invoice: Invoice) -> None:
    billed = [
        Paragraph("BILL TO", _styles()["section"]),
        Paragraph(f"<b>{escape(invoice.client_name)}</b>", _styles()["value"]),
    ]
    if invoice.client_contact_name:
        billed.append(
            Paragraph(escape(invoice.client_contact_name), _styles()["meta_left"])
        )
    if invoice.client_address:
        for line in invoice.client_address.splitlines():
            if line.strip():
                billed.append(Paragraph(escape(line.strip()), _styles()["meta_left"]))
    if invoice.client_email:
        billed.append(Paragraph(escape(invoice.client_email), _styles()["meta_left"]))
    if invoice.client_tax_id:
        billed.append(
            Paragraph(
                f"Tax ID: {escape(invoice.client_tax_id)}",
                _styles()["meta_left"],
            )
        )

    details = [
        Paragraph("INVOICE DETAILS", _styles()["section"]),
        Paragraph(
            f"<b>Issue date:</b> {_date(invoice.issue_date)}",
            _styles()["meta_left"],
        ),
        Paragraph(
            f"<b>Due date:</b> {_date(invoice.due_date)}",
            _styles()["meta_left"],
        ),
        Paragraph(
            f"<b>Currency:</b> {escape(invoice.currency)}", _styles()["meta_left"]
        ),
    ]
    if invoice.reference:
        details.append(
            Paragraph(
                f"<b>Reference:</b> {escape(invoice.reference)}",
                _styles()["meta_left"],
            )
        )

    table = Table([[billed, details]], colWidths=[105 * mm, 75 * mm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), SOFT_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))


def _items(story: list, invoice: Invoice) -> None:
    rows = [
        [
            Paragraph("#", _styles()["table_head"]),
            Paragraph("DESCRIPTION", _styles()["table_head"]),
            Paragraph("QTY", _styles()["table_head_right"]),
            Paragraph("RATE", _styles()["table_head_right"]),
            Paragraph("AMOUNT", _styles()["table_head_right"]),
        ]
    ]
    for index, item in enumerate(invoice.items.all(), start=1):
        rows.append(
            [
                Paragraph(str(index), _styles()["cell"]),
                Paragraph(escape(item.description), _styles()["cell"]),
                Paragraph(f"{item.quantity:,.2f}", _styles()["cell_right"]),
                Paragraph(
                    _money(item.unit_price, invoice.currency),
                    _styles()["cell_right"],
                ),
                Paragraph(
                    _money(item.amount, invoice.currency),
                    _styles()["cell_right"],
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[10 * mm, 94 * mm, 20 * mm, 28 * mm, 28 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#fafbfd")],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(Paragraph("ITEMS", _styles()["section"]))
    story.append(table)
    story.append(Spacer(1, 10))


def _totals(story: list, invoice: Invoice) -> None:
    rows = [
        [
            Paragraph("Subtotal", _styles()["total_label"]),
            Paragraph(
                _money(invoice.subtotal, invoice.currency),
                _styles()["total_value"],
            ),
        ]
    ]
    if invoice.discount_amount:
        rows.append(
            [
                Paragraph("Discount", _styles()["total_label"]),
                Paragraph(
                    f"− {_money(invoice.discount_amount, invoice.currency)}",
                    _styles()["total_value"],
                ),
            ]
        )
    rows.append(
        [
            Paragraph(f"Tax ({invoice.tax_rate:.2f}%)", _styles()["total_label"]),
            Paragraph(
                _money(invoice.tax_amount, invoice.currency),
                _styles()["total_value"],
            ),
        ]
    )
    rows.append(
        [
            Paragraph("Total", _styles()["total_label_strong"]),
            Paragraph(
                f"<b>{_money(invoice.total_amount, invoice.currency)}</b>",
                _styles()["total_value_strong"],
            ),
        ]
    )
    rows.append(
        [
            Paragraph("Amount paid", _styles()["total_label"]),
            Paragraph(
                _money(invoice.amount_paid, invoice.currency),
                _styles()["total_value"],
            ),
        ]
    )
    rows.append(
        [
            Paragraph("BALANCE DUE", _styles()["balance_label"]),
            Paragraph(
                _money(invoice.balance_due, invoice.currency),
                _styles()["balance_value"],
            ),
        ]
    )

    table = Table(rows, colWidths=[125 * mm, 55 * mm])
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, 0), (-1, 3), 0.5, BORDER),
                ("BACKGROUND", (0, -1), (-1, -1), ACCENT_SOFT),
                ("BOX", (0, -1), (-1, -1), 1, ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)


def _payment_history(story: list, invoice: Invoice) -> None:
    payments = list(invoice.payments.all())
    if not payments:
        return
    rows = [
        [
            Paragraph("DATE", _styles()["table_head"]),
            Paragraph("METHOD", _styles()["table_head"]),
            Paragraph("REFERENCE", _styles()["table_head"]),
            Paragraph("AMOUNT", _styles()["table_head_right"]),
        ]
    ]
    for payment in payments:
        rows.append(
            [
                Paragraph(_date(payment.payment_date), _styles()["cell"]),
                Paragraph(payment.get_method_display(), _styles()["cell"]),
                Paragraph(escape(payment.reference or "—"), _styles()["cell"]),
                Paragraph(
                    _money(payment.amount, invoice.currency), _styles()["cell_right"]
                ),
            ]
        )
    table = Table(rows, colWidths=[30 * mm, 35 * mm, 85 * mm, 30 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(Spacer(1, 12))
    story.append(Paragraph("PAYMENTS RECEIVED", _styles()["section"]))
    story.append(table)


def _notes(story: list, invoice: Invoice) -> None:
    if not invoice.notes and not invoice.terms:
        return
    story.append(Spacer(1, 12))
    story.append(Paragraph("NOTES & TERMS", _styles()["section"]))
    bits: list[str] = []
    if invoice.terms:
        bits.append(f"<b>Payment terms:</b> {escape(invoice.terms)}")
    if invoice.notes:
        bits.append(escape(invoice.notes))
    story.append(Paragraph("<br/><br/>".join(bits), _styles()["notes"]))


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
            spaceAfter=3,
        ),
        "invoice": ParagraphStyle(
            "Invoice",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=25,
            textColor=INK,
            alignment=2,
            spaceAfter=1,
        ),
        "number": ParagraphStyle(
            "Number",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=ACCENT,
            alignment=2,
            spaceAfter=3,
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=MUTED,
            alignment=2,
        ),
        "meta_left": ParagraphStyle(
            "MetaLeft",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=MUTED,
            alignment=0,
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
        "value": ParagraphStyle(
            "Value",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=INK,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.5,
            textColor=INK,
        ),
        "cell_right": ParagraphStyle(
            "CellRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=11.5,
            textColor=INK,
            alignment=2,
        ),
        "table_head": ParagraphStyle(
            "TableHead",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.6,
            leading=9.8,
            textColor=colors.white,
        ),
        "table_head_right": ParagraphStyle(
            "TableHeadRight",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.6,
            leading=9.8,
            textColor=colors.white,
            alignment=2,
        ),
        "total_label": ParagraphStyle(
            "TotalLabel",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=INK,
        ),
        "total_value": ParagraphStyle(
            "TotalValue",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=INK,
            alignment=2,
        ),
        "total_label_strong": ParagraphStyle(
            "TotalLabelStrong",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=INK,
        ),
        "total_value_strong": ParagraphStyle(
            "TotalValueStrong",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=INK,
            alignment=2,
        ),
        "balance_label": ParagraphStyle(
            "BalanceLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=ACCENT,
        ),
        "balance_value": ParagraphStyle(
            "BalanceValue",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=ACCENT,
            alignment=2,
        ),
        "status_draft": ParagraphStyle(
            "StatusDraft",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=DANGER,
            alignment=1,
        ),
        "status_bad": ParagraphStyle(
            "StatusBad",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=DANGER,
            alignment=1,
        ),
        "notes": ParagraphStyle(
            "Notes",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
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
    canvas.drawString(15 * mm, 10.5 * mm, "This is a computer-generated invoice.")
    canvas.drawRightString(
        width - 15 * mm, 10.5 * mm, f"Page {canvas.getPageNumber()}"
    )
    canvas.restoreState()


def render_invoice_pdf(invoice: Invoice) -> bytes:
    """Render one invoice as PDF bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
        title=f"Invoice {invoice.invoice_number}",
        author="HRMS",
        subject=f"Invoice {invoice.invoice_number} for {invoice.client_name}",
    )
    story: list = []
    _header(story, invoice)
    _parties(story, invoice)
    _items(story, invoice)
    _totals(story, invoice)
    _payment_history(story, invoice)
    _notes(story, invoice)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
