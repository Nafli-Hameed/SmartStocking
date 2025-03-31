import requests
from bs4 import BeautifulSoup
import re
from models import db, StockItem

class WebScraper:
    def __init__(self):
        self.base_url = None
        self.raw_data = None

    def fetch_data(self, url):
        try:
            self.base_url = url
            response = requests.get(self.base_url)
            response.raise_for_status()
            self.raw_data = response.text
            return True
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return False

    def parse_data(self):
        if not self.raw_data:
            return []

        soup = BeautifulSoup(self.raw_data, 'html.parser')
        items = []
        
        for article in soup.find_all('article', class_='product_pod'):
            try:
                # Extract the book name
                name = article.h3.a['title']

                # Extract the price, removing the £ sign and any encoding issues
                price_text = article.find('p', class_='price_color').text.strip()
                # Remove any non-numeric characters except for the decimal point
                price_text = price_text.replace('£', '').replace('Â', '').replace(',', '')  # Remove comma if present
                price = float(price_text)

                # Extract the availability. If it's in stock, assign a random stock level
                availability = article.find('p', class_='instock availability').text.strip()
                if "In stock" in availability:
                    current_stock = 20  # Fixed quantity of books
                else:
                    current_stock = 0

                items.append({
                    'name': name,
                    'category': "Books",  # All items are books
                    'current_stock': current_stock,
                    'reorder_threshold': 5,
                    'price': price
                })
            except Exception as e:
                print(f"Failed to extract item: {e}")

        return items

    def update_database(self, url):
        if not self.fetch_data(url):
            print("Failed to fetch data")
            return 0

        items = self.parse_data()
        if not items:
            print("No items parsed")
            return 0

        count = 0
        for item_data in items:
            print(f"Processing item: {item_data['name']}")
            
            existing_item = StockItem.query.filter_by(name=item_data['name']).first()

            if existing_item:
                print(f"Updating {item_data['name']}")
                existing_item.current_stock = item_data['current_stock']
                existing_item.price = item_data['price']
            else:
                print(f"Adding {item_data['name']}")
                new_item = StockItem(**item_data)
                db.session.add(new_item)

            count += 1

        try:
            db.session.commit()
            print("Database updated successfully")
        except Exception as e:
            db.session.rollback()
            print(f"Failed to commit updates: {e}")

        return count
