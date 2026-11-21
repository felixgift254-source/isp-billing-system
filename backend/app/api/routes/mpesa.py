from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
from datetime import datetime
from app.api.deps import get_db
from app.models import Payment, Customer, Invoice
from app.services.mpesa import MpesaService
from app.services.billing import BillingService
from app.workers.celery_app import celery_app
from decimal import Decimal

router = APIRouter()

class STKPushRequest(BaseModel):
    phone: str
    amount: int
    customer_id: uuid.UUID

@router.post("/stk-push")
async def stk_push(data: STKPushRequest, db: AsyncSession = Depends(get_db)):
    mpesa_service = MpesaService()
    res = await mpesa_service.stk_push(data.phone, data.amount, str(data.customer_id), "Internet Bill")
    
    checkout_id = res.get("CheckoutRequestID")
    
    new_payment = Payment(
        phone_number=data.phone,
        amount=data.amount,
        customer_id=data.customer_id,
        payment_method="STK_PUSH",
        checkout_request_id=checkout_id,
        status="PENDING",
        transaction_date=datetime.now()
    )
    db.add(new_payment)
    await db.commit()
    return res

@router.post("/stk-callback")
async def stk_callback(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    mpesa_service = MpesaService()
    parsed = mpesa_service.parse_stk_callback(data)
    
    if parsed["result_code"] == 0:
        celery_app.send_task('app.workers.tasks.process_payment_task', args=[parsed])
    else:
        checkout_id = parsed["checkout_request_id"]
        result = await db.execute(select(Payment).where(Payment.checkout_request_id == checkout_id))
        payment = result.scalar_one_or_none()
        if payment:
            payment.status = "FAILED"
            payment.raw_callback = data
            await db.commit()
            
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.post("/c2b/validation")
async def c2b_validation(request: Request, db: AsyncSession = Depends(get_db)):
    """Validation endpoint for M-Pesa C2B Paybill.
    Always accepts so funds are captured and routed to reconciliation queue if unassigned.
    """
    return {"ResultCode": 0, "ResultDesc": "Accepted"}

@router.post("/c2b/confirmation")
async def c2b_confirmation(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()
    celery_app.send_task('app.workers.tasks.process_payment_task', args=[{"c2b_callback": data}])
    return {"ResultCode": 0, "ResultDesc": "Accepted"}
