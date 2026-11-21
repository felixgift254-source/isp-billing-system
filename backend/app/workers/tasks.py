from app.workers.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models import Customer, Invoice, Router, Plan, Payment
from app.config import settings
from cryptography.fernet import Fernet
import httpx
from datetime import datetime, timedelta
import logging
from decimal import Decimal
import asyncio

logger = logging.getLogger(__name__)
fernet = Fernet(settings.FERNET_KEY)


def _parse_speed_mbps(speed_str: str) -> int:
    """Parse MikroTik rate-limit value to Mbps integer.

    Examples: '50M' -> 50, '128k' -> 0, '1G' -> 1000
    """
    speed_str = speed_str.strip().upper()
    if speed_str.endswith("G"):
        return int(float(speed_str[:-1]) * 1000)
    elif speed_str.endswith("M"):
        return int(float(speed_str[:-1]))
    elif speed_str.endswith("K"):
        return max(0, int(float(speed_str[:-1]) / 1000))
    return 0

def get_mikrotik_client(router):
    password = fernet.decrypt(router.api_password.encode()).decode()
    scheme = "https" if router.use_ssl else "http"
    base_url = f"{scheme}://{router.ip_address}:{router.api_port}"
    return httpx.Client(
        base_url=base_url,
        auth=(router.api_username, password),
        verify=False,
        timeout=10.0
    )

@celery_app.task
def generate_invoices():
    db = SyncSessionLocal()
    today = datetime.now().date()
    try:
        customers = db.query(Customer).filter(Customer.status == 'ACTIVE').all()
        for c in customers:
            if c.subscription_end and c.subscription_end.date() == today:
                plan = db.query(Plan).filter(Plan.id == c.plan_id).first()
                if not plan: continue
                
                invoice = Invoice(
                    invoice_number=f"INV-{today.strftime('%Y%m%d')}-{str(c.id)[:4].upper()}",
                    customer_id=c.id,
                    amount=plan.price,
                    due_date=today,
                    status="PENDING",
                    billing_period_start=c.subscription_end,
                    billing_period_end=c.subscription_end + timedelta(days=plan.validity_days)
                )
                db.add(invoice)
                c.subscription_end = invoice.billing_period_end
                db.commit()
    finally:
        db.close()

@celery_app.task
def check_overdue_invoices():
    """Evaluate overdue invoices and manage the grace period before suspending users."""
    db = SyncSessionLocal()
    today = datetime.now().date()
    try:
        # 1. Flag newly overdue invoices and start grace period
        invoices = db.query(Invoice).filter(Invoice.status == 'PENDING', Invoice.due_date <= today).all()
        for inv in invoices:
            inv.status = 'OVERDUE'
            c = db.query(Customer).filter(Customer.id == inv.customer_id).first()
            if c:
                plan = db.query(Plan).filter(Plan.id == c.plan_id).first()
                grace_days = plan.grace_period_days if plan else 2
                c.grace_period_end = inv.due_date + timedelta(days=grace_days)
                _send_sms_sync(
                    c.phone_number,
                    f"Dear {c.full_name}, your bill of KES {inv.amount} is due. "
                    f"You have a {grace_days}-day grace period until {c.grace_period_end.strftime('%d-%m-%Y')} "
                    f"to pay Paybill {settings.MPESA_BUSINESS_SHORTCODE}, Acc: {c.pppoe_username}."
                )
        db.commit()

        # 2. Suspend customers whose grace period has now expired
        expired_customers = db.query(Customer).filter(
            Customer.status == 'ACTIVE',
            Customer.grace_period_end.isnot(None),
            Customer.grace_period_end < today
        ).all()

        for c in expired_customers:
            c.status = 'SUSPENDED'
            router = db.query(Router).filter(Router.id == c.router_id).first()
            if router and c.mikrotik_secret_id:
                with get_mikrotik_client(router) as client:
                    try:
                        client.patch(f"/rest/ppp/secret/{c.mikrotik_secret_id}", json={"profile": "suspended"})
                        res = client.get(f"/rest/ppp/active?name={c.pppoe_username}")
                        if res.status_code == 200 and res.json():
                            act_id = res.json()[0]['.id']
                            client.delete(f"/rest/ppp/active/{act_id}")
                    except Exception as e:
                        logger.error(f"Failed to suspend {c.pppoe_username}: {e}")

            _send_sms_sync(
                c.phone_number,
                f"Notice: Your internet account {c.pppoe_username} has been suspended due to non-payment. "
                f"Please pay via Paybill {settings.MPESA_BUSINESS_SHORTCODE}, Acc: {c.pppoe_username} to restore service immediately."
            )
        db.commit()
    finally:
        db.close()

@celery_app.task
def sync_router_status():
    db = SyncSessionLocal()
    try:
        routers = db.query(Router).filter(Router.is_active == True).all()
        for r in routers:
            try:
                with get_mikrotik_client(r) as client:
                    res = client.get("/rest/system/resource")
                    r.status = "ONLINE" if res.status_code == 200 else "OFFLINE"
            except:
                r.status = "OFFLINE"
            r.last_sync_at = datetime.now()
        db.commit()
    finally:
        db.close()

@celery_app.task
def sync_active_connections():
    db = SyncSessionLocal()
    try:
        routers = db.query(Router).filter(Router.is_active == True, Router.status == 'ONLINE').all()
        for r in routers:
            try:
                with get_mikrotik_client(r) as client:
                    res = client.get("/rest/ppp/active")
                    if res.status_code == 200:
                        active_users = {u.get('name') for u in res.json()}
                        customers = db.query(Customer).filter(Customer.router_id == r.id).all()
                        for c in customers:
                            if c.pppoe_username in active_users:
                                c.is_online = True
                                c.last_online_at = datetime.now()
                            else:
                                c.is_online = False
                db.commit()
            except Exception as e:
                logger.error(f"Active sync error on {r.name}: {e}")
    finally:
        db.close()

@celery_app.task
def process_payment_task(payment_data: dict):
    db = SyncSessionLocal()
    try:
        customer = None
        payment = None
        if "c2b_callback" in payment_data:
            cb = payment_data["c2b_callback"]
            amount = Decimal(cb.get("TransAmount", 0))
            receipt = cb.get("TransID")
            phone = cb.get("MSISDN", "")
            ref = cb.get("BillRefNumber", "").strip()

            customer = db.query(Customer).filter((Customer.phone_number == ref) | (Customer.pppoe_username == ref)).first()
            if not customer:
                # Store as unmatched payment for staff manual reconciliation
                payment = Payment(
                    mpesa_receipt_number=receipt,
                    phone_number=phone,
                    amount=amount,
                    transaction_date=datetime.now(),
                    customer_id=None,
                    payment_method="C2B_PAYBILL",
                    status="COMPLETED",
                    reconciliation_status="PENDING_REVIEW",
                    bill_ref_number=ref,
                    raw_callback=payment_data
                )
                db.add(payment)
                db.commit()
                logger.warning(f"Unmatched payment received: Receipt={receipt}, Phone={phone}, Ref={ref}, Amount={amount}")
                return

            payment = Payment(
                mpesa_receipt_number=receipt,
                phone_number=phone,
                amount=amount,
                transaction_date=datetime.now(),
                customer_id=customer.id,
                payment_method="C2B_PAYBILL",
                status="COMPLETED",
                reconciliation_status="MATCHED",
                bill_ref_number=ref,
                raw_callback=payment_data
            )
            db.add(payment)
        else:
            receipt = payment_data.get("receipt_number")
            checkout_id = payment_data.get("checkout_request_id")
            amount = Decimal(payment_data.get("amount", 0))

            payment = db.query(Payment).filter(Payment.checkout_request_id == checkout_id).first()
            if payment:
                payment.status = "COMPLETED"
                payment.reconciliation_status = "MATCHED"
                payment.mpesa_receipt_number = receipt
                payment.amount = amount
                payment.raw_callback = payment_data
                customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
            else:
                return

        if customer and payment:
            # Reconcile customer and check if suspended/in grace
            reconcile_customer_account(db, customer, payment)

        db.commit()
    finally:
        db.close()


def reconcile_customer_account(db, customer, payment):
    """Marks pending invoices as paid, resets grace periods, and reactivates router secret."""
    inv = db.query(Invoice).filter(
        Invoice.customer_id == customer.id,
        Invoice.status.in_(['PENDING', 'OVERDUE'])
    ).order_by(Invoice.due_date).first()

    if inv and payment.amount >= inv.amount:
        inv.status = 'PAID'
        inv.paid_at = datetime.now()
        payment.invoice_id = inv.id

    customer.grace_period_end = None

    if customer.status == 'SUSPENDED':
        customer.status = 'ACTIVE'
        router = db.query(Router).filter(Router.id == customer.router_id).first()
        plan = db.query(Plan).filter(Plan.id == customer.plan_id).first()
        if router and plan and customer.mikrotik_secret_id:
            with get_mikrotik_client(router) as client:
                try:
                    client.patch(
                        f"/rest/ppp/secret/{customer.mikrotik_secret_id}",
                        json={"profile": plan.mikrotik_profile_name, "disabled": "false"}
                    )
                    res = client.get(f"/rest/ppp/active?name={customer.pppoe_username}")
                    if res.status_code == 200 and res.json():
                        act_id = res.json()[0]['.id']
                        client.delete(f"/rest/ppp/active/{act_id}")
                except Exception as e:
                    logger.error(f"Failed to reactivate {customer.pppoe_username}: {e}")

    _send_sms_sync(
        customer.phone_number,
        f"Thank you {customer.full_name}! Payment of KES {payment.amount} (Ref: {payment.mpesa_receipt_number}) received. "
        f"Your internet service is ACTIVE."
    )

@celery_app.task
def sync_profiles_from_router_task(router_id: str):
    """Import PPPoE profiles from a MikroTik router into the Plan table."""
    db = SyncSessionLocal()
    try:
        router = db.query(Router).filter(Router.id == router_id).first()
        if not router:
            logger.error(f"Router {router_id} not found")
            return

        with get_mikrotik_client(router) as client:
            res = client.get("/rest/ppp/profile")
            if res.status_code != 200:
                logger.error(f"Failed to fetch profiles from {router.name}")
                return

            profiles = res.json()
            created_count = 0
            for profile in profiles:
                profile_name = profile.get("name", "")
                if profile_name in ("default", "default-encryption"):
                    continue

                existing = db.query(Plan).filter(
                    Plan.mikrotik_profile_name == profile_name
                ).first()
                if existing:
                    continue

                # Parse rate-limit (e.g. "50M/50M" or "128k/128k")
                rate_limit = profile.get("rate-limit", "0/0")
                download_speed = 0
                upload_speed = 0
                try:
                    parts = rate_limit.split("/")
                    download_speed = _parse_speed_mbps(parts[0])
                    upload_speed = _parse_speed_mbps(parts[1]) if len(parts) > 1 else download_speed
                except (ValueError, IndexError):
                    pass

                new_plan = Plan(
                    name=profile_name.replace("-", " ").title(),
                    mikrotik_profile_name=profile_name,
                    download_speed_mbps=download_speed,
                    upload_speed_mbps=upload_speed,
                    price=Decimal("0.00"),  # Admin sets price later
                    validity_days=30,
                    is_active=True,
                )
                db.add(new_plan)
                created_count += 1

            db.commit()
            logger.info(f"Imported {created_count} profiles from {router.name}")
    except Exception as e:
        logger.error(f"Profile sync error for router {router_id}: {e}")
    finally:
        db.close()


@celery_app.task
def send_expiry_reminders():
    """Send SMS reminders to customers whose subscription expires tomorrow."""
    db = SyncSessionLocal()
    tomorrow = datetime.now().date() + timedelta(days=1)
    try:
        customers = db.query(Customer).filter(Customer.status == 'ACTIVE').all()
        reminded = 0
        for c in customers:
            if c.subscription_end and c.subscription_end == tomorrow:
                plan = db.query(Plan).filter(Plan.id == c.plan_id).first()
                if plan:
                    _send_sms_sync(
                        c.phone_number,
                        f"Hi {c.full_name}, your internet subscription expires tomorrow. "
                        f"Pay KES {plan.price} to Paybill {settings.MPESA_BUSINESS_SHORTCODE}, "
                        f"Account: {c.pppoe_username} to avoid disconnection."
                    )
                    reminded += 1
        logger.info(f"Sent {reminded} expiry reminders")
    except Exception as e:
        logger.error(f"Error sending expiry reminders: {e}")
    finally:
        db.close()


def _send_sms_sync(phone: str, message: str):
    """Send SMS via Africa's Talking (synchronous for Celery tasks)."""
    try:
        url = (
            "https://api.africastalking.com/version1/messaging"
            if settings.AT_USERNAME != "sandbox"
            else "https://api.sandbox.africastalking.com/version1/messaging"
        )
        headers = {
            "apiKey": settings.AT_API_KEY,
            "Accept": "application/json",
        }
        data = {
            "username": settings.AT_USERNAME,
            "to": phone,
            "message": message,
        }
        if settings.AT_SENDER_ID:
            data["from"] = settings.AT_SENDER_ID

        with httpx.Client(timeout=15.0) as client:
            response = client.post(url, headers=headers, data=data)
            response.raise_for_status()
            logger.info(f"SMS sent to {phone}")
            return response.json()
    except Exception as e:
        logger.error(f"Failed to send SMS to {phone}: {e}")
        return None

