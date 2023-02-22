from flask import Flask, render_template, request
from flask_socketio import SocketIO
from flask_cors import CORS
from threading import Lock

FDO_messageLog = ''
DMS_messageLog = ''
THINGSBOARD_messageLog = ''
BKC_messageLog = ''

app = Flask(__name__, template_folder="./templates", static_url_path='', static_folder='./templates')
app.config["SECRET_KEY"] = "secret!"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000  # 16MB

CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/update-data', methods = ['POST'])
def update_data():
    global FDO_messageLog
    global DMS_messageLog
    global THINGSBOARD_messageLog
    global BKC_messageLog

    data = request.json
    if data['source'] == 'fdo':
        FDO_messageLog = f"{FDO_messageLog}{data['msg']}<br>"
        socketio.emit('update-fdo', {'data': FDO_messageLog})

    elif data['source'] == 'dms':
        DMS_messageLog = f"{DMS_messageLog}{data['msg']}<br>"
        socketio.emit('update-dms', {'data': DMS_messageLog})

    elif data['source'] == 'thingsboard':
        THINGSBOARD_messageLog = f"{THINGSBOARD_messageLog}{data['msg']}<br>"
        socketio.emit('update-thingsboard', {'data': THINGSBOARD_messageLog})

    elif data['source'] == 'bkc':
        BKC_messageLog = f"{BKC_messageLog}{data['msg']}<br>"
        socketio.emit('update-bkc', {'data': BKC_messageLog})

    return 'Success', 200

@app.route('/clear-data', methods = ['POST'])
def clear_data():
    global FDO_messageLog
    global DMS_messageLog
    global THINGSBOARD_messageLog
    global BKC_messageLog

    data = request.json
    
    if data['source'] == 'fdo':
        FDO_messageLog = ""

    elif data['source'] == 'dms':
        DMS_messageLog = ""

    elif data['source'] == 'thingsboard':
        THINGSBOARD_messageLog = ""

    elif data['source'] == 'bkc':
        BKC_messageLog = ""
    
    return 'Success', 200

@app.route('/')
def hello_world():
    return render_template("dashboard.html")

@socketio.on('connect')
def connect():
    global FDO_messageLog
    global DMS_messageLog
    global THINGSBOARD_messageLog
    global BKC_messageLog

    FDO_messageLog = ''
    DMS_messageLog = ''
    THINGSBOARD_messageLog = ''
    BKC_messageLog = ''
    print('Client connected')

@socketio.on('disconnect')
def disconnect():
    global FDO_messageLog
    global DMS_messageLog
    global THINGSBOARD_messageLog
    global BKC_messageLog

    FDO_messageLog = ''
    DMS_messageLog = ''
    THINGSBOARD_messageLog = ''
    BKC_messageLog = ''
    print('Client disconnected',  request.sid)

if __name__ == "__main__":
    socketio.run(app, debug=True, port=5300, host="0.0.0.0", use_reloader=False)