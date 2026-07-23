# PENUMBRA — VPS deployment (co-hosted with KESSLER)

Deployed to the shared `mumbai-vps` (ap-south-1, 13.127.244.0) **without disturbing KESSLER**:
a separate systemd service on port 8001, exposed via its own nginx server block on port 8080.
KESSLER keeps port 80.

## Layout on the VPS

```
/opt/penumbra/backend        app + .venv (Python 3.12) + .env
/opt/penumbra/ui/dist        built UI (served by FastAPI SPA fallback)
/etc/systemd/system/penumbra.service      (MemoryMax=190M, port 8001)
/etc/nginx/sites-available/penumbra        (listen 8080 -> 127.0.0.1:8001)
```

## Coexistence guarantees (NFR-5)

- KESSLER's `/etc/nginx/sites-available/kessler` (:80) is **never edited**.
- PENUMBRA binds only :8001 (app) and :8080 (nginx); both were free before deploy.
- `MemoryMax=190M` bounds PENUMBRA on the shared 414 MB host (host has a 512 MB swap).

## Operations

```bash
ssh -i ~/.ssh/lightsail-ap-south-1.pem ubuntu@13.127.244.0
sudo systemctl status penumbra
sudo systemctl restart penumbra
journalctl -u penumbra -f
```

## Redeploy (from dev machine)

```bash
cd /d/PROJECT/penumbra
npm --prefix ui run build
tar --exclude='.venv' --exclude='node_modules' --exclude='logs/*' \
    --exclude='app/data/cache.db' --exclude='.env' \
    -czf /tmp/penumbra-deploy.tar.gz backend ui/dist README.md
scp -i ~/.ssh/lightsail-ap-south-1.pem /tmp/penumbra-deploy.tar.gz ubuntu@13.127.244.0:/tmp/
ssh -i ~/.ssh/lightsail-ap-south-1.pem ubuntu@13.127.244.0 \
  'tar -xzf /tmp/penumbra-deploy.tar.gz -C /opt/penumbra &&
   /opt/penumbra/backend/.venv/bin/pip install -q -r /opt/penumbra/backend/requirements.txt &&
   sudo systemctl restart penumbra'
```

## Access

`http://13.127.244.0:8080` (after opening Lightsail TCP 8080). For live NOAA data instead of the
bundled demo series, set `PENUMBRA_LIVE=1` in `/opt/penumbra/backend/.env` and restart.
