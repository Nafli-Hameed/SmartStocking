from models import InventoryItem, StockItem
from db import db
from flask import current_app

def match_items(inventory_items, market_items):
    matched_items = []
    mismatched_items = []

    for inventory_item in inventory_items:
        matched = False
        for market_item in market_items:
            if inventory_item.name == market_item.name:
                # Match if name is the same and market item is available
                if market_item.market_availability:
                    matched_items.append((inventory_item, market_item))
                    matched = True
                    break
        if not matched:
            mismatched_items.append(inventory_item)
    
    return matched_items, mismatched_items



def forecast_reorder(matched_items):
    reorders = []
    
    for inventory_item, market_item in matched_items:
        forecasted_demand = calculate_forecasted_demand(market_item)

        # If inventory stock is less than forecasted demand and the item is available in the market
        if inventory_item.current_stock < forecasted_demand:
            amount_to_reorder = forecasted_demand - inventory_item.current_stock
            if amount_to_reorder > 0:
                reorders.append({
                    'name': inventory_item.name,
                    'amount_to_reorder': amount_to_reorder,
                    'when_to_reorder': "Based on market availability and forecasted demand"
                })
    
    return reorders




def calculate_forecasted_demand(market_item):
    if market_item.market_availability:
        # Simple logic for forecasting demand, adjust as needed
        return market_item.current_stock  
    else:
        return 0  # If not available in the market, no forecasted demand


