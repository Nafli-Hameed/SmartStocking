from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL

class ScrapeForm(FlaskForm):
    url = StringField('Enter URL to Scrape', validators=[DataRequired(), URL()])
    submit = SubmitField('Update Stock Data')
