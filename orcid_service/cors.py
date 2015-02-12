
from flask_cors import CORS
from app import app

cors = CORS(app, allow_headers=('Content-Type', 'Authorization', 'Orcid-Authorization'))

app.run('127.0.0.1', port=5000, debug=True)
