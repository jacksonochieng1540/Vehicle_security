#!/usr/bin/env bash
# deployment/scripts/deploy.sh
# One-shot deployment script for the Raspberry Pi (bare-metal, no Docker).
# Run as the 'pi' user, not as root.
#
# Usage:
#   chmod +x deployment/scripts/deploy.sh
#   ./deployment/scripts/deploy.sh

set -euo pipefail

# ── Colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()    { echo -e "${GREEN}[deploy]${NC} $*"; }
warning() { echo -e "${YELLOW}[deploy]${NC} $*"; }
error()   { echo -e "${RED}[deploy]${NC} $*"; exit 1; }

# ── Config ─────────────────────────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PYTHON="$VENV_DIR/bin/python"
PIP="$VENV_DIR/bin/pip"

info "Project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

# ── Guard ──────────────────────────────────────────────────────────────────
[ -f ".env" ] || error ".env file not found. Copy .env.docker to .env and fill in values."

# ── 1. System packages ─────────────────────────────────────────────────────
info "Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    python3-pip python3-venv python3-dev \
    libpq-dev libatlas-base-dev libopenblas-dev libgl1-mesa-glx libglib2.0-0 \
    postgresql postgresql-contrib \
    nginx \
    git build-essential

# ── 2. Groups ──────────────────────────────────────────────────────────────
info "Adding pi to dialout and gpio groups..."
sudo usermod -aG dialout pi
sudo usermod -aG gpio    pi

# ── 3. Virtual environment ─────────────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

info "Installing Python dependencies..."
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -r requirements.txt
"$PIP" install --quiet pynmea2 requests RPi.GPIO opencv-contrib-python==4.8.1.78

# ── 4. Database ────────────────────────────────────────────────────────────
info "Ensuring PostgreSQL is running..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Source .env to get DB credentials
set -a; source .env; set +a

info "Creating database and user (safe to re-run)..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" \
    | grep -q 1 \
    || sudo -u postgres psql -c "CREATE DATABASE ${DB_NAME};"

sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='${DB_USER}'" \
    | grep -q 1 \
    || sudo -u postgres psql -c "CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';"

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"
sudo -u postgres psql -c "ALTER DATABASE ${DB_NAME} OWNER TO ${DB_USER};"

# ── 5. Django setup ────────────────────────────────────────────────────────
export DJANGO_SETTINGS_MODULE=config.settings_production

info "Running migrations..."
"$PYTHON" manage.py migrate --noinput

info "Collecting static files..."
"$PYTHON" manage.py collectstatic --noinput --clear

# Create superuser if DJANGO_SUPERUSER_USERNAME is set in .env
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ]; then
    info "Creating superuser '${DJANGO_SUPERUSER_USERNAME}' if not exists..."
    "$PYTHON" manage.py createsuperuser --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email    "${DJANGO_SUPERUSER_EMAIL:-admin@vehicle-security.local}" \
        2>/dev/null || true
fi

# ── 6. Gunicorn socket dir ─────────────────────────────────────────────────
sudo mkdir -p /run/gunicorn
sudo chown pi:pi /run/gunicorn
sudo chmod 750   /run/gunicorn

# ── 7. systemd services ────────────────────────────────────────────────────
info "Installing systemd services..."
sudo cp deployment/scripts/vehicle-security.service /etc/systemd/system/
sudo cp deployment/scripts/vehicle-autorun.service  /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vehicle-security.service vehicle-autorun.service
sudo systemctl restart vehicle-security.service
sudo systemctl restart vehicle-autorun.service

# ── 8. Nginx ───────────────────────────────────────────────────────────────
info "Configuring Nginx..."
sudo cp deployment/nginx/vehicle_security.conf /etc/nginx/sites-available/vehicle_security
sudo ln -sf /etc/nginx/sites-available/vehicle_security \
            /etc/nginx/sites-enabled/vehicle_security
sudo rm -f /etc/nginx/sites-enabled/default   # remove the default placeholder
sudo nginx -t && sudo systemctl reload nginx

# ── 9. Status report ───────────────────────────────────────────────────────
info "Deployment complete! Service status:"
sudo systemctl status vehicle-security.service --no-pager -l | tail -6
sudo systemctl status vehicle-autorun.service  --no-pager -l | tail -4

PI_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}======================================================"
echo " Vehicle Security System deployed successfully!"
echo "======================================================"
echo -e " Web interface : http://${PI_IP}${NC}"
echo ""
warning "NOTE: Re-login or reboot for group changes (dialout/gpio) to take effect."