from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User, Product,PriceHistory
from scraper import get_product_details
from scheduler import start_scheduler
import os
from dotenv import load_dotenv
from predictor import predict_price_trend
from flask_mail import Mail, Message
import random
import threading


load_dotenv()

# --- App setup ---
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "devkey123")
database_url = os.getenv("DATABASE_URL", "sqlite:///tracker.db")

if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

mail = Mail(app)

# --- Extensions setup ---
db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- Routes ---

@app.route("/")
def index():
    return render_template("index.html")

def send_otp_email(username, email, otp):
    try:
        with app.app_context():
            msg = Message(
                subject="Verify your Price Tracker account",
                sender=os.getenv("MAIL_USERNAME"),
                recipients=[email]
            )
            msg.body = f"""
Hi {username},

Welcome to Price Tracker!

Your verification OTP is: {otp}

Enter this on the verification page to activate your account.

- Price Tracker Team
            """
            mail.send(msg)
            print("OTP email sent!")
    except Exception as e:
        print(f"Mail error: {e}")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered!", "danger")
            return redirect(url_for("register"))

        otp = str(random.randint(100000, 999999))
        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        new_user = User(
            username=username,
            email=email,
            password=hashed_pw,
            otp=otp,
            is_verified=False
        )
        db.session.add(new_user)
        db.session.commit()

        # Send email in background — don't block the request
        thread = threading.Thread(
            target=send_otp_email,
            args=[username, email, otp]
        )
        thread.daemon = True
        thread.start()

        flash("OTP sent to your email!", "success")
        return redirect(url_for("verify_otp", email=email))

    return render_template("register.html")

@app.route("/verify/<email>", methods=["GET", "POST"])
def verify_otp(email):
    user = User.query.filter_by(email=email).first_or_404()

    if request.method == "POST":
        entered_otp = request.form.get("otp")

        if entered_otp == user.otp:
            user.is_verified = True
            user.otp = None
            db.session.commit()
            flash("Email verified! Please login.", "success")
            return redirect(url_for("login"))
        else:
            flash("Invalid OTP! Please try again.", "danger")

    return render_template("verify_otp.html", email=email)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            if not user.is_verified:
                flash("Please verify your email first!", "danger")
                return redirect(url_for("verify_otp", email=email))
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password!", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    products = Product.query.filter_by(user_id=current_user.id).all()

    # Get prediction for each product
    predictions = {}
    for product in products:
        history = PriceHistory.query.filter_by(product_id=product.id)\
            .order_by(PriceHistory.checked_at.asc()).all()
        prices = [h.price for h in history]
        predictions[product.id] = predict_price_trend(prices)

    return render_template("dashboard.html", products=products, predictions=predictions)


@app.route("/add_product", methods=["POST"])
@login_required
def add_product():
    url = request.form.get("url")
    target_price = float(request.form.get("target_price"))

    # Check if user already tracking this product
    existing = Product.query.filter_by(
        url=url,
        user_id=current_user.id
    ).first()

    if existing:
        flash("You are already tracking this product!", "danger")
        return redirect(url_for("dashboard"))

    result = get_product_details(url)
    if not result:
        flash("Could not fetch product — please try again!", "danger")
        return redirect(url_for("dashboard"))

    new_product = Product(
        url=url,
        title=result["title"],
        current_price=result["price"],
        target_price=target_price,
        user_id=current_user.id
    )
    db.session.add(new_product)
    db.session.commit()

    flash(f"'{result['title']}' added successfully!", "success")
    return redirect(url_for("dashboard"))

@app.route("/delete_product/<int:product_id>")
@login_required
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for("dashboard"))

    PriceHistory.query.filter_by(product_id=product_id).delete()
    
    db.session.delete(product)
    db.session.commit()
    flash("Product removed!", "success")
    return redirect(url_for("dashboard"))

@app.route("/product/<int:product_id>/history")
@login_required
def product_history(product_id):
    product = Product.query.get_or_404(product_id)

    if product.user_id != current_user.id:
        flash("Unauthorized!", "danger")
        return redirect(url_for("dashboard"))

    history = PriceHistory.query.filter_by(product_id=product_id)\
        .order_by(PriceHistory.checked_at.asc()).all()

    labels = [h.checked_at.strftime('%d %b %H:%M') for h in history]
    prices = [h.price for h in history]

    return render_template(
        "history.html",
        product=product,
        labels=labels,
        prices=prices
    )

@app.route("/run-price-check/<token>")
def run_price_check(token):
    if token != os.getenv("CRON_TOKEN"):
        return "Unauthorized", 401

    from threading import Thread
    def run_check():
        with app.app_context():
            from models import Product, PriceHistory
            from scraper import get_product_details, send_email_alert
            from datetime import datetime
            import time

            products = Product.query.all()
            for product in products:
                result = get_product_details(product.url)
                if result:
                    product.current_price = result["price"]
                    product.last_checked = datetime.utcnow()

                    history_entry = PriceHistory(
                        product_id=product.id,
                        price=result["price"]
                    )
                    db.session.add(history_entry)

                    # Send alert only once
                    if result["price"] <= product.target_price and not product.alert_sent:
                        send_email_alert(
                            mail,
                            result["title"],
                            result["price"],
                            product.owner.email
                        )
                        product.alert_sent = True

                    # Reset if price goes back up
                    if result["price"] > product.target_price:
                        product.alert_sent = False

                    db.session.commit()
                time.sleep(5)

    thread = Thread(target=run_check)
    thread.daemon = True
    thread.start()

    return "Price check started!", 200

# --- Create database tables ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        print("Database created!")

    scheduler = start_scheduler(app, db, Product, PriceHistory, mail)

    app.run(debug=True, use_reloader=False)