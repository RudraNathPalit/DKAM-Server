from flask import Flask, jsonify,request
from flask_pymongo import PyMongo
from flask_cors import CORS

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
app.config["MONGO_URI"] = "mongodb://10.99.115.172:27017/FDO"
CORS(app, resources={r"/*": {"origins": "*"}})

mongodb_client = PyMongo(app)
db = mongodb_client.db

@app.route('/')
def hello_world():
    return 'Rendezvous server is running', 200

@app.route("/verify", methods=["GET","POST"])
def verify():
    f = request.json    
    print (f['ov'], flush=True)
    print (f['guid'], flush=True)
    if db['ren-serv'].find_one({'ov':f['ov'], 'guid':f['guid']}, {}):
        return jsonify({"auth-status":'Authenticated', "dms-ip":"10.99.115.211", "dms-port":"5055"})
    else:
        return jsonify({"auth-status":None, "dms-ip":None, "dms-port":None})
    
if __name__=="__main__":
    app.run(host="0.0.0.0", port=5100, debug=True)