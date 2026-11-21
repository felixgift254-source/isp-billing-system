from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
from app.api.deps import get_db, get_current_admin, record_audit_log
from app.models import Customer, Plan, Router
from app.services.billing import BillingService
from app.services.mikrotik import MikroTikService
import json
import redis as redis_sync

router = APIRouter()

class CustomerCreate(BaseModel):
    full_name: str
    phone_number: str
    email: Optional[str] = None
    router_id: uuid.UUID
    plan_id: uuid.UUID
    billing_day: Optional[int] = None

class CustomerUpdate(BaseModel):
    full_name: str | None = None
    phone_number: str | None = None
    email: str | None = None
    router_id: uuid.UUID | None = None
    plan_id: uuid.UUID | None = None
    status: str | None = None

@router.get("/")
async def list_customers(
    search: str = None, 
    status: str = None,
    router_id: uuid.UUID = None,
    plan_id: uuid.UUID = None,
    skip: int = 0, 
    limit: int = 100, 
    db: AsyncSession = Depends(get_db), 
    admin=Depends(get_current_admin)
):
    stmt = select(Customer)
    if search:
        stmt = stmt.where(or_(
            Customer.full_name.ilike(f"%{search}%"),
            Customer.phone_number.ilike(f"%{search}%"),
            Customer.pppoe_username.ilike(f"%{search}%")
        ))
    if status:
        stmt = stmt.where(Customer.status == status)
    if router_id:
        stmt = stmt.where(Customer.router_id == router_id)
    if plan_id:
        stmt = stmt.where(Customer.plan_id == plan_id)
        
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

@router.post("/")
async def create_customer(data: CustomerCreate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    plan = await db.execute(select(Plan).where(Plan.id == data.plan_id))
    plan = plan.scalar_one_or_none()
    if not plan: raise HTTPException(status_code=404, detail="Plan not found")
    
    router_db = await db.execute(select(Router).where(Router.id == data.router_id))
    router_db = router_db.scalar_one_or_none()
    if not router_db: raise HTTPException(status_code=404, detail="Router not found")
    
    username, password = BillingService.generate_pppoe_credentials(data.phone_number)
    now = datetime.now()
    billing_day = data.billing_day or now.day
    sub_end = now + timedelta(days=plan.validity_days)
    
    new_customer = Customer(
        full_name=data.full_name,
        phone_number=data.phone_number,
        email=data.email,
        pppoe_username=username,
        pppoe_password=password,
        status="ACTIVE",
        router_id=data.router_id,
        plan_id=data.plan_id,
        billing_day=billing_day,
        subscription_start=now,
        subscription_end=sub_end
    )
    
    mk_service = MikroTikService(router_db)
    try:
        secret = await mk_service.create_secret(username, password, plan.mikrotik_profile_name, f"Customer: {data.full_name}")
        new_customer.mikrotik_secret_id = secret.get(".id")
        await mk_service.close()
    except Exception as e:
        await mk_service.close()
        raise HTTPException(status_code=500, detail=f"MikroTik error: {e}")
        
    db.add(new_customer)
    await db.commit()
    await db.refresh(new_customer)
    return new_customer

@router.get("/{id}")
async def get_customer(id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Customer).where(Customer.id == id))
    customer = result.scalar_one_or_none()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.patch("/{id}")
async def update_customer(id: uuid.UUID, data: CustomerUpdate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Customer).where(Customer.id == id))
    customer = result.scalar_one_or_none()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    
    if data.plan_id and data.plan_id != customer.plan_id:
        plan = await db.execute(select(Plan).where(Plan.id == data.plan_id))
        plan = plan.scalar_one_or_none()
        router_db = await db.execute(select(Router).where(Router.id == customer.router_id))
        router_db = router_db.scalar_one_or_none()
        if plan and router_db and customer.mikrotik_secret_id:
            mk_service = MikroTikService(router_db)
            try:
                await mk_service.update_secret(customer.mikrotik_secret_id, profile=plan.mikrotik_profile_name)
                await mk_service.close()
            except Exception as e:
                await mk_service.close()
                raise HTTPException(status_code=500, detail=f"MikroTik update failed: {e}")
                
    for key, value in data.dict(exclude_unset=True).items():
        setattr(customer, key, value)
        
    await db.commit()
    await db.refresh(customer)
    return customer

@router.post("/{id}/suspend")
async def suspend_customer(id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Customer).where(Customer.id == id))
    customer = result.scalar_one_or_none()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    
    router_db = await db.execute(select(Router).where(Router.id == customer.router_id))
    router_db = router_db.scalar_one_or_none()
    
    if router_db and customer.mikrotik_secret_id:
        mk_service = MikroTikService(router_db)
        try:
            await mk_service.suspend_user(customer.mikrotik_secret_id, customer.pppoe_username)
            await mk_service.close()
        except Exception as e:
            await mk_service.close()
            raise HTTPException(status_code=500, detail=f"MikroTik suspend failed: {e}")
            
    prev_status = customer.status
    customer.status = "SUSPENDED"

    await record_audit_log(
        db,
        action="SUSPEND",
        user=admin,
        target_type="Customer",
        target_id=str(customer.id),
        details={"previous_status": prev_status, "pppoe_username": customer.pppoe_username},
        request=request,
    )

    await db.commit()
    return {"message": "Suspended successfully"}

@router.post("/{id}/activate")
async def activate_customer(id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Customer).where(Customer.id == id))
    customer = result.scalar_one_or_none()
    if not customer: raise HTTPException(status_code=404, detail="Customer not found")
    
    router_db = await db.execute(select(Router).where(Router.id == customer.router_id))
    router_db = router_db.scalar_one_or_none()
    
    plan_db = await db.execute(select(Plan).where(Plan.id == customer.plan_id))
    plan_db = plan_db.scalar_one_or_none()
    
    if router_db and plan_db and customer.mikrotik_secret_id:
        mk_service = MikroTikService(router_db)
        try:
            await mk_service.reactivate_user(customer.mikrotik_secret_id, customer.pppoe_username, plan_db.mikrotik_profile_name)
            await mk_service.close()
        except Exception as e:
            await mk_service.close()
            raise HTTPException(status_code=500, detail=f"MikroTik reactivate failed: {e}")

    prev_status = customer.status
    customer.status = "ACTIVE"

    await record_audit_log(
        db,
        action="REACTIVATE",
        user=admin,
        target_type="Customer",
        target_id=str(customer.id),
        details={"previous_status": prev_status, "pppoe_username": customer.pppoe_username},
        request=request,
    )

    await db.commit()
    return {"message": "Activated successfully"}


@router.get("/{id}/session-diagnostics")
async def get_session_diagnostics(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """
    Fetch live PPPoE session data for a customer directly from MikroTik.

    Results are cached in Redis for 20 seconds to protect the router from
    excessive polling. Returns `is_online: false` if the user has no active
    session rather than raising an error.
    """
    from app.config import settings
    import redis as redis_sync
    import json

    result = await db.execute(select(Customer).where(Customer.id == id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    router_db = await db.execute(select(Router).where(Router.id == customer.router_id))
    router_db = router_db.scalar_one_or_none()
    if not router_db:
        raise HTTPException(status_code=404, detail="Router not found")

    cache_key = f"session_diag:{customer.id}"

    # Try Redis cache first (synchronous client is fine here — it's a quick read)
    try:
        rc = redis_sync.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        cached = rc.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # Redis unavailable — fall through to live fetch

    # Live fetch from MikroTik
    mk_service = MikroTikService(router_db)
    try:
        session = await mk_service.find_active_by_name(customer.pppoe_username)
        await mk_service.close()
    except Exception as e:
        await mk_service.close()
        raise HTTPException(status_code=503, detail=f"MikroTik unreachable: {e}")

    if session:
        diagnostics = {
            "is_online": True,
            "pppoe_username": customer.pppoe_username,
            "uptime": session.get("uptime", "—"),
            "ip_address": session.get("address", "—"),
            "mac_address": session.get("caller-id", "—"),
            "bytes_in": session.get("bytes-in", 0),
            "bytes_out": session.get("bytes-out", 0),
            "packets_in": session.get("packets-in", 0),
            "packets_out": session.get("packets-out", 0),
            "session_id": session.get(".id", "—"),
            "encoding": session.get("encoding", "—"),
        }
    else:
        diagnostics = {
            "is_online": False,
            "pppoe_username": customer.pppoe_username,
            "uptime": None,
            "ip_address": None,
            "mac_address": None,
            "bytes_in": 0,
            "bytes_out": 0,
            "packets_in": 0,
            "packets_out": 0,
            "session_id": None,
            "encoding": None,
        }

    # Cache result for 20 seconds
    try:
        rc = redis_sync.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        rc.setex(cache_key, 20, json.dumps(diagnostics))
    except Exception:
        pass

    return diagnostics


@router.delete("/{id}/session")
async def kick_session(
    id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin=Depends(get_current_admin),
):
    """Force-disconnect the customer's active PPPoE session (they will reconnect automatically)."""
    result = await db.execute(select(Customer).where(Customer.id == id))
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    router_db = await db.execute(select(Router).where(Router.id == customer.router_id))
    router_db = router_db.scalar_one_or_none()
    if not router_db:
        raise HTTPException(status_code=404, detail="Router not found")

    mk_service = MikroTikService(router_db)
    try:
        session = await mk_service.find_active_by_name(customer.pppoe_username)
        if session and ".id" in session:
            await mk_service.disconnect_user(session[".id"])
        await mk_service.close()
    except Exception as e:
        await mk_service.close()
        raise HTTPException(status_code=503, detail=f"MikroTik kick failed: {e}")

    await record_audit_log(
        db,
        action="KICK_SESSION",
        user=admin,
        target_type="Customer",
        target_id=str(customer.id),
        details={"pppoe_username": customer.pppoe_username},
        request=request,
    )
    await db.commit()

    return {"message": f"Session for {customer.pppoe_username} terminated. They will reconnect automatically."}
