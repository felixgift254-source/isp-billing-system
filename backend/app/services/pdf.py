"""
PDF generation service for invoices and payment receipts.

Uses ReportLab to produce branded, single-page PDFs that can be streamed
directly from the FastAPI response or emailed as attachments.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)

# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------
BRAND_BLUE = colors.HexColor("#1a56db")
BRAND_DARK = colors.HexColor("#111827")
BRAND_GREY = colors.HexColor("#6b7280")
BRAND_LIGHT = colors.HexColor("#f9fafb")
SUCCESS_GREEN = colors.HexColor("#059669")
WARNING_AMBER = colors.HexColor("#d97706")
DANGER_RED = colors.HexColor("#dc2626")

COMPANY_NAME = "NetISP Ltd."
COMPANY_TAGLINE = "High-Speed Internet · PPPoE Management"
COMPANY_EMAIL = "billing@netisp.example.com"
COMPANY_PHONE = "+254 700 000 000"
COMPANY_ADDRESS = "P.O. Box 00100, Nairobi, Kenya"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_styles():
    base = getSampleStyleSheet()
    styles = {
        "company_name": ParagraphStyle(
            "company_name",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=BRAND_BLUE,
            spaceAfter=2,
        ),
        "company_sub": ParagraphStyle(
            "company_sub",
            fontName="Helvetica",
            fontSize=9,
            textColor=BRAND_GREY,
            spaceAfter=2,
        ),
        "doc_title": ParagraphStyle(
            "doc_title",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=BRAND_DARK,
            alignment=TA_RIGHT,
            spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=BRAND_GREY,
            spaceAfter=1,
        ),
        "value": ParagraphStyle(
            "value",
            fontName="Helvetica",
            fontSize=10,
            textColor=BRAND_DARK,
            spaceAfter=4,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=BRAND_BLUE,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=BRAND_GREY,
            alignment=TA_CENTER,
        ),
        "normal": base["Normal"],
    }
    return styles


def _fmt_currency(amount) -> str:
    try:
        return f"KES {float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"KES {amount}"


def _fmt_date(d) -> str:
    if d is None:
        return "—"
    if isinstance(d, (datetime,)):
        return d.strftime("%d %B %Y")
    # date object
    return d.strftime("%d %B %Y")


def _status_color(status: str):
    s = (status or "").upper()
    if s in ("PAID", "COMPLETED", "ACTIVE"):
        return SUCCESS_GREEN
    if s in ("OVERDUE", "FAILED", "SUSPENDED"):
        return DANGER_RED
    return WARNING_AMBER


# ---------------------------------------------------------------------------
# Invoice PDF
# ---------------------------------------------------------------------------

def generate_invoice_pdf(invoice, customer, plan) -> bytes:
    """
    Generate a branded A4 invoice PDF.

    Parameters
    ----------
    invoice : Invoice ORM object
    customer : Customer ORM object (pre-loaded, NOT lazy)
    plan     : Plan ORM object (pre-loaded, NOT lazy)

    Returns
    -------
    bytes  – raw PDF bytes ready for streaming
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = _build_styles()
    story = []

    # ---- Header row -------------------------------------------------------
    status_hex = "059669" if invoice.status.upper() == "PAID" else "d97706"
    header_data = [
        [
            [
                Paragraph(COMPANY_NAME, styles["company_name"]),
                Paragraph(COMPANY_TAGLINE, styles["company_sub"]),
                Paragraph(COMPANY_EMAIL, styles["company_sub"]),
                Paragraph(COMPANY_PHONE, styles["company_sub"]),
            ],
            [
                Paragraph("INVOICE", styles["doc_title"]),
                Paragraph(
                    f"<font color='#{status_hex}'>{invoice.invoice_number}</font>",
                    ParagraphStyle(
                        "inv_num",
                        fontName="Helvetica-Bold",
                        fontSize=12,
                        textColor=_status_color(invoice.status),
                        alignment=TA_RIGHT,
                    ),
                ),
            ],
        ]
    ]
    header_table = Table(header_data, colWidths=["55%", "45%"])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE))
    story.append(Spacer(1, 0.4 * cm))

    # ---- Bill To / Invoice Details ----------------------------------------
    details_data = [
        [
            [
                Paragraph("BILL TO", styles["label"]),
                Paragraph(customer.full_name, styles["value"]),
                Paragraph(customer.phone_number, styles["value"]),
                Paragraph(customer.email or "—", styles["value"]),
                Paragraph(f"PPPoE: <b>{customer.pppoe_username}</b>", styles["value"]),
            ],
            [
                Paragraph("INVOICE DATE", styles["label"]),
                Paragraph(_fmt_date(invoice.created_at), styles["value"]),
                Paragraph("DUE DATE", styles["label"]),
                Paragraph(_fmt_date(invoice.due_date), styles["value"]),
                Paragraph("STATUS", styles["label"]),
                Paragraph(
                    invoice.status,
                    ParagraphStyle(
                        "status_val",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=_status_color(invoice.status),
                    ),
                ),
            ],
        ]
    ]
    details_table = Table(details_data, colWidths=["50%", "50%"])
    details_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(details_table)
    story.append(Spacer(1, 0.6 * cm))

    # ---- Line items -------------------------------------------------------
    story.append(Paragraph("SERVICE DETAILS", styles["section_header"]))

    items = [
        ["Description", "Period", "Amount"],
        [
            f"{plan.name} Internet Plan\n"
            f"{plan.download_speed_mbps} Mbps ↓ / {plan.upload_speed_mbps} Mbps ↑",
            f"{_fmt_date(invoice.billing_period_start)} – {_fmt_date(invoice.billing_period_end)}",
            _fmt_currency(invoice.amount),
        ],
    ]

    item_table = Table(items, colWidths=["50%", "30%", "20%"])
    item_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BRAND_LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e5e7eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(item_table)
    story.append(Spacer(1, 0.3 * cm))

    # ---- Total box --------------------------------------------------------
    total_data = [
        ["", "TOTAL DUE", _fmt_currency(invoice.amount)],
    ]
    if invoice.status == "PAID" and invoice.paid_at:
        total_data.append(["", "PAID ON", _fmt_date(invoice.paid_at)])

    total_table = Table(total_data, colWidths=["50%", "30%", "20%"])
    total_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (1, 0), (-1, 0), BRAND_DARK),
                ("TEXTCOLOR", (1, 0), (-1, 0), colors.white),
                ("FONTNAME", (1, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (1, 0), (-1, 0), 11),
                ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (1, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(total_table)
    story.append(Spacer(1, 1.5 * cm))

    # ---- Footer -----------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_GREY))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"{COMPANY_NAME} · {COMPANY_ADDRESS} · {COMPANY_EMAIL} · {COMPANY_PHONE}",
            styles["footer"],
        )
    )
    story.append(
        Paragraph(
            "Thank you for your business. For billing queries, contact us at the details above.",
            styles["footer"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Payment Receipt PDF
# ---------------------------------------------------------------------------

def generate_receipt_pdf(payment, customer=None) -> bytes:
    """
    Generate a branded A4 payment receipt PDF.

    Parameters
    ----------
    payment  : Payment ORM object
    customer : Customer ORM object (optional – shown if available)

    Returns
    -------
    bytes  – raw PDF bytes ready for streaming
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = _build_styles()
    story = []

    # ---- Header -----------------------------------------------------------
    header_data = [
        [
            [
                Paragraph(COMPANY_NAME, styles["company_name"]),
                Paragraph(COMPANY_TAGLINE, styles["company_sub"]),
                Paragraph(COMPANY_EMAIL, styles["company_sub"]),
                Paragraph(COMPANY_PHONE, styles["company_sub"]),
            ],
            [Paragraph("PAYMENT RECEIPT", styles["doc_title"])],
        ]
    ]
    header_table = Table(header_data, colWidths=["55%", "45%"])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=SUCCESS_GREEN))
    story.append(Spacer(1, 0.6 * cm))

    # ---- Received-from / receipt reference --------------------------------
    left_items = [Paragraph("RECEIVED FROM", styles["label"])]
    if customer:
        left_items += [
            Paragraph(customer.full_name, styles["value"]),
            Paragraph(customer.phone_number, styles["value"]),
        ]
    else:
        left_items.append(Paragraph(payment.phone_number, styles["value"]))

    right_items = [
        Paragraph("RECEIPT DATE", styles["label"]),
        Paragraph(_fmt_date(payment.transaction_date), styles["value"]),
        Paragraph("PAYMENT METHOD", styles["label"]),
        Paragraph((payment.payment_method or "M-PESA").replace("_", " "), styles["value"]),
        Paragraph("M-PESA RECEIPT #", styles["label"]),
        Paragraph(payment.mpesa_receipt_number or "PENDING", styles["value"]),
    ]

    meta_data = [[left_items, right_items]]
    meta_table = Table(meta_data, colWidths=["50%", "50%"])
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(meta_table)
    story.append(Spacer(1, 0.6 * cm))

    # ---- Amount box -------------------------------------------------------
    amount_data = [
        ["AMOUNT RECEIVED", _fmt_currency(payment.amount)],
    ]
    amount_table = Table(amount_data, colWidths=["70%", "30%"])
    amount_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SUCCESS_GREEN),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 14),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 14),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    story.append(amount_table)
    story.append(Spacer(1, 1.5 * cm))

    # ---- Status note ------------------------------------------------------
    status_color = _status_color(payment.status)
    story.append(
        Paragraph(
            f"Transaction Status: <b>{payment.status}</b>",
            ParagraphStyle(
                "status_note",
                fontName="Helvetica",
                fontSize=11,
                textColor=status_color,
                alignment=TA_CENTER,
            ),
        )
    )
    story.append(Spacer(1, 1.5 * cm))

    # ---- Footer -----------------------------------------------------------
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_GREY))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"{COMPANY_NAME} · {COMPANY_ADDRESS} · {COMPANY_EMAIL} · {COMPANY_PHONE}",
            styles["footer"],
        )
    )
    story.append(
        Paragraph(
            "This is an electronically generated receipt. No signature required.",
            styles["footer"],
        )
    )

    doc.build(story)
    return buffer.getvalue()
