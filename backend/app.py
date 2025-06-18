from flask import Flask, request, jsonify, redirect, url_for, make_response, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from database import db, init_db
from models import User, FunnelLink, Lead # Added Lead here
import click
import re # For path validation

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # Important: Change this in production!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///unhyreable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Or a conceptual frontend login route name

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    # Check for referral cookie and pass it to the frontend or use it server-side
    referral_funnel_path = request.cookies.get('referral_funnel_path')
    # For now, just serve index.html. Later, this might pass data to the template.
    # If index.html is in the root:
    return send_from_directory('../', 'index.html')
    # If index.html is in a static folder at the root:
    # return send_from_directory('../static', 'index.html')

# --- Static File Serving Routes ---
@app.route('/signup.html')
def signup_page():
    return send_from_directory('../', 'signup.html')

@app.route('/login.html')
def login_page():
    return send_from_directory('../', 'login.html')

@app.route('/dashboard.html')
@login_required
def dashboard_page():
    return send_from_directory('../', 'dashboard.html')

@app.route('/auth.js')
def auth_js_file():
    return send_from_directory('../', 'auth.js')

@app.route('/dashboard.js')
def dashboard_js_file():
    return send_from_directory('../', 'dashboard.js')

# --- Email Sending Utility ---
def send_email_notification(to_email, subject, body):
    """
    Sends an email. For now, prints to console.
    Replace with actual email sending logic (e.g., smtplib, SendGrid, etc.) in production.
    """
    import sys # Add sys import for flushing
    print(f"--- SENDING EMAIL ---")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"--- EMAIL END ---")
    sys.stdout.flush() # Explicitly flush stdout

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    # Keep handling direct referred_by_user_id from payload for now,
    # but prioritize cookie-based referral for funnel tracking.
    direct_referred_by_user_id = data.get('referred_by_user_id')


    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400

    hashed_password = generate_password_hash(password)

    referrer_id_from_cookie = None
    referral_funnel_path = request.cookies.get('referral_funnel_path')
    used_funnel_link = None

    if referral_funnel_path:
        funnel_link_obj = FunnelLink.query.filter_by(path_identifier=referral_funnel_path).first()
        if funnel_link_obj:
            referrer_id_from_cookie = funnel_link_obj.user_id
            used_funnel_link = funnel_link_obj # Store for notification

    new_user = User(email=email, password_hash=hashed_password)

    if referrer_id_from_cookie:
        new_user.referred_by_user_id = referrer_id_from_cookie
    elif direct_referred_by_user_id: # Fallback to payload if no cookie referral
        # Ensure this user exists if provided directly
        if User.query.get(direct_referred_by_user_id):
             new_user.referred_by_user_id = direct_referred_by_user_id
        else:
            # Optionally handle if direct_referred_by_user_id is invalid (e.g., log, ignore, or error)
            print(f"Warning: Invalid direct_referred_by_user_id '{direct_referred_by_user_id}' provided during registration for {email}.")


    db.session.add(new_user)
    db.session.commit()

    # Send notification if referred
    if new_user.referred_by_user_id:
        referrer = User.query.get(new_user.referred_by_user_id)
        if referrer and used_funnel_link: # Make sure we have a funnel link for the context
            subject = "New User Signup Referral!"
            body = f"Congratulations! User {new_user.email} has signed up via your funnel link: {used_funnel_link.path_identifier}."
            send_email_notification(referrer.email, subject, body)
        elif referrer: # Generic referral if no specific funnel link was involved (e.g. direct ID)
            subject = "New User Signup Referral!"
            body = f"Congratulations! User {new_user.email} has signed up and mentioned you as the referrer."
            send_email_notification(referrer.email, subject, body)


    return jsonify({'message': 'User registered successfully'}), 201

@app.route('/api/submit_lead', methods=['POST'])
def submit_lead():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    investment_interest = data.get('investment_interest')
    language = data.get('language') # Assuming 'language' comes from the form

    if not name or not email:
        return jsonify({'error': 'Name and email are required for lead submission.'}), 400

    funnel_id = None
    attr_user_id = None
    referral_funnel_path = request.cookies.get('referral_funnel_path')

    if referral_funnel_path:
        funnel_link = FunnelLink.query.filter_by(path_identifier=referral_funnel_path).first()
        if funnel_link:
            funnel_id = funnel_link.id
            attr_user_id = funnel_link.user_id
            # Optionally, you could increment funnel_link.click_count here as well,
            # or decide that only direct visits to the funnel link increment it.
            # For now, we assume visit to /<funnel_path> handles click_count.

    new_lead = Lead(
        name=name,
        email=email,
        phone=phone,
        investment_interest=investment_interest,
        language=language,
        funnel_link_id=funnel_id,
        attributed_user_id=attr_user_id
    )

    db.session.add(new_lead)
    db.session.commit()

    # Future: Notify admin about the new lead
    # send_email_notification(app.config['ADMIN_EMAIL'], "New Lead Submitted", f"Lead: {name}, {email}")

    return jsonify({'message': 'Lead submitted successfully'}), 201

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            "is_authenticated": True,
            "email": current_user.email,
            "user_id": current_user.id
        }), 200
    else:
        return jsonify({"is_authenticated": False}), 200 # Or 401, but 200 with False is fine for client check

@app.route('/api/funnels/my_links', methods=['GET'])
@login_required
def my_funnel_links():
    links = FunnelLink.query.filter_by(user_id=current_user.id).order_by(FunnelLink.created_at.desc()).all()
    results = []
    # Assuming the app is hosted at unhyreable.com for constructing full_url
    # In a real app, this domain should come from config or request headers.
    base_url = "http://unhyreable.com/" # Or request.host_url if served by same domain

    for link in links:
        # Count leads for this specific funnel link
        leads_count = Lead.query.filter_by(funnel_link_id=link.id).count()
        results.append({
            "id": link.id,
            "path_identifier": link.path_identifier,
            "full_url": f"{base_url}{link.path_identifier}",
            "click_count": link.click_count,
            "leads_generated_count": leads_count
        })
    return jsonify(results), 200

@app.route('/api/analytics/my_referred_signups_count', methods=['GET'])
@login_required
def my_referred_signups_count():
    count = User.query.filter_by(referred_by_user_id=current_user.id).count()
    return jsonify({"referred_signups_count": count}), 200


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password'}), 401

    login_user(user)
    return jsonify({'message': 'Login successful'}), 200

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@app.route('/api/funnels/create', methods=['POST'])
@login_required
def create_funnel():
    data = request.get_json()
    path_identifier = data.get('path_identifier')

    if not path_identifier:
        return jsonify({'error': 'Path identifier is required'}), 400

    # Validate path_identifier: only letters, numbers, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", path_identifier):
        return jsonify({'error': 'Invalid characters in path. Use letters, numbers, hyphens, or underscores.'}), 400

    if len(path_identifier) < 3 or len(path_identifier) > 50:
        return jsonify({'error': 'Path identifier must be between 3 and 50 characters.'}), 400


    existing_funnel = FunnelLink.query.filter_by(path_identifier=path_identifier).first()
    if existing_funnel:
        return jsonify({'error': 'This path identifier is already taken.'}), 400

    new_funnel = FunnelLink(
        user_id=current_user.id,
        path_identifier=path_identifier,
        click_count=0 # Initial click count
    )
    db.session.add(new_funnel)
    db.session.commit()

    return jsonify({'message': 'Funnel link created successfully', 'funnel_path': path_identifier}), 201

@app.route('/<funnel_path>')
def funnel_redirect(funnel_path):
    funnel = FunnelLink.query.filter_by(path_identifier=funnel_path).first()
    if funnel:
        funnel.click_count += 1
        db.session.commit()

        response = make_response(redirect(url_for('index')))
        # Set cookie for 30 days
        response.set_cookie('referral_funnel_path', funnel_path, max_age=30*24*60*60, httponly=True, samesite='Lax')
        return response
    else:
        # If you want to serve index.html for any non-funnel path, do this:
        # return send_from_directory('../', 'index.html')
        # Or, if it should strictly be a 404 for unknown funnels:
        abort(404)


@app.cli.command('init-db')
def init_db_command():
    """Initializes the database and creates tables."""
    with app.app_context():
        # This will create all tables defined in models.py
        db.create_all()
    print('Initialized the database and created tables (User, FunnelLink, Lead).')

if __name__ == '__main__':
    # Make sure the app context is available for operations like db.create_all()
    with app.app_context():
        # You might want to run init_db() here automatically for development,
        # or rely on the flask init-db command.
        # For this setup, we'll rely on the command.
        pass
    app.run(debug=True)
