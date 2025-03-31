import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from models import db, StockItem, Forecast

class ForecastModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False

    def prepare_data(self):
        """Prepare training data from database records"""
        items = StockItem.query.all()
        data = []
        
        for item in items:
            # Ensure you handle potential division by zero
            total_price = item.current_stock * item.price
            data.append({
                'stock_id': item.id,
                'current_stock': item.current_stock,
                'price': item.price,
                'total_value': total_price  # Aggregate value of stock
            })
        
        return pd.DataFrame(data)

    def train_model(self):
        """Train the machine learning model"""
        df = self.prepare_data()
        if len(df) < 5:  # Minimum data check
            print("Insufficient data to train model")
            return False
            
        X = df[['current_stock', 'price', 'total_value']]
        y = df['current_stock']  # Target variable
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        self.model.fit(X_train, y_train)
        self.is_trained = True
        return True

    def predict(self, stock_id):
        """Make prediction for specific stock item"""
        if not self.is_trained:
            if not self.train_model():
                return None
                
        item = StockItem.query.get(stock_id)
        if not item:
            return None
            
        input_data = pd.DataFrame([{
            'current_stock': item.current_stock,
            'price': item.price,
            'total_value': item.current_stock * item.price
        }])
        
        try:
            return max(0, round(self.model.predict(input_data)[0]))
        except Exception as e:
            print(f"Prediction error: {str(e)}")
            return None
