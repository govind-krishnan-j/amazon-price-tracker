import sys
import os
sys.path.insert(0, '/home/Govind707/amazon-price-tracker')
sys.path.insert(0, '/home/Govind707/amazon-price-tracker/.venv/lib/python3.13/site-packages')

from dotenv import load_dotenv
load_dotenv('/home/Govind707/amazon-price-tracker/.env')

from app import app, mail
from models import db, Product, PriceHistory
from scraper import get_product_details, send_email_alert
from datetime import datetime
import time

with app.app_context():
    products = Product.query.all()
    print(f"Checking {len(products)} products...")

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
            db.session.commit()

            print(f"Price: ₹{result['price']} | Target: ₹{product.target_price}")

            if result["price"] <= product.target_price:
                send_email_alert(
                    mail,
                    result["title"],
                    result["price"],
                    product.owner.email
                )
                print(f"Alert sent!")
        else:
            print(f"Could not fetch: {product.title[:30]}")

        time.sleep(5)

    print("Done checking all products!")