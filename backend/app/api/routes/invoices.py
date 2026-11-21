from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid
from app.api.deps import get_db, get_current_admin
from app.models import Invoice, Customer
from app.services.billing import BillingService

router = APIRouter()

class InvoiceCreate(BaseModel):
    customer_id: uuid.UUID

class InvoiceUpdate(BaseModel):
    status: str

@router.get("/")
async def list_invoices(status: str = None, customer_id: uuid.UUID = None, skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    stmt = select(Invoice)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if customer_id:
        stmt = stmt.where(Invoice.customer_id == customer_id)
    
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/")
async def create_invoice(data: InvoiceCreate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Customer).where(Customer.id == data.customer_id))
    customer = result.scalar_one_or_none()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    
    invoice = await BillingService.create_invoice_for_customer(db, customer)
    return invoice

@router.patch("/{id}")
async def update_invoice(id: uuid.UUID, data: InvoiceUpdate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Invoice).where(Invoice.id == id))
    invoice = result.scalar_one_or_none()
    if not invoice: raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice.status = data.status
    await db.commit()
    await db.refresh(invoice)
    return invoice
