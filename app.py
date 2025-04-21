from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import StockItem, Forecast, InventoryItem
from scraper import WebScraper
from ml_model import ForecastModel
from utils import match_items, forecast_reorder
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import pandas as pd
import os
from db import db

# Flask app initialization
app = Flask(__name__)
app.config.from_object(Config)
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB and ML model
with app.app_context():
    db.init_app(app)
    db.create_all()

scraper = WebScraper()
forecaster = ForecastModel()

# -------------------- ROUTES --------------------

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    items = StockItem.query.order_by(StockItem.name, StockItem.date_scraped).all()
    grouped_items = {}
    for item in items:
        grouped_items.setdefault(item.name, {})[item.date_scraped.strftime('%Y-%m-%d')] = item.current_stock
    all_dates = sorted({item.date_scraped.strftime('%Y-%m-%d') for item in items})
    return render_template('dashboard.html', grouped_items=grouped_items, all_dates=all_dates)

@app.route('/update-stock', methods=['POST'])
def update_stock():
    custom_url = request.form.get('url')
    if not custom_url:
        flash('URL not provided')
        return redirect(url_for('dashboard'))
    try:
        scraper.update_database(url=custom_url)
    except Exception as e:
        flash(f'URL not valid or error fetching data: {str(e)}')
    return redirect(url_for('dashboard'))

@app.route('/upload', methods=['POST'])
def upload_data():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected')
        return redirect(request.url)

    if file.filename.endswith('.csv'):
        path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
        file.save(path)
        try:
            df = pd.read_csv(path)
            for _, row in df.iterrows():
                date_scraped = datetime.strptime(row['date_scraped'], '%m/%d/%Y')
                existing = StockItem.query.filter_by(name=row['name'], date_scraped=date_scraped).first()
                if existing:
                    existing.current_stock, existing.price = row['current_stock'], row['price']
                else:
                    db.session.add(StockItem(
                        name=row['name'], category=row['category'], current_stock=row['current_stock'],
                        price=row['price'], date_scraped=date_scraped))
            db.session.commit()
            flash('CSV data imported into market inventory.')
        except Exception as e:
            flash(f'Error processing CSV: {str(e)}')
        finally:
            os.remove(path)
        return redirect(url_for('dashboard'))
    flash('Invalid file type')
    return redirect(url_for('manage_inventory'))

@app.route('/forecast/<int:stock_id>')
def stock_forecast(stock_id):
    item = StockItem.query.get_or_404(stock_id)
    inventory_item = InventoryItem.query.filter_by(name=item.name).first()
    if not inventory_item:
        flash(f'No matching inventory item for {item.name}')
        return redirect(url_for('forecast'))
    forecast_value = forecaster.predict(item.id)
    if forecast_value is not None:
        db.session.add(Forecast(stock_id=item.id, predicted_demand=forecast_value, forecast_date=datetime.now(timezone.utc)))
        db.session.commit()
        flash(f'Forecast for {item.name}: {forecast_value}')
    else:
        flash(f'Forecast failed for {item.name}')
    return redirect(url_for('forecast'))

@app.route('/clear-dashboard', methods=['POST'])
def clear_dashboard():
    try:
        StockItem.query.delete()
        Forecast.query.delete()
        db.session.commit()
        flash('Dashboard cleared successfully')
    except Exception as e:
        flash(f'Error clearing dashboard: {str(e)}')
    return redirect(url_for('dashboard'))

@app.route('/reorder', methods=['GET', 'POST'])
def reorder():
    if request.method == 'POST':
        try:
            market_items = StockItem.query.all()
            inventory_items = InventoryItem.query.all()
            most_recent_market = {}
            for item in market_items:
                if item.name not in most_recent_market or item.date_scraped > most_recent_market[item.name].date_scraped:
                    most_recent_market[item.name] = item
            reorder_results = []
            for market_item in most_recent_market.values():
                inventory_item = next((i for i in inventory_items if i.name == market_item.name), None)
                if inventory_item:
                    restock_amount, restock_by, predicted_demand = forecaster.predict(market_item.id)
                    reorder_results.append({
                        'item_name': market_item.name,
                        'warehouse_stock': inventory_item.current_stock,
                        'market_stock': market_item.current_stock,
                        'restock_amount': restock_amount,
                        'restock_by': restock_by,
                        'predicted_demand': predicted_demand
                    })
            matched, mismatched = match_items(inventory_items, market_items)
            reorders = forecast_reorder(matched)
            graph_data = [{'Item': r['name'], 'Amount': r['amount_to_reorder']} for r in reorders]
            return render_template('reorder.html', reorder_results=reorder_results, mismatched_items=mismatched, graph_data=graph_data)
        except Exception as e:
            flash(f'Reorder error: {str(e)}')
            return redirect(url_for('reorder'))
    return render_template('reorder.html', reorder_results=None)

@app.route('/clear-reorder-forecasts', methods=['POST'])
def clear_reorder_forecasts():
    try:
        Forecast.query.delete()
        db.session.commit()
        flash('Reorder forecasts cleared.')
    except Exception as e:
        flash(f'Error clearing reorder forecasts: {str(e)}')
    return redirect(url_for('reorder'))

@app.route('/compare-market-inventory', methods=['POST'])
def compare_market_inventory():
    market_items = StockItem.query.all()
    inventory_items = InventoryItem.query.all()
    reorder_results = []
    for market_item in market_items:
        inventory_item = next((i for i in inventory_items if i.name == market_item.name), None)
        if inventory_item:
            restock_amount, restock_by, predicted_demand = forecaster.predict(market_item.name, market_item.current_stock, inventory_item.current_stock)
            reorder_results.append({
                'item_name': market_item.name,
                'warehouse_stock': inventory_item.current_stock,
                'market_stock': market_item.current_stock,
                'restock_amount': restock_amount,
                'restock_by': restock_by,
                'predicted_demand': predicted_demand
            })
    return render_template('reorder.html', reorder_results=reorder_results)

@app.route('/clear-warehouse-inventory', methods=['POST'])
def clear_warehouse_inventory():
    try:
        InventoryItem.query.delete()
        db.session.commit()
        flash('Warehouse inventory cleared.')
    except Exception as e:
        flash(f'Error clearing warehouse inventory: {str(e)}')
    return redirect(url_for('manage_inventory'))

@app.route('/manage-inventory', methods=['GET', 'POST'])
def manage_inventory():
    items = InventoryItem.query.all()
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('No file selected')
            return redirect(request.url)
        if file.filename.endswith('.csv'):
            path = os.path.join(UPLOAD_FOLDER, secure_filename(file.filename))
            file.save(path)
            try:
                df = pd.read_csv(path)
                for _, row in df.iterrows():
                    existing = InventoryItem.query.filter_by(name=row['name']).first()
                    if existing:
                        existing.current_stock, existing.price = row['current_stock'], row['price']
                    else:
                        db.session.add(InventoryItem(
                            name=row['name'], category=row['category'],
                            current_stock=row['current_stock'],
                            price=row['price']))
                db.session.commit()
                flash('Inventory updated from CSV.')
            except Exception as e:
                flash(f'CSV processing error: {str(e)}')
            finally:
                os.remove(path)
            return redirect(url_for('manage_inventory'))
    return render_template('manage_inventory.html', items=items)

@app.route('/edit-stock/<int:stock_id>', methods=['GET', 'POST'])
def edit_stock(stock_id):
    item = InventoryItem.query.get_or_404(stock_id)
    if request.method == 'POST':
        item.name = request.form['name']
        item.category = request.form['category']
        item.current_stock = request.form['current_stock']
        item.price = request.form['price']
        db.session.commit()
        flash('Stock item updated')
        return redirect(url_for('manage_inventory'))
    return render_template('edit_stock.html', item=item)

@app.route('/delete-stock/<int:stock_id>')
def delete_stock(stock_id):
    item = InventoryItem.query.get_or_404(stock_id)
    db.session.delete(item)
    db.session.commit()
    flash('Stock item deleted')
    return redirect(url_for('manage_inventory'))

@app.route('/add-stock', methods=['GET', 'POST'])
def add_stock():
    if request.method == 'POST':
        db.session.add(InventoryItem(
            name=request.form['name'], category=request.form['category'],
            current_stock=int(request.form['current_stock']),
            price=float(request.form['price'])))
        db.session.commit()
        flash('Stock item added')
        return redirect(url_for('manage_inventory'))
    return render_template('add_stock.html')

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
