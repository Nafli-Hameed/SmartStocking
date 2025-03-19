from flask import Flask, render_template, request, redirect, url_for
from config import Config
from models import db, User, Order, OrderItem, StockItem, Forecast
from scraper import WebScraper
from ml_model import ForecastModel
import plotly.express as px
from datetime import datetime, timedelta

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
    scraper.update_database()
    return redirect(url_for('dashboard'))

@app.route('/forecast/<int:stock_id>')
def stock_forecast(stock_id):
    item = StockItem.query.get_or_404(stock_id)
    forecast = forecaster.predict(stock_id)
    
    # Store forecast
    new_forecast = Forecast(
        stock_id=stock_id,
        predicted_demand=forecast,
        forecast_date=datetime.utcnow()
    )
    db.session.add(new_forecast)
    db.session.commit()
    
    return redirect(url_for('forecast_view'))

@app.route('/forecasts')
def forecast_view():
    forecasts = Forecast.query.order_by(Forecast.forecast_date.desc()).limit(10).all()
    
    # Create Plotly chart
    fig = px.line(
        x=[f.forecast_date for f in forecasts],
        y=[f.predicted_demand for f in forecasts],
        labels={'x': 'Date', 'y': 'Predicted Demand'},
        title='Demand Forecast History'
    )
    chart = fig.to_html()
    
    return render_template('forecast.html', chart=chart, forecasts=forecasts)

@app.route('/reorder')
def reorder_list():
    items = StockItem.query.filter(StockItem.current_stock < StockItem.reorder_threshold).all()
    return render_template('reorder.html', items=items)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
