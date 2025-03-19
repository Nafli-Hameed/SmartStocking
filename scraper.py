import requests
from bs4 import BeautifulSoup
from models import db, StockItem

class WebScraper:
    def __init__(self, base_url="https://books.toscrape.com/"):
        self.base_url = base_url
        self.raw_data = None  # Initialize raw_data here
        
    def fetch_data(self):
        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()
            self.raw_data = response.text
            return True
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            self.raw_data = None  # Explicitly set to None on failure
            return False

    def update_database(self):
        if not self.raw_data and not self.fetch_data():
            print("Failed to fetch data for update")
            return 0
       
        items = self.parse_data()
        for item_data in items:
            existing = StockItem.query.filter_by(name=item_data['name']).first()
            if existing:
                existing.current_stock = item_data['current_stock']
            else:
                new_item = StockItem(**item_data)
                db.session.add(new_item)
        
        db.session.commit()
        return len(items)
