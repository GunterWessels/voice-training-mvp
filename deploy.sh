#!/bin/bash
# LiquidSMARTS™ CCE Voice Simulation — Deploy Script
# Usage: ./deploy.sh [--skip-build]
# Target: Hostinger liquidsmarts-web (72.60.67.231), /opt/cce-liquidsmarts
# Prerequisites: SSH access, .env.production file present

set -euo pipefail

REMOTE_USER="root"
REMOTE_HOST="72.60.67.231"
REMOTE_DIR="/opt/cce-liquidsmarts"
LOCAL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKIP_BUILD=false

for arg in "$@"; do
  [ "$arg" = "--skip-build" ] && SKIP_BUILD=true
done

echo "==> LiquidSMARTS™ CCE Voice Simulation Deploy"
echo "    Target: $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"
echo ""

# Step 1: Require .env.production
if [ ! -f "$LOCAL_DIR/.env.production" ]; then
  echo "ERROR: .env.production not found."
  echo "Copy .env.production.example to .env.production and fill in values."
  exit 1
fi

# Step 2: Ensure app-network exists on server
echo "==> Ensuring Docker app-network exists..."
ssh "$REMOTE_USER@$REMOTE_HOST" "
  docker network inspect app-network >/dev/null 2>&1 || docker network create app-network
"

# Step 3: Sync files to server
echo "==> Syncing files..."
rsync -avz \
  --exclude 'node_modules' \
  --exclude '.next' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude 'backend/.env' \
  --exclude 'frontend-next/.env.local' \
  "$LOCAL_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# Step 4: Sync env file
echo "==> Syncing environment config..."
rsync -avz "$LOCAL_DIR/.env.production" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/.env.production"

# Step 5: Build and restart on server
echo "==> Building and restarting containers..."
if [ "$SKIP_BUILD" = false ]; then
  ssh "$REMOTE_USER@$REMOTE_HOST" "
    cd $REMOTE_DIR
    cp .env.production .env
    docker compose build --no-cache
    docker compose up -d --remove-orphans
    docker compose ps
  "
else
  ssh "$REMOTE_USER@$REMOTE_HOST" "
    cd $REMOTE_DIR
    set -a && source .env.production && set +a
    docker compose up -d --remove-orphans
    docker compose ps
  "
fi

# Step 5b: Run database migrations (idempotent SQL files)
echo "==> Running database migrations..."
ssh "$REMOTE_USER@$REMOTE_HOST" "
  cd $REMOTE_DIR
  echo '  Waiting for DB to be ready...'
  docker compose exec -T db pg_isready -U postgres --timeout=30
  echo '  Running 001_initial.sql...'
  docker compose exec -T db psql -U postgres -d voice_training \
    -c '\set ON_ERROR_STOP off' \
    -f /dev/stdin < backend/migrations/001_initial.sql 2>&1 | grep -v 'already exists' || true
  echo '  Running 002_rag.sql...'
  docker compose exec -T db psql -U postgres -d voice_training \
    -c '\set ON_ERROR_STOP off' \
    -f /dev/stdin < backend/migrations/002_rag.sql 2>&1 | grep -v 'already exists' || true
  echo '  Migrations complete.'
"

# Step 6: Add Caddy vhost (idempotent)
# Caddy runs as a container; Caddyfile is mounted at /home/deploy/caddy/Caddyfile
echo "==> Checking Caddy configuration..."
ssh "$REMOTE_USER@$REMOTE_HOST" "
  CADDYFILE=/home/deploy/caddy/Caddyfile
  if grep -q 'cce.liquidsmarts.com' \$CADDYFILE 2>/dev/null; then
    echo '  Caddy vhost already configured.'
  else
    echo '  Adding CCE vhost to Caddyfile...'
    cat >> \$CADDYFILE << 'CADDYEOF'

cce.liquidsmarts.com {
    handle /ws/* {
        reverse_proxy cce-backend:8000 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Real-IP {remote_host}
        }
    }
    handle /api/* {
        reverse_proxy cce-backend:8000 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Real-IP {remote_host}
        }
    }
    handle {
        reverse_proxy cce-frontend:3002 {
            header_up X-Forwarded-Proto {scheme}
            header_up X-Real-IP {remote_host}
        }
    }
    header {
        X-Frame-Options DENY
        X-Content-Type-Options nosniff
        Referrer-Policy strict-origin-when-cross-origin
        Permissions-Policy \"camera=(), microphone=(self), geolocation=()\"
        -Server
    }
    encode gzip
    log {
        output file /var/log/caddy/cce.access.log {
            roll_size 10mb
            roll_keep 5
        }
    }
}
CADDYEOF
    docker exec caddy caddy reload --config /etc/caddy/Caddyfile
    echo '  Caddy reloaded.'
  fi
"

echo ""
echo "==> Deploy complete!"
echo "    CCE Platform: https://cce.liquidsmarts.com"
echo ""
echo "First-deploy checklist:"
echo "  1. DNS: Add CNAME cce -> 72.60.67.231 in Hostinger DNS panel"
echo "  2. Supabase Auth: Add https://cce.liquidsmarts.com to allowed redirect URLs"
echo "  3. Run DB migration: cd voice-training-mvp && python3 backend/migrations/run.py"
echo "  4. Seed BSCI scenarios: python3 backend/seeds/seed_bsci.py"
echo "  5. Verify: curl -I https://cce.liquidsmarts.com"
