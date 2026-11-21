from typing import Annotated, Optional
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.config import settings
from app.database import get_db
from app.models import User, Customer
from app.models.audit_log import AuditLog

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/login')

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != 'ADMIN':
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return user

async def get_current_customer(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Customer:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        customer_id: str = payload.get("sub")
        role: str = payload.get("role")
        if customer_id is None or role != "customer":
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(Customer).where(Customer.id == customer_id))
    customer = result.scalar_one_or_none()
    if customer is None:
        raise credentials_exception
    return customer


async def get_current_actor(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> dict:
    """Allow either an Admin User or a Customer to access endpoints with role checks."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        sub: str = payload.get("sub")
        role: str = payload.get("role")
        if not sub:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        if role == "ADMIN":
            res = await db.execute(select(User).where(User.id == sub))
            user = res.scalar_one_or_none()
            if user:
                return {"type": "ADMIN", "id": user.id, "obj": user}
        elif role == "customer":
            res = await db.execute(select(Customer).where(Customer.id == sub))
            cust = res.scalar_one_or_none()
            if cust:
                return {"type": "CUSTOMER", "id": cust.id, "obj": cust}

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not recognized")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


async def record_audit_log(
    db: AsyncSession,
    *,
    action: str,
    user: Optional[User] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """
    Persist an immutable audit-log entry.

    Parameters
    ----------
    db          : active async DB session
    action      : short verb, e.g. SUSPEND, REACTIVATE, RECONCILE, PLAN_CHANGE
    user        : the User performing the action (may be None for system tasks)
    target_type : model class name, e.g. 'Customer', 'Payment'
    target_id   : str(UUID) of the affected record
    details     : arbitrary JSON payload with before/after context
    request     : FastAPI Request (used to extract IP + User-Agent)
    """
    ip = None
    ua = None
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        ip = forwarded.split(",")[0].strip() if forwarded else (
            request.client.host if request.client else None
        )
        ua = request.headers.get("user-agent")

    log = AuditLog(
        user_id=user.id if user else None,
        user_email=user.email if user else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else None,
        details=details,
        ip_address=ip,
        user_agent=ua,
    )
    db.add(log)
    # Flush but don't commit — caller owns the transaction
    await db.flush([log])
    return log
