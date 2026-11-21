from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext

from app.config import settings
from app.database import SyncSessionLocal
from app.models.user import User
from app.api.routes import api_router
from app.services.mpesa import MpesaService

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_admin_if_not_exists():
    """Create the default admin user on first startup."""
    with SyncSessionLocal() as session:
        admin = session.query(User).filter(User.username == settings.ADMIN_USERNAME).first()
        if not admin:
            hashed_password = pwd_context.hash(settings.ADMIN_PASSWORD)
            new_admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                hashed_password=hashed_password,
                full_name="Administrator",
                role="ADMIN",
                is_active=True,
            )
            session.add(new_admin)
            session.commit()
            logger.info("Default admin user created.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    create_admin_if_not_exists()

    if settings.MPESA_ENVIRONMENT != "sandbox":
        try:
            mpesa = MpesaService()
            result = await mpesa.register_c2b_urls()
            logger.info(f"M-Pesa C2B URLs registered: {result}")
        except Exception as e:
            logger.error(f"Failed to register M-Pesa C2B URLs: {e}")

    yield
    # Shutdown


app = FastAPI(
    title="ISP Billing System",
    description="ISP Internet Billing & PPPoE Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all API routes under /api/v1
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ISP Billing System"}
