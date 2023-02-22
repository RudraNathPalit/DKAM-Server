from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import os
import requests
from time import sleep
import re

DMS_HOST = '10.99.115.211'
THINGSBOARD_HOST = '10.99.115.211'
THINGSBOARD_PORT = '8080'
DMS_PORT = '5055'

proxies = {
  "http": "",
  "https": "",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"
app.config["INSTALLER"] = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'installer')
CORS(app, resources={r"/*": {"origins": "*"}})

def upload_ThingsBoard(title, version, platform, profile):
    # Get Tenant and Profile ids from DMS
    ids = requests.post(f'http://{DMS_HOST}:{DMS_PORT}/get-bkc-id', json={'profile': profile, 'platform': platform}, proxies=proxies)
    if ids.status_code != 200:
        print('Error fetching ThingsBoard credentials', flush=True)
        return False
    
    ids = ids.json()

    # Get JWT token
    url = f'http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/auth/login'
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    loginJSON = {'username': 'tenant@thingsboard.org', 'password': 'tenant'}
    response = requests.post(url, headers=headers, json=loginJSON, proxies=proxies)
    if response.status_code !=200:
        print('Error fetching JWT token', flush=True)
        return False
    
    JWT_TOKEN = response.json()['token']

    # Create package Metadata
    packageJson = {
        "additionalInfo" : {"description": f"Updates for {platform} {profile}"},
        "tenantId": {"id": ids['tenant_id'], "entityType": "TENANT"},
        "deviceProfileId": {"id": ids['profile_id'], 'entityType': "DEVICE_PROFILE"},
        "title": title,
        "version": version,
        "type": "SOFTWARE",
        "tag": f"{title} {version}",
        "fileName": f"{title}_{version}"
    }

    headers = {
        "X-Authorization": f"Bearer {JWT_TOKEN}",
        "Accept": "application/json"
    }

    # Create package container
    res = requests.post(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/otaPackage", 
                        json=packageJson, 
                        headers = headers,
                        proxies=proxies
                        )
    if res.status_code != 200:
        print('Failed to create Package container at ThingsBoard', flush=True)
        return False

    otaPackageId = res.json()["id"]["id"]
    
    # Upload Package to ThingsBoard
    uploadFile = {
            "file": ( f"{title}_{version}", 
                     open(os.path.join(app.config['INSTALLER'], f'installer_{platform}_{profile}_{version}'), 'rb'),
                     'application/octet-stream'
                    )
        }
    headers = {
        "X-Authorization": f"Bearer {JWT_TOKEN}"
        }
    
    res = requests.post(
        f'http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/otaPackage/{otaPackageId}?checksumAlgorithm=SHA256', 
        files=uploadFile, 
        headers=headers,
        proxies=proxies
        )
    if res.status_code!= 200:
        print('Error: File upload to ThingsBoard failed.', flush=True)
        return False
    return True


@app.route('/')
def hello_world():
    return 'Dynamic BKC server is running', 200

@app.route("/update-new", methods=["GET","POST"])
def updateNew():
    data = request.json
    installer_version = data['version']
    url = data['url']
    profile = data['profile']
    platform = data['platform']

    package = url.split('/')[-1]
    version = url[url.find('linux'):].split('/')[0].lstrip('linux-')
    
    
    # Generate Installer File
    with open(os.path.join(app.config['INSTALLER'], 'base_installer'), 'rt') as f:
        commands = f.read()
    commands=re.sub('SUBSTITUTE_URL', url, commands)
    commands=re.sub('SUBSTITUTE_PACKAGE', package, commands)
    commands=re.sub('SUBSTITUTE_VERSION', version, commands)

    with open(os.path.join(app.config['INSTALLER'], f'installer_{platform}_{profile}_{installer_version}'), 'wt') as f:
        f.write(commands)

    if not upload_ThingsBoard(f'{platform} {profile} Update', installer_version, platform, profile):
        return 'Failed', 501
    return 'Success', 200


if __name__=="__main__":
    app.run(host="0.0.0.0", port=5200, debug=True)