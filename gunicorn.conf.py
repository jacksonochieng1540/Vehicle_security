

import multiprocessing
import os

bind    = "unix:/run/gunicorn/vehicle_security.sock"




workers          = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class     = 'sync'          
worker_connections = 1000
threads          = 1               


timeout          = 120    
graceful_timeout = 30
keepalive        = 5

proc_name        = 'vehicle_security_system'


accesslog        = '-'
errorlog         = '-'
loglevel         = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

reload           = os.environ.get('GUNICORN_RELOAD', 'false').lower() == 'true'


umask            = 0o007          
