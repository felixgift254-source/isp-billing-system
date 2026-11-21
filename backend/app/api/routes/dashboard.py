from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from app.api.deps import get_db, get_current_admin
from app.models import Customer, Payment, Invoice, Router

router = APIRouter()

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    total_cust = await db.scalar(select(func.count(Customer.id)))
    active_cust = await db.scalar(select(func.count(Customer.id)).where(Customer.status == 'ACTIVE'))
    suspended_cust = await db.scalar(select(func.count(Customer.id)).where(Customer.status == 'SUSPENDED'))
    
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue = await db.scalar(select(func.sum(Payment.amount)).where(
        Payment.status == 'COMPLETED',
        Payment.transaction_date >= month_start
    ))
    
    pending_inv = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == 'PENDING'))
    overdue_inv = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == 'OVERDUE'))
    
    routers_res = await db.execute(select(Router))
    routers = [{"name": r.name, "status": r.status, "connected_users": 0} for r in routers_res.scalars().all()]
    
    payments_res = await db.execute(select(Payment).order_by(Payment.transaction_date.desc()).limit(10))
    recent_payments = payments_res.scalars().all()
    
    return {
        "customers": {
            "total": total_cust,
            "active": active_cust,
            "suspended": suspended_cust
        },
        "revenue_this_month": revenue or 0,
        "invoices": {
            "pending": pending_inv,
            "overdue": overdue_inv
        },
        "routers": routers,
        "recent_payments": recent_payments
    }
