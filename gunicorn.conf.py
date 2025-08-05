# Gunicorn configuration for Render deployment
import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = 1  # Render free tier has limited memory
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 10

# Restart workers after this many requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "wizzy-bot"

# Preload app for better performance
preload_app = True

# Enable auto-reload in development
if os.getenv('ENVIRONMENT') == 'development':
    reload = True
