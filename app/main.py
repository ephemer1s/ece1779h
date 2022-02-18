from re import TEMPLATE


import os
TEMPLATE_DIR = os.path.abspath("./templates")
STATIC_DIR = os.path.abspath("./static")

from flask import json, render_template, url_for, request
from app import webapp, memcache


#===================================Under Construction=============================================
@webapp.route('/')
def main():
    return render_template("index.html")


@webapp.route('/upload')
def upload():
    return render_template("main-old.html")  # TODO: need to adjust this html and corresponding get codes


@webapp.route('/browse')
def browse():
    pass


@webapp.route('/keylist')
def keylist():
    pass


@webapp.route('/config')
def config():
    pass


@webapp.route('/status')
def status():
    pass
#===================================Under Construction=============================================

@webapp.route('/get',methods=['POST'])
def get():
    key = request.form.get('key')

    if key in memcache:
        value = memcache[key]
        response = webapp.response_class(
            response=json.dumps(value),
            status=200,
            mimetype='application/json'
        )
    else:
        response = webapp.response_class(
            response=json.dumps("Unknown key"),
            status=400,
            mimetype='application/json'
        )

    return response

@webapp.route('/put',methods=['POST'])
def put():
    key = request.form.get('key')
    value = request.form.get('value')
    memcache[key] = value

    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )

    return response

