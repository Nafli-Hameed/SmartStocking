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
    reorder_threshold = db.Column(db.Integer)
    price = db.Column(db.Float)
    forecasts = db.relationship('Forecast', backref='stock_item', lazy=True)
    def needs_reorder(self):
        # Assume the model has current_stock and reorder_threshold fields
        return self.current_stock <= self.reorder_threshold

class InventoryItem(db.Model):
    # Model definition for inventory management data
    __bind_key__ = 'inventory_db'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    current_stock = db.Column(db.Integer, nullable=False)
    reorder_threshold = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)


    def needs_reorder(self):
        return self.current_stock < self.reorder_threshold

class Forecast(db.Model):
    __tablename__ = 'forecasts'
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock_items.id'), nullable=False)
    predicted_demand = db.Column(db.Float)
    forecast_date = db.Column(db.DateTime, default=datetime.utcnow)
