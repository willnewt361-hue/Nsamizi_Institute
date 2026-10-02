# Gunicorn configuration for Nsamizi Institute
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
user = "www-data"
group = "www-data"
tmp_upload_dir = None
