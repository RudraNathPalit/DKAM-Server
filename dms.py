from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask import jsonify, request
import os

THINGSBOARD_HOST = '10.99.115.211'
THINGSBOARD_PORT = '8080'
THINGSBOARD_MQTT_PORT = '1883'

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
app.config["MONGO_URI"] = "mongodb://10.99.115.172:27017/FDO"
app.config["SCRIPTS"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scripts')
CORS(app, resources={r"/*": {"origins": "*"}})

mongodb_client = PyMongo(app)
db = mongodb_client.db

@app.route('/device-updater', methods = ['GET', 'POST'])
def getUpdaterScript():
    return send_from_directory(app.config['SCRIPTS'], 'device_update_manager.py')

@app.route('/get-provisioner', methods = ['GET', 'POST'])
def getProvisionerScript():
    return send_from_directory(app.config['SCRIPTS'], 'provisioner.py')

@app.route('/get-bkc-id', methods = ['POST'])
def getBkcId():
    data = request.json
    response = db.deviceProfiles.find_one({'profile': data['profile'], 'platform': data['platform']}, 
        {'_id': 0, 'profile_id': 1, 'tenant_id': 1})
    if response:
        return response, 200
    return 'Not such platform-profile found', 404

@app.route('/')
def hello_world():
    return 'Success', 200


@app.route('/get-keys', methods = ["POST"])
def getKeys():
    data = request.json

    # Verify SUT
    print(data)
    if not db['ren-serv'].find_one({"guid": data['guid']}, {}):
        return {}, 401
    
    # Fetch Thingsboard Keys for required Platform and Profile
    keys = db.deviceProfiles.find_one({"platform": data['platform'], "profile": data["profile"]}, {'_id': 0, 'device-key': 1, 'device-secret': 1})
    keys['thingsboard-host'] = THINGSBOARD_HOST
    keys['thingsboard-port'] = THINGSBOARD_PORT
    keys['thingsboard-mqtt-port'] = THINGSBOARD_MQTT_PORT
    return keys, 200

if __name__ == "__main__":
    app.run(debug=True, port=5055, host="0.0.0.0") 