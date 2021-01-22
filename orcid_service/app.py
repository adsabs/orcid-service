from __future__ import absolute_import
from werkzeug.serving import run_simple
from adsmutils import ADSFlask
from .views import bp
from flask.ext.discoverer import Discoverer

def create_app(**config):

    app = ADSFlask(__name__, static_folder=None, local_config=config or {})

    app.url_map.strict_slashes = False
    
    ## pysqlite driver breaks transactions, we have to apply some hacks as per
    ## http://docs.sqlalchemy.org/en/rel_0_9/dialects/sqlite.html#pysqlite-serializable
    if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', None):
        from sqlalchemy import event
        engine = app.db.engine
        
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

    discoverer = Discoverer(app)

    return app

if __name__ == "__main__":
    run_simple('0.0.0.0', 5000, create_app(), use_reloader=False, use_debugger=False)