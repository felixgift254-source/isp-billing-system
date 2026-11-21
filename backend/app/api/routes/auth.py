from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import bcrypt
from app.api.deps import get_db, create_access_token, get_current_user
from app.models import User, Customer

router = APIRouter()

class PortalLogin(BaseModel):
    phone_number: str
    password: str

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": access_token, "token_type": "bearer", "user": {"id": user.id, "username": user.username, "role": user.role}}

@router.post("/portal-login")
async def portal_login(data: PortalLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Customer).where(Customer.phone_number == data.phone_number))
    customer = result.scalar_one_or_none()
    
    if not customer or customer.pppoe_password != data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password",
        )
        
    access_token = create_access_token(data={"sub": str(customer.id), "role": "customer"})
    return {"access_token": access_token, "token_type": "bearer", "customer": {"id": customer.id, "name": customer.full_name}}

@router.get("/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
