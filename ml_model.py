import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from models import db, StockItem, Forecast

class ForecastModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        
    def prepare_data(self):
        items = StockItem.query.all()
        data = [{
            'stock_id': item.id,
            'historical_sales': sum(oi.quantity for o in item.orders for oi in o.items),
            'current_stock': item.current_stock
        } for item in items]
        
        return pd.DataFrame(data)

    def train(self):
        df = self.prepare_data()
        if df.empty:
            return False
            
        X = df[['historical_sales', 'current_stock']]
        y = df['current_stock']  # Simplified example
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        self.model.fit(X_train, y_train)
        return True

    def predict(self, stock_id):
        item = StockItem.query.get(stock_id)
        if not item:
            return None
            
        input_data = pd.DataFrame([{
            'historical_sales': sum(oi.quantity for o in item.orders for oi in o.items),
            'current_stock': item.current_stock
        }])
        
        prediction = self.model.predict(input_data)[0]
        return max(0, round(prediction))
