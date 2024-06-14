# -*- coding: utf-8 -*-
import os

# Django WSGI application path in pattern MODULE_NAME:VARIABLE_NAME
wsgi_app = "sweepstake.wsgi:application"
# The granularity of Error log outputs
loglevel = "debug"
# The number of worker processes for handling requests
workers = int(os.environ.get("WORKERS", 2))
# The socket to bind
bind = "0.0.0.0:80"
# Restart workers when code changes (development only!)
reload = False
# Write access and error info to /var/log
# accesslog = errorlog = "./data/gunicorn.log"
# Redirect stdout/stderr to log file
capture_output = False
# PID file so you can easily fetch process ID
# pidfile = "./gunicorn.pid"
# Daemonize the Gunicorn process (detach & enter background)
daemon = False
