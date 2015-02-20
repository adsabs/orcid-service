from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware
from orcid_service import views

application = views.app

if __name__ == "__main__":
    run_simple('0.0.0.0', 5000, application, use_reloader=False, use_debugger=False)
