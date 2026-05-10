readme_content = '''# 🚢 M&K Shipping — Ferry Booking System

A Django-based ferry and passenger booking management system with real-time seat updates, QR code ticketing, payment system, background task processing, and full Docker support.

## 🌐 Live Site

Visit: https://mkshippinglines.com/
Admin: https://mkshippinglines.com/dashboard/

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Docker Setup](#docker-setup)
- [WebSocket & Real-time Features](#websocket--real-time-features)
- [Celery Background Tasks](#celery-background-tasks)
- [Project Structure](#project-structure)
- [Booking Flow](#booking-flow)
- [Author](#author)

---

## 📌 About

M&K Shipping is a ferry passenger booking platform that allows:
- Online seat booking and ticketing
- QR code generation for each booking
- Passenger manifest and PDF generation
- Ship schedule and seat layout management
- Real-time seat availability via WebSocket
- Payment processing system
- Background email/notification processing via Celery
- Full Docker containerized deployment

---

## ✨ Features

- ✅ Passenger booking system
- ✅ QR code ticket generation
- ✅ PDF manifest export
- ✅ Real-time seat layout (WebSocket)
- ✅ Live booking notifications (WebSocket)
- ✅ Admin live dashboard (WebSocket)
- ✅ Payment system
- ✅ Background email & notifications (Celery)
- ✅ Ship and schedule management
- ✅ Booking cancellation tracking
- ✅ User accounts & authentication
- ✅ Fully Dockerized (multi-container)

---

## 🛠 Tech Stack

| Layer              | Technology                  |
|--------------------|-----------------------------|
| Backend            | Python 3.x, Django          |
| Real-time / ASGI   | Django Channels, Daphne     |
| WebSocket          | Django Channels + Redis     |
| Background Tasks   | Celery                      |
| Message Broker     | Redis 7                     |
| Frontend           | HTML, CSS, JavaScript       |
| Database           | PostgreSQL 13 (production)  |
| QR Code            | qrcode library              |
| PDF                | Django PDF rendering        |
| Payment            | Payment Gateway Integration |
| Containerization   | Docker, Docker Compose      |

---

## 🐳 Docker Setup

This project uses **Docker Compose** with 4 containers:

| Container | Image          | Role                              |
|-----------|----------------|-----------------------------------|
| web       | Custom build   | Django app (Daphne ASGI server)   |
| redis     | redis:7-alpine | Message broker for Celery & WS    |
| celery    | Custom build   | Background task worker            |
| db        | postgres:13    | PostgreSQL database               |

### Run with Docker

```bash
# Build and start all containers
docker-compose up --build

# Run in background
docker-compose up -d --build

# Apply migrations inside container
docker-compose exec web python manage.py migrate

# Create superuser inside container
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic

# Stop all containers
docker-compose down
```

### View Logs

```bash
# All containers
docker-compose logs -f

# Specific container
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f redis
docker-compose logs -f db
```

---

## 🚀 Getting Started (Without Docker)

### 1. Clone the Repository

```bash
git clone https://github.com/NihalSWE/M-K-Shipping.git
cd M-K-Shipping
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\\Scripts\\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup Environment Variables

Create a `.env` file in the root directory:

```env
SECRET_KEY=your-secret-key
DEBUG=True
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379
```

### 5. Start Redis

```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 6. Apply Migrations

```bash
python manage.py migrate
```

### 7. Create Superuser

```bash
python manage.py createsuperuser
```

### 8. Start Celery Worker (new terminal)

```bash
celery -A config worker --loglevel=info
```

### 9. Run Server (Daphne)

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Visit: http://127.0.0.1:8000
Admin: http://127.0.0.1:8000/admin

---

## ⚡ WebSocket & Real-time Features

This project uses **Django Channels** with **Daphne** as the ASGI server and **Redis** as the channel layer for:

- 🪑 **Live seat availability** — seat map updates instantly when someone books
- 🔔 **Real-time booking notifications** — admin gets notified on new bookings
- 📊 **Admin live dashboard** — live stats without page refresh

---

## 📬 Celery Background Tasks

**Redis** is used as the Celery message broker for:

- 📧 Sending booking confirmation emails
- 🔔 Triggering notifications after booking

Check Celery status:

```bash
# Local
celery -A config status

# Docker
docker-compose exec celery celery -A config status
```

---

## 📁 Project Structure