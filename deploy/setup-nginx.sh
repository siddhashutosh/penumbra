#!/usr/bin/env bash
# PENUMBRA public gateway on port 8080 — runs ON the VPS, alongside KESSLER (:80).
# Does NOT touch KESSLER's nginx config. Run:  bash setup-nginx.sh
set -euo pipefail

echo "[1/3] writing PENUMBRA nginx server block (port 8080)..."
sudo tee /etc/nginx/sites-available/penumbra > /dev/null << 'CONF'
limit_req_zone $binary_remote_addr zone=pen_api:10m rate=30r/m;

server {
    listen 8080 default_server;
    server_name _;

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;

    # admin-only refresh trigger stays private
    location = /api/v1/pipeline/refresh { return 403; }

    location /api/ {
        limit_req zone=pen_api burst=20 nodelay;
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header X-Forwarded-For $remote_addr;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header X-Forwarded-For $remote_addr;
    }
}
CONF

echo "[2/3] enabling site (KESSLER's :80 block untouched)..."
sudo ln -sf /etc/nginx/sites-available/penumbra /etc/nginx/sites-enabled/penumbra
sudo nginx -t

echo "[3/3] reloading nginx..."
sudo systemctl reload nginx
sleep 3
curl -s -o /dev/null -w "penumbra via nginx :8080 = %{http_code}\n" http://localhost:8080/api/v1/health
curl -s -o /dev/null -w "kessler still :80    = %{http_code}\n" http://localhost/api/v1/health
echo "Done. Open Lightsail TCP 8080 in the firewall to expose http://13.127.244.0:8080"
