# utils.py
from models import InventoryItem, StockItem
from db import db
from flask import current_app

# utils.py
def match_items(inventory_items, market_items):
    matched_items = []
    mismatched_items = []
    
    for inventory_item in inventory_items:
        for market_item in market_items:
            if inventory_item.name == market_item.name:
                matched_items.append((inventory_item, market_item))
                break
        else:
            mismatched_items.append(inventory_item)
    
    return matched_items, mismatched_items

def forecast_reorder(matched_items):
    reorders = []
    
    for inventory_item, market_item in matched_items:
        forecasted_demand = market_item.current_stock  # Simple forecasting example
        
        if inventory_item.current_stock < inventory_item.reorder_threshold:
            amount_to_reorder = forecasted_demand - inventory_item.current_stock
            
            reorders.append({
                'name': inventory_item.name,
                'amount_to_reorder': amount_to_reorder,
                'when_to_reorder': "When stock falls below threshold"
            })
    
    return reorders


def calculate_forecasted_demand(market_item):
    # Implement your forecasting model here
    return market_item.current_stock
