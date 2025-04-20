import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from models import db, StockItem, Forecast
from sklearn.metrics import mean_squared_error, r2_score
from datetime import datetime, timedelta

class ForecastModel:
    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False

    def prepare_data(self):
        """Prepare training data from database records"""
        items = StockItem.query.all()
        data = []
        
        for item in items:
            # Feature engineering: Extract useful date-based features
            month = item.date_scraped.month
            day_of_week = item.date_scraped.weekday()  # 0=Monday, 6=Sunday
            year = item.date_scraped.year
            week_of_year = item.date_scraped.isocalendar()[1]  # ISO week number
            
            total_price = item.current_stock * item.price
            market_stock = item.market_availability  # Assuming market stock availability is a boolean value or can be a stock number
            
            # Adding additional historical data features (you can add more features based on your business logic)
            previous_stock = item.current_stock  # You could store historical data like previous month's stock, etc.

            data.append({
                'stock_id': item.id,
                'current_stock': item.current_stock,
                'price': item.price,
                'total_value': total_price,
                'market_stock': market_stock,  # Include market stock
                'previous_stock': previous_stock,  # Example additional feature
                'month': month,
                'day_of_week': day_of_week,
                'year': year,
                'week_of_year': week_of_year
            })
        
        return pd.DataFrame(data)




    def train_model(self):
        """Train the machine learning model"""
        df = self.prepare_data()
        
        print(df.head())  # Check the training data

        if len(df) < 5:  # Minimum data check
            print("Insufficient data to train model")
            return False

        # Include new features: market stock, warehouse stock, etc.
        X = df[['current_stock', 'price', 'total_value', 'market_stock', 'month', 'day_of_week', 'year', 'week_of_year']]  # Features
        y = df['current_stock']  # Target variable (use this for training the model)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

        print(f"Training on {len(X_train)} items")
        print(f"Test data size: {len(X_test)}")

        self.model.fit(X_train, y_train)
        self.is_trained = True
        print("Model training complete.")
        return True




    def evaluate_model(self):
        """Evaluate the trained model"""
        df = self.prepare_data()
        X = df[['current_stock', 'price', 'total_value']]
        y = df['current_stock']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
        
        self.model.fit(X_train, y_train)
        
        # Predict on test data
        y_pred = self.model.predict(X_test)
        
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Mean Squared Error: {mse}")
        print(f"R-squared: {r2}")

        return mse, r2



    def predict(self, stock_id):
        """Make prediction for specific stock item"""
        if not self.is_trained:
            print("Model not trained. Training now...")
            if not self.train_model():
                print("Model training failed.")
                return 0, None, 0  # Return default values if model training fails
        else:
            print("Model already trained.")

        item = StockItem.query.get(stock_id)
        if not item:
            print(f"Item {stock_id} not found.")
            return 0, None, 0  # Return default values if item is not found

        # Prepare input data with the new features
        input_data = pd.DataFrame([{
            'current_stock': item.current_stock,
            'price': item.price,
            'total_value': item.current_stock * item.price,
            'market_stock': item.market_availability,  # Market stock data
            'month': item.date_scraped.month,
            'day_of_week': item.date_scraped.weekday(),
            'year': item.date_scraped.year,
            'week_of_year': item.date_scraped.isocalendar()[1]
        }])

        print(f"Prediction input data: {input_data}")  # Debugging log
        
        try:
            # Predict the stock amount (how much to restock)
            prediction = self.model.predict(input_data)
            restock_amount = max(0, round(prediction[0]))  # Ensure prediction is positive

            # Calculate restock date dynamically based on predicted demand
            restock_by = datetime.now() + timedelta(days=7)  # Example restock prediction logic (7 days from today)
            if restock_amount > 0:
                # Adjust restock_by based on demand (this can be replaced with more sophisticated logic)
                restock_by = datetime.now() + timedelta(days=(restock_amount // 10))  # Simple logic to adjust restock date
            
            print(f"Restock amount for {item.name}: {restock_amount}")
            print(f"Restock by date for {item.name}: {restock_by}")
            
            # Also predict demand (this could be an optional output from the model or a separate logic)
            predicted_demand = (item.current_stock + item.price) / 2  # Example demand prediction logic
            
            return restock_amount, restock_by.strftime('%Y-%m-%d'), predicted_demand  # Return restock amount and date
        except Exception as e:
            print(f"Prediction error: {str(e)}")
            return 0, None, 0  # Return default values if there's an error




