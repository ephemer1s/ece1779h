#!../venv/bin/python
# from app import webapp
# from app.main import main
import time, os

if not os.path.exists('./logs'):
    os.mkdir('./logs')
import werkzeug

# from werkzeug.serving import run_simple  # werkzeug development server
# use to combine each Flask app into a larger one that is dispatched based on prefix
# from werkzeug.middleware.dispatcher import DispatcherMiddleware


from backEnd import webapp as backEnd
#from frontEnd import webapp as frontEnd
#from managerApp import webapp as managerApp

backEnd.secret_key = "Secreeeeeeeeeeet"


# application = DispatcherMiddleware({'/backEnd': backEnd})

if __name__ == "__main__":
    try:
        print(werkzeug.__version__)
    except ImportError as error:
        print(error.__class__.__name__ + ": " + error.message)
        with open("./logs/memcache.log", 'a') as f:
            f.write(str(time.time()) + error.__class__.__name__ + ": " + error.message)
    except Exception as exception:
        print(exception.__class__.__name__ + ": " + exception.message)
        with open("./logs/memcache.log", 'a') as f:
            f.write(str(time.time()) + exception.__class__.__name__ + ": " + exception.message)
    with open("./logs/memcache.log", 'a') as f:
        f.write(str(time.time()) + "    Memcache has loaded!\n")
    backEnd.run(host='0.0.0.0', port=5001)
    # """Using "threaded = True", the function can call API within itself while dealing with user requests.
    # """
    # run_simple('0.0.0.0', 5001, application,
    #            use_reloader=True,
    #            use_debugger=True,
    #            use_evalex=True,
    #            threaded=True)

