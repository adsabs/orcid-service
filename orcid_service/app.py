from werkzeug.serving import run_simple
import os, sys

# simple loader of the orcid-service application
# for running things in wsgi container; use
# wsgi.py from the rootdir

def create_app():
    
    opath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if opath not in sys.path:
        sys.path.insert(0, opath)
    
    from orcid_service import views as orcid_views
    reload(orcid_views) # don't want singletons
    return orcid_views.app

if __name__ == '__main__':
    run_simple('0.0.0.0', 5000, create_app(), use_reloader=False, use_debugger=False)