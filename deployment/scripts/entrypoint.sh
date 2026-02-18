#!/bin/sh
# deployment/scripts/entrypoint.sh
# Runs inside the Django/Gunicorn container before the CMD.
# Handles: migrations, superuser creation, then hands off to CMD.

set -e   # exit immediately on any error

echo "======================================================"
echo " Vehicle Security System — Container Starting"
echo "======================================================"

# ── 1. Wait for PostgreSQL to be ready ────────────────────────────────────
echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT:-5432}..."

# Simple TCP check using Python (already installed)
python3 - <<'EOF'
import sys, time, socket, os

host = os.environ.get('DB_HOST', 'db')
port = int(os.environ.get('DB_PORT', 5432))
retries = 30

for attempt in range(retries):
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        print(f"[entrypoint] PostgreSQL is ready (attempt {attempt + 1})")
        sys.exit(0)
    except (socket.error, ConnectionRefusedError):
        print(f"[entrypoint] Waiting for PostgreSQL... ({attempt + 1}/{retries})")
        time.sleep(2)

print("[entrypoint] ERROR: PostgreSQL did not become ready in time.")
sys.exit(1)
EOF

# ── 2. Run database migrations ─────────────────────────────────────────────
echo "[entrypoint] Running database migrations..."
python manage.py migrate --noinput

# ── 3. Create default superuser if DJANGO_SUPERUSER_* vars are set ─────────
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "[entrypoint] Creating superuser '${DJANGO_SUPERUSER_USERNAME}' if not exists..."
    python manage.py createsuperuser \
        --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email    "${DJANGO_SUPERUSER_EMAIL:-admin@vehicle-security.local}" \
        2>/dev/null && echo "[entrypoint] Superuser created." \
                    || echo "[entrypoint] Superuser already exists — skipping."
fi

# ── 4. Ensure media subdirectories exist ───────────────────────────────────
mkdir -p \
    /app/media/facial_encodings \
    /app/media/unauthorized_images \
    /app/media/alert_images \
    /app/media/authentication_logs \
    /app/media/profile_images

# ── 5. Ensure Gunicorn socket directory is writable ───────────────────────
mkdir -p /run/gunicorn

echo "[entrypoint] Startup complete. Handing off to: $*"
echo "======================================================"

# ── 6. Execute the CMD (gunicorn) ─────────────────────────────────────────
exec "$@"