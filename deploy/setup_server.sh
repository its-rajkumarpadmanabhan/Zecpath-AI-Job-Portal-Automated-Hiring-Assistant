#!/usr/bin/env bash
# ==============================================================================
# Zecpath AI Recruitment Platform - Automated Cloud Server Provisioning Script
# OS: Ubuntu 24.04 LTS (AWS EC2 / DigitalOcean Droplet)
# ==============================================================================

set -e

echo "=== [1/6] Updating system packages & installing dependencies ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl git ufw

echo "=== [2/6] Configuring UFW Firewall ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable
sudo ufw status

echo "=== [3/6] Setting up Virtual Environment and Dependencies ==="
cd /home/ubuntu/zecpath-backend
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [4/6] Running Migrations and Static Collection ==="
python manage.py migrate --noinput
python manage.py collectstatic --noinput

echo "=== [5/6] Setting up Gunicorn Systemd Service ==="
sudo cp /home/ubuntu/zecpath-backend/deploy/gunicorn.service /etc/systemd/system/gunicorn.service
sudo systemctl daemon-reload
sudo systemctl enable gunicorn
sudo systemctl restart gunicorn

echo "=== [6/6] Setting up Nginx Reverse Proxy Configuration ==="
sudo cp /home/ubuntu/zecpath-backend/deploy/nginx_zecpath.conf /etc/nginx/sites-available/zecpath
sudo ln -sf /etc/nginx/sites-available/zecpath /etc/nginx/sites-enabled/zecpath
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "=== Cloud Provisioning & Service Boot Completed Successfully! ==="
echo "--- Gunicorn Status ---"
sudo systemctl status gunicorn --no-pager
echo "--- Nginx Status ---"
sudo systemctl status nginx --no-pager
