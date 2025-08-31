import sqlite3
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db():
    # Create tables if they don't exist
    db.create_all()

def get_db_connection():
    conn = sqlite3.connect('unhyreable.db')
    conn.row_factory = sqlite3.Row
    return conn
