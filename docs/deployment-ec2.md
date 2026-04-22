# EC2 Deployment (Ubuntu + systemd + Nginx)

This setup keeps deployment minimal:
- FastAPI runs as a `systemd` service on `127.0.0.1:8000`
- Nginx serves frontend static files and reverse-proxies `/api/*` and `/sample_data/*`
- `.env` stays at repo root (already how this app is configured)

## 1) One-time server packages

```bash
sudo apt-get update
sudo apt-get install -y git curl nginx python3 python3-venv python3-pip rsync
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v
npm -v
python3 --version
```

## 2) Clone (or pull) repo

```bash
cd /home/ubuntu
if [ ! -d News-intelligence-agent/.git ]; then
  git clone <YOUR_GIT_REMOTE_URL> News-intelligence-agent
fi
cd News-intelligence-agent
git pull
```

## 3) Backend venv + dependencies

```bash
cd /home/ubuntu/News-intelligence-agent
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
deactivate
```

## 4) Frontend install + production build

```bash
cd /home/ubuntu/News-intelligence-agent/frontend
npm ci
npm run build
```

## 5) Configure `.env` for production

```bash
cd /home/ubuntu/News-intelligence-agent
cp -n .env.example .env
nano .env
```

Minimum production values to set:

```env
APP_ENV=production
APP_HOST=127.0.0.1
APP_PORT=8000
LOG_LEVEL=INFO

# single allowed browser origin
FRONTEND_ORIGIN=http://<EC2_PUBLIC_IP_OR_DOMAIN>

# optional: comma-separated list overrides FRONTEND_ORIGIN
# FRONTEND_ORIGINS=https://example.com,https://www.example.com
```

Keep your existing model/API keys and ingestion settings in this same `.env`.

## 6) Manual backend start command from repo root

Use this stable command shape (preserves `app.*` imports with backend app-dir):

```bash
cd /home/ubuntu/News-intelligence-agent
source .venv/bin/activate
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Or use the included script:

```bash
cd /home/ubuntu/News-intelligence-agent
chmod +x deploy/start_backend.sh
./deploy/start_backend.sh
```

## 7) Install backend `systemd` service

```bash
cd /home/ubuntu/News-intelligence-agent
chmod +x deploy/start_backend.sh
sudo cp deploy/news-intelligence-agent.service /etc/systemd/system/news-intelligence-agent.service
sudo systemctl daemon-reload
sudo systemctl enable --now news-intelligence-agent
sudo systemctl status news-intelligence-agent --no-pager
```

Useful logs:

```bash
sudo journalctl -u news-intelligence-agent -n 100 --no-pager
```

## 8) Publish frontend build and configure Nginx

```bash
cd /home/ubuntu/News-intelligence-agent
sudo mkdir -p /var/www/news-intelligence-agent/frontend/dist
sudo rsync -av --delete frontend/dist/ /var/www/news-intelligence-agent/frontend/dist/
sudo cp deploy/nginx/news-intelligence-agent.conf /etc/nginx/sites-available/news-intelligence-agent
sudo ln -sfn /etc/nginx/sites-available/news-intelligence-agent /etc/nginx/sites-enabled/news-intelligence-agent
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx
```

## 9) Verify deployment with curl

Health through backend socket:

```bash
curl -i http://127.0.0.1:8000/api/health
```

Health through Nginx/public entrypoint:

```bash
curl -i http://<EC2_PUBLIC_IP_OR_DOMAIN>/api/health
```

Analyze route through Nginx:

```bash
curl -i -X POST http://<EC2_PUBLIC_IP_OR_DOMAIN>/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"query":"AI policy updates","max_articles":3}'
```

Ingest + status through Nginx:

```bash
curl -i -X POST http://<EC2_PUBLIC_IP_OR_DOMAIN>/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"query":"shipping disruptions","max_articles":5}'

curl -i http://<EC2_PUBLIC_IP_OR_DOMAIN>/api/status/<TASK_ID>
```

## 10) Deploying updates quickly

```bash
cd /home/ubuntu/News-intelligence-agent
git pull
source .venv/bin/activate
pip install -r backend/requirements.txt
deactivate
cd frontend
npm ci
npm run build
cd ..
sudo rsync -av --delete frontend/dist/ /var/www/news-intelligence-agent/frontend/dist/
sudo systemctl restart news-intelligence-agent
sudo systemctl reload nginx
```
