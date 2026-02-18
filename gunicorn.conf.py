# gunicorn.conf.py
# Gunicorn configuration for vehicle_security_system
# Used by Docker and the bare-metal systemd service alike.
#
# Start with:
#   gunicorn -c gunicorn.conf.py config.wsgi:application

import multiprocessing
import os

# ── Binding ────────────────────────────────────────────────────────────────
# Gunicorn listens on a Unix socket so Nginx can forward to it without
# opening a network port on the container / host.
bind    = "unix:/run/gunicorn/vehicle_security.sock"
# Fallback for local dev without Nginx:
# bind = "0.0.0.0:8000"

# ── Workers ────────────────────────────────────────────────────────────────
# Raspberry Pi has 4 cores; (2 × cores) + 1 is the standard formula.
# On a VPS with more cores, this auto-scales.
workers          = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class     = 'sync'          # sync is correct for a standard WSGI app
worker_connections = 1000
threads          = 1               # keep at 1 per sync worker

# ── Timeouts ───────────────────────────────────────────────────────────────
timeout          = 120    # raised to 120 s to allow facial recognition processing
graceful_timeout = 30
keepalive        = 5

# ── Process naming ─────────────────────────────────────────────────────────
proc_name        = 'vehicle_security_system'

# ── Logging ────────────────────────────────────────────────────────────────
# '-' sends logs to stdout/stderr so Docker and journald capture them.
accesslog        = '-'
errorlog         = '-'
loglevel         = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ── Reload (development only – never use in production) ────────────────────
reload           = os.environ.get('GUNICORN_RELOAD', 'false').lower() == 'true'

# ── Socket permissions ─────────────────────────────────────────────────────
umask            = 0o007           # socket is rw for owner + group only