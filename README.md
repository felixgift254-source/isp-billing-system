# ISP Internet Billing & PPPoE Management System

A full-stack ISP management platform for automating subscriber billing, PPPoE session control, M-Pesa payments, and SMS notifications — built around a **Database as Source of Truth** architecture.

---

## Architecture Overview

The system follows a **Database as Source of Truth** pattern: all subscriber, billing, and session state lives in PostgreSQL. MikroTik routers are treated as enforcement endpoints — the backend reads authoritative state from the database and pushes configuration changes to routers via their REST API. This ensures consistency, auditability, and resilience even when routers are temporarily unreachable.

```
┌────────────┐     ┌────────────────┐     ┌──────────────┐
│  Next.js   │────▶│  FastAPI        │────▶│  PostgreSQL  │
│  Frontend  │◀────│  Backend        │◀────│  (Source of  │
│  :3000     │     │  :8000          │     │   Truth)     │
└────────────┘     └──────┬─────────┘     └──────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌─────────┐ ┌──────────────┐
        │  Redis   │ │ Celery  │ │  MikroTik    │
        │  Cache   │ │ Workers │ │  Routers     │
        │  :6379   │ │ & Beat  │ │  (REST API)  │
        └──────────┘ └─────────┘ └──────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌─────────────┐ ┌────────────┐
        │  M-Pesa  │ │  Africa's   │ │  Scheduled │
        │  Daraja  │ │  Talking    │ │  Tasks     │
        │  API     │ │  SMS API    │ │  (Billing) │
        └──────────┘ └─────────────┘ └────────────┘
```

### Key Flows

- **Payment**: M-Pesa STK Push → Daraja callback → backend records payment → Celery activates PPPoE on router
- **Expiry**: Celery Beat checks subscriptions → expires overdue accounts → removes PPPoE profiles from router → sends SMS notice
- **Sync**: Periodic Celery tasks reconcile router state with database truth

---

## Tech Stack

| Layer           | Technology                                |
| --------------- | ----------------------------------------- |
| **Frontend**    | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui |
| **Backend**     | FastAPI, Python 3.12, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Database**    | PostgreSQL 16                             |
| **Cache/Broker**| Redis 7                                   |
| **Task Queue**  | Celery 5 (worker + beat scheduler)        |
| **Payments**    | Safaricom M-Pesa Daraja API (STK Push)    |
| **SMS**         | Africa's Talking SMS Gateway              |
| **Router Mgmt** | MikroTik REST API (RouterOS 7.x)         |
| **Auth**        | JWT (HS256) with role-based access control |
| **Encryption**  | Fernet symmetric encryption (router passwords) |
| **Containers**  | Docker & Docker Compose                   |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) ≥ 24.0
- [Docker Compose](https://docs.docker.com/compose/install/) ≥ 2.20 (V2, included with Docker Desktop)
- [Git](https://git-scm.com/)

For M-Pesa sandbox testing:
- [ngrok](https://ngrok.com/) or any HTTPS tunnel for exposing callbacks

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/billing-system.git
cd billing-system
```

### 2. Configure Environment Variables

```bash
# Backend environment
cp .env.example .env
# Edit .env and fill in your actual values (JWT secret, M-Pesa keys, etc.)

# Frontend environment
cp frontend/.env.local.example frontend/.env.local
# Edit frontend/.env.local if needed
```

> **Important:** Generate secure values for `JWT_SECRET_KEY` and `FERNET_KEY` — see the comments in `.env.example` for generation commands.

### 3. Start All Services

```bash
docker-compose up -d
```

This starts PostgreSQL, Redis, the FastAPI backend, Celery worker/beat, and the Next.js frontend.

### 4. Run Database Migrations

```bash
docker-compose exec backend alembic upgrade head
```

### 5. Access the Application

| Service          | URL                                  |
| ---------------- | ------------------------------------ |
| **Frontend**     | [http://localhost:3000](http://localhost:3000) |
| **API Docs**     | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **ReDoc**        | [http://localhost:8000/redoc](http://localhost:8000/redoc) |

### 6. Login with Default Admin

```
Username: admin
Password: changeme123
```

> **⚠️ Change the default admin password immediately after first login.**

---

## Environment Variables Reference

| Variable                     | Description                                          | Default / Example                        |
| ---------------------------- | ---------------------------------------------------- | ---------------------------------------- |
| `DATABASE_URL`               | Async PostgreSQL connection string (asyncpg)         | `postgresql+asyncpg://...`               |
| `DATABASE_URL_SYNC`          | Sync PostgreSQL connection string (psycopg2)         | `postgresql+psycopg2://...`              |
| `REDIS_URL`                  | Redis connection string                              | `redis://redis:6379/0`                   |
| `JWT_SECRET_KEY`             | Secret key for signing JWT tokens                    | *(generate with secrets.token_hex)*      |
| `JWT_ALGORITHM`              | JWT signing algorithm                                | `HS256`                                  |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes                         | `480`                                    |
| `FERNET_KEY`                 | Fernet key for encrypting router passwords           | *(generate with Fernet.generate_key())*  |
| `MPESA_ENVIRONMENT`          | M-Pesa environment: `sandbox` or `production`        | `sandbox`                                |
| `MPESA_CONSUMER_KEY`         | Daraja API consumer key                              | —                                        |
| `MPESA_CONSUMER_SECRET`      | Daraja API consumer secret                           | —                                        |
| `MPESA_BUSINESS_SHORTCODE`   | Paybill or Till number                               | `174379`                                 |
| `MPESA_PASSKEY`              | Daraja API passkey                                   | *(sandbox default provided)*             |
| `MPESA_CALLBACK_BASE_URL`    | Public HTTPS URL for M-Pesa callbacks                | `https://your-domain.com`                |
| `AT_USERNAME`                | Africa's Talking username                            | `sandbox`                                |
| `AT_API_KEY`                 | Africa's Talking API key                             | —                                        |
| `AT_SENDER_ID`               | SMS sender ID (optional)                             | *(empty for default)*                    |
| `ADMIN_USERNAME`             | Default admin username (created on first startup)    | `admin`                                  |
| `ADMIN_PASSWORD`             | Default admin password                               | `changeme123`                            |
| `ADMIN_EMAIL`                | Default admin email                                  | `admin@example.com`                      |

---

## Project Structure

```
billing-system/
├── docker-compose.yml          # Container orchestration
├── .env.example                # Environment variable template
├── README.md                   # This file
│
├── backend/                    # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/                # Database migrations
│   │   └── versions/
│   └── app/
│       ├── main.py             # FastAPI application entry point
│       ├── config.py           # Pydantic Settings configuration
│       ├── database.py         # SQLAlchemy async engine & session
│       ├── models/             # SQLAlchemy ORM models (UUID PKs)
│       │   ├── user.py
│       │   ├── customer.py
│       │   ├── package.py
│       │   ├── subscription.py
│       │   ├── payment.py
│       │   ├── router.py
│       │   └── sms_log.py
│       ├── schemas/            # Pydantic request/response schemas
│       ├── api/                # API route handlers
│       │   ├── auth.py
│       │   ├── customers.py
│       │   ├── packages.py
│       │   ├── payments.py
│       │   ├── routers.py
│       │   └── dashboard.py
│       ├── services/           # Business logic layer
│       │   ├── mpesa.py        # M-Pesa Daraja integration
│       │   ├── sms.py          # Africa's Talking SMS
│       │   ├── mikrotik.py     # MikroTik REST API client
│       │   └── billing.py     # Subscription & billing logic
│       ├── workers/            # Celery tasks
│       │   ├── celery_app.py   # Celery application config
│       │   └── tasks.py        # Scheduled & async tasks
│       └── utils/              # Shared utilities
│           ├── encryption.py   # Fernet encrypt/decrypt
│           └── dependencies.py # FastAPI dependency injection
│
└── frontend/                   # Next.js frontend
    ├── Dockerfile
    ├── .env.local.example
    ├── package.json
    ├── tailwind.config.ts
    ├── next.config.js
    └── src/
        └── app/                # App Router pages & layouts
            ├── layout.tsx
            ├── page.tsx        # Dashboard
            ├── login/
            ├── customers/
            ├── packages/
            ├── payments/
            └── routers/
```

---

## API Documentation

FastAPI provides auto-generated interactive API documentation:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs) — interactive endpoint explorer with "Try It Out" functionality
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc) — alternative read-friendly API reference

All endpoints require a valid JWT token in the `Authorization: Bearer <token>` header, except for:
- `POST /api/auth/login` — authenticate and receive a token
- `POST /api/payments/mpesa/callback` — M-Pesa callback endpoint (validated by Safaricom)

---

## Development

### Hot Reload

Both the backend and frontend run with hot-reload enabled in development:

- **Backend**: `uvicorn --reload` watches for Python file changes
- **Frontend**: Next.js fast refresh watches for TypeScript/React changes

### Running Tests

```bash
# Backend tests
docker-compose exec backend pytest -v

# Frontend tests
docker-compose exec frontend npm test
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f celery-worker
```

### Database Shell

```bash
docker-compose exec postgres psql -U billing_user -d billing_db
```

### Creating Migrations

```bash
docker-compose exec backend alembic revision --autogenerate -m "description of changes"
docker-compose exec backend alembic upgrade head
```

---

## M-Pesa Setup (Daraja API)

### 1. Register on Daraja Portal

1. Go to [https://developer.safaricom.co.ke](https://developer.safaricom.co.ke)
2. Create an account and a new app
3. Enable **Lipa Na M-Pesa Online** (STK Push)
4. Copy your **Consumer Key** and **Consumer Secret** to `.env`

### 2. Sandbox Testing

The sandbox uses test credentials pre-configured in `.env.example`. Use the Safaricom test phone number `254708374149` and the test MSISDN for STK Push simulations.

### 3. Exposing Callbacks with ngrok

M-Pesa requires a publicly accessible HTTPS URL for payment callbacks:

```bash
# Install ngrok and start a tunnel to your backend
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
# Set it as MPESA_CALLBACK_BASE_URL in .env
```

> **Note:** The callback URL path must NOT contain the words `mpesa`, `m-pesa`, or `safaricom` — Daraja will reject it.

### 4. Going to Production

1. Apply for [Go Live](https://developer.safaricom.co.ke/APIs/go-live) on the Daraja portal
2. Complete KYC verification
3. Receive production credentials
4. Set `MPESA_ENVIRONMENT=production` in `.env`
5. Update all credentials to production values

---

## MikroTik Router Setup

### 1. Enable REST API (RouterOS 7.x)

The REST API is available on RouterOS 7.1beta4+ and is served over the `www-ssl` service:

```
/ip service enable www-ssl
/certificate add name=local-cert common-name=router.local days-valid=3650 key-size=2048
/certificate sign local-cert
/ip service set www-ssl certificate=local-cert
```

### 2. Create a Dedicated API User

Create a restricted user for the billing system:

```
/user group add name=billing-api policy=read,write,api,sensitive
/user add name=billing-api password=secure-password-here group=billing-api
```

### 3. Configure Firewall (Recommended)

Restrict REST API access to your billing server's IP only:

```
/ip firewall filter add chain=input src-address=YOUR_SERVER_IP dst-port=443 protocol=tcp action=accept comment="Allow Billing System API"
/ip firewall filter add chain=input dst-port=443 protocol=tcp action=drop comment="Block other REST API access"
```

### 4. Add Router in the Billing System

1. Log in to the billing system dashboard
2. Navigate to **Routers** → **Add Router**
3. Enter the router's IP/hostname, port (443), and the API credentials created above
4. The system will test the connection and confirm it's reachable

> **Security Note:** Router passwords are encrypted at rest using Fernet symmetric encryption. The `FERNET_KEY` in your `.env` file is the master key — back it up securely.

---

## License

This project is licensed under the [MIT License](LICENSE).
