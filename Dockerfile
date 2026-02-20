# Dockerfile
# Multi-stage build for vehicle_security_system
# Stage 1 builds Python wheels; Stage 2 is the slim runtime image.
# Compatible with: linux/arm64 (Raspberry Pi 4/5) and linux/amd64 (VPS/laptop)

# ── Stage 1: Builder ───────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# System dependencies needed only to compile Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        libpq-dev \
        libblas-dev \
        liblapack-dev \
        libopenblas-dev \
        libhdf5-dev \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

WORKDIR /wheels

# Copy only requirements first so Docker layer cache works
COPY requirements.txt .

# Build wheels for all packages (without --no-deps to ensure all dependencies are included)
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Install extra packages needed by hardware modules (not in original requirements.txt)
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
        pynmea2 \
        requests \
        opencv-contrib-python==4.8.1.78


# ── Stage 2: Runtime ───────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Labels for documentation
LABEL maintainer="Jackson Ochieng & Elijah Sunkuli — JKUAT ENE 2026"
LABEL description="Vehicle Security System — Django + Gunicorn"

# Runtime system libraries (smaller set than builder)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
        libblas3 \
        liblapack3 \
        libopenblas0 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1001 appgroup && \
    useradd  --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# Install Python packages from builder's wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# App directory
WORKDIR /app

# Copy project source
COPY --chown=appuser:appgroup . .

# Create directories that the app writes to at runtime
# These are mounted as Docker volumes in docker-compose.yml
RUN mkdir -p \
        /app/staticfiles \
        /app/media/facial_encodings \
        /app/media/unauthorized_images \
        /app/media/alert_images \
        /app/media/authentication_logs \
        /app/media/profile_images \
        /run/gunicorn \
    && chown -R appuser:appgroup \
        /app/staticfiles \
        /app/media \
        /run/gunicorn

# Switch to non-root user
USER appuser

# Collect static files at build time so the image is self-contained
# The SECRET_KEY value here is only for the collectstatic command; the real
# secret is injected at runtime via environment variables.
RUN DJANGO_SETTINGS_MODULE=config.settings_production \
    SECRET_KEY=build-time-placeholder-not-used-at-runtime \
    DB_HOST=placeholder \
    python manage.py collectstatic --noinput --clear

# Expose nothing — Gunicorn uses a Unix socket shared with Nginx via a volume
# If you want to run without Nginx during development, uncomment:
# EXPOSE 8000

# Gunicorn socket directory must exist and be writable
VOLUME ["/run/gunicorn", "/app/media", "/app/staticfiles"]

# ── Entrypoint ─────────────────────────────────────────────────────────────
COPY --chown=appuser:appgroup deployment/scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "-c", "gunicorn.conf.py", "config.wsgi:application"]