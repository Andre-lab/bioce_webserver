import sys
import os
import logging
#logging.basicConfig(stream=sys.stderr)

sys.path.insert(0, '/var/www/html/bioce_webserver/')
sys.path.insert(0, '/var/www/html/bioce_webserver/frontend')
sys.path.append('/var/www/html/bioce_webserver/backend/bioce')

from frontend import app as application
