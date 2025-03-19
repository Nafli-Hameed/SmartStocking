import requests
from bs4 import BeautifulSoup
from models import db, StockItem
from flask import Flask

# Initialize Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'  # Change to your actual database
db.init_app(app)

class WebScraper:
    def __init__(self, base_url="https://books.toscrape.com/"):
        self.base_url = base_url

    def fetch_data(self, url):
        """Fetch HTML content from the given URL."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {str(e)}")
            return None

    def parse_data(self, html):
        """Extract book details from a page."""
        soup = BeautifulSoup(html, 'html.parser')
        items = []

        for item in soup.find_all('article', class_='product_pod'):
            name = item.find('h3').find('a')['title']
            stock_text = item.find('p', class_='instock availability').text.strip()
            stock = 1 if "In stock" in stock_text else 0  

            items.append({
                'name': name,
                'category': "Books",
                'current_stock': stock,
                'reorder_threshold': 5  
            })
        return items

    def get_all_pages(self):
        """Iterate through valid pages of the site."""
        all_items = []
        page_number = 1  

        while True:
            url = f"{self.base_url}catalogue/page-{page_number}.html" if page_number > 1 else self.base_url
            print(f"Scraping page {page_number}...")
            
            html = self.fetch_data(url)
            if not html:  
                break  

            parsed_items = self.parse_data(html)
            if not parsed_items:  
                break  

            all_items.extend(parsed_items)
            page_number += 1  

        return all_items

    def update_database(self):
        """Update the database with scraped inventory data."""
        with app.app_context():  # Ensure Flask app context is active
            items = self.get_all_pages()
            if not items:
                print("No data scraped, skipping update.")
                return 0

            existing_items = {item.name: item for item in StockItem.query.all()}  
            new_entries = []

            for item_data in items:
                if item_data['name'] in existing_items:
                    existing_items[item_data['name']].current_stock = item_data['current_stock']
                else:
                    new_entries.append(StockItem(**item_data))

            if new_entries:
                db.session.bulk_save_objects(new_entries)

            db.session.commit()
            print(f"Updated database with {len(items)} records.")
            return len(items)

# Usage
if __name__ == "__main__":
    scraper = WebScraper()
    scraper.update_database()
