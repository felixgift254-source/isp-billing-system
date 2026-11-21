from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from cryptography.fernet import Fernet
import uuid
from app.api.deps import get_db, get_current_admin
from app.models import Router, Plan
from app.config import settings
from app.services.mikrotik import MikroTikService

router = APIRouter()
fernet = Fernet(settings.FERNET_KEY)

class RouterCreate(BaseModel):
    name: str
    ip_address: str
    api_port: int
    api_username: str
    api_password: str
    use_ssl: bool = False
    is_active: bool = True

class RouterUpdate(BaseModel):
    name: str | None = None
    ip_address: str | None = None
    api_port: int | None = None
    api_username: str | None = None
    api_password: str | None = None
    use_ssl: bool | None = None
    is_active: bool | None = None

@router.get("/")
async def list_routers(db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Router))
    return result.scalars().all()

@router.post("/")
async def create_router(data: RouterCreate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    encrypted_pwd = fernet.encrypt(data.api_password.encode()).decode()
    new_router = Router(
        name=data.name,
        ip_address=data.ip_address,
        api_port=data.api_port,
        api_username=data.api_username,
        api_password=encrypted_pwd,
        use_ssl=data.use_ssl,
        is_active=data.is_active
    )
    db.add(new_router)
    await db.commit()
    await db.refresh(new_router)
    return new_router

@router.patch("/{id}")
async def update_router(id: uuid.UUID, data: RouterUpdate, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Router).where(Router.id == id))
    router_db = result.scalar_one_or_none()
    if not router_db:
        raise HTTPException(status_code=404, detail="Router not found")
        
    for key, value in data.dict(exclude_unset=True).items():
        if key == 'api_password':
            value = fernet.encrypt(value.encode()).decode()
        setattr(router_db, key, value)
        
    await db.commit()
    await db.refresh(router_db)
    return router_db

@router.delete("/{id}")
async def delete_router(id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Router).where(Router.id == id))
    router_db = result.scalar_one_or_none()
    if not router_db:
        raise HTTPException(status_code=404, detail="Router not found")
        
    router_db.is_active = False
    await db.commit()
    return {"message": "Router soft deleted"}

@router.post("/{id}/check-connectivity")
async def check_connectivity(id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Router).where(Router.id == id))
    router_db = result.scalar_one_or_none()
    if not router_db:
        raise HTTPException(status_code=404, detail="Router not found")
        
    service = MikroTikService(router_db)
    try:
        is_connected = await service.check_connectivity()
        await service.close()
        return {"connected": is_connected}
    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.post("/{id}/sync-profiles")
async def sync_profiles(id: uuid.UUID, db: AsyncSession = Depends(get_db), admin=Depends(get_current_admin)):
    result = await db.execute(select(Router).where(Router.id == id))
    router_db = result.scalar_one_or_none()
    if not router_db:
        raise HTTPException(status_code=404, detail="Router not found")
        
    service = MikroTikService(router_db)
    try:
        profiles = await service.get_profiles()
        await service.close()
        
        synced = 0
        for p in profiles:
            name = p.get("name")
            if name == "default" or name == "default-encryption":
                continue
                
            plan_res = await db.execute(select(Plan).where(Plan.mikrotik_profile_name == name))
            existing = plan_res.scalar_one_or_none()
            if existing:
                continue
                
            rate_limit = p.get("rate-limit", "")
            dl_speed, up_speed = 0, 0
            if rate_limit:
                parts = rate_limit.split('/')
                if len(parts) == 2:
                    up_str, dl_str = parts[0], parts[1]
                    try:
                        up_speed = int(up_str.replace('M','').replace('k',''))
                        dl_speed = int(dl_str.replace('M','').replace('k',''))
                    except ValueError:
                        pass

            new_plan = Plan(
                name=f"Imported {name}",
                mikrotik_profile_name=name,
                download_speed_mbps=dl_speed,
                upload_speed_mbps=up_speed,
                price=0,
                validity_days=30
            )
            db.add(new_plan)
            synced += 1
            
        await db.commit()
        return {"message": f"Synced {synced} profiles"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
