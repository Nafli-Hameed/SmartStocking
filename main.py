# Import necessary libraries
from flask import Flask, render_template, jsonify
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from textblob import TextBlob
import spacy

# Initialize Flask app
app = Flask(__name__)

# Load NLP model (spaCy)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

# Sample inventory data (replace with actual data later)
inventory_data = [
    {'item': 'Laptops', 'current_stock': 45, 'threshold': 30},
    {'item': 'Smartphones', 'current_stock': 120, 'threshold': 80},
    {'item': 'Accessories', 'current_stock': 25, 'threshold': 20}
]

# Machine Learning Model (Mocked for simplicity)
def train_ml_model():
    # Generate sample data (replace with real data later)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='D')
    data = pd.DataFrame({
        'date': dates,
        'sales': pd.Series(range(len(dates))),
        'stock_level': pd.Series(range(len(dates), 0, -1))
    })
    data['day_of_week'] = data['date'].dt.dayofweek

    # Features and target variable
    X = data[['day_of_week', 'sales']]
    y = data['stock_level']

    # Train Random Forest model
    model = RandomForestRegressor(n_estimators=10, random_state=42)
    model.fit(X, y)
    return model

model = train_ml_model()

# NLP Analysis Function
def analyze_market_text(text):
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    sentiment = TextBlob(text).sentiment
    return {
        'entities': entities,
        'sentiment': {
            'polarity': sentiment.polarity,
            'subjectivity': sentiment.subjectivity
        }
    }

# Flask Routes
@app.route('/')
def dashboard():
    return render_template('dashboard.html', inventory=inventory_data)

@app.route('/predict')
def predict():
    # Example prediction input (replace with real-time input later)
    sample_input = pd.DataFrame([[3, 50]], columns=['day_of_week', 'sales'])
    prediction = model.predict(sample_input)
    return jsonify({'predicted_stock': prediction[0]})

@app.route('/analyze')
def analyze():
    market_report = """
        Electronics demand is expected to rise 15% QoQ based on market trends.
        Major retailers report supply chain improvements. Consumer sentiment remains positive.
    """
    analysis_results = analyze_market_text(market_report)
    return jsonify(analysis_results)

if __name__ ==
