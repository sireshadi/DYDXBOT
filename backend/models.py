from .database import db # Changed to relative import
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False) # Increased length
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    favicon_path = db.Column(db.String(255), nullable=True) # Path relative to user_uploads/<user_id>/ e.g. favicons/favicon.ico
    referred_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Relationship: Users referred by this user
    referrals = db.relationship('User', foreign_keys=[referred_by_user_id], backref=db.backref('referrer', remote_side=[id]), lazy='dynamic')

    # Flask-Login expects get_id to return a string
    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

class FunnelLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    path_identifier = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref=db.backref('funnel_links', lazy=True))
    # The UserPage associated with this FunnelLink
    user_page = db.relationship('UserPage', backref='funnel_link', uselist=False, lazy=True, cascade="all, delete-orphan")


    def __repr__(self):
        return f'<FunnelLink {self.path_identifier}>'

class UserPage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    funnel_link_id = db.Column(db.Integer, db.ForeignKey('funnel_link.id'), unique=True, nullable=False)
    page_data = db.Column(db.JSON, nullable=False, default=lambda: []) # Changed to JSON, non-nullable, with default
    css_content = db.Column(db.Text, nullable=True) # Keep as Text, can be empty
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship defined in FunnelLink model via backref 'user_page'

    def __repr__(self):
        return f'<UserPage for FunnelLink {self.funnel_link_id}>'

class UserAsset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False) # Relative path to stored asset
    content_type = db.Column(db.String(120), nullable=True) # E.g., 'image/jpeg', 'application/pdf'
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('assets', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<UserAsset {self.file_name} by User {self.user_id}>'

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=True) # Increased length for phone
    investment_interest = db.Column(db.String(200), nullable=True)
    language = db.Column(db.String(50), nullable=True) # From the form, String(50) is fine
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Attribution fields
    funnel_link_id = db.Column(db.Integer, db.ForeignKey('funnel_link.id'), nullable=True)
    attributed_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Owner of the funnel link

    # Relationships (optional but good practice)
    funnel_link = db.relationship('FunnelLink', backref=db.backref('leads', lazy='dynamic'))
    attributed_user = db.relationship('User', backref=db.backref('attributed_leads', lazy='dynamic'))

    def __repr__(self):
        return f'<Lead {self.email}>'
