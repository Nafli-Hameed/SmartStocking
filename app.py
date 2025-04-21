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
from datetime import datetime, timezone


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
    # Fetch all items from the StockItem table, ordered by name and date_scraped
    items = StockItem.query.order_by(StockItem.name, StockItem.date_scraped).all()

    # Initialize a dictionary to group items by name
    grouped_items = {}

    # Loop over items to group them by name and date
    for item in items:
        if item.name not in grouped_items:
            grouped_items[item.name] = {}
        # Store the stock for each date under the item's name
        grouped_items[item.name][item.date_scraped.strftime('%Y-%m-%d')] = item.current_stock

    # Get a list of all unique dates, sorted in ascending order
    all_dates = sorted(set(item.date_scraped.strftime('%Y-%m-%d') for item in items))

    # Debugging: Check the grouped items and dates
    print(f"Grouped Items: {grouped_items}")
    print(f"All Dates: {all_dates}")

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
                date_scraped = datetime.strptime(row['date_scraped'], '%m/%d/%Y')
                
                # Check if the item already exists
                existing = StockItem.query.filter_by(name=name, date_scraped=date_scraped).first()
                
                if existing:
                    existing.current_stock = row['current_stock']
                    existing.price = row['price']
                else:
                    item = StockItem(
                        name=row['name'],
                        category=row['category'],
                        current_stock=row['current_stock'],
                        price=row['price'],
                        date_scraped=date_scraped
                    )
                    db.session.add(item)
            
            db.session.commit()  # Ensure the commit happens

            # Debugging: Print the number of items in the database
            print(f"Number of items in database: {StockItem.query.count()}")
            print(f"Items in the database: {StockItem.query.all()}")

            flash('CSV data imported successfully into market inventory.')
        except Exception as e:
            flash(f'Error processing CSV: {str(e)}')
        finally:
            os.remove(file_path)
        
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid file type (must be .csv)')
        return redirect(url_for('manage_inventory'))




@app.route('/forecast/<int:stock_id>')
def stock_forecast(stock_id):
    item = StockItem.query.get_or_404(stock_id)  # Get stock item by ID

    # Check if the item exists in the inventory
    inventory_item = InventoryItem.query.filter_by(name=item.name).first()

    if not inventory_item:
        flash(f'No matching item found in the inventory for {item.name}. Forecast not generated.')
        return redirect(url_for('forecast'))

    forecast_value = forecaster.predict(item.id)

    if forecast_value is not None:
        # Save the forecast in the database
        new_forecast = Forecast(
            stock_id=item.id, 
            predicted_demand=forecast_value, 
            forecast_date=datetime.now(timezone.utc)
        )
        db.session.add(new_forecast)
        db.session.commit()  # Commit the changes to the database
        flash(f'Forecast for {item.name} updated: {forecast_value}')
    else:
        flash(f'No forecast could be generated for {item.name}.')

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


'''@app.route('/forecast', methods=['GET'])
def forecast():
    with app.app_context():
        # Fetch items from both inventory and market stock (StockItem and InventoryItem)
        inventory_items = InventoryItem.query.all()
        market_items = StockItem.query.all()
        forecasts = Forecast.query.all()

        # Match items between market and inventory based on name and availability
        matched_items, mismatched_items = match_items(inventory_items, market_items)
        print(f"Forecasts fetched: {forecasts}")  # Debugging log

        if not forecasts:
            flash('No forecasts available. Generate forecasts from the dashboard.')

        return render_template('forecast.html', forecasts=forecasts)
        # Log matched and mismatched items for debugging
        # print(f"Matched Items: {matched_items}")
        # print(f"Mismatched Items: {mismatched_items}")

        # Calculate reorders based on matching items
        reorders = forecast_reorder(matched_items)

        # If no items need to be reordered, show a message
        if not reorders:
            flash('No items need reordering at this time.')

        # Render forecast page with reorder information
        return render_template('forecast.html', reorders=reorders, mismatched_items=mismatched_items)'''

'''@app.route('/clear-forecasts', methods=['POST'])
def clear_forecasts():
    try:
        Forecast.query.delete()  # Deletes all records in the Forecast table
        db.session.commit()  # Commit the changes to the database
        flash('All forecasts have been cleared.')
    except Exception as e:
        flash(f'Error clearing forecasts: {str(e)}')

    return redirect(url_for('forecast'))'''


@app.route('/reorder', methods=['GET', 'POST'])
def reorder():
    if request.method == 'POST':
        try:
            market_items = StockItem.query.all()  # All items in the market (dashboard)
            inventory_items = InventoryItem.query.all()  # All items in the inventory

            reorder_results = []  # List to store reorder recommendations

             # Group market items by name and select the most recent one
            most_recent_market_items = {}
            for market_item in market_items:
                # If this item is already in the dictionary, check if the current date is more recent
                if market_item.name not in most_recent_market_items or market_item.date_scraped > most_recent_market_items[market_item.name].date_scraped:
                    most_recent_market_items[market_item.name] = market_item

            # Compare each unique market item (most recent) with the inventory and calculate restock needs
            for market_item in most_recent_market_items.values():
                # Find matching inventory item
                inventory_item = next((item for item in inventory_items if item.name == market_item.name), None)


                if inventory_item:
                    # Compare the stock
                    market_stock = market_item.current_stock
                    warehouse_stock = inventory_item.current_stock

                    # Call ML model to predict when to restock and by how much
                    restock_amount, restock_by, predicted_demand = forecaster.predict(market_item.id)

                    reorder_results.append({
                        'item_name': market_item.name,
                        'warehouse_stock': warehouse_stock,
                        'market_stock': market_stock,
                        'restock_amount': restock_amount,
                        'restock_by': restock_by,
                        'predicted_demand': predicted_demand
                    })
                else:
                    # If no inventory item is found for the market item, skip it
                    continue
            matched_items, mismatched_items = match_items(inventory_items, market_items)
            reorders = forecast_reorder(matched_items)    
            graph_data = [{'Item': r['name'], 'Amount': r['amount_to_reorder']} for r in reorders]
           
            # Display results on the reorder page
            return render_template('reorder.html', reorder_results=reorder_results, mismatched_items=mismatched_items, graph_data=graph_data)

        except Exception as e:
            flash(f'An error occurred while processing the reorder request: {str(e)}')
            return redirect(url_for('reorder'))  # Redirect back to the reorder page with an error message
    else:
        # If it's a GET request, simply render the page without any changes
        return render_template('reorder.html', reorder_results=None)




@app.route('/clear-reorder-forecasts', methods=['POST'])
def clear_reorder_forecasts():
    try:
        # Delete all forecasts from the Forecast table
        Forecast.query.delete()
        db.session.commit()  # Commit the changes to the database
        flash('All reorder forecasts have been cleared.')
    except Exception as e:
        flash(f'Error clearing reorder forecasts: {str(e)}')

    return redirect(url_for('reorder'))

@app.route('/compare-market-inventory', methods=['POST'])
def compare_market_inventory():
    # Fetch all market items and inventory items
    market_items = StockItem.query.all()  # Market stock
    inventory_items = InventoryItem.query.all()  # Warehouse inventory

    reorder_results = []  # List to store reorder recommendations

    # Compare market stock with warehouse inventory
    for market_item in market_items:
        # Find the corresponding inventory item
        inventory_item = next((item for item in inventory_items if item.name == market_item.name), None)

        if inventory_item:
            # Compare the stock
            market_stock = market_item.current_stock
            warehouse_stock = inventory_item.current_stock

            # Call ML model to predict when to restock and by how much
            restock_amount, restock_by, predicted_demand = forecaster.predict(market_item.name, market_stock, warehouse_stock)

            reorder_results.append({
                'item_name': market_item.name,
                'warehouse_stock': warehouse_stock,
                'market_stock': market_stock,
                'restock_amount': restock_amount,
                'restock_by': restock_by,
                'predicted_demand': predicted_demand
            })
        else:
            # If no inventory item is found for the market item, skip it
            continue

    # Display results on the reorder page
    return render_template('reorder.html', reorder_results=reorder_results)


@app.route('/clear-warehouse-inventory', methods=['POST'])
def clear_warehouse_inventory():
    try:
        # Delete all records in the InventoryItem table
        InventoryItem.query.delete()
        db.session.commit()  # Commit the changes to the database
        flash('Warehouse inventory has been cleared.')
    except Exception as e:
        flash(f'Error clearing warehouse inventory: {str(e)}')
    
    return redirect(url_for('manage_inventory'))


'''@app.route('/set_threshold', methods=['POST'])
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
    return redirect(url_for('dashboard'))'''

@app.route('/manage-inventory', methods=['GET', 'POST'])
def manage_inventory():
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
                        existing.price = row['price']
                    else:
                        item = InventoryItem(
                            name=row['name'],
                            category=row['category'],
                            current_stock=row['current_stock'],
                            price=row['price']
                            # No need to process 'reorder_threshold' anymore
                        )
                        db.session.add(item)
                db.session.commit()
                flash('CSV data imported successfully into inventory.')
            except Exception as e:
                flash(f'Error processing CSV: {str(e)}')
            finally:
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
            #reorder_threshold=int(request.form['reorder_threshold']),
            price=float(request.form['price'])
        )
        db.session.add(item)
        db.session.commit()
        flash('New stock item added successfully')
        return redirect(url_for('manage_inventory'))
    
    return render_template('add_stock.html')


'''@app.route('/update_threshold/<int:item_id>', methods=['POST'])
def update_threshold(item_id):
    item = StockItem.query.get_or_404(item_id)
    try:
        item.reorder_threshold = int(request.form['threshold'])
        db.session.commit()
        flash(f'Threshold updated for {item.name}')
    except ValueError:
        flash('Invalid threshold value')
    return redirect(url_for('dashboard'))'''

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
