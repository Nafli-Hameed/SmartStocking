from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    current_stock = db.Column(db.Integer, default=0)
    reorder_threshold = db.Column(db.Integer)
    price = db.Column(db.Float)  # Make sure this line is present and correct
    forecasts = db.relationship('Forecast', backref='stock_item', lazy=True)

    def needs_reorder(self):
        return self.current_stock < self.reorder_threshold

class Forecast(db.Model):
    __tablename__ = 'forecasts'
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=False)
    predicted_demand = db.Column(db.Float)
    forecast_date = db.Column(db.DateTime, default=datetime.utcnow)
