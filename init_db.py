import os
from app import app
from models import db

print("Starting database initialization...")

with app.app_context():
    try:
        db.create_all()
        print("✅ Database tables created successfully!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise e