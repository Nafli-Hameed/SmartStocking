import requests
from bs4 import BeautifulSoup
from models import db, StockItem

class WebScraper:
    def __init__(self, base_url="https://example-inventory-source.com"):
        self.base_url = base_url
        
    def fetch_data(self):
        try:
            response = requests.get(self.base_url, timeout=10)
            response.raise_for_status()
            self.raw_data = response.text
            return True
        except Exception as e:
            print(f"Error fetching data: {str(e)}")
            return False

    def parse_data(self):
        soup = BeautifulSoup(self.raw_data, 'html.parser')
        items = []
        
        # Example parsing logic - adjust according to target site structure
        for item in soup.find_all('div', class_='stock-item'):
            name = item.find('h2').text.strip()
            category = item.find('span', class_='category').text.strip()
            stock = int(item.find('div', class_='stock-level').text)
            
            items.append({
                'name': name,
                'category': category,
                'current_stock': stock,
                'reorder_threshold': 20  # Default threshold
            })
        
        return items

    def update_database(self):
        if not self.raw_data:
            self.fetch_data()
            
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
