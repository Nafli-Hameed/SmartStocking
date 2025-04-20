from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from flask import current_app
from db import db

class StockItem(db.Model):
    __tablename__ = 'stock_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50))
    current_stock = db.Column(db.Integer, default=0)
    market_availability = db.Column(db.Boolean, default=True)
    price = db.Column(db.Float)
    date_scraped = db.Column(db.DateTime, default=datetime.utcnow)  # Add the date_scraped field
    
    # Relationship for forecasting (if needed)
    forecasts = db.relationship('Forecast', back_populates='stock_item', lazy=True)

    def needs_reorder(self):
        return self.current_stock < 1  # Modify logic based on your needs



class InventoryItem(db.Model):
    __bind_key__ = 'inventory_db'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    current_stock = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


class Forecast(db.Model):
    __tablename__ = 'forecasts'
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=False)
    predicted_demand = db.Column(db.Float)
    forecast_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Use back_populates instead of backref to avoid conflict
    stock_item = db.relationship('StockItem', back_populates='forecasts')
