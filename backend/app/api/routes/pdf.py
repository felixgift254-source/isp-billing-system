"""
PDF download endpoints.

GET /api/v1/invoices/{invoice_id}/pdf    → streams invoice as PDF
GET /api/v1/payments/{payment_id}/receipt/pdf → streams receipt as PDF
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import io
import uuid

from app.api.deps import get_db, get_current_actor
from app.models import Invoice, Payment, Customer, Plan
from app.services.pdf import generate_invoice_pdf, generate_receipt_pdf

router = APIRouter()


@router.get("/invoices/{invoice_id}/pdf")
async def download_invoice_pdf(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor=Depends(get_current_actor),
):
    """Generate and stream an invoice as a branded PDF."""
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.customer).selectinload(Customer.plan))
        .where(Invoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if actor["type"] == "CUSTOMER" and invoice.customer_id != actor["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this invoice")

    customer = invoice.customer
    plan = customer.plan

    pdf_bytes = generate_invoice_pdf(invoice, customer, plan)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="invoice-{invoice.invoice_number}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


@router.get("/payments/{payment_id}/receipt/pdf")
async def download_receipt_pdf(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    actor=Depends(get_current_actor),
):
    """Generate and stream a payment receipt as a branded PDF."""
    result = await db.execute(
        select(Payment)
        .options(selectinload(Payment.customer))
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if actor["type"] == "CUSTOMER" and payment.customer_id != actor["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this receipt")

    customer = payment.customer  # may be None for unmatched payments

    pdf_bytes = generate_receipt_pdf(payment, customer)

    filename = (
        f"receipt-{payment.mpesa_receipt_number}.pdf"
        if payment.mpesa_receipt_number
        else f"receipt-{payment.id}.pdf"
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
