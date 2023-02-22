import subprocess
import argparse
from time import sleep
from zlib import crc32
from hashlib import sha256, sha384, sha512, md5
import os
import sys

try:
    import requests
except:
    err = subprocess.run([sys.executable, '-m', 'pip', 'install', 'requests'], stderr=subprocess.PIPE).stderr.decode('utf-8')
    if err !='':
        print('Error installing required packages.')
        print(err)
        exit(2)
    import requests

try:
    from mmh3 import hash, hash128
except:
    err = subprocess.run([sys.executable, '-m', 'pip', 'install', 'mmh3'], stderr=subprocess.PIPE).stderr.decode('utf-8')
    if err !='':
        print('Error installing required packages')
        print(err)
        exit(3)
    from mmh3 import hash, hash128

# Debug
MESSENGER_URL = 'http://10.99.115.211:5300'

# CLOUD IPs
THINGSBOARD_HOST = ''
THINGSBOARD_PORT = ''
DMS_HOST = ''
DMS_PORT = ''
TOKEN = ''
THINGSBOARD_MQTT_PORT = ''

# SOFTWARE Versioning CONSTANTS
SW_CHECKSUM_ATTR = "sw_checksum"
SW_CHECKSUM_ALG_ATTR = "sw_checksum_algorithm"
SW_SIZE_ATTR = "sw_size"
SW_TITLE_ATTR = "sw_title"
SW_VERSION_ATTR = "sw_version"
SW_STATE_ATTR = "sw_state"

REQUIRED_SHARED_KEYS = [SW_CHECKSUM_ATTR, SW_CHECKSUM_ALG_ATTR, SW_SIZE_ATTR, SW_TITLE_ATTR, SW_VERSION_ATTR]


# Command colors
BLUE = '\033[94m'
CYAN = '\033[96m'
GREEN = '\033[92m'
WARNING = '\033[93m'
ENDC = '\033[0m'

def getProvisioningKeys(board, GUID, profile):
# Fetch Secret key from Database
    response = requests.post(f'{DMS_HOST}:{DMS_PORT}/get-keys', json = {'platform': board, 'guid': GUID, 'profile': profile})
    if response.status_code != 200:
        return None
    return response.json()

# Register device to ThingsBoard
def registerDevice(device_key, device_secret, board, guid):
    PROVISION_REQUEST = {
        "deviceName": f"{board}_{guid}",
        "provisionDeviceKey": device_key,
        "provisionDeviceSecret": device_secret
    }

    response = requests.post(f'http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/provision', json = PROVISION_REQUEST)
    if response.status_code != 200:
        print(WARNING+'Error: Failed to register device to ThingsBoard.'+ENDC)
        return None
    return response.json().get("credentialsValue")

def send_telemetry(telemetry):
    requests.post(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/{TOKEN}/telemetry",json=telemetry)

def get_software_info():
    response = requests.get(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/{TOKEN}/attributes", params={"sharedKeys": REQUIRED_SHARED_KEYS})
    if response.status_code == 200:
        return response.json().get("shared", {})
    else:
        return None

def verify_checksum(software_data, checksum_alg, checksum):
    if software_data is None:
        print(WARNING+"Error: No Software was received!"+ENDC)
        return False
    if checksum is None:
        print(WARNING+"Error: No Checksum was provided!"+ENDC)
        return False
    checksum_of_received_software = None
    if checksum_alg.lower() == "sha256":
        checksum_of_received_software = sha256(software_data).digest().hex()
    elif checksum_alg.lower() == "sha384":
        checksum_of_received_software = sha384(software_data).digest().hex()
    elif checksum_alg.lower() == "sha512":
        checksum_of_received_software = sha512(software_data).digest().hex()
    elif checksum_alg.lower() == "md5":
        checksum_of_received_software = md5(software_data).digest().hex()
    elif checksum_alg.lower() == "murmur3_32":
        reversed_checksum = f'{hash(software_data, signed=False):0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_software = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    elif checksum_alg.lower() == "murmur3_128":
        reversed_checksum = f'{hash128(software_data, signed=False):0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_software = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    elif checksum_alg.lower() == "crc32":
        reversed_checksum = f'{crc32(software_data) & 0xffffffff:0>2X}'
        if len(reversed_checksum) % 2 != 0:
            reversed_checksum = '0' + reversed_checksum
        checksum_of_received_software = "".join(reversed([reversed_checksum[i:i+2] for i in range(0, len(reversed_checksum), 2)])).lower()
    else:
        print("Client error. Unsupported checksum algorithm.")
    return checksum_of_received_software == checksum

def set_client_attributes(software_info):
    current_software_info = {
        SW_TITLE_ATTR: str(software_info.get(SW_TITLE_ATTR)),
        SW_VERSION_ATTR: str(software_info.get(SW_VERSION_ATTR)),
        SW_CHECKSUM_ATTR: str(software_info.get(SW_CHECKSUM_ATTR)),
        SW_CHECKSUM_ALG_ATTR: str(software_info.get(SW_CHECKSUM_ALG_ATTR)),
        SW_SIZE_ATTR: str(software_info.get(SW_SIZE_ATTR))
    }
    response = requests.post(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/{TOKEN}/attributes",json=current_software_info)
    return response.status_code == 200

def get_software(sw_info):
    software_data = b''
    params = {"title": sw_info.get(SW_TITLE_ATTR),
                "version": sw_info.get(SW_VERSION_ATTR),
                "size": sw_info.get(SW_SIZE_ATTR, 0),
                "chunk": 0
            }
    response = requests.get(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/{TOKEN}/software", params=params)
    if response.status_code != 200:
        print(WARNING+"Error received updates:"+ENDC)
        response.raise_for_status()
        return
    software_data = software_data + response.content
    return software_data

def provisionAutoUpdate():
    print('\n')
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Activating Auto Update...'})
    print(CYAN+'Activating Auto Update...'+ENDC)
    response = requests.get(f'{DMS_HOST}:{DMS_PORT}/device-updater')
    if response.status_code != 200:
        print(WARNING+'Error: Failed to provision auto update feature'+ENDC)
    else:
        open("device_update_manager.py", "wb").write(response.content)
        fout = open('sensitive/auto_update_log.txt', 'w')
        process_pid = subprocess.Popen(['sudo', sys.executable, 'device_update_manager.py', 
                            '--host', THINGSBOARD_HOST, 
                            '--http', THINGSBOARD_PORT, 
                            '--mqtt', THINGSBOARD_MQTT_PORT, 
                            '--token', TOKEN], 
                            stdout=fout,
                            stderr=fout, 
                            preexec_fn=os.setpgrp).pid
        sleep(2)
        requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': f'Auto update activated with PID {process_pid}'})
        print(f'Auto update activated with PID {process_pid}')
            
def upgrade(filename):
    err = subprocess.run(['sudo', 'bash', filename], stderr=subprocess.PIPE).stderr.decode('utf-8')
    if err!= '':
        print(err)
        return False
    return True

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default = '10.99.115.211', help='Enter DMS HOST IP')
    parser.add_argument("--port", default = '5055', help='Enter DMS Port')
    args = parser.parse_args()

    # Set DMS Config
    DMS_HOST = f'http://{args.host}'
    DMS_PORT = args.port

    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'dms', 'msg': 'Installing setup script...'})
    print('Initiating Setup Script...')

    # Verify Board GUID
    with open('sensitive/ov.tpm','r') as f:
        secure_data = f.read().split(':')
        GUID = secure_data[4]
        board = secure_data[6]

    #  Get secure Provisioning Keys
    profile = input(f'Enter Profile for device {board}_{GUID}:\t').upper()

    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'dms', 'msg': 'Fetching ThingsBoard Provisioning keys...'})
    print('Fetching ThingsBoard Provisioning keys from DMS...')
    keys = getProvisioningKeys(board, GUID, profile)
    sleep(1)
    if not keys:
        print(WARNING+'Error: Failed to fetch Device provisioning keys.'+ENDC)
        exit(1)
    
    # Set ThingsBoard Credentials
    THINGSBOARD_HOST = keys['thingsboard-host']
    THINGSBOARD_PORT = keys['thingsboard-port']
    THINGSBOARD_MQTT_PORT = keys['thingsboard-mqtt-port']

    print('\n')
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Device connecting to Thingsboard...'})
    print(CYAN+'Connecting to Thingsboard...'+ENDC)

    sleep(1)
    # Register Device
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Registering device...'})
    print('Registering device...')
    TOKEN = registerDevice(keys['device-key'], keys['device-secret'], board, GUID)
    if not TOKEN:
        print(WARNING+'Error: Failed to fetch device provisioning token.'+ENDC)
        exit(1)

    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Saving secure Authentication token...'})
    print('Saving secure Authentication token...')
    with open('sensitive/access-token', 'w') as f:
        f.write(TOKEN)
    print('Secure Authentication token saved...')

    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Success: Device registered to Thingsboard!!'})
    print(GREEN+'Success: Device registered to Thingsboard'+ENDC)
    print('\n')
    
    sleep(3)

    # #############################################
    # Completed: Device Registration to ThingsBoard
    # #############################################
    current_software_info = {
        "current_sw_title": None,
        "current_sw_version": None
    }
    # print(f"Sending current software details to {THINGSBOARD_HOST}:{THINGSBOARD_PORT}/api/v1/{TOKEN}/software...")
    send_telemetry(current_software_info)
    sleep(1)

    
    # Check for Updated Software Bundle
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': "Checking for Updates from ThingsBoard..."})
    print(CYAN+"Checking for Updates from ThingsBoard..." + ENDC)
    software_info = get_software_info()
    if not software_info:
        print(WARNING+'Error: Failed to communicate with ThingsBoard'+ENDC)
        exit(1)

    elif (software_info.get(SW_VERSION_ATTR) is None or software_info.get(SW_VERSION_ATTR) == current_software_info.get("current_" + SW_VERSION_ATTR)) \
            or (software_info.get(SW_TITLE_ATTR) is None or software_info.get(SW_TITLE_ATTR) == current_software_info.get("current_" + SW_TITLE_ATTR)):
        requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'No Update available!'})
        print('No Update available!')
        provisionAutoUpdate()
        exit(0)

    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': "New Updates available!"})
    print(BLUE+"New Updates available!"+ENDC)

    #  Start Downloading Updated Software
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Downloading Update Installation script...'})
    print('Downloading Update Installation script...')
    current_software_info[SW_STATE_ATTR] = "DOWNLOADING"
    sleep(1)
    send_telemetry(current_software_info)
    software_data = get_software(software_info)
    
    # Complete Downloading Software Data
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Completed downloading Update Installation Script'})
    print('Completed downloading Update Installation Script')
    current_software_info[SW_STATE_ATTR] = "DOWNLOADED"
    sleep(1)
    send_telemetry(current_software_info)

    # Verify File Checksum
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Verifying Update Integrity...'})
    print('Verifying Update Integrity...')
    verification_result = verify_checksum(software_data, software_info.get(SW_CHECKSUM_ALG_ATTR), software_info.get(SW_CHECKSUM_ATTR))
    if verification_result:
        print(GREEN+"Update Integrity verified!"+ENDC)
        current_software_info[SW_STATE_ATTR] = "VERIFIED"
        sleep(1)
        send_telemetry(current_software_info)
    else:
        print(WARNING+"Error: Failed to verify Update Integrity."+ENDC)
        current_software_info[SW_STATE_ATTR] = "FAILED"
        sleep(1)
        send_telemetry(current_software_info)
        exit(4)

    # Save Data to file
    with open(software_info.get(SW_TITLE_ATTR), "wb") as software_file:
        software_file.write(software_data)

    # Start Updates
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Invoking Update Installtion Script...'})
    print('Invoking Update Installtion Script...')
    current_software_info[SW_STATE_ATTR] = "UPDATING"
    sleep(1)
    send_telemetry(current_software_info)

    if not upgrade(software_info.get(SW_TITLE_ATTR)):
        print(WARNING+'Error: Failed to Upgrade System'+ENDC)
        exit(5)

    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Success: System updated!!'})
    print(GREEN+'Success: System updated!'+ENDC)
    current_software_info = {
            "current_" + SW_TITLE_ATTR: software_info.get(SW_TITLE_ATTR),
            "current_" + SW_VERSION_ATTR: software_info.get(SW_VERSION_ATTR),
            SW_STATE_ATTR: "UPDATED"
    }
    sleep(1)
    send_telemetry(current_software_info)
    print('\n')
    print(CYAN+'Carrying out clean-up and maintenance activity...'+ENDC)
    print('Removing Installer Scripts')
    os.remove(software_info.get(SW_TITLE_ATTR))

    # Set Client Attribute
    if not set_client_attributes(software_info):
        print(WARNING+'Error: Failed to update Device Update Status'+ENDC)
        exit(6)
    provisionAutoUpdate()
    sleep(2)
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Done!'})
    print(GREEN+'Done!'+ENDC)