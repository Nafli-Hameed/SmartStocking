from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import Config
from models import db, StockItem, Forecast
from scraper import WebScraper
from ml_model import ForecastModel
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Initialize components
scraper = WebScraper()
forecaster = ForecastModel()

@app.route('/')
def dashboard():
    items = StockItem.query.all()
    return render_template('dashboard.html', items=items)

@app.route('/update-stock', methods=['POST'])
def update_stock():
    data = request.get_json()
    url = data.get('url')
    print(f"Received URL: {url}")  # Print the received URL
    if url:
        item_count = scraper.update_database(url)
        flash(f"Updated {item_count} items from {url}", "success")
    else:
        flash("URL is required.", "error")
    return jsonify({'success': True})

#    return redirect(url_for('dashboard'))

@app.route('/forecast/<int:stock_id>')
def stock_forecast(stock_id):
    item = StockItem.query.get_or_404(stock_id)
    forecast_value = forecaster.predict(item.id)
    
    if forecast_value is not None:
        # Store forecast in the database
        new_forecast = Forecast(stock_id=item.id, predicted_demand=forecast_value, forecast_date=datetime.utcnow())
        db.session.add(new_forecast)
        db.session.commit()
        
        flash("Forecast generated successfully!", "success")
    else:
        flash("Could not generate forecast.", "error")
        
    return redirect(url_for('forecast_view'))

@app.route('/clear-stock', methods=['GET', 'POST'])
def clear_stock():
    try:
        StockItem.query.delete()
        db.session.commit()
        flash("Stock cleared successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Failed to clear stock: {e}", "error")
    return redirect(url_for('dashboard'))


@app.route('/forecasts')
def forecast_view():
    forecasts = Forecast.query.all()

    # Create dataframe for chart
    df = pd.DataFrame([(f.stock_item.name, f.predicted_demand, f.forecast_date) for f in forecasts],
                      columns=['Stock Name', 'Predicted Demand', 'Forecast Date'])

    # Create Plotly line chart
    fig = px.line(df, x='Forecast Date', y='Predicted Demand', color='Stock Name',
                  title='Demand Forecast History')

    chart = fig.to_html(full_html=False)

    return render_template('forecast.html', forecasts=forecasts, chart=chart)

@app.route('/reorder')
def reorder_list():
    items = StockItem.query.all()
    reorder_items = [item for item in items if item.needs_reorder()]
    return render_template('reorder.html', items=reorder_items)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
