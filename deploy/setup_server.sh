#!/usr/bin/env bash
# ==============================================================================
# Zecpath AI Recruitment Platform - Automated Cloud Server Provisioning Script
# OS: Ubuntu 24.04 LTS (AWS EC2 / DigitalOcean Droplet)
# ==============================================================================

set -e

echo "=== [1/5] Updating system packages & installing dependencies ==="
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv python3-dev libpq-dev postgresql postgresql-contrib nginx curl git ufw

echo "=== [2/5] Configuring UFW Firewall ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

echo "=== [3/5] Setting up Gunicorn Systemd Service ==="
sudo cp /home/ubuntu/zecpath-backend/deploy/zecpath.service /etc/systemd/system/zecpath.service
sudo systemctl daemon-reload
sudo systemctl enable zecpath
sudo systemctl restart zecpath

echo "=== [4/5] Setting up Nginx Reverse Proxy Configuration ==="
sudo cp /home/ubuntu/zecpath-backend/deploy/nginx_zecpath.conf /etc/nginx/sites-available/zecpath
sudo ln -sf /etc/nginx/sites-available/zecpath /etc/nginx/sites-enabled/zecpath
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "=== [5/5] Cloud Provisioning Complete! ==="
echo "Status check:"
sudo systemctl status zecpath --no-pager
sudo systemctl status nginx --no-pager
