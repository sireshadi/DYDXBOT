from flask import Flask, request, jsonify, redirect, url_for, send_from_directory, abort, make_response, session, render_template
# werkzeug.security imports removed as they are now in models.py (User model)
# UserMixin removed from this import, it's used in models.py (User model)
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
import bleach
import os
import sys
from datetime import datetime, timedelta

# Import db instance from .database
from .database import db
# Import models from .models
from .models import User, FunnelLink, Lead, UserPage, UserAsset

# Model definitions for User, FunnelLink, Lead are now in models.py and imported above.

# Bleach sanitization constants
ALLOWED_TAGS = [
    'div', 'p', 'span', 'a', 'img', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'br', 'hr', 'strong', 'em', 'b', 'i', 'u', 's',
    'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'figure', 'figcaption', 'iframe', 'video', 'audio', 'source', 'track',
    'nav', 'section', 'article', 'aside', 'header', 'footer', 'main', 'address',
    'details', 'summary'
]
ALLOWED_ATTRIBUTES = {
    '*': ['class', 'id', 'style', 'title', 'data-*'], # Allow data-* for custom attributes
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'loading'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen', 'sandbox'], # Added sandbox
    'video': ['src', 'controls', 'width', 'height', 'autoplay', 'muted', 'loop', 'poster'],
    'audio': ['src', 'controls', 'autoplay', 'muted', 'loop'],
    'source': ['src', 'type'],
    'track': ['src', 'kind', 'srclang', 'label', 'default'],
    'table': ['border', 'cellspacing', 'cellpadding', 'width', 'summary'],
    'th': ['colspan', 'rowspan', 'scope', 'abbr'],
    'td': ['colspan', 'rowspan', 'headers'],
}
# For CSS, bleach doesn't directly parse/validate CSS properties within <style> tags in the same way as HTML.
# The primary concern for CSS within <style> tags is ensuring it doesn't break out of the tag.
# If allowing 'style' attributes on elements, these are the CSS properties bleach will allow.
ALLOWED_STYLES = [
    'color', 'background-color', 'font-family', 'font-size', 'font-weight', 'font-style',
    'text-align', 'text-decoration', 'line-height',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'border', 'border-color', 'border-style', 'border-width', 'border-radius',
    'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
    'display', 'position', 'top', 'right', 'bottom', 'left', 'z-index',
    'float', 'clear', 'overflow', 'overflow-x', 'overflow-y',
    'list-style-type', 'list-style-position', 'list-style-image',
    'box-shadow', 'opacity', 'text-shadow', 'word-wrap', 'white-space',
    'vertical-align', 'grid-template-columns', 'grid-template-rows', 'grid-gap', 'gap' # Added some grid styles
]

# Allowed attributes for general sanitization. '*' means for all tags.
# Specific tags can have their own list.
SAFE_ATTRIBUTES = {
    '*': ['class', 'id', 'title', 'style'], # 'style' will be sanitized separately
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height', 'loading'],
    'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen'], # 'sandbox' can be restrictive
    'video': ['src', 'controls', 'width', 'height', 'autoplay', 'muted', 'loop', 'poster'],
    'audio': ['src', 'controls', 'autoplay', 'muted', 'loop'],
    'source': ['src', 'type'],
    'track': ['src', 'kind', 'srclang', 'label', 'default'],
    'table': ['border', 'cellspacing', 'cellpadding', 'width', 'summary'],
    'th': ['colspan', 'rowspan', 'scope', 'abbr'],
    'td': ['colspan', 'rowspan', 'headers'],
}
# ALLOWED_STYLES is already defined globally and will be used for inline styles.

MAX_RECURSION_DEPTH = 30 # Define max recursion depth

# Helper function to render GrapesJS components to HTML
def render_grapesjs_component(component_json, current_depth=0):
    if current_depth > MAX_RECURSION_DEPTH:
        # Log this event heavily if it occurs.
        # Consider app.logger.error() if app context is available, or basic print to stderr.
        print(f"ERROR: Max recursion depth ({MAX_RECURSION_DEPTH}) exceeded.", file=sys.stderr)
        return "<!-- Max recursion depth exceeded -->"

    if not isinstance(component_json, dict):
        return ""

    comp_type = component_json.get('type', '')
    
    if comp_type == 'textnode':
        raw_content = component_json.get('content', '')
        return bleach.clean(raw_content, tags=[], strip=True)

    tag_name = component_json.get('tagName')
    if not tag_name:
        if component_json.get('content'):
             return bleach.clean(component_json.get('content', ''), tags=[], strip=True)
        inner_html = ""
        if isinstance(component_json.get('components'), list):
            inner_html = "".join([render_grapesjs_component(child, current_depth + 1) for child in component_json.get('components', [])])
        return inner_html


    attributes = component_json.get('attributes', {})
    style_dict = component_json.get('style', {}) # GrapesJS style is a dict

    # Build attributes string
    attrs_list = []
    for attr_name, attr_value in attributes.items():
        # Sanitize attribute name (basic)
        sane_attr_name = bleach.clean(attr_name, tags=[], strip=True).lower()
        if not sane_attr_name or not sane_attr_name.isalnum(): # Allow only alphanumeric attr names for simplicity
            continue

        # Check against whitelist
        allowed_for_all = SAFE_ATTRIBUTES.get('*', [])
        allowed_for_tag = SAFE_ATTRIBUTES.get(tag_name.lower(), [])

        if sane_attr_name not in allowed_for_all and sane_attr_name not in allowed_for_tag:
            continue

        sane_attr_value = str(attr_value) # Ensure it's a string
        if sane_attr_name in ['href', 'src']:
            if sane_attr_value.strip().lower().startswith('javascript:'):
                sane_attr_value = '#'
            # Use bleach.clean for basic well-formedness, but allow common URL schemes
            # This won't validate if the URL is "good", just if it's a basic, safe-ish URL structure.
            # bleach.clean with strip=False and no tags/attributes might still allow some things.
            # A more robust URL check would be ideal, but for now, this is a slight improvement.
            # Ensure common schemes are allowed if necessary (http, https, mailto, relative paths).
            # The primary goal is to prevent javascript: URLs.
            temp_cleaned_val = bleach.clean(sane_attr_value, tags=[], strip=True) # Clean it first to normalize
            if temp_cleaned_val.lower().startswith('javascript:'): # Check after potential obfuscation removed by clean
                 sane_attr_value = '#'
            else:
                 # If not javascript:, allow relative paths and common schemes.
                 # For a stricter approach, one might parse with urllib.parse and check scheme.
                 # For now, rely on the initial javascript: check and that GrapesJS/user input is mostly well-behaved.
                 # Re-assign the original value if it's not a JS url, as bleach.clean(strip=False) is too permissive.
                 # The original code used strip=False. If we want to allow URLs as they are (after JS check):
                 pass # Keep sane_attr_value as is, after the JS check.
        else:
            sane_attr_value = bleach.clean(sane_attr_value, tags=[], strip=True)

        attrs_list.append(f'{sane_attr_name}="{bleach.clean(sane_attr_value, tags=[], strip=True)}"') # Final clean for safety in attribute value

    # Process and sanitize inline styles from the style_dict
    if isinstance(style_dict, dict) and style_dict:
        style_str_list = []
        for prop, value in style_dict.items():
            # Basic sanitization for property name and value
            sane_prop = bleach.clean(prop, tags=[], strip=True)
            sane_value = bleach.clean(str(value), tags=[], strip=True) # Ensure value is string
            if sane_prop in ALLOWED_STYLES: # Check against our global ALLOWED_STYLES list
                 style_str_list.append(f"{sane_prop}: {sane_value};")

        if style_str_list:
            # The style string itself doesn't need bleach.clean if individual props/values are fine
            # and we trust our ALLOWED_STYLES list.
            attrs_list.append(f'style="{" ".join(style_str_list)}"')


    attrs_string = " ".join(attrs_list)

    # Render inner content or components
    inner_html = ""
    if component_json.get('content') and not component_json.get('components'): # Simple content
        # If it's a void element, it shouldn't have content; GrapesJS might model this differently.
        # For simple text content, sanitize it.
        inner_html = bleach.clean(component_json.get('content', ''), tags=[], strip=True)
    elif isinstance(component_json.get('components'), list):
        inner_html = "".join([render_grapesjs_component(child, current_depth + 1) for child in component_json.get('components', [])])

    # Void elements (elements that cannot have content)
    void_elements = ["area", "base", "br", "col", "embed", "hr", "img", "input", "keygen", "link", "meta", "param", "source", "track", "wbr"]
    if tag_name.lower() in void_elements:
        return f"<{tag_name} {attrs_string}>"
    else:
        return f"<{tag_name} {attrs_string}>{inner_html}</{tag_name}>"


def create_app():
    app = Flask(__name__, static_folder=None) # No default static folder from backend
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_for_development') # IMPORTANT: Change this in production!
    # Construct SQLite path relative to the 'backend' directory where app.py is
    instance_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(instance_folder_path, 'unhyreable.db')}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'user_uploads')
    # Consider a more comprehensive list based on expected asset types
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'ico', 'webp', 'mp4', 'mov', 'pdf', 'txt', 'md'}

    # Ensure the instance folder exists (Flask usually creates app.instance_path on first access if not present)
    # os.makedirs(app.instance_path, exist_ok=True) # Generally not needed to manually create app.instance_path

    # Ensure UPLOAD_FOLDER exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # Helper function for checking allowed file extensions
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login_page' # Route function name for frontend login page
    # login_manager.login_message_category = "info" # Optional: for flashing messages

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # --- Helper Function for Email (Console Simulation) ---
    def send_email_notification(to_email, subject, body):
        print(f"--- EMAIL SIMULATION ---")
        print(f"To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print(f"--- END EMAIL SIMULATION ---")
        sys.stdout.flush()


    # --- Static File Serving Routes (from project root) ---
    # Assumes app.py is in 'backend' and HTML/JS files are in parent directory ('../')
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

    @app.route('/')
    def index():
        return send_from_directory(project_root, 'index.html')

    @app.route('/signup.html')
    def signup_page():
        return send_from_directory(project_root, 'signup.html')

    @app.route('/login.html')
    def login_page():
        return send_from_directory(project_root, 'login.html')

    @app.route('/dashboard.html')
    @login_required
    def dashboard_page():
        return send_from_directory(project_root, 'dashboard.html')

    @app.route('/auth.js')
    def auth_js_file():
        return send_from_directory(project_root, 'auth.js')

    @app.route('/dashboard.js')
    def dashboard_js_file():
        return send_from_directory(project_root, 'dashboard.js')

    @app.route('/editor.html')
    @login_required # Similar to dashboard, editor should be login protected
    def editor_page():
        return send_from_directory(project_root, 'editor.html')

    @app.route('/editor.js')
    def editor_js_file(): # Should this also be @login_required? If served via <script> tag, session cookie will be sent.
                           # For simplicity, JS files are often not login_required directly if they don't expose sensitive info by themselves.
                           # The APIs it calls are protected.
        return send_from_directory(project_root, 'editor.js')

    # --- Route to serve user-uploaded files ---
    @app.route('/user_uploads/<int:requested_user_id>/<path:filename>')
    def serve_user_asset(requested_user_id, filename):
        # UPLOAD_FOLDER is 'instance/user_uploads'
        # UserAsset.file_path is '<user_id>/<filename_on_disk>'
        # So, the requested_user_id in the URL *is* the user_id part of the path.
        # The filename in the URL is the filename_on_disk.

        upload_folder_base = app.config.get('UPLOAD_FOLDER')
        if not upload_folder_base:
            app.logger.error("UPLOAD_FOLDER not configured.")
            return abort(500)

        # The UserAsset.file_path already contains the user_id as the first part of its path.
        # So, we don't join requested_user_id again here if filename is the full UserAsset.file_path.
        # However, GrapesJS constructed the URL as /user_uploads/USER_ID/FILENAME where FILENAME is just the base name.
        # And UserAsset.file_path is 'USER_ID/FILENAME'.
        # So, the GrapesJS URL structure matches this function's parameters.
        # We need to construct the directory to search in, which is user_specific_upload_dir.

        user_specific_directory_name = str(requested_user_id)
        directory_to_serve_from = os.path.join(upload_folder_base, user_specific_directory_name)

        # Check if the directory exists. send_from_directory might do this, but explicit check is fine.
        if not os.path.isdir(directory_to_serve_from):
            app.logger.info(f"User asset directory not found: {directory_to_serve_from}")
            return abort(404)

        # app.logger.info(f"Attempting to serve: {filename} from directory: {directory_to_serve_from}")
        return send_from_directory(directory_to_serve_from, filename)

    # --- API Routes ---
    @app.route('/api/register', methods=['POST'])
    def register():
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({"message": "Email already registered"}), 400

        new_user = User(email=email)
        new_user.set_password(password)
        
        referrer_id_from_cookie = None
        referral_path = request.cookies.get('referral_funnel_path')
        if referral_path:
            funnel_link_obj = FunnelLink.query.filter_by(path_identifier=referral_path).first()
            if funnel_link_obj:
                referrer_id_from_cookie = funnel_link_obj.user_id
        
        if referrer_id_from_cookie:
            new_user.referred_by_user_id = referrer_id_from_cookie

        db.session.add(new_user)
        db.session.commit()

        if new_user.referred_by_user_id:
            referrer = User.query.get(new_user.referred_by_user_id)
            # Check referral_path to ensure it was through a link for this specific notification context
            if referrer and referral_path: 
                send_email_notification(
                    referrer.email,
                    "New User Signup Referral!",
                    f"Congratulations! User {new_user.email} has signed up via your funnel link: {referral_path}."
                )
        return jsonify({"message": "User registered successfully"}), 201

    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400
        email = data.get('email')
        password = data.get('password')
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user) # Flask-Login handles session
            return jsonify({"message": "Login successful", "email": user.email}), 200
        return jsonify({"message": "Invalid email or password"}), 401

    @app.route('/api/logout', methods=['POST'])
    @login_required
    def logout():
        logout_user()
        return jsonify({"message": "Logout successful"}), 200

    @app.route('/api/check_auth', methods=['GET'])
    def check_auth():
        if current_user.is_authenticated:
            favicon_url = None
            if current_user.favicon_path:
                # Construct full URL for the favicon.
                # The User.favicon_path is relative to the user's specific upload folder for favicons,
                # e.g., 'favicons/favicon.png'.
                # The serve_user_asset route is /user_uploads/<user_id>/<path:filename>
                # So, if favicon_path is 'favicons/favicon.png', the URL becomes
                # /user_uploads/<current_user.id>/favicons/favicon.png
                favicon_url = f"/user_uploads/{current_user.id}/{current_user.favicon_path}"

            return jsonify({
                "is_authenticated": True,
                "email": current_user.email,
                "user_id": current_user.id,
                "favicon_path": current_user.favicon_path, # Send the raw path
                "favicon_url": favicon_url # Send the constructed URL for easy use by frontend
            })
        return jsonify({"is_authenticated": False})

    @app.route('/api/user/favicon', methods=['POST'])
    @login_required
    def upload_favicon():
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "No selected file"}), 400

        # Define allowed extensions for favicons
        # Note: app.config['ALLOWED_EXTENSIONS'] is for general assets, this is specific for favicons
        allowed_favicon_extensions = {'png', 'ico', 'jpg', 'jpeg', 'svg'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''

        if not file_ext or file_ext not in allowed_favicon_extensions:
            return jsonify({"message": f"File type not allowed. Allowed: {', '.join(allowed_favicon_extensions)}"}), 400

        filename = secure_filename(file.filename) # Sanitize original filename first
        # Standardize favicon name, e.g., favicon.png, or favicon + original extension
        # Using a fixed name like "favicon.[ext]" simplifies retrieval and ensures one favicon per user.
        saved_favicon_filename = f"favicon.{file_ext}"

        favicons_dir_name = "favicons" # Subdirectory within user's upload folder
        user_specific_favicons_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id), favicons_dir_name)
        os.makedirs(user_specific_favicons_dir, exist_ok=True)

        save_path = os.path.join(user_specific_favicons_dir, saved_favicon_filename)
        file.save(save_path)

        # Store path relative to the user's ID folder (e.g., 'favicons/favicon.png')
        # This is because the serve_user_asset route takes user_id and then the rest of the path.
        relative_favicon_path = os.path.join(favicons_dir_name, saved_favicon_filename)
        # On Windows, os.path.join uses backslashes. Ensure URL paths are forward slashes.
        relative_favicon_path = relative_favicon_path.replace(os.sep, '/')


        current_user.favicon_path = relative_favicon_path
        db.session.commit()

        return jsonify({
            "message": "Favicon uploaded successfully",
            "favicon_path": current_user.favicon_path, # e.g., "favicons/favicon.png"
             "favicon_url": f"/user_uploads/{current_user.id}/{current_user.favicon_path}"
        }), 200


    @app.route('/api/funnels/create', methods=['POST'])
    @login_required
    def create_funnel():
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400
        path_identifier = data.get('path_identifier')

        if not path_identifier:
            return jsonify({"message": "Path identifier is required"}), 400
        
        if not path_identifier.isalnum() or ' ' in path_identifier:
             return jsonify({"message": "Path can only contain letters and numbers, no spaces."}), 400
        if len(path_identifier) < 3 or len(path_identifier) > 50:
            return jsonify({"message": "Path must be between 3 and 50 characters."}), 400

        if FunnelLink.query.filter_by(path_identifier=path_identifier).first():
            return jsonify({"message": "This path is already taken"}), 400

        new_link = FunnelLink(user_id=current_user.id, path_identifier=path_identifier)
        db.session.add(new_link)
        db.session.commit()
        return jsonify({"message": "Funnel link created successfully", "link_id": new_link.id, "path": new_link.path_identifier}), 201

    @app.route('/api/funnels/my_links', methods=['GET'])
    @login_required
    def get_my_funnels():
        links_data = []
        
        # Determine base_url more carefully for display
        # For local dev, request.url_root is fine. For production, you might configure this.
        display_base_url = request.host_url # e.g., http://127.0.0.1:5000/
        # If you want to always show 'unhyreable.com' for display purposes, regardless of actual host:
        # display_base_url = "http://unhyreable.com/"

        for link in current_user.funnel_links:
            leads_count = Lead.query.filter_by(funnel_link_id=link.id).count()
            links_data.append({
                "id": link.id,
                "path_identifier": link.path_identifier,
                "full_url": f"{display_base_url.rstrip('/')}/{link.path_identifier}",
                "click_count": link.click_count,
                "leads_generated_count": leads_count
            })
        return jsonify(links_data)

    @app.route('/api/analytics/my_referred_signups_count', methods=['GET'])
    @login_required
    def get_my_referred_signups_count():
        count = User.query.filter_by(referred_by_user_id=current_user.id).count()
        return jsonify({"referred_signups_count": count})
    
    @app.route('/api/submit_lead', methods=['POST'])
    def submit_lead():
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400
        
        name = data.get('name')
        email = data.get('email')
        if not name or not email: 
            return jsonify({"message": "Name and email are required for lead submission."}), 400

        new_lead = Lead(
            name=name,
            email=email,
            phone=data.get('phone'),
            investment_interest=data.get('investment_interest'),
            language=data.get('language')
        )

        referral_path = request.cookies.get('referral_funnel_path')
        if referral_path:
            funnel_link_obj = FunnelLink.query.filter_by(path_identifier=referral_path).first()
            if funnel_link_obj:
                new_lead.funnel_link_id = funnel_link_obj.id
                new_lead.attributed_user_id = funnel_link_obj.user_id
        
        db.session.add(new_lead)
        db.session.commit()

        send_email_notification(
            "admin@example.com", # Placeholder admin email
            "New Lead Submitted",
            f"A new lead has been submitted:\nName: {name}\nEmail: {email}\nPhone: {data.get('phone')}\nInterest: {data.get('investment_interest')}"
        )
        return jsonify({"message": "Lead submitted successfully"}), 201

    # --- User Asset Management API Routes ---

    @app.route('/api/userpage/assets/upload', methods=['POST'])
    @login_required
    def upload_user_asset():
        if 'file' not in request.files:
            return jsonify({"message": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"message": "No selected file"}), 400

        if file and allowed_file(file.filename): # allowed_file is now defined in create_app scope
            filename = secure_filename(file.filename)
            # User-specific directory within UPLOAD_FOLDER
            user_specific_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(current_user.id))
            os.makedirs(user_specific_upload_dir, exist_ok=True)

            save_path = os.path.join(user_specific_upload_dir, filename)

            # Check for filename conflict
            if os.path.exists(save_path):
                # Simple conflict resolution: append a short timestamp or counter
                # For this example, let's just inform the user. A more robust solution might be needed.
                # return jsonify({"message": "Filename conflict. Please rename or upload a different file."}), 409
                # Or, auto-rename:
                name_part, ext_part = os.path.splitext(filename)
                filename = f"{name_part}_{int(datetime.utcnow().timestamp())}{ext_part}"
                filename = secure_filename(filename) # re-secure after modification
                save_path = os.path.join(user_specific_upload_dir, filename)


            file.save(save_path)

            # Store path relative to UPLOAD_FOLDER for consistency and serving logic later
            relative_file_path = os.path.join(str(current_user.id), filename)

            new_asset = UserAsset(
                user_id=current_user.id,
                file_name=filename, # Secured and potentially conflict-resolved filename
                file_path=relative_file_path,
                content_type=file.content_type
            )
            db.session.add(new_asset)
            db.session.commit()

            return jsonify({
                "message": "File uploaded successfully",
                "asset_id": new_asset.id,
                "file_name": new_asset.file_name,
                "file_path": new_asset.file_path,
                "content_type": new_asset.content_type,
                "uploaded_at": new_asset.uploaded_at.isoformat()
            }), 201
        else:
            # Check if it was the allowed_file function that returned false
            if not allowed_file(file.filename):
                 return jsonify({"message": "File type not allowed"}), 400
            return jsonify({"message": "Upload failed for an unknown reason"}), 400


    @app.route('/api/userpage/assets', methods=['GET'])
    @login_required
    def get_user_assets():
        assets = UserAsset.query.filter_by(user_id=current_user.id).order_by(UserAsset.uploaded_at.desc()).all()
        assets_data = [{
            "id": asset.id,
            "file_name": asset.file_name,
            "file_path": asset.file_path,
            "content_type": asset.content_type,
            "uploaded_at": asset.uploaded_at.isoformat()
        } for asset in assets]
        return jsonify(assets_data), 200

    @app.route('/api/userpage/assets/<int:asset_id>', methods=['DELETE'])
    @login_required
    def delete_user_asset(asset_id):
        asset = UserAsset.query.get(asset_id)
        if not asset:
            return jsonify({"message": "Asset not found"}), 404

        if asset.user_id != current_user.id: # Authorization check
            return jsonify({"message": "Forbidden: You do not own this asset"}), 403

        try:
            # Construct full path from UPLOAD_FOLDER and the relative file_path
            full_asset_path = os.path.join(app.config['UPLOAD_FOLDER'], asset.file_path)

            if os.path.exists(full_asset_path):
                 os.remove(full_asset_path)
            else:
                # Log this: DB record exists but file doesn't. Might not be an error for the user.
                print(f"Warning: File not found for deletion, but deleting DB record: {full_asset_path}", file=sys.stderr)

        except OSError as e:
            # Log error during file deletion, but proceed to delete DB record.
            # Depending on policy, this might be a hard fail (return 500).
            print(f"Error deleting physical file {full_asset_path}: {e}", file=sys.stderr)
            # For this implementation, we'll proceed to delete the DB record even if file deletion fails.
            # Consider returning an error if physical file deletion is critical:
            # return jsonify({"message": f"Error deleting physical file: {e}. Database record not deleted."}), 500


        db.session.delete(asset)
        db.session.commit()

        return jsonify({"message": "Asset deleted successfully"}), 200

    # --- User Page Content API Routes ---

    @app.route('/api/userpage/content/save', methods=['POST'])
    @login_required
    def save_user_page_content():
        data = request.get_json()
        if not data:
            return jsonify({"message": "No input data provided"}), 400

        funnel_link_id = data.get('funnel_link_id')
        page_data_from_request = data.get('page_data') # Expected to be JSON (list/dict)
        css_content = data.get('css_content')

        if funnel_link_id is None:
            return jsonify({"message": "funnel_link_id is required"}), 400

        # Validate page_data structure (must be list or dict for db.JSON)
        # Allow null/None to clear the page_data, or an empty list/dict
        if page_data_from_request is not None and not isinstance(page_data_from_request, (list, dict)):
            return jsonify({"message": "Invalid format for page_data. Expected a list or object (or null)."}), 400

        # If page_data_from_request is None, we can store it as such if nullable, or use default.
        # Our model has default=[] and nullable=False. So client should send at least [] or {}.
        # For now, let's enforce that client must send a valid structure if key is present.
        # If client wants to "clear", they should send page_data: [] or page_data: {}
        if 'page_data' in data and not isinstance(page_data_from_request, (list, dict)): # Stricter: if key 'page_data' is there, it must be list/dict
             return jsonify({"message": "Invalid format for page_data. Expected a list or object if key is present."}), 400


        funnel_link = FunnelLink.query.get(funnel_link_id)
        if not funnel_link:
            return jsonify({"message": "FunnelLink not found"}), 404

        if funnel_link.user_id != current_user.id:
            return jsonify({"message": "Forbidden: You do not own this FunnelLink"}), 403

        user_page = funnel_link.user_page # Access via one-to-one relationship backref

        if not user_page:
            user_page = UserPage(funnel_link_id=funnel_link.id)
            # If UserPage is new and funnel_link.user_page is how it's primarily accessed,
            # ensure the relationship is correctly established if not done automatically by backref.
            # For SQLAlchemy, assigning to the parent's collection (or scalar for one-to-one)
            # and adding the new object to the session usually handles FKs correctly.
            # Here, UserPage has funnel_link_id, so that's the primary link.
            # The relationship on FunnelLink (user_page) should populate from this.
            # Explicitly setting funnel_link.user_page = user_page might be needed if the backref isn't immediate.
            # However, UserPage model has funnel_link_id, which is the FK.
            # And FunnelLink model defines `user_page = db.relationship('UserPage', backref='funnel_link', ...)`
            # So, creating UserPage with funnel_link_id and adding to session should be sufficient.
            # For clarity, one might also do: funnel_link.user_page = user_page
            # db.session.add(user_page)

        user_page.page_data = page_data_from_request if page_data_from_request is not None else [] # Ensure non-null for db
        user_page.css_content = css_content
        user_page.last_updated_at = datetime.utcnow()

        # If user_page was new, it needs to be added to the session.
        # If it was existing, it's already persistent and changes will be picked up.
        db.session.add(user_page) # Safe to call add on existing managed objects too
        db.session.commit()

        return jsonify({"message": "Page content saved successfully", "last_updated_at": user_page.last_updated_at.isoformat()}), 200

    @app.route('/api/userpage/content/load', methods=['GET'])
    @login_required
    def load_user_page_content():
        funnel_link_id = request.args.get('funnel_link_id', type=int)
        if funnel_link_id is None:
            return jsonify({"message": "funnel_link_id query parameter is required"}), 400

        funnel_link = FunnelLink.query.get(funnel_link_id)
        if not funnel_link:
            return jsonify({"message": "FunnelLink not found"}), 404

        if funnel_link.user_id != current_user.id:
            return jsonify({"message": "Forbidden: You do not own this FunnelLink"}), 403

        user_page = funnel_link.user_page

        if user_page:
            # page_data is already a Python list/dict due to db.JSON type
            return jsonify({
                "funnel_link_id": funnel_link.id,
                "page_data": user_page.page_data, # Should be a list/dict
                "css_content": user_page.css_content,
                "last_updated_at": user_page.last_updated_at.isoformat() if user_page.last_updated_at else None
            }), 200
        else:
            # Default response for a page without content, matches model default for page_data
            return jsonify({
                "funnel_link_id": funnel_link.id,
                "page_data": [], # Return empty list as per model default
                "css_content": "",
                "last_updated_at": None
            }), 200

    # --- Funnel Link Redirection Route ---
    @app.route('/<path:funnel_path>') # Use <path:> to capture arbitrary strings including those with non-alphanumeric chars if needed, though our creation logic is stricter.
    def funnel_redirect(funnel_path):
        link = FunnelLink.query.filter_by(path_identifier=funnel_path).first()

        if not link:
            abort(404)

        link.click_count += 1
        db.session.commit()

        user_page = link.user_page
        page_owner = link.user # User object who owns the funnel link (and thus the page)

        favicon_url = None
        if page_owner and page_owner.favicon_path:
            favicon_url = f"/user_uploads/{page_owner.id}/{page_owner.favicon_path}"


        user_page = link.user_page
        page_owner = link.user

        favicon_url = None
        if page_owner and page_owner.favicon_path:
            favicon_url = f"/user_uploads/{page_owner.id}/{page_owner.favicon_path}"

        if user_page and isinstance(user_page.page_data, list) and user_page.page_data:
            rendered_html_list = [render_grapesjs_component(comp, 0) for comp in user_page.page_data] # Initial depth 0
            final_html_content = "".join(rendered_html_list)

            # SECURITY NOTE: user_page.css_content is user-provided CSS.
            # While it's rendered within <style> tags, and modern browsers are good at isolating,
            # it's still a vector for certain types of attacks if not sanitized (e.g., @import, expression()).
            # Full CSS sanitization is complex. For now, we trust it or accept the risk.
            # A future step could involve a dedicated CSS sanitizer.
            css_to_render = user_page.css_content if user_page.css_content else ""
            
            response_content = render_template(
                'custom_page_render.html',
                html_content=final_html_content,
                css_content=css_to_render,
                favicon_url=favicon_url
            )
        else:
            response_content = render_template('page_not_customized.html', favicon_url=favicon_url)

        response = make_response(response_content)
        response.set_cookie(
            'referral_funnel_path',
            funnel_path,
            max_age=timedelta(days=7).total_seconds(),
            httponly=True,
            samesite='Lax'
        )
        return response

    # --- CLI command to initialize DB ---
    @app.cli.command('init-db')
    def init_db_command():
        """Initializes the database and creates tables."""
        from .models import User, FunnelLink, Lead, UserPage, UserAsset # Explicit import for CLI context
        # No need to check/create instance_folder here for db.create_all(),
        # as SQLAlchemy uses the app's configured URI which includes the instance path.
        with app.app_context(): 
            db.create_all() # This will now use the db instance that knows about all models in models.py
        print('Initialized the database and created tables from models.py: User, FunnelLink, Lead, UserPage, UserAsset.')

    return app

# This is for direct execution `python app.py` (less common for Flask apps now)
# For development, `flask run` is preferred after setting FLASK_APP=app:create_app (or just FLASK_APP=app.py if app is created at global scope)
# To use `create_app` factory pattern with `flask run`, set FLASK_APP=app:create_app
# Example: export FLASK_APP=app:create_app then flask run

# If you want to be able to run `python app.py` directly:
# if __name__ == '__main__':
#     app = create_app()
#     app.run(debug=True) # Set debug=False in production
