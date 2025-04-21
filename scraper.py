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

                # Extract the price
                price_text = article.find('p', class_='price_color').text.strip()
                price_text = price_text.replace('£', '').replace('Â', '').replace(',', '')
                price = float(price_text)

                # Extract relative URL to product detail page
                detail_href = article.h3.a['href']
                detail_url = self.base_url.rsplit('/', 1)[0] + '/' + detail_href

                # Fetch product detail page
                detail_response = requests.get(detail_url)
                detail_soup = BeautifulSoup(detail_response.text, 'html.parser')

                # Extract availability from product table
                availability_text = detail_soup.find('table', class_='table table-striped').find(string=re.compile("In stock"))
                stock_match = re.search(r'\((\d+)\s+available\)', availability_text)
                current_stock = int(stock_match.group(1)) if stock_match else 0

                items.append({
                    'name': name,
                    'category': "Books",
                    'current_stock': current_stock,
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
