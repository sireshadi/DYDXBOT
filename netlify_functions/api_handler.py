import serverless_wsgi
import sys
import os

# Add the 'backend' directory to sys.path to allow importing 'app' from 'backend.app'
# This assumes 'api_handler.py' is in 'netlify_functions/', and 'backend/' is at the same level as 'netlify_functions/'
# Adjust if your directory structure for the handler is different relative to 'backend'.
# The path needs to point to the directory *containing* the 'backend' package.
# If netlify_functions is at the root, and backend is also at the root, this path is correct.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from backend.app import create_app

app = create_app()

# Optional: If your Flask app relies on instance_path for SQLite DB or uploads,
# and this path needs to be writable in serverless (which is usually /tmp),
# you might need to adjust app.instance_path here.
# However, for SQLite and local file uploads on Netlify, this will be problematic
# due to the ephemeral nature of serverless function storage.
# For instance, if UPLOAD_FOLDER uses app.instance_path:
# if os.environ.get('NETLIFY_DEV') != 'true': # Not running in netlify dev
#    app.instance_path = '/tmp/instance' # Change instance path for deployed functions
#    if not os.path.exists(app.instance_path):
#        os.makedirs(app.instance_path)
#    # This also means the SQLite DB would need to be in /tmp or a cloud DB used.
# This part is complex and highlights the SQLite/local uploads issue.
# For now, let's keep it simple and assume create_app() sets up instance_path as needed,
# acknowledging it won't persist across invocations for file storage.

def handler(event, context):
    # serverless_wsgi translates API Gateway/Lambda event & context to WSGI
    return serverless_wsgi.handle_request(app, event, context)
