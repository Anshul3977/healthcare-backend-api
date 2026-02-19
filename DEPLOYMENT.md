# 🏥 Healthcare API — Deployment Guide

Production deployment instructions for the **Healthcare Backend** Django REST API.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Variables](#environment-variables)
- [Security Checklist](#security-checklist)
- [Option 1 — Heroku (with PostgreSQL Add-on)](#option-1--heroku-with-postgresql-add-on)
- [Option 2 — AWS EC2 (with RDS PostgreSQL)](#option-2--aws-ec2-with-rds-postgresql)
- [Option 3 — Docker Production Setup](#option-3--docker-production-setup)
- [Database Migrations](#database-migrations)
- [Post-Deployment Verification](#post-deployment-verification)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## Prerequisites

| Tool          | Version  | Purpose                        |
|---------------|----------|--------------------------------|
| Python        | 3.11+    | Runtime                        |
| PostgreSQL    | 15+      | Database                       |
| Git           | Latest   | Version control                |
| Docker        | 24+      | Containerization (Option 3)    |
| Heroku CLI    | Latest   | Heroku deployment (Option 1)   |
| AWS CLI       | v2       | EC2/RDS deployment (Option 2)  |

---

## Environment Variables

All deployment options require these environment variables. **Never commit secrets to Git.**

```bash
# ── Core Django ──────────────────────────────────────────
SECRET_KEY=<generate-a-64-char-random-string>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# ── Database ─────────────────────────────────────────────
DATABASE_NAME=healthcare_db
DATABASE_USER=healthcare_user
DATABASE_PASSWORD=<strong-random-password>
DATABASE_HOST=<db-host>          # localhost, RDS endpoint, or docker service name
DATABASE_PORT=5432
```

### Generating a Secure `SECRET_KEY`

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Security Checklist

Before deploying to production, apply these changes to `healthcare_backend/settings.py`:

### 1. Update `settings.py` for Production

```python
# ── settings.py — Production overrides ───────────────────

# Must be False in production
DEBUG = config('DEBUG', default=False, cast=bool)

# Restrict to your actual domain(s)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=lambda v: [s.strip() for s in v.split(',')])

# ── HTTPS / Cookie security ──────────────────────────────
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── CORS — restrict in production ────────────────────────
CORS_ALLOW_ALL_ORIGINS = DEBUG          # Only allow all in dev
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# ── Static files (for Heroku / production) ───────────────
STATIC_ROOT = BASE_DIR / 'staticfiles'
```

### 2. Add Production Dependencies

Add these to `requirements.txt`:

```
gunicorn==21.2.0
whitenoise==6.6.0
dj-database-url==2.1.0
```

### 3. Add WhiteNoise Middleware

In `MIDDLEWARE`, add `WhiteNoise` right after `SecurityMiddleware`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # ← add this
    # ... rest of middleware
]
```

---

## Option 1 — Heroku (with PostgreSQL Add-on)

### Step 1: Install Heroku CLI & Login

```bash
# macOS
brew tap heroku/brew && brew install heroku
heroku login
```

### Step 2: Create the Heroku App

```bash
heroku create healthcare-api-prod
```

### Step 3: Add PostgreSQL Add-on

```bash
heroku addons:create heroku-postgresql:essential-0
```

This automatically sets `DATABASE_URL`. To use it with `dj-database-url`, add to `settings.py`:

```python
import dj_database_url

# Override DATABASES when DATABASE_URL is present (Heroku)
DATABASE_URL = config('DATABASE_URL', default=None)
if DATABASE_URL:
    DATABASES['default'] = dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
        ssl_require=True
    )
```

### Step 4: Set Environment Variables

```bash
heroku config:set SECRET_KEY="$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")"
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=healthcare-api-prod.herokuapp.com
heroku config:set CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

### Step 5: Create `Procfile`

Create a file named `Procfile` (no extension) in the project root:

```
web: gunicorn healthcare_backend.wsgi --bind 0.0.0.0:$PORT --workers 3 --timeout 120
release: python manage.py migrate --noinput && python manage.py collectstatic --noinput
```

### Step 6: Create `runtime.txt`

```
python-3.11.7
```

### Step 7: Deploy

```bash
git add .
git commit -m "Configure for Heroku deployment"
git push heroku main
```

### Step 8: Create Superuser & Verify

```bash
heroku run python manage.py createsuperuser
heroku open /api/docs/
```

---

## Option 2 — AWS EC2 (with RDS PostgreSQL)

### Step 1: Launch RDS PostgreSQL Instance

```bash
aws rds create-db-instance \
    --db-instance-identifier healthcare-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15 \
    --master-username healthcare_user \
    --master-user-password '<strong-password>' \
    --allocated-storage 20 \
    --vpc-security-group-ids sg-xxxxxxxx \
    --db-name healthcare_db \
    --backup-retention-period 7 \
    --multi-az \
    --storage-encrypted
```

> **Note:** Ensure your EC2 security group allows inbound traffic on port `5432` from the EC2 instance, and the RDS is in the same VPC.

### Step 2: Launch & Configure EC2 Instance

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@<ec2-public-ip>

# Update and install dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip nginx
```

### Step 3: Clone & Configure the Application

```bash
cd /home/ubuntu
git clone <your-repo-url> healthcare_backend
cd healthcare_backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 4: Set Environment Variables

```bash
# Create /home/ubuntu/healthcare_backend/.env
cat > .env << 'EOF'
SECRET_KEY=<your-generated-secret-key>
DEBUG=False
ALLOWED_HOSTS=<ec2-public-ip>,yourdomain.com
DATABASE_NAME=healthcare_db
DATABASE_USER=healthcare_user
DATABASE_PASSWORD=<rds-password>
DATABASE_HOST=healthcare-db.xxxxxxxxxx.us-east-1.rds.amazonaws.com
DATABASE_PORT=5432
CORS_ALLOWED_ORIGINS=https://your-frontend.com
EOF

chmod 600 .env
```

### Step 5: Run Migrations & Collect Static Files

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### Step 6: Configure Gunicorn as a systemd Service

```bash
sudo tee /etc/systemd/system/healthcare.service > /dev/null << 'EOF'
[Unit]
Description=Healthcare API Gunicorn Service
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/healthcare_backend
EnvironmentFile=/home/ubuntu/healthcare_backend/.env
ExecStart=/home/ubuntu/healthcare_backend/venv/bin/gunicorn \
    healthcare_backend.wsgi:application \
    --bind unix:/run/gunicorn/healthcare.sock \
    --workers 3 \
    --timeout 120 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log

[Install]
WantedBy=multi-user.target
EOF

# Create required directories
sudo mkdir -p /run/gunicorn /var/log/gunicorn
sudo chown ubuntu:www-data /run/gunicorn /var/log/gunicorn

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable healthcare
sudo systemctl start healthcare
sudo systemctl status healthcare
```

### Step 7: Configure Nginx as Reverse Proxy

```bash
sudo tee /etc/nginx/sites-available/healthcare > /dev/null << 'EOF'
server {
    listen 80;
    server_name yourdomain.com <ec2-public-ip>;

    client_max_body_size 10M;

    location /static/ {
        alias /home/ubuntu/healthcare_backend/staticfiles/;
    }

    location / {
        proxy_pass http://unix:/run/gunicorn/healthcare.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/healthcare /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

### Step 8: Set Up SSL with Let's Encrypt (Recommended)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Step 9: Configure EC2 Security Group

| Rule      | Port | Source          | Purpose          |
|-----------|------|-----------------|------------------|
| SSH       | 22   | Your IP only   | Admin access     |
| HTTP      | 80   | 0.0.0.0/0      | Web traffic      |
| HTTPS     | 443  | 0.0.0.0/0      | Secure traffic   |
| PostgreSQL| 5432 | EC2 SG only    | DB (RDS ↔ EC2)   |

---

## Option 3 — Docker Production Setup

### Step 1: Create `Dockerfile`

Create `Dockerfile` in the project root:

```dockerfile
# ── Build stage ──────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ────────────────────────────────────────
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r django && useradd -r -g django django

COPY --from=builder /install /usr/local
COPY . .

RUN python manage.py collectstatic --noinput 2>/dev/null || true && \
    chown -R django:django /app

USER django

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/docs/ || exit 1

CMD ["gunicorn", "healthcare_backend.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
```

### Step 2: Create `docker-compose.prod.yml`

```yaml
version: "3.8"

services:
  db:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-healthcare_db}
      POSTGRES_USER: ${DATABASE_USER:-healthcare_user}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER:-healthcare_user}"]
      interval: 10s
      timeout: 5s
      retries: 5

  web:
    build:
      context: .
      dockerfile: Dockerfile
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env.prod
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - static_files:/app/staticfiles
      - log_files:/app/logs

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_files:/app/staticfiles:ro
      - ./nginx/certs:/etc/nginx/certs:ro         # mount SSL certs if available
    depends_on:
      - web

volumes:
  postgres_data:
  static_files:
  log_files:
```

### Step 3: Create Nginx Config

```bash
mkdir -p nginx
```

Create `nginx/nginx.conf`:

```nginx
upstream django {
    server web:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    client_max_body_size 10M;

    location /static/ {
        alias /app/staticfiles/;
    }

    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
    }
}
```

### Step 4: Create `.env.prod`

```bash
SECRET_KEY=<your-generated-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,localhost
DATABASE_NAME=healthcare_db
DATABASE_USER=healthcare_user
DATABASE_PASSWORD=<strong-random-password>
DATABASE_HOST=db
DATABASE_PORT=5432
CORS_ALLOWED_ORIGINS=https://your-frontend.com
```

> **Important:** Add `.env.prod` to `.gitignore`. Never commit production secrets.

### Step 5: Create `.dockerignore`

```
venv/
__pycache__/
*.pyc
.env
.env.prod
.git/
logs/
*.log
```

### Step 6: Build & Launch

```bash
# Build and start all services
docker compose -f docker-compose.prod.yml up -d --build

# Run migrations
docker compose -f docker-compose.prod.yml exec web python manage.py migrate --noinput

# Create superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# View logs
docker compose -f docker-compose.prod.yml logs -f web
```

---

## Database Migrations

Migrations must be run on every deployment. The method depends on your platform:

| Platform       | Command                                                                            |
|----------------|------------------------------------------------------------------------------------|
| **Local**      | `python manage.py migrate --noinput`                                               |
| **Heroku**     | Automatic via `release` phase in `Procfile`                                        |
| **EC2**        | `source venv/bin/activate && python manage.py migrate --noinput`                   |
| **Docker**     | `docker compose -f docker-compose.prod.yml exec web python manage.py migrate`      |

### Migration Best Practices

1. **Always test migrations locally** before deploying:
   ```bash
   python manage.py makemigrations --dry-run
   python manage.py migrate --plan
   ```

2. **Back up the database** before running migrations in production:
   ```bash
   # Heroku
   heroku pg:backups:capture

   # RDS
   aws rds create-db-snapshot \
       --db-instance-identifier healthcare-db \
       --db-snapshot-identifier pre-migration-$(date +%Y%m%d)

   # Docker
   docker compose -f docker-compose.prod.yml exec db \
       pg_dump -U healthcare_user healthcare_db > backup_$(date +%Y%m%d).sql
   ```

3. **Never edit or delete applied migration files.** Always create new migration files.

---

## Post-Deployment Verification

Run these checks after every deployment:

```bash
# 1. Verify the application is running
curl -s https://yourdomain.com/api/docs/ | head -20

# 2. Check health via API schema endpoint
curl -s https://yourdomain.com/api/schema/ -o /dev/null -w "%{http_code}"
# Expected: 200

# 3. Verify JWT authentication works
TOKEN=$(curl -s -X POST https://yourdomain.com/api/token/ \
    -H "Content-Type: application/json" \
    -d '{"username":"admin","password":"yourpassword"}' | python3 -c "import sys,json;print(json.load(sys.stdin)['access'])")

curl -s https://yourdomain.com/api/patients/ \
    -H "Authorization: Bearer $TOKEN" | head -20

# 4. Check migration status
# Heroku:  heroku run python manage.py showmigrations
# EC2:     python manage.py showmigrations
# Docker:  docker compose -f docker-compose.prod.yml exec web python manage.py showmigrations
```

---

## Monitoring & Maintenance

### Log Locations

| Platform   | Logs                                                             |
|------------|------------------------------------------------------------------|
| Heroku     | `heroku logs --tail`                                             |
| EC2        | `/var/log/gunicorn/access.log`, `/var/log/gunicorn/error.log`    |
| Docker     | `docker compose -f docker-compose.prod.yml logs -f web`          |
| Django     | `logs/django.log` (configured in `settings.py`)                  |

### Restart Commands

```bash
# Heroku
heroku restart

# EC2
sudo systemctl restart healthcare
sudo systemctl restart nginx

# Docker
docker compose -f docker-compose.prod.yml restart web
```

### Scaling

```bash
# Heroku — scale web dynos
heroku ps:scale web=2

# Docker — scale web containers
docker compose -f docker-compose.prod.yml up -d --scale web=3
# (Update nginx upstream to round-robin across containers)
```

---

> **Questions or issues?** Check the [Django Deployment Checklist](https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/) for additional security recommendations.
