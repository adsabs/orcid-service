from __future__ import absolute_import

from flask_cors import CORS
from .app import create_app

if __name__ == '__main__':
    app = create_app()
    cors = CORS(app, allow_headers=('Content-Type', 'Authorization', 'Orcid-Authorization'))
    app.run('0.0.0.0', port=5000, debug=True)
