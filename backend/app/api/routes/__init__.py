from fastapi import APIRouter

from app.api.routes import auth, routers, plans, customers, invoices, payments, mpesa, dashboard, portal, pdf, audit_logs

api_router = APIRouter()
api_router.include_router(auth.router, prefix='/auth', tags=['Auth'])
api_router.include_router(routers.router, prefix='/routers', tags=['Routers'])
api_router.include_router(plans.router, prefix='/plans', tags=['Plans'])
api_router.include_router(customers.router, prefix='/customers', tags=['Customers'])
api_router.include_router(invoices.router, prefix='/invoices', tags=['Invoices'])
api_router.include_router(payments.router, prefix='/payments', tags=['Payments'])
api_router.include_router(mpesa.router, prefix='/billing', tags=['Billing'])
api_router.include_router(dashboard.router, prefix='/dashboard', tags=['Dashboard'])
api_router.include_router(portal.router, prefix='/portal', tags=['Portal'])
api_router.include_router(pdf.router, prefix='', tags=['PDF Downloads'])
api_router.include_router(audit_logs.router, prefix='/audit-logs', tags=['Audit Logs'])
