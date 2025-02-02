import nltk

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
nltk.download('stopwords')
nltk.download('vader_lexicon')

from flask import Flask, render_template, jsonify
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import nltk
from nltk import word_tokenize, pos_tag, ne_chunk
from nltk.sentiment import SentimentIntensityAnalyzer

# Download necessary NLTK resources
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')
nltk.download('stopwords')
nltk.download('vader_lexicon')

# Initialize Flask app
app = Flask(__name__)

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

# NLP Analysis Function using NLTK
def analyze_market_text(text):
    # Tokenization and POS tagging
    tokens = word_tokenize(text)
    pos_tags = pos_tag(tokens)

    # Named Entity Recognition (NER)
    ner_tree = ne_chunk(pos_tags)
    entities = []
    for chunk in ner_tree:
        if hasattr(chunk, 'label'):
            entities.append((chunk.label(), ' '.join(c[0] for c in chunk)))

    # Sentiment Analysis using VADER
    sia = SentimentIntensityAnalyzer()
    sentiment = sia.polarity_scores(text)

    return {
        'entities': entities,
        'sentiment': {
            'positive': sentiment['pos'],
            'neutral': sentiment['neu'],
            'negative': sentiment['neg'],
            'compound': sentiment['compound']
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

if __name__ == '__main__':
    app.run(debug=True)
