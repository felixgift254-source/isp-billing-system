import random
import string
import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc
from app.models import Customer, Invoice, Payment, Plan

logger = logging.getLogger(__name__)

class BillingService:
    """Invoice generation and billing cycle management."""
    
    @staticmethod
    def generate_invoice_number() -> str:
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"INV-{date_str}-{random_str}"
    
    @staticmethod
    async def create_invoice_for_customer(db: AsyncSession, customer: Customer) -> Invoice:
        stmt = select(Plan).where(Plan.id == customer.plan_id)
        result = await db.execute(stmt)
        plan = result.scalar_one_or_none()
        
        if not plan:
            raise ValueError(f"Customer {customer.id} has no valid plan.")
            
        amount = plan.price
        due_date = customer.subscription_end.date() if customer.subscription_end else datetime.now().date()
        
        invoice = Invoice(
            invoice_number=BillingService.generate_invoice_number(),
            customer_id=customer.id,
            amount=amount,
            due_date=due_date,
            status="PENDING",
            billing_period_start=customer.subscription_end,
            billing_period_end=None
        )
        db.add(invoice)
        await db.commit()
        await db.refresh(invoice)
        return invoice
    
    @staticmethod
    async def process_payment_for_customer(
        db: AsyncSession, customer_id: UUID, amount: Decimal,
        receipt: str, phone: str, method: str,
        checkout_request_id: str = None, raw_callback: dict = None
    ) -> tuple[Payment, Invoice | None]:
        
        payment = Payment(
            mpesa_receipt_number=receipt,
            phone_number=phone,
            amount=amount,
            transaction_date=datetime.now(),
            customer_id=customer_id,
            payment_method=method,
            checkout_request_id=checkout_request_id,
            status="COMPLETED",
            raw_callback=raw_callback or {}
        )
        db.add(payment)
        
        stmt = select(Invoice).where(
            Invoice.customer_id == customer_id,
            Invoice.status.in_(["PENDING", "OVERDUE"])
        ).order_by(asc(Invoice.due_date))
        
        result = await db.execute(stmt)
        invoices = result.scalars().all()
        
        remaining_amount = amount
        matched_invoice = None
        
        for inv in invoices:
            if remaining_amount >= inv.amount:
                inv.status = "PAID"
                inv.paid_at = datetime.now()
                remaining_amount -= inv.amount
                if not matched_invoice:
                    matched_invoice = inv
                    payment.invoice_id = inv.id
            else:
                break
                
        stmt_cust = select(Customer).where(Customer.id == customer_id)
        res_cust = await db.execute(stmt_cust)
        customer = res_cust.scalar_one_or_none()
        if customer:
            customer.balance = (customer.balance or Decimal('0')) + remaining_amount
            
        await db.commit()
        await db.refresh(payment)
        return payment, matched_invoice
    
    @staticmethod
    def generate_pppoe_credentials(phone: str) -> tuple[str, str]:
        clean_phone = phone[-9:] if len(phone) >= 9 else phone
        username = f"ppp_{clean_phone}"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        return username, password
