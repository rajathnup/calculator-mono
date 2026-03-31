# CLAUDE.md — Calculator App (Monolithic)

This file contains all instructions, constraints, and context for building and
deploying a monolithic calculator app. Claude Code should read this before
doing anything in this project.

---

## Project Overview

A simple calculator web app built as a **monolith** — all logic, routing, and
frontend serving in a single deployable unit. This is Phase 1 of a two-phase
learning project. Phase 2 (microservices) comes later using the same app as
the base.

---

## Stack

| Layer       | Technology              |
|-------------|-------------------------|
| Backend     | Python + FastAPI        |
| Server      | Uvicorn                 |
| Frontend    | Plain HTML / CSS / JS   |
| Container   | Docker                  |
| Reverse proxy | Nginx                 |
| SSL         | Let's Encrypt (Certbot) |
| Cloud       | GCP Compute Engine      |
| OS on VM    | Ubuntu 22.04 LTS        |

---

## Folder Structure

```
calculator-mono/
├── app/
│   ├── main.py           ← FastAPI app, all routes
│   └── calculator.py     ← pure business logic (no HTTP concerns)
├── frontend/
│   └── index.html        ← plain HTML/CSS/JS UI
├── Dockerfile
└── requirements.txt
```

---

## Code Rules

### calculator.py
- Contains ONLY pure functions: `add`, `subtract`, `multiply`, `divide`
- No FastAPI imports here — no HTTP concerns whatsoever
- `divide` must raise `ValueError` on division by zero

### main.py
- Imports functions from `app.calculator` — never inline the math here
- Mounts frontend at `/static` via `StaticFiles(directory="frontend")`
- All routes: `POST /add`, `POST /subtract`, `POST /multiply`, `POST /divide`
- Health check route: `GET /health` returns `{"status": "ok", "app": "calculator-monolith"}`
- Request body validated via Pydantic `CalcRequest(a: float, b: float)`
- `divide` route catches `ValueError` and raises `HTTPException(status_code=400)`

### frontend/index.html
- Single file — no separate CSS or JS files
- All API calls use `fetch()` pointing to `/{operation}` (same origin, no CORS needed)
- Inputs: two number fields (a and b)
- Four buttons: Add, Subtract, Multiply, Divide
- Shows result in a result div
- Shows error message (e.g. divide by zero) in an error div

### requirements.txt
```
fastapi==0.111.0
uvicorn==0.29.0
python-multipart==0.0.9
```

---

## Docker Rules

### Dockerfile
- Base image: `python:3.11-slim`
- Working directory: `/app`
- Copy `requirements.txt` first, then `pip install`, then copy source code
  (this order preserves Docker layer cache)
- Copy both `app/` and `frontend/` into the image
- CMD: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

### Running locally
```bash
docker build -t calculator-mono .
docker run -p 8000:8000 calculator-mono
```

Access at: `http://localhost:8000/static/index.html`
Test API: `http://localhost:8000/docs`

### Running on GCP VM (production)
```bash
docker run -d \
  --name calculator \
  --restart unless-stopped \
  -p 8000:8000 \
  calculator-mono
```

- `-d` runs detached (background)
- `--restart unless-stopped` auto-restarts on VM reboot

---

## GCP Constraints — Free Tier

**Always stay within these limits to avoid billing:**

| Resource             | Free Tier Limit                        |
|----------------------|----------------------------------------|
| VM type              | `e2-micro` ONLY                        |
| Region               | `us-central1`, `us-west1`, or `us-east1` ONLY |
| Zone                 | `us-central1-a` (recommended)          |
| Persistent disk      | 30 GB standard (do not exceed)         |
| Egress traffic       | 1 GB/month                             |
| Static external IP   | Free only when attached to running VM — delete or release when VM is stopped |

**VM config to select in GCP Console:**
```
Name:         calculator-vm
Region:       us-central1
Zone:         us-central1-a
Machine type: e2-micro
Boot disk:    Ubuntu 22.04 LTS, 30 GB standard
Firewall:     Allow HTTP ✅  Allow HTTPS ✅
```

---

## Domain and DNS

- Domain: `bitbybit.co.in` (purchased on GoDaddy)
- Target URL: `https://calculator.bitbybit.co.in`

**GoDaddy DNS record to add:**
```
Type:   A
Name:   calculator
Value:  <VM public IP>
TTL:    600
```

Verify DNS propagation before running Certbot:
```bash
nslookup calculator.bitbybit.co.in
# must return the VM's public IP
```

---

## Nginx Rules

Config file location:
```
/etc/nginx/sites-available/calculator
```

Activate with symlink:
```bash
sudo ln -s /etc/nginx/sites-available/calculator /etc/nginx/sites-enabled/calculator
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

**Config before SSL (HTTP only):**
```nginx
server {
    listen 80;
    server_name calculator.bitbybit.co.in;

    location /static/ {
        alias /home/<USERNAME>/calculator-mono/frontend/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Replace `<USERNAME>` with the actual Linux user (`whoami` to check).

After Certbot runs, it will auto-edit this file to add SSL — do not manually
add SSL blocks.

**Always run before reloading Nginx:**
```bash
sudo nginx -t
```

**Nginx log locations:**
```
/var/log/nginx/access.log
/var/log/nginx/error.log
```

---

## SSL — Let's Encrypt via Certbot

Run only after DNS has propagated:
```bash
sudo certbot --nginx -d calculator.bitbybit.co.in
```

- Select yes to HTTP → HTTPS redirect when prompted
- Certbot auto-edits the Nginx config
- Auto-renewal cron job is set up automatically (renews at 60 days, cert expires at 90)

Verify auto-renewal:
```bash
sudo certbot renew --dry-run
```

---

## VM Setup Commands (in order)

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io
sudo usermod -aG docker $USER
newgrp docker

# 3. Install Nginx and Certbot
sudo apt install -y nginx
sudo apt install -y certbot python3-certbot-nginx

# 4. Copy code from local machine (run on local machine, not VM)
gcloud compute scp --recurse . calculator-vm:~/calculator-mono --zone=us-central1-a

# 5. Build and run container (back on VM)
cd ~/calculator-mono
docker build -t calculator-mono .
docker run -d --name calculator --restart unless-stopped -p 8000:8000 calculator-mono

# 6. Configure Nginx
sudo nano /etc/nginx/sites-available/calculator
# (paste config from above)
sudo ln -s /etc/nginx/sites-available/calculator /etc/nginx/sites-enabled/calculator
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# 7. Get SSL cert (only after DNS propagates)
sudo certbot --nginx -d calculator.bitbybit.co.in
```

---

## Verification Checklist

```
[ ] docker ps                          → calculator container is running
[ ] curl http://localhost:8000/health  → {"status": "ok"}
[ ] nslookup calculator.bitbybit.co.in → returns VM public IP
[ ] http://calculator.bitbybit.co.in   → Nginx welcome or calculator page
[ ] https://calculator.bitbybit.co.in  → padlock visible, calculator loads
[ ] POST /add returns correct result   → test via /docs or curl
[ ] Divide by zero returns HTTP 400    → not a 500 crash
[ ] sudo certbot renew --dry-run       → all simulated renewals succeeded
```

---

## Useful Debug Commands

```bash
# Container
docker ps                        # is it running?
docker logs calculator           # app logs
docker restart calculator        # restart container

# Nginx
sudo nginx -t                    # syntax check
sudo systemctl status nginx      # is nginx running?
sudo systemctl reload nginx      # apply config changes
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# SSL
sudo certbot certificates        # view cert expiry dates
sudo certbot renew --dry-run     # test auto-renewal

# DNS
nslookup calculator.bitbybit.co.in
```

---

## What Comes Next — Phase 2 (Microservices)

This same calculator will be split into 5 separate services:

```
api-gateway/     ← routes requests to correct service
add-service/     ← only handles addition
sub-service/     ← only handles subtraction
mul-service/     ← only handles multiplication
div-service/     ← only handles division
docker-compose.yml
```

Each service will be its own FastAPI app, its own Docker container, its own
port. Orchestrated with Docker Compose. Deployed to the same GCP e2-micro VM.

Do not start Phase 2 until Phase 1 is fully working and deployed at
`https://calculator.bitbybit.co.in`.
