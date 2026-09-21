# Day 51: Cloud Deployment & Server Setup

This guide details the end-to-end production deployment configuration for the **Zecpath AI Recruitment Platform** on **Ubuntu 24.04 LTS** (AWS EC2 / DigitalOcean Droplet).

---

## 1. Server Provisioning & Firewall Configuration

### System Updates & Core Packages
```bash
# Update and install system dependencies
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl git ufw
```

### UFW Firewall Hardening
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
```

---

## 2. Gunicorn Service Unit Configuration

A systemd service unit file is configured at `/etc/systemd/system/zecpath.service`:

```ini
[Unit]
Description=Gunicorn instance serving Zecpath AI Recruitment Platform
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/zecpath-backend
Environment="PATH=/home/ubuntu/zecpath-backend/venv/bin"
EnvironmentFile=/home/ubuntu/zecpath-backend/.env
ExecStart=/home/ubuntu/zecpath-backend/venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/home/ubuntu/zecpath-backend/zecpath.sock \
          zecpath_backend.wsgi:application

[Install]
WantedBy=multi-user.target
```

### Activation Commands
```bash
sudo systemctl daemon-reload
sudo systemctl start zecpath
sudo systemctl enable zecpath
```

---

## 3. Nginx Reverse Proxy Configuration

Nginx server configuration is placed at `/etc/nginx/sites-available/zecpath`:

```nginx
server {
    listen 80;
    server_name api.zecpath.com 127.0.0.1;

    client_max_body_size 25M;

    location /static/ {
        alias /home/ubuntu/zecpath-backend/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/zecpath-backend/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/zecpath-backend/zecpath.sock;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Linking & Testing
```bash
sudo ln -s /etc/nginx/sites-available/zecpath /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

---

## 4. Automated Deployment Script

The automated script is available in the repository at `deploy/setup_server.sh`:
```bash
chmod +x deploy/setup_server.sh
./deploy/setup_server.sh
```
