from bs4 import BeautifulSoup
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def get_product_details(url):
    try:
        payload = {
            "x-api-key": os.getenv("SCRAPING_ANT_KEY"),
            "url": url,
            "browser": "false"
        }
        response = requests.get(
            "https://api.scrapingant.com/v2/general",
            params=payload,
            timeout=60
        )

        soup = BeautifulSoup(response.content, "html.parser")

        price = float(
            soup.find(class_="a-price-whole")
            .get_text()
            .replace("INR", "")
            .replace(",", "")
            .strip()
        )
        title = soup.find(id="productTitle").get_text().strip()

        return {"title": title, "price": price}

    except Exception as e:
        print(f"Scraping error: {e}")
        return None

def send_email_alert(mail, title, price, user_email):
    try:
        from flask_mail import Message
        msg = Message(
            subject="🔔 Price Drop Alert — Price Tracker",
            sender=os.getenv("MAIL_USERNAME"),
            recipients=[user_email]
        )
        msg.body = f"""
Hi there!

Great news — a product you're tracking has dropped below your target price!

Product: {title}
Current Price: ₹{price:,.0f}

Login to your Price Tracker dashboard to view more details.

Happy shopping!
        """
        mail.send(msg)
        print(f"Email alert sent to {user_email}!")
    except Exception as e:
        print(f"Email alert error: {e}")
