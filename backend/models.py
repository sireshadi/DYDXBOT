from database import db
from datetime import datetime
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    referred_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    # Flask-Login expects get_id to return a string
    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return f'<User {self.email}>'

class FunnelLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    path_identifier = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    click_count = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref=db.backref('funnel_links', lazy=True))

    def __repr__(self):
        return f'<FunnelLink {self.path_identifier}>'

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    investment_interest = db.Column(db.String(200), nullable=True)
    language = db.Column(db.String(50), nullable=True) # From the form
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Attribution fields
    funnel_link_id = db.Column(db.Integer, db.ForeignKey('funnel_link.id'), nullable=True)
    attributed_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) # Owner of the funnel link

    # Relationships (optional but good practice)
    funnel_link = db.relationship('FunnelLink', backref=db.backref('leads', lazy='dynamic'))
    attributed_user = db.relationship('User', backref=db.backref('attributed_leads', lazy='dynamic'))

    def __repr__(self):
        return f'<Lead {self.email}>'
