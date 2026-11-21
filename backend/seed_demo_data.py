"""
Seed database with demo Router, Plans, Customer, Invoice, and Payment for testing.
"""

import sys
import uuid
from datetime import datetime, date, timedelta
from cryptography.fernet import Fernet

from app.database import SyncSessionLocal
from app.config import settings
from app.models import Router, Plan, Customer, Invoice, Payment


def seed():
    with SyncSessionLocal() as session:
        # 1. Router
        router = session.query(Router).filter_by(name="Core-MikroTik-01").first()
        if not router:
            fernet = Fernet(settings.FERNET_KEY)
            encrypted_pw = fernet.encrypt(b"admin123").decode()
            router = Router(
                name="Core-MikroTik-01",
                ip_address="192.168.88.1",
                api_port=8728,
                api_username="admin",
                api_password=encrypted_pw,
                use_ssl=False,
                is_active=True,
                status="ONLINE",
            )
            session.add(router)
            session.flush()
            print(f"Created Router: {router.name}")

        # 2. Plans
        plan_10m = session.query(Plan).filter_by(name="Home Fast 10M").first()
        if not plan_10m:
            plan_10m = Plan(
                name="Home Fast 10M",
                mikrotik_profile_name="10M_profile",
                download_speed_mbps=10,
                upload_speed_mbps=5,
                price=2000.0,
                validity_days=30,
                grace_period_days=2,
                is_active=True,
            )
            session.add(plan_10m)

        plan_20m = session.query(Plan).filter_by(name="Business Pro 20M").first()
        if not plan_20m:
            plan_20m = Plan(
                name="Business Pro 20M",
                mikrotik_profile_name="20M_profile",
                download_speed_mbps=20,
                upload_speed_mbps=10,
                price=3500.0,
                validity_days=30,
                grace_period_days=3,
                is_active=True,
            )
            session.add(plan_20m)

        session.flush()
        print("Created Plans")

        # 3. Customer (John Doe)
        phone = "0712345678"
        customer = session.query(Customer).filter_by(phone_number=phone).first()
        today = date.today()
        if not customer:
            customer = Customer(
                full_name="John Doe",
                phone_number=phone,
                email="john.doe@example.com",
                pppoe_username="johndoe_pppoe",
                pppoe_password="password123",
                status="ACTIVE",
                balance=-2000.0,
                router_id=router.id,
                plan_id=plan_10m.id,
                is_online=True,
                last_online_at=datetime.utcnow(),
                billing_day=today.day,
                subscription_start=today - timedelta(days=15),
                subscription_end=today + timedelta(days=15),
                grace_period_end=today + timedelta(days=17),
            )
            session.add(customer)
            session.flush()
            print(f"Created Customer: {customer.full_name} ({customer.phone_number})")

            # 4. Invoice
            invoice = Invoice(
                invoice_number="INV-2026-0001",
                customer_id=customer.id,
                amount=2000.0,
                due_date=today + timedelta(days=5),
                status="PENDING",
                billing_period_start=today,
                billing_period_end=today + timedelta(days=30),
            )
            session.add(invoice)

            # 5. Previous completed Payment
            past_invoice = Invoice(
                invoice_number="INV-2026-0000",
                customer_id=customer.id,
                amount=2000.0,
                due_date=today - timedelta(days=30),
                status="PAID",
                paid_at=datetime.utcnow() - timedelta(days=30),
                billing_period_start=today - timedelta(days=30),
                billing_period_end=today,
            )
            session.add(past_invoice)
            session.flush()

            payment = Payment(
                mpesa_receipt_number="QWE1234567",
                phone_number=phone,
                amount=2000.0,
                transaction_date=datetime.utcnow() - timedelta(days=30),
                invoice_id=past_invoice.id,
                customer_id=customer.id,
                payment_method="STK_PUSH",
                checkout_request_id="ws_CO_TEST_12345",
                status="COMPLETED",
                reconciliation_status="MATCHED",
            )
            session.add(payment)

        session.commit()
        print("Demo data successfully seeded!")


if __name__ == "__main__":
    seed()
