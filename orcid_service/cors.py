
from flask_cors import CORS
from views import app

cors = CORS(app, allow_headers=('Content-Type', 'Authorization', 'Orcid-Authorization'))

if __name__ == '__main__':
    app.run('127.0.0.1', port=5000, debug=True)
