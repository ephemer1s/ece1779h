#!../venv/bin/python
# from app import webapp
# from app.main import main

from werkzeug.serving import run_simple  # werkzeug development server
# use to combine each Flask app into a larger one that is dispatched based on prefix
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from backEnd import webapp as backEnd
from frontEnd import webapp as frontEnd
applications = DispatcherMiddleware(frontEnd, {
    '/backEnd': backEnd
})

if __name__ == "__main__":
    # applications.run('0.0.0.0', 5000, debug=True)
    run_simple('localhost', 5000, applications, use_reloader=True,
               use_debugger=False, use_evalex=True)
