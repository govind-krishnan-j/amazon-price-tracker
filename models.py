from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    otp = db.Column(db.String(6), nullable=True)  
    alert_sent = db.Column(db.Boolean, default=False)            
    is_verified = db.Column(db.Boolean, default=False)

    # One user can have many products
    products = db.relationship("Product", backref="owner", lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(2000), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    target_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=True)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    last_checked = db.Column(db.DateTime, nullable=True)
    price_history = db.relationship("PriceHistory", backref="product", lazy=True)

    # Link to the user who added this product
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __repr__(self):
        return f"<Product {self.title}>"

class PriceHistory(db.Model):
    __tablename__ = "price_history"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    price = db.Column(db.Float, nullable=False)
    checked_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PriceHistory {self.product_id} - {self.price}>"