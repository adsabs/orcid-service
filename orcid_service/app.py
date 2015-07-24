from flask import Flask
from views import bp
from flask.ext.consulate import Consul, ConsulConnectionError
from flask.ext.discoverer import Discoverer


def create_app():
    app = Flask(__name__, static_folder=None)
    app.url_map.strict_slashes = False

    Discoverer(app)
    Consul(app)  # load_config expects consul to be registered
    load_config(app)
    app.register_blueprint(bp)
    return app


def load_config(app):
    """
    Loads configuration in the following order:
        1. config.py
        2. local_config.py (ignore failures)
        3. consul (ignore failures)
    :param app: flask.Flask application instance
    :return: None
    """

    app.config.from_pyfile('config.py')

    try:
        app.config.from_pyfile('local_config.py')
    except IOError:
        app.logger.warning("Could not load local_config.py")
    try:
        app.extensions['consul'].apply_remote_config()
    except ConsulConnectionError, e:
        app.logger.warning("Could not apply config from consul: {}".format(e))