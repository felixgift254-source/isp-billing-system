from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from app.api.deps import get_db, get_current_customer
from app.models import Customer, Invoice, Payment, Plan

router = APIRouter()

@router.get("/me")
async def get_my_profile(customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Customer)
        .options(selectinload(Customer.plan))
        .where(Customer.id == customer.id)
    )
    cust = res.scalar_one_or_none()
    return cust

@router.get("/invoices")
async def get_my_invoices(customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Invoice).where(Invoice.customer_id == customer.id).order_by(desc(Invoice.due_date)))
    return res.scalars().all()

@router.get("/payments")
async def get_my_payments(customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Payment).where(Payment.customer_id == customer.id).order_by(desc(Payment.transaction_date)))
    return res.scalars().all()

@router.post("/pay")
async def trigger_payment(customer: Customer = Depends(get_current_customer), db: AsyncSession = Depends(get_db)):
    from app.services.mpesa import MpesaService
    from app.models import Payment
    from datetime import datetime
    
    res = await db.execute(select(Invoice).where(Invoice.customer_id == customer.id, Invoice.status.in_(['PENDING', 'OVERDUE'])).order_by(Invoice.due_date))
    invoice = res.scalar_one_or_none()
    
    if not invoice:
        return {"message": "No outstanding invoices."}
        
    mpesa_service = MpesaService()
    res_stk = await mpesa_service.stk_push(customer.phone_number, int(invoice.amount), str(customer.id), "Internet Bill")
    checkout_id = res_stk.get("CheckoutRequestID")
    
    new_payment = Payment(
        phone_number=customer.phone_number,
        amount=invoice.amount,
        customer_id=customer.id,
        invoice_id=invoice.id,
        payment_method="STK_PUSH",
        checkout_request_id=checkout_id,
        status="PENDING",
        transaction_date=datetime.now()
    )
    db.add(new_payment)
    await db.commit()
    return res_stk
