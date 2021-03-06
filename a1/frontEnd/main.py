import base64
import frontEnd
from frontEnd.config import Config
import mysql.connector
from frontEnd import webapp, old_memcache
from flask import json, render_template, url_for, request, g, flash, redirect, send_file, jsonify
from re import TEMPLATE
import http.client
import requests
import time
import threading

import os
TEMPLATE_DIR = os.path.abspath("./templates")
STATIC_DIR = os.path.abspath("./static")


def connect_to_database():
    return mysql.connector.connect(user=Config.db_config['user'],
                                   password=Config.db_config['password'],
                                   host=Config.db_config['host'],
                                   database=Config.db_config['database'])


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = connect_to_database()
    return db


@webapp.teardown_appcontext
def teardown_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# ===================================Under Construction=============================================


@webapp.before_first_request
def _run_on_start():
    """Initialization when the flask app first startup. 
    Includes memcache init, memcache getting configuration from database, and starting to update statistics every 5s.
    """

    # initialize backend memcache
    makeAPI_Call(
        "http://127.0.0.1:5000/backEnd/init", "get", 5)

    # let backend read config data from database
    makeAPI_Call(
        "http://127.0.0.1:5000/backEnd/refreshConfiguration/131417728/1", "get", 5)

    # # clear database table
    # cnx = mysql.connector.connect(user=Config.db_config['user'],
    #                               password=Config.db_config['password'],
    #                               host=Config.db_config['host'],
    #                               database=Config.db_config['database'])

    # cursor = cnx.cursor()
    # sql = "DELETE FROM keylist"
    # cursor.execute(sql)
    # cnx.commit()
    # cnx.close()

    x = threading.Thread(target=backEndUpdater)
    x.start()


def backEndUpdater():
    """Loops every 5s, caller to updater()
    """
    while True:
        updater()
        time.sleep(5)


def updater():
    """Update the memcache stats from the memcache to the database. Called every 5s.
    """
    json_dict = makeAPI_Call(
        "http://127.0.0.1:5000/backEnd/statistic", "get", 10)

    # statsDict = json.loads(json_acceptable_string)
    statsList = [-1, -1, -1, 0.0, 0.0]
    if (json_dict['success'] == 'true'):
        statsList = json_dict['message']
    print("Stats List: ", statsList)

    # Code to upload to database @ HaoZhe

    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()

    sql = "UPDATE statistics SET itemNum = %s, itemTotalSize = %s, requestNum = %s, missRate = %s, hitRate = %s  WHERE id = 0"
    val = (statsList[0], statsList[1],
           statsList[2], statsList[3], statsList[4], )
    cursor.execute(sql, val)
    cnx.commit()
    cnx.close()

    pass


@webapp.route('/')
def main():
    """Main Page

    Returns:
        html of Main Page
    """
    return render_template("index.html")


@webapp.route('/upload')
def upload():
    """Upload Page

    Returns:
        html of the uploading Page
    """
    return render_template("upload.html")


@webapp.route('/browse')
def browse():
    return render_template("browse.html")


@webapp.route('/api/list_keys', methods=['POST'])
def api_List_Keys():
    """Keylist Page: Display all keys in the database

    Returns:
        html of the keylist Page
    """

    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()
    query = "SELECT keyID FROM keylist"
    cursor.execute(query)
    RDBMS_Data = cursor.fetchall()

    returnList = []

    if RDBMS_Data:
        for i in RDBMS_Data:
            returnList.append(i[0])

    cnx.close()
    return jsonify({"success": "true",
                    "keys": returnList})


@webapp.route('/keylist')
def keylist():
    """Keylist Page: Display all keys in the database

    Returns:
        html of the keylist Page
    """

    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()
    query = "SELECT keyID, path FROM keylist"
    cursor.execute(query)
    view = render_template("keylist.html", title="Key List", cursor=cursor)
    cnx.close()
    return view


@webapp.route('/configs', methods=['GET'])
def configs():
    """Configure the memcache parameters (capacity & policy)

    Returns:
        html of the config Page
    """

    return render_template("configs.html")


@webapp.route('/configsUpdate', methods=['POST'])
#  Update memcache parameters in database when confirmed
def configsUpdate():
    """API function to update the changes from the user to database, and call memcache to refreshConfigurations

    Returns:
        Response message if updating successfully
    """

    capacityMB = request.form.get('capacityMB', "")
    replacepolicy = request.form.get('replacepolicy', "")

    # convert MB form capacity into B form
    capacityB = int(capacityMB) * 1048576

    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()
    cursor.execute("UPDATE configuration SET capacityB = %s, replacepolicy = %s WHERE id = 0",
                   (capacityB, replacepolicy,))
    cnx.commit()
    cnx.close()

    status = makeAPI_Call(
        "http://127.0.0.1:5000/backEnd/refreshConfiguration" + "/" + str(capacityB) + "/" + str(replacepolicy), "get", 5)

    print(status)

    response = webapp.response_class(
        response=json.dumps("Cache Configs Update Successfully."),
        status=200,
        mimetype='application/json'
    )
    print(response)

    return response


@webapp.route('/status')
def status():
    """Statistics Page: Display current statistics of  the memcache

    Returns:
        Html of the statistics page
    """

    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()
    query = "SELECT itemNum, itemTotalSize, requestNum, missRate, hitRate FROM statistics WHERE id = 0"
    cursor.execute(query)
    memCacheStatistics = cursor.fetchall()

    view = render_template("statistics.html", cursor=memCacheStatistics)
    cnx.close()
    return view


@webapp.route('/home')
def backHome():
    """Home Page: Call to go back to main page "/"

    Returns:
        html of Main Page
    """
    return render_template("index.html")


@webapp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@webapp.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# @app.route('/display/<filename>')
# def display_image(filename):
# 	print('display_image filename: ' + filename)
# 	return redirect(url_for('static', filename='uploads/' + filename), code=301)  # path is ./frontEnd/static/uploads


@webapp.route('/api/key/<key_value>', methods=['POST', 'GET'])
def api_Retreive_Image(key_value):
    """Get the path of the image given a key. Will first try to get from cache, then try to get from database if cache miss.

    Returns:
        the file contents
    """
    # key = request.form.get('key')

    pathToImage = ""

    # Call cache and see if cache has the path

    api_url = "http://127.0.0.1:5000/backEnd/get/" + key_value

    returnDict = makeAPI_Call(api_url, "get", 5)
    content = ""
    if returnDict['cache'] == "hit":
        pathToImage = returnDict['filePath']
        content = returnDict['content']
    elif returnDict['cache'] == "miss":
        cnx = mysql.connector.connect(user=Config.db_config['user'],
                                      password=Config.db_config['password'],
                                      host=Config.db_config['host'],
                                      database=Config.db_config['database'])

        cursor = cnx.cursor()
        cursor.execute("SELECT path FROM keylist WHERE keyID = %s",
                       (key_value,))
        RDBMS_Data = cursor.fetchall()
        cnx.close()
        if(not RDBMS_Data):
            # Even the RDBMS does not have it
            return jsonify({"success": "false",
                            "error": {
                                "code": 400,
                                "message": "Unknown Key."
                            }})

        elif(RDBMS_Data):
            # RDBMS has path; Need to save file to memcache

            # Seperate filepath into name and extension

            # OS independence
            filepath = RDBMS_Data[0][0]
            filepath = filepath.replace('\\', '/')

            filenameWithExtension = os.path.basename(filepath)

            print("filenameWithExtension: ", filenameWithExtension)

            api_url = "http://127.0.0.1:5000/backEnd/put/" + \
                key_value + "/" + filenameWithExtension + "/" + filepath

            returnDict = makeAPI_Call(api_url, "get", 5)

            pathToImage = filepath
            print(pathToImage)
            # response = webapp.response_class(
            #     response=json.dumps(pathToImage),
            #     status=200,
            #     mimetype='application/json'
            # )

            # return response
            filepath = pathToImage.replace('\\', '/')

            filenameWithExtension = os.path.basename(filepath)

            if not os.path.isfile(filepath):
                return jsonify({"success": "false",
                                "error": {
                                    "code": 400,
                                    "message": "File not found."
                                }})

            image = open(filepath, 'rb')
            image_Binary = image.read()
            content = base64.b64encode(image_Binary).decode()
    return jsonify({"success": "true",
                    "content": content})


@webapp.route('/get', methods=['GET', 'POST'])
def get():
    """Get the path of the image given a key. Will first try to get from cache, then try to get from database if cache miss.

    Returns:
        the file contents
    """
    key_value = request.form.get('key')

    pathToImage = ""
    extension = ""
    # Call cache and see if cache has the path

    api_url = "http://127.0.0.1:5000/backEnd/get/" + key_value

    returnDict = makeAPI_Call(api_url, "get", 5)
    content = ""
    if returnDict['cache'] == "hit":
        pathToImage = returnDict['filePath']
        content = returnDict['content']

        filepath = pathToImage.replace('\\', '/')

        filenameWithExtension = os.path.basename(filepath)
        extension = os.path.splitext(filenameWithExtension)[1]

    elif returnDict['cache'] == "miss":
        cnx = mysql.connector.connect(user=Config.db_config['user'],
                                      password=Config.db_config['password'],
                                      host=Config.db_config['host'],
                                      database=Config.db_config['database'])

        cursor = cnx.cursor()
        cursor.execute("SELECT path FROM keylist WHERE keyID = %s",
                       (key_value,))
        RDBMS_Data = cursor.fetchall()
        cnx.close()
        if(not RDBMS_Data):
            # Even the RDBMS does not have it
            return jsonify({"success": "false",
                            "error": {
                                "code": 400,
                                "message": "Unknown Key."
                            }})

        elif(RDBMS_Data):
            # RDBMS has path; Need to save file to memcache

            # Seperate filepath into name and extension

            # OS independence
            filepath = RDBMS_Data[0][0]
            filepath = filepath.replace('\\', '/')

            filenameWithExtension = os.path.basename(filepath)

            print("filenameWithExtension: ", filenameWithExtension)

            api_url = "http://127.0.0.1:5000/backEnd/put/" + \
                key_value + "/" + filenameWithExtension + "/" + filepath

            returnDict = makeAPI_Call(api_url, "get", 5)

            pathToImage = filepath
            print(pathToImage)

            # response = webapp.response_class(
            #     response=json.dumps(pathToImage),
            #     status=200,
            #     mimetype='application/json'
            # )

            # return response
            filepath = pathToImage.replace('\\', '/')

            filenameWithExtension = os.path.basename(filepath)

            # check if file exist

            if not os.path.isfile(filepath):
                return jsonify({"success": "false",
                                "error": {
                                    "code": 400,
                                    "message": "File not found."
                                }})

            image = open(filepath, 'rb')
            image_Binary = image.read()
            content = base64.b64encode(image_Binary).decode()
            extension = os.path.splitext(filenameWithExtension)[1]

    return render_template("browse.html", content=content, extension=extension)


@webapp.route('/api/upload', methods=['POST'])
def apiUpload():
    """Upload key image pair. image is stored in local filesystem, and its path is sent to database for storage. 
    invalidateKey() is called on memcache. Has logic that deals with missing or repeated filename.

    Alternative route to put()

    Returns:
        json response
    """
    key = request.form.get('key')
    file = request.files['file']

    if file.filename == '':  # If file not given, quit
        return ({"success": "false",
                 "error": {
                     "code": 400,
                     "message": "No file given"
                 }
                 })

    # Go on database to find if key exist already. If it does, find path, drop
    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()
    cursor.execute("SELECT path FROM keylist WHERE keyID = %s",
                   (key,))
    RDBMS_Data = cursor.fetchall()

    uploadedFile = False

    if file:
        print(type(file))
        upload_folder = webapp.config['UPLOAD_FOLDER']
        if not os.path.isdir(upload_folder):
            os.mkdir(upload_folder)
        filename = os.path.join(upload_folder, file.filename)
        print("filename : ", filename)
        filename = filename.replace('\\', '/')
        print("filename : ", filename)
        if RDBMS_Data:
            # use path to delete from local filesystem
            if os.path.isfile(RDBMS_Data[0][0]):
                os.remove(RDBMS_Data[0][0])

        # Check if filename already exists in folder
        fileExists = True
        currentFileName = file.filename
        while (fileExists):
            if not os.path.isfile(filename):
                fileExists = False
            else:
                split_tup = os.path.splitext(currentFileName)
                currentFileName = split_tup[0] + "_copy_" + split_tup[1]
                filename = os.path.join(
                    upload_folder, currentFileName)

        file.save(filename)
        # return redirect(url_for('download_file', name=file.filename))
        uploadedFile = True

        if not RDBMS_Data:
            print("Database does not have this key.")
            # push to db
            cursor.execute("INSERT INTO keylist (keyID, path) VALUES (%s, %s)",
                           (key, filename,))
            cnx.commit()

        elif RDBMS_Data:
            print("Database has this key.")

            # drop from db
            cursor.execute("UPDATE keylist SET path = %s WHERE keyID = %s",
                           (filename, key,))
            cnx.commit()

    cnx.close()

    old_memcache[key] = file

    if file is not None:
        # base64_data = base64.b64encode(file)
        pass

    if uploadedFile:
        # Call backEnd to invalidateKey
        api_url = "http://127.0.0.1:5000/backEnd/invalidateKey/" + key

        json_acceptable_string = makeAPI_Call(api_url, "get", 5)

    return jsonify({"success": "true"})


@webapp.route('/put', methods=['POST'])
def put():
    """Upload key image pair. image is stored in local filesystem, and its path is sent to database for storage. 
    invalidateKey() is called on memcache. Has logic that deals with missing or repeated filename.

    Returns:
        json response
    """
    key = request.form.get('key')
    file = request.files['file']

    if not key:  # If key not given, quit
        response = webapp.response_class(
            response=json.dumps("Key not given."),
            status=400,
            mimetype='application/json'
        )
        print(response)
        return response

    # print(key, file)

    if file.filename == '':  # If file not given, quit
        response = webapp.response_class(
            response=json.dumps("File not selected"),
            status=400,
            mimetype='application/json'
        )
        print(response)
        return response

    # Go on database to find if key exist already. If it does, find path, drop
    cnx = mysql.connector.connect(user=Config.db_config['user'],
                                  password=Config.db_config['password'],
                                  host=Config.db_config['host'],
                                  database=Config.db_config['database'])

    cursor = cnx.cursor()
    cursor.execute("SELECT path FROM keylist WHERE keyID = %s",
                   (key,))
    RDBMS_Data = cursor.fetchall()

    uploadedFile = False

    if file:
        print(type(file))
        upload_folder = webapp.config['UPLOAD_FOLDER']
        if not os.path.isdir(upload_folder):
            os.mkdir(upload_folder)
        filename = os.path.join(upload_folder, file.filename)
        print("filename : ", filename)
        filename = filename.replace('\\', '/')
        print("filename : ", filename)
        if RDBMS_Data:
            # use path to delete from local filesystem
            if os.path.isfile(RDBMS_Data[0][0]):
                os.remove(RDBMS_Data[0][0])

        # Check if filename already exists in folder
        fileExists = True
        currentFileName = file.filename
        while (fileExists):
            if not os.path.isfile(filename):
                fileExists = False
            else:
                split_tup = os.path.splitext(currentFileName)
                currentFileName = split_tup[0] + "_copy_" + split_tup[1]
                filename = os.path.join(
                    upload_folder, currentFileName)

        file.save(filename)
        # return redirect(url_for('download_file', name=file.filename))
        uploadedFile = True

        if not RDBMS_Data:
            print("Database does not have this key.")
            # push to db
            cursor.execute("INSERT INTO keylist (keyID, path) VALUES (%s, %s)",
                           (key, filename,))
            cnx.commit()

        elif RDBMS_Data:
            print("Database has this key.")

            # drop from db
            cursor.execute("UPDATE keylist SET path = %s WHERE keyID = %s",
                           (filename, key,))
            cnx.commit()

    cnx.close()

    # old_memcache[key] = file

    # if file is not None:
    #     # base64_data = base64.b64encode(file)
    #     pass

    if uploadedFile:
        # Call backEnd to invalidateKey
        api_url = "http://127.0.0.1:5000/backEnd/invalidateKey/" + key

        json_acceptable_string = makeAPI_Call(api_url, "get", 5)

    response = webapp.response_class(
        response=json.dumps("OK"),
        status=200,
        mimetype='application/json'
    )
    print(response)
    return response


def makeAPI_Call(api_url: str, method: str, _timeout: int):
    """Helper function to call an API.

    Args:
        api_url (str): URL to the API function
        method (str): get, post, delete, or put
        _timeout (int): (in seconds) how long should the front end wait for a response

    Returns:
        <?>: response
    """
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36', "Upgrade-Insecure-Requests": "1",
               "DNT": "1", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.5", "Accept-Encoding": "gzip, deflate"}
    method = method.lower()
    if method == "get":
        r = requests.get(api_url, timeout=_timeout, headers=headers)
    if method == "post":
        r = requests.post(api_url, timeout=_timeout, headers=headers)
    if method == "delete":
        r = requests.delete(api_url, timeout=_timeout, headers=headers)
    if method == "put":
        r = requests.put(api_url, timeout=_timeout, headers=headers)

    json_acceptable_string = r.json()

    # print("Here is response: ", json_acceptable_string)
    return json_acceptable_string
