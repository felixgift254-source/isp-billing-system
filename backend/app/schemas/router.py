from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class RouterBase(BaseModel):
    name: str
    ip_address: str
    api_port: int = 443
    api_username: str
    use_ssl: bool = True
    is_active: bool = True
    status: str = "OFFLINE"

class RouterCreate(RouterBase):
    api_password: str

class RouterUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    api_port: Optional[int] = None
    api_username: Optional[str] = None
    api_password: Optional[str] = None
    use_ssl: Optional[bool] = None
    is_active: Optional[bool] = None
    status: Optional[str] = None

class RouterResponse(RouterBase):
    id: UUID
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
