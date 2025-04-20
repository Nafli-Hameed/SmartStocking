from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from config import Config
from models import StockItem, Forecast, InventoryItem
from scraper import WebScraper
from ml_model import ForecastModel
import pandas as pd
import plotly.express as px
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from db import db
from utils import match_items, forecast_reorder


app = Flask(__name__)
app.config.from_object(Config)

with app.app_context():
    db.init_app(app)
    db.create_all()

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize components
scraper = WebScraper()
forecaster = ForecastModel()

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    items = StockItem.query.all()
    return render_template('dashboard.html', items=items)



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
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            df = pd.read_csv(file_path)
            for _, row in df.iterrows():
                name = row['name']
                existing = StockItem.query.filter_by(name=name).first()
                if existing:
                    existing.current_stock = row['current_stock']
                    existing.reorder_threshold = row['reorder_threshold']
                    existing.price = row['price']
                    if 'market_availability' in row:
                        existing.market_availability = row['market_availability']
                    else:
                        existing.market_availability = True
                else:
                    item = StockItem(
                        name=row['name'],
                        category=row['category'],
                        current_stock=row['current_stock'],
                        reorder_threshold=row['reorder_threshold'],
                        price=row['price'],
                        market_availability=row.get('market_availability', True)
                    )
                    db.session.add(item)
            db.session.commit()
            flash('CSV data imported successfully')
        except Exception as e:
            flash(f'Error processing CSV: {str(e)}')
        finally:
            # Clean up the uploaded file
            os.remove(file_path)
        
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid file type (must be .csv)')
        return redirect(url_for('dashboard'))

@app.route('/forecast/<int:stock_id>')
def stock_forecast(stock_id):
    item = StockItem.query.get_or_404(stock_id)
    forecast_value = forecaster.predict(item.id)
    
    if forecast_value is not None:
        new_forecast = Forecast(stock_id=item.id, predicted_demand=forecast_value, forecast_date=datetime.utcnow())
        db.session.add(new_forecast)
        db.session.commit()
        
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


@app.route('/forecast', methods=['GET'])
def forecast():
    with app.app_context():
        inventory_items = InventoryItem.query.all()
        market_items = StockItem.query.all()
        
        matched_items, mismatched_items = match_items(inventory_items, market_items)
        reorders = forecast_reorder(matched_items)
        
        # Check if reorders list is empty
        if not reorders:
            flash('No items need reordering at this time.')
        
        return render_template('forecast.html', reorders=reorders, mismatched_items=mismatched_items)


@app.route('/reorder', methods=['GET'])
def reorder():
    inventory_items = InventoryItem.query.all()
    market_items = StockItem.query.all()
    
    matched_items, mismatched_items = match_items(inventory_items, market_items)
    reorders = forecast_reorder(matched_items)
    
    return render_template('reorder.html', reorders=reorders)

@app.route('/set_threshold', methods=['POST'])
def set_threshold():
    try:
        threshold = int(request.form['threshold'])
        # Update all items
        for item in StockItem.query.all():
            item.reorder_threshold = threshold
        db.session.commit()
        flash('Global threshold updated successfully')
    except ValueError:
        flash('Invalid threshold value')
    return redirect(url_for('dashboard'))

@app.route('/manage-inventory', methods=['GET', 'POST'])
def manage_inventory():
    # Using InventoryItem (inventory_db)
    items = InventoryItem.query.all()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            try:
                df = pd.read_csv(file_path)
                for _, row in df.iterrows():
                    name = row['name']
                    existing = InventoryItem.query.filter_by(name=name).first()
                    if existing:
                        existing.current_stock = row['current_stock']
                    else:
                        item = InventoryItem(
                            name=row['name'],
                            category=row.get('category', ''),
                            current_stock=row['current_stock'],
                            reorder_threshold=row.get('reorder_threshold', 0),
                            price=row.get('price', 0.0)
                        )
                        db.session.add(item)
                db.session.commit()
                flash('CSV data imported successfully into inventory.')
            except Exception as e:
                flash(f'Error processing CSV: {str(e)}')
            finally:
                # Clean up the uploaded file
                os.remove(file_path)
        
            return redirect(url_for('manage_inventory'))
    
    return render_template('manage_inventory.html', items=items)


@app.route('/edit-stock/<int:stock_id>', methods=['GET', 'POST'])
def edit_stock(stock_id):
    item = InventoryItem.query.get_or_404(stock_id)
    
    if request.method == 'POST':
        item.name = request.form['name']
        item.category = request.form['category']
        item.current_stock = request.form['current_stock']
        item.reorder_threshold = request.form['reorder_threshold']
        item.price = request.form['price']
        
        db.session.commit()
        flash('Stock item updated successfully')
        return redirect(url_for('manage_inventory'))
    
    return render_template('edit_stock.html', item=item)

@app.route('/delete-stock/<int:stock_id>')
def delete_stock(stock_id):
    item = InventoryItem.query.get_or_404(stock_id)
    db.session.delete(item)
    db.session.commit()
    flash('Stock item deleted successfully')
    return redirect(url_for('manage_inventory'))

@app.route('/add-stock', methods=['GET', 'POST'])
def add_stock():
    if request.method == 'POST':
        item = InventoryItem(
            name=request.form['name'],
            category=request.form['category'],
            current_stock=int(request.form['current_stock']),
            reorder_threshold=int(request.form['reorder_threshold']),
            price=float(request.form['price'])
        )
        db.session.add(item)
        db.session.commit()
        flash('New stock item added successfully')
        return redirect(url_for('manage_inventory'))
    
    return render_template('add_stock.html')


@app.route('/update_threshold/<int:item_id>', methods=['POST'])
def update_threshold(item_id):
    item = StockItem.query.get_or_404(item_id)
    try:
        item.reorder_threshold = int(request.form['threshold'])
        db.session.commit()
        flash(f'Threshold updated for {item.name}')
    except ValueError:
        flash('Invalid threshold value')
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
