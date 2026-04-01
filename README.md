# 🛒 E-Commerce Shopping System — REST API Backend

> A production-ready, scalable RESTful API backend for an e-commerce management system, built with **Python**, **FastAPI**, and **PostgreSQL**. Designed with clean architecture principles, JWT authentication, real-time notifications, and full Docker support.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Database Design](#database-design)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Docker Deployment](#docker-deployment)
- [Database Migrations](#database-migrations)
- [Project Structure](#project-structure)

---

## Overview

This project is a **backend API system** for a full-featured e-commerce platform, handling product inventory, client management, billing, payments, stock monitoring, and multi-channel notifications (Email + WhatsApp). It follows **RESTful API design** principles and implements **role-based access control** for admin and client users.

Built to be deployed as a containerized microservice using **Docker** and hosted on cloud platforms such as **Railway**.

---

## Tech Stack

| Layer                      | Technology                            |
| -------------------------- | ------------------------------------- |
| **Language**               | Python 3.11                           |
| **Framework**              | FastAPI 0.122                         |
| **Database**               | PostgreSQL (via psycopg2-binary)      |
| **ORM**                    | SQLAlchemy 2.0                        |
| **Migrations**             | Alembic 1.17                          |
| **Authentication**         | JWT (JSON Web Tokens) via python-jose |
| **Password Hashing**       | bcrypt / passlib                      |
| **Data Validation**        | Pydantic v2                           |
| **Image Storage**          | Cloudinary                            |
| **Email Notifications**    | SMTP (Gmail)                          |
| **WhatsApp Notifications** | Twilio API                            |
| **OTP / 2FA**              | Custom OTP service                    |
| **Server**                 | Uvicorn + Gunicorn                    |
| **Containerization**       | Docker + Docker Compose               |
| **Cloud Deployment**       | Railway                               |

---

## Architecture

The project follows a **layered, modular architecture**:

```
├── routers/         # Route handlers (controllers) — one file per domain
├── models/          # SQLAlchemy ORM models — database schema definitions
├── schemas/         # Pydantic schemas — request/response validation & serialization
├── utils/           # Database session management, helpers
├── config/          # Third-party service configurations (Cloudinary, etc.)
├── alembic/         # Database migration scripts (version-controlled)
├── main.py          # FastAPI application entry point, middleware, router registration
```

This separation of concerns makes the codebase maintainable, testable, and easy to extend — following industry-standard **backend engineering** best practices.

---

## Features

### 🔐 Authentication & Security

- JWT-based stateless authentication
- Role-based access control (Admin / Client)
- Secure password hashing with bcrypt
- OTP (One-Time Password) generation and verification for sensitive operations
- Token expiration and refresh logic

### 🧑‍💼 Admin Management

- Admin registration and login
- Multi-admin support with individual profiles

### 👤 Client Management

- Client registration, login, and profile management
- Client account balance tracking
- Active/inactive account states

### 📦 Product & Inventory Management

- Full CRUD for products and categories
- Product variants support (JSON-based configuration)
- Barcode support per product
- Multi-image upload via Cloudinary
- Stock quantity tracking with configurable minimum thresholds

### 🔔 Automated Stock Alerts

- Automatic low-stock detection and alert generation
- Alert history per product

### 🧾 Billing & Order Management

- Bill creation linked to clients and products
- Bill items with variant support
- Delivery status tracking (`not_delivered`, `on_the_way`, `delivered`)
- Bill status tracking (`paid`, `not paid`)

### 💳 Payment Management

- Multiple partial payments per bill
- Real-time balance calculation (`total_amount`, `total_paid`, `total_remaining`)
- Full payment history per bill

### 📬 Notification System

- Automated Email notifications via SMTP
- WhatsApp notifications via Twilio
- Notification history per bill and client

---

## API Endpoints

| Resource       | Base Path         | Operations                             |
| -------------- | ----------------- | -------------------------------------- |
| Auth           | `/auth`           | Login                                  |
| Admin          | `/admin`          | CRUD, profile                          |
| Client         | `/client`         | CRUD, profile, activation              |
| Client Account | `/client-account` | Balance, transactions                  |
| Category       | `/category`       | CRUD                                   |
| Product        | `/product`        | CRUD, variants, barcode, images        |
| Bill           | `/bill`           | Create, read, update status & delivery |
| Payment        | `/payment`        | Create, read, history                  |
| Stock Alert    | `/stock-alert`    | List, acknowledge                      |
| Notification   | `/notification`   | Send, history                          |
| OTP            | `/otp`            | Generate, verify                       |
| Upload         | `/upload`         | Image upload to Cloudinary             |

Full interactive API documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Database Design

The system uses a **relational PostgreSQL** database with the following core entities and relationships:

- **Admin** — manages products and oversees the system
- **Client** — places orders, has account balance
- **Category** — groups products
- **Product** — belongs to a category, managed by an admin; has stock level, barcode, images, variants
- **Bill** — belongs to a client; contains bill items; has payment and notification history
- **BillItem** — links a bill to a product with quantity and variant info
- **Payment** — partial or full payment records per bill
- **StockAlert** — triggered automatically when a product falls below minimum stock
- **Notification** — email/WhatsApp records linked to bills
- **OTP** — one-time password records for verification flows
- **ClientAccount** — tracks client balance and credit

All schema changes are version-controlled using **Alembic migrations**.

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Docker & Docker Compose (optional)

### Local Setup

```bash
# 1. Clone the repository
git clone https://github.com/your-username/shoping_app_system.git
cd shoping_app_system

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment variables
cp .env.example .env
# Edit .env with your database URL, JWT secret, SMTP, and Twilio credentials

# 5. Apply database migrations
alembic upgrade head

# 6. Start the development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: `http://localhost:8000`  
Swagger docs: `http://localhost:8000/docs`

---

## Docker Deployment

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# Stop services
docker-compose down
```

The `docker-compose.yml` spins up:

- The FastAPI application container
- A PostgreSQL database container

Migrations are applied automatically on container startup via:

```
alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

---

## Database Migrations

This project uses **Alembic** for schema version control.

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration (after modifying models)
alembic revision --autogenerate -m "describe your change"

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Project Structure

```
shoping_app_system/
├── alembic/
│   ├── env.py
│   ├── versions/          # Migration scripts
│   └── script.py.mako
├── config/
│   └── cloudinary_config.py
├── models/
│   ├── admin.py
│   ├── bill.py
│   ├── bill_item.py
│   ├── category.py
│   ├── client.py
│   ├── client_account.py
│   ├── notification.py
│   ├── otp.py
│   ├── payment.py
│   ├── product.py
│   └── stock_alert.py
├── routers/
│   ├── admin.py
│   ├── auth.py
│   ├── bill.py
│   ├── category.py
│   ├── client.py
│   ├── client_account.py
│   ├── notification.py
│   ├── otp.py
│   ├── payment.py
│   ├── product.py
│   ├── stock_alert.py
│   └── upload.py
├── schemas/               # Pydantic request/response models
├── utils/
│   └── db.py              # Database session, init, seed
├── .env.example
├── .dockerignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── main.py
└── requirements.txt
```

---

## Keywords

`Python` · `FastAPI` · `PostgreSQL` · `SQLAlchemy` · `Alembic` · `REST API` · `RESTful API` · `Backend Development` · `API Development` · `Pydantic` · `JWT Authentication` · `OAuth2` · `Docker` · `Docker Compose` · `Uvicorn` · `Gunicorn` · `ORM` · `Database Migrations` · `Microservices` · `Cloud Deployment` · `Railway` · `Cloudinary` · `Twilio` · `SMTP` · `Notification System` · `Inventory Management` · `E-Commerce Backend` · `Async Python` · `API Security` · `Role-Based Access Control` · `RBAC` · `bcrypt` · `OTP` · `Two-Factor Authentication` · `Backend Engineer` · `Software Engineer` · `Python Developer`

---

## 📄 License

This project is licensed under the **MIT License**.

---

<p align="center">
  Built with me MESSAOUD MOSBAH using <strong>FastAPI</strong> · <strong>PostgreSQL</strong> · <strong>SQLAlchemy</strong> · Deployed on <strong>Railway</strong>
</p>
