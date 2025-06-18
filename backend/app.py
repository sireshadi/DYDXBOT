from flask import Flask, request, jsonify, redirect, url_for, send_from_directory, abort, make_response, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import os
import sys
from datetime import datetime, timedelta # Added timedelta for cookie expiry

# Database setup
db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    referred_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationship: Users referred by this user
    referrals = db.relationship('User', foreign_keys=[referred_by_user_id], backref=db.backref('referrer', remote_side=[id]), lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class FunnelLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    path_identifier = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref=db.backref('funnel_links', lazy='dynamic'))

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(50), nullable=True)
    investment_interest = db.Column(db.String(200), nullable=True)
    language = db.Column(db.String(10), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    funnel_link_id = db.Column(db.Integer, db.ForeignKey('funnel_link.id'), nullable=True)
    attributed_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Owner of the funnel link

    # Relationships
    funnel_link = db.relationship('FunnelLink', backref=db.backref('leads', lazy='dynamic'))
    attributed_user = db.relationship('User', backref=db.backref('attributed_leads', lazy='dynamic'))


def create_app():
    app = Flask(__name__, static_folder=None) # No default static folder from backend
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key_for_development') # IMPORTANT: Change this in production!
    # Construct SQLite path relative to the 'backend' directory where app.py is
    instance_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(instance_folder_path, 'unhyreable.db')}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Ensure the instance folder exists
    if not os.path.exists(instance_folder_path):
        os.makedirs(instance_folder_path)

    db.init_app(app)

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
            return jsonify({"is_authenticated": True, "email": current_user.email, "user_id": current_user.id})
        return jsonify({"is_authenticated": False})

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

    # --- Funnel Link Redirection Route ---
    @app.route('/<path:funnel_path>') # Use <path:> to capture arbitrary strings including those with non-alphanumeric chars if needed, though our creation logic is stricter.
    def funnel_redirect(funnel_path):
        link = FunnelLink.query.filter_by(path_identifier=funnel_path).first()
        if link:
            link.click_count += 1
            db.session.commit()
            
            response = make_response(redirect(url_for('index')))
            response.set_cookie('referral_funnel_path', funnel_path, max_age=timedelta(days=7).total_seconds(), httponly=True, samesite='Lax')
            return response
        else:
            # If not a funnel link, it might be another static file or a mistake
            # For a SPA, you might redirect to index.html. For this setup, 404 is clearer if no other route matches.
            abort(404) 

    # --- CLI command to initialize DB ---
    @app.cli.command('init-db')
    def init_db_command():
        """Initializes the database and creates tables."""
        # No need to check/create instance_folder here, Flask does it if using app_context for db ops.
        with app.app_context(): 
            db.create_all()
        print('Initialized the database and created tables: User, FunnelLink, Lead.')

    return app

# This is for direct execution `python app.py` (less common for Flask apps now)
# For development, `flask run` is preferred after setting FLASK_APP=app:create_app (or just FLASK_APP=app.py if app is created at global scope)
# To use `create_app` factory pattern with `flask run`, set FLASK_APP=app:create_app
# Example: export FLASK_APP=app:create_app then flask run

# If you want to be able to run `python app.py` directly:
# if __name__ == '__main__':
#     app = create_app()
#     app.run(debug=True) # Set debug=False in production
