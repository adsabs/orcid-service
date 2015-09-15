from flask import Flask
from views import bp
from flask.ext.consulate import Consul, ConsulConnectionError
from flask.ext.discoverer import Discoverer
from flask.ext.sqlalchemy import SQLAlchemy
from .models import db

def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.url_map.strict_slashes = False

    Discoverer(app)
    Consul(app)  # load_config expects consul to be registered
    load_config(app, config)
    db.init_app(app)
    
     ## pysqlite driver breaks transactions, we have to apply some hacks as per
    ## http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#pysqlite-serializable
    
    if 'sqlite' in (app.config.get('SQLALCHEMY_BINDS') or {'orcid':''})['orcid']:
        from sqlalchemy import event
        
        binds = app.config.get('SQLALCHEMY_BINDS')
        if binds and 'orcid' in binds:
            engine = db.get_engine(app, bind=(app.config.get('SQLALCHEMY_BINDS') and 'orcid'))
        else:
            engine = db.get_engine(app)
        
        @event.listens_for(engine, "connect")
        def do_connect(dbapi_connection, connection_record):
            # disable pysqlite's emitting of the BEGIN statement entirely.
            # also stops it from emitting COMMIT before any DDL.
            dbapi_connection.isolation_level = None

        @event.listens_for(engine, "begin")
        def do_begin(conn):
            # emit our own BEGIN
            conn.execute("BEGIN")
    
    app.register_blueprint(bp)
    return app


def load_config(app, config=None):
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
        
    if config:
        app.config.update(config)