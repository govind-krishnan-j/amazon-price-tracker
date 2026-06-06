from apscheduler.schedulers.background import BackgroundScheduler
from scraper import get_product_details, send_email_alert
from datetime import datetime
import time

def check_all_prices(app, db, Product, PriceHistory, mail):
    with app.app_context():
        products = Product.query.all()
        print(f"\n[{datetime.now().strftime('%d %b %Y %H:%M')}] Checking {len(products)} products...")

        for product in products:
            print(f"Checking: {product.title[:50]}...")

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
                    owner = product.owner
                    send_email_alert(
                        mail,
                        result["title"],
                        result["price"],
                        owner.email
                    )
                    print(f"Email alert sent for {product.title[:30]}!")
            else:
                print(f"Could not fetch price for {product.title[:30]}")

            time.sleep(5)

        print("Done checking all products!\n")


def start_scheduler(app, db, Product, PriceHistory, mail):
    scheduler = BackgroundScheduler()

    scheduler.add_job(
        func=check_all_prices,
        trigger="interval",
        hours=6,
        args=[app, db, Product, PriceHistory, mail],
        id="price_check",
        name="Check all product prices",
        replace_existing=True
    )

    scheduler.start()
    print("Scheduler started — checking prices every 6 hours!")
    return scheduler