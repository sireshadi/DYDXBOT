import serverless_wsgi
# Assuming your Flask app's create_app factory is in backend/app.py
# Adjust the import path if your app.py is structured differently or located elsewhere relative to 'backend/functions/'
# The typical way to import from a parent directory or sibling module in Python can be tricky with serverless functions' execution environment.
# A common way is to ensure the parent 'backend' directory is in the Python path.
# For Netlify, it often handles this if functions are in a subdirectory of the code it deploys.
# Let's try a relative import path that should work if 'backend' is the root for the function's perspective or in sys.path.

# Option 1: If Netlify adds the 'backend' directory to sys.path for functions in backend/functions
# from app import create_app
# This assumes app.py is directly in 'backend' and 'backend' is effectively a root for imports.

# Option 2: A more robust way if the execution path is tricky,
# is to adjust sys.path if needed, or structure so 'backend' is a package.
# For now, let's assume Netlify's Python runtime for functions in `backend/functions`
# can find `app.py` in the `backend` directory.
# A common structure that works is if `app.py` is in the root of the functions deployment package.
# Given our `netlify.toml` specifies `functions = "backend/functions/"`,
# code in `backend/app.py` needs to be accessible.
# One way is to ensure our Flask app (`app.py`, `models.py` etc.) are deployed alongside the function handler,
# or installed as part of its dependencies.
# The simplest way for Netlify is often that the function file can import from its parent if the parent is deployed.

import sys
import os

# Add the parent directory (backend) to sys.path to allow importing 'app'
# This assumes api.py is in backend/functions/ and app.py is in backend/
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import app # Now this should work. Assumes app object is directly available.
                    # If using create_app factory: from app import create_app; app = create_app()

# If using create_app, uncomment the line below and comment out the line above
# from app import create_app
# app = create_app()

def handler(event, context):
    # Wrap the Flask app with serverless_wsgi to handle API Gateway/Lambda events
    return serverless_wsgi.handle_request(app, event, context)
