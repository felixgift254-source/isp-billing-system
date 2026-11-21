from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid
from app.api.deps import get_db, get_current_admin, record_audit_log
from app.models import Payment, Customer, Invoice, User
from app.schemas.payment import PaymentReconcileRequest
from app.workers.celery_app import celery_app

router = APIRouter()

@router.get("/")
async def list_payments(
    status: str = None,
    reconciliation_status: str = None,
    customer_id: uuid.UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    stmt = (
        select(Payment)
        .options(selectinload(Payment.customer), selectinload(Payment.invoice))
        .order_by(desc(Payment.transaction_date))
    )
    if status:
        stmt = stmt.where(Payment.status == status)
    if reconciliation_status:
        stmt = stmt.where(Payment.reconciliation_status == reconciliation_status)
    if customer_id:
        stmt = stmt.where(Payment.customer_id == customer_id)
        
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/unmatched")
async def list_unmatched_payments(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin)
):
    """List all payments that require manual reconciliation."""
    stmt = (
        select(Payment)
        .where(Payment.reconciliation_status == "PENDING_REVIEW")
        .order_by(desc(Payment.transaction_date))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{payment_id}/reconcile")
async def reconcile_payment(
    payment_id: uuid.UUID,
    data: PaymentReconcileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Manually assign an unassigned payment to a customer and trigger service reconciliation."""
    stmt = select(Payment).where(Payment.id == payment_id)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    customer_stmt = select(Customer).where(Customer.id == data.customer_id)
    cust_res = await db.execute(customer_stmt)
    customer = cust_res.scalar_one_or_none()

    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    payment.customer_id = customer.id
    payment.reconciliation_status = "MANUALLY_ASSIGNED"
    payment.matched_by_user_id = admin.id
    payment.matched_at = datetime.now()
    if data.invoice_id:
        payment.invoice_id = data.invoice_id

    # Audit the reconciliation action
    await record_audit_log(
        db,
        action="RECONCILE",
        user=admin,
        target_type="Payment",
        target_id=str(payment.id),
        details={
            "customer_id": str(customer.id),
            "customer_name": customer.full_name,
            "amount": float(payment.amount),
            "mpesa_receipt": payment.mpesa_receipt_number,
            "invoice_id": str(data.invoice_id) if data.invoice_id else None,
        },
        request=request,
    )

    await db.commit()

    # Trigger async reactivation/invoice sync task in Celery worker
    celery_app.send_task(
        'app.workers.tasks.process_payment_task',
        args=[{
            "receipt_number": payment.mpesa_receipt_number,
            "checkout_request_id": payment.checkout_request_id or f"manual-{payment.id}",
            "amount": float(payment.amount)
        }]
    )

    return {"message": "Payment successfully reconciled to customer", "payment_id": payment.id}
