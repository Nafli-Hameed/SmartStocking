import requests
from bs4 import BeautifulSoup
from models import db, StockItem

class WebScraper:
    def __init__(self, base_url="https://books.toscrape.com/"):
        self.base_url = base_url
        self.raw_data = None  

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
            stock = 1 if "In stock" in stock_text else 0  # Convert stock to binary (1 for in stock, 0 for out of stock)

            items.append({
                'name': name,
                'category': "Books",
                'current_stock': stock,
                'reorder_threshold': 5  # Example threshold
            })
        return items

    def get_all_pages(self):
        """Iterate through all pages of the site."""
        all_items = []
        page = 1
        next_page = self.base_url

        while next_page:
            print(f"Scraping page {page}...")
            html = self.fetch_data(next_page)
            if not html:
                break  

            all_items.extend(self.parse_data(html))

            # Check for next page link
            soup = BeautifulSoup(html, 'html.parser')
            next_button = soup.find('li', class_='next')
            if next_button:
                next_page = self.base_url + next_button.find('a')['href']
                page += 1
            else:
                next_page = None  # Stop loop when no next page

        return all_items

    def update_database(self):
        """Update the database with scraped inventory data."""
        items = self.get_all_pages()
        if not items:
            print("No data scraped, skipping update.")
            return 0
        
        # Bulk update logic
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
scraper = WebScraper()
scraper.update_database()
