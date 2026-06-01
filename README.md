# MK Shipping Lines — Vessel Booking Platform

**Live Site:** [https://mkshippinglines.com](https://mkshippinglines.com)

A full-featured vessel/ferry ticket booking platform built with Django, Django Channels (WebSockets), Celery, and PostgreSQL — containerised with Docker Compose.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Prerequisites](#prerequisites)
5. [Environment Variables](#environment-variables)
6. [Getting Started (Local Development)](#getting-started-local-development)
7. [Loading Fixture Data](#loading-fixture-data)
8. [Running Migrations](#running-migrations)
9. [Creating a Superuser](#creating-a-superuser)
10. [Useful Docker Commands](#useful-docker-commands)
11. [Services Overview](#services-overview)
12. [Deployment Notes](#deployment-notes)
13. [Common Errors & Fixes](#common-errors--fixes)

---

## Project Overview

MK Shipping Lines is an online vessel ticketing system that allows passengers to:

- Browse available ship routes and schedules
- Select seats from an interactive deck/cabin layout
- Book and pay for tickets online (SSLCommerz gateway integrated)
- Receive QR-code-based e-tickets
- Manage bookings (cancel, view, download PDF tickets)

The admin panel supports:

- Ship, deck, route, and trip management
- Counter and agent (sales channel) management
- Real-time seat hold & auto-release via Celery Beat
- Blog, about, and CMS-style content management
- Newsletter subscribers and footer settings

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Django 4/5 |
| Async / WebSocket | Django Channels + Daphne |
| Task Queue | Celery + Redis |
| Scheduler | Celery Beat |
| Database | PostgreSQL 18 |
| Cache / Broker | Redis 7 |
| Payment | SSLCommerz |
| PDF Generation | WeasyPrint (Cairo/Pango) |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
MKShipping/
├── accounts/           # Custom user model, profiles, counter assignment
├── admin_panel/        # Core app — ships, routes, trips, bookings, tickets
│   ├── fixtures/       # Fixture JSON files
│   ├── migrations/     # Database migrations (0001 → 0071+)
│   ├── management/     # Custom management commands
│   ├── templates/      # HTML templates for admin panel
│   ├── static/         # App-level static files
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   ├── tasks.py        # Celery tasks (seat auto-release, etc.)
│   └── signals.py
├── config/             # Django project config
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py         # ASGI entry point (Daphne)
│   ├── celery.py       # Celery app definition
│   └── middleware.py
├── payment/            # Payment gateway integration (SSLCommerz)
├── portal/             # Public-facing portal / frontend views
├── ticketing/          # Ticket rendering, QR code, PDF generation
├── media/              # Uploaded media files (runtime)
├── static/             # Collected static files
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── manage.py
└── mk_shipping.json    # Full database fixture (seed data)
```

---

## Prerequisites

Make sure the following are installed on your machine:

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- [Docker Compose](https://docs.docker.com/compose/) (included in Docker Desktop)
- Git

---

## Environment Variables

Create a `.env` file in the project root. Use the `.env` file already present (it is listed in `.gitignore`, so it is never committed).

A minimal example:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,mkshippinglines.com

# Database (must match docker-compose.yml db service)
DB_NAME=mydb
DB_USER=myuser
DB_PASSWORD=mypassword
DB_HOST=db
DB_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/0

# SSLCommerz Payment Gateway
SSLCZ_STORE_ID=your_store_id
SSLCZ_STORE_PASS=your_store_password
SSLCZ_SANDBOX=True   # Set to False in production

# Email (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your@email.com
EMAIL_HOST_PASSWORD=your-app-password
```

---

## Getting Started (Local Development)

### 1. Clone the repository

```bash
git clone https://your-repo-url/MKShipping.git
cd MKShipping
```

### 2. Build and start all services

```bash
docker-compose up --build
```

This starts four services:
- `web` — Django app served via Daphne on port **8000**
- `db` — PostgreSQL on port **5432**
- `redis` — Redis on port **6379**
- `celery` — Celery worker
- `celery-beat` — Celery beat scheduler

### 3. Run migrations (first time only)

Open a second terminal while the containers are running:

```bash
docker-compose exec web python manage.py migrate
```

### 4. Load seed/fixture data

```bash
docker-compose exec web python manage.py loaddata mk_shipping.json
```

> **Important:** Always run `migrate` before `loaddata`. If you run `loaddata` before the tables exist, you will get a `relation "admin_panel_ship" does not exist` error. See [Common Errors](#common-errors--fixes) below.

### 5. Collect static files

```bash
docker-compose exec web python manage.py collectstatic --noinput
```

### 6. Access the app

| URL | Description |
|---|---|
| http://localhost:8000 | Public portal |
| http://localhost:8000/admin | Django admin |

---

## Loading Fixture Data

The file `mk_shipping.json` contains 1 593 objects covering ships, routes, trips, seat categories, locations, and CMS content.

```bash
# Make sure migrations are applied first
docker-compose exec web python manage.py migrate

# Then load the fixture
docker-compose exec web python manage.py loaddata mk_shipping.json
```

---

## Running Migrations

```bash
# Detect new model changes and create migration files
docker-compose exec web python manage.py makemigrations

# Apply all pending migrations to the database
docker-compose exec web python manage.py migrate
```

---

## Creating a Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password. Then log in at http://localhost:8000/admin.

---

## Useful Docker Commands

```bash
# Start all services (detached / background mode)
docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes (wipes the database — use with caution)
docker-compose down -v

# Rebuild images after dependency changes
docker-compose up --build

# View live logs for all services
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f web
docker-compose logs -f celery

# Open a shell inside the web container
docker-compose exec web bash

# Run any Django management command
docker-compose exec web python manage.py <command>

# Check running containers
docker-compose ps
```

---

## Services Overview

### `web` — Django / Daphne

Serves the Django application over ASGI using Daphne, enabling both HTTP and WebSocket connections.

### `db` — PostgreSQL 18

Persistent database. Data is stored in the `postgres_data` Docker volume so it survives container restarts.

### `redis` — Redis 7

Acts as both the Django Channels layer (WebSocket message broker) and the Celery task broker.

### `celery` — Celery Worker

Executes background tasks defined in `admin_panel/tasks.py`, including:
- Automatic seat-hold expiry and release
- Booking auto-cancellation after the hold timer expires
- Email/notification dispatch

### `celery-beat` — Celery Beat Scheduler

Triggers periodic tasks on a schedule (defined in `config/celery.py` or the `celerybeat-schedule` file).

---

## Deployment Notes

For production deployment:

1. Set `DEBUG=False` in `.env`
2. Add your domain to `ALLOWED_HOSTS`
3. Use a reverse proxy (Nginx) in front of Daphne
4. Set `SSLCZ_SANDBOX=False` and use live SSLCommerz credentials
5. Ensure `SECRET_KEY` is a long, random, unique value
6. Run `collectstatic` and serve the `/static/` and `/media/` directories via Nginx
7. Use a managed PostgreSQL instance or ensure the Docker volume is backed up regularly

A minimal Nginx config for proxying to Daphne:

```nginx
server {
    listen 80;
    server_name mkshippinglines.com;

    location /static/ {
        alias /app/static/;
    }

    location /media/ {
        alias /app/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Common Errors & Fixes

### `relation "admin_panel_ship" does not exist` during `loaddata`

**Cause:** You ran `loaddata` before running `migrate`, so the database tables do not exist yet.

**Fix:**
```bash
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py loaddata mk_shipping.json
```

---

### `docker-compose.yml: the attribute 'version' is obsolete`

**Cause:** Newer versions of Docker Compose no longer require the `version:` key.

**Fix:** Remove the `version: '3.8'` line from `docker-compose.yml`. This is a warning only and does not break anything.

---

### Celery tasks not running

**Cause:** The `celery` or `celery-beat` service may not have started correctly.

**Fix:**
```bash
docker-compose logs celery
docker-compose logs celery-beat
docker-compose restart celery celery-beat
```

---

### Static files not loading (404 on CSS/JS)

**Fix:**
```bash
docker-compose exec web python manage.py collectstatic --noinput
```

Make sure `STATIC_ROOT` is set correctly in `settings.py` and that Nginx (in production) points to that directory.

---

### Database connection refused on startup

**Cause:** The `web` service starts before `db` is ready to accept connections.

**Fix:** Add a health-check or `restart: on-failure` to the `web` service in `docker-compose.yml`, or simply wait a few seconds and restart:

```bash
docker-compose restart web
```

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit your changes: `git commit -m "Add your feature"`
3. Push the branch: `git push origin feature/your-feature`
4. Open a pull request for review

---

## Contact

For questions or support, contact the repository owner .