# search_functionality.py

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from marshmallow import Schema, fields, ValidationError
import redis

# Setup Flask application
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///search_db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Setup Redis for caching
cache = redis.StrictRedis(host='localhost', port=6379, db=0)

# Database model for search items
class SearchItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(500), nullable=False)

# Schema for validating search queries
class SearchSchema(Schema):
    query = fields.Str(required=True)

def create_db():
    """Create database tables."""
    with app.app_context():
        db.create_all()

@app.route('/search', methods=['GET'])
def search():
    """Search endpoint to retrieve items based on query."""
    # Input validation
    try:
        args = SearchSchema().load(request.args)
    except ValidationError as err:
        return jsonify({'error': 'Invalid input', 'details': err.messages}), 400

    query = args['query']
    # Check cache first
    cached_results = cache.get(query)
    if cached_results:
        return jsonify({'results': eval(cached_results.decode('utf-8'))})

    try:
        # Fetch results from the database
        results = SearchItem.query.filter(SearchItem.title.ilike(f'%{query}%')).all()
        if not results:
            return jsonify({'message': 'No results found for your query.'}), 404

        # Format results for response
        formatted_results = [{'id': item.id, 'title': item.title, 'description': item.description} for item in results]

        # Cache the results for future requests
        cache.set(query, str(formatted_results), ex=300)  # Cache expires in 300 seconds

        return jsonify({'results': formatted_results})
    except SQLAlchemyError as e:
        return jsonify({'error': str(e)}), 500

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    """Provide autocomplete suggestions based on input."""
    user_input = request.args.get('input', '')
    results = SearchItem.query.filter(SearchItem.title.ilike(f'%{user_input}%')).limit(5).all()

    suggestions = [item.title for item in results]
    return jsonify({'suggestions': suggestions})

if __name__ == '__main__':
    create_db()
    app.run(debug=True)