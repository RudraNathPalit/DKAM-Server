from paho.mqtt.client import Client
from time import sleep
from json import dumps, loads
from zlib import crc32
from hashlib import sha256, sha384, sha512, md5
from mmh3 import hash, hash128
from threading import Thread
import subprocess
import sys
import requests
import argparse
import os

# Debug
MESSENGER_URL = 'http://10.99.115.211:5300'
proxies = {
   'http': '',
   'https': '',
}

# Keys
SW_CHECKSUM_ATTR = "sw_checksum"
SW_CHECKSUM_ALG_ATTR = "sw_checksum_algorithm"
SW_SIZE_ATTR = "sw_size"
SW_TITLE_ATTR = "sw_title"
SW_VERSION_ATTR = "sw_version"
SW_STATE_ATTR = "sw_state"

REQUIRED_SHARED_KEYS = f"{SW_CHECKSUM_ATTR},{SW_CHECKSUM_ALG_ATTR},{SW_SIZE_ATTR},{SW_TITLE_ATTR},{SW_VERSION_ATTR}"
THINGSBOARD_HOST = ''
THINGSBOARD_MQTT_PORT = ''
THINGSBOARD_HTTP_PORT = ''
TOKEN = ''

def verify_checksum(software_data, checksum_alg, checksum):
    if software_data is None:
        print("Error: No Software was received!", flush=True)
        return False
    
    if checksum is None:
        print("Error: No Checksum was provided!", flush=True)
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
        print("Error. Unsupported checksum algorithm.", flush=True)
    return checksum_of_received_software == checksum

def set_client_attributes(software_info):
    current_software_info = {
        SW_TITLE_ATTR: str(software_info.get(SW_TITLE_ATTR)),
        SW_VERSION_ATTR: str(software_info.get(SW_VERSION_ATTR)),
        SW_CHECKSUM_ATTR: str(software_info.get(SW_CHECKSUM_ATTR)),
        SW_CHECKSUM_ALG_ATTR: str(software_info.get(SW_CHECKSUM_ALG_ATTR)),
        SW_SIZE_ATTR: str(software_info.get(SW_SIZE_ATTR))
    }
    response = requests.post(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_HTTP_PORT}/api/v1/{TOKEN}/attributes",json=current_software_info, proxies=proxies)
    return response.status_code == 200

def upgrade(filename, version_from, version_to):
    err = subprocess.run(['sudo', 'bash', filename], stderr=subprocess.PIPE).stderr.decode('utf-8')
    requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': f'Device updated from version {version_from} to {version_to}'}, proxies=proxies)
    print(f'Device updated from version {version_from} to {version_to}', flush=True)
    try:
        os.remove(filename)
    except:
        pass
    
    if err!= '':
        print(err, flush=True)
        return False
    return True

def get_current_software_info():
    response = requests.get(f"http://{THINGSBOARD_HOST}:{THINGSBOARD_HTTP_PORT}/api/v1/{TOKEN}/attributes", params={"clientKeys": REQUIRED_SHARED_KEYS}, proxies=proxies)
    if response.status_code == 200:
        return loads(response.text).get('client')
    else:
        return None
    
class softwareClient(Client):
    def __init__(self):
        super().__init__()
        self.on_connect = self.__on_connect
        self.on_message = self.__on_message

        self.__request_id = 0
        self.__software_request_id = 0
        
        client_software_attribute = get_current_software_info()
        self.current_software_info = {
            "current_" + SW_TITLE_ATTR: client_software_attribute[SW_TITLE_ATTR],
            "current_" + SW_VERSION_ATTR: str(client_software_attribute[SW_VERSION_ATTR])
            }
        self.software_data = b''
        self.__target_software_length = 0
        self.software_received = False
        self.__updating_thread = Thread(target=self.__update_thread, name="Updating thread")
        self.__updating_thread.daemon = True
        self.__updating_thread.start()

    def __on_connect(self, client, userdata, flags, result_code, *extra_params):
        self.subscribe("v1/devices/me/attributes/response/+")
        self.subscribe("v1/devices/me/attributes")
        self.subscribe("v2/sw/response/+")
        self.send_telemetry(self.current_software_info)
        sleep(2)

        print('Device connected to Thingsboard', flush=True)
        self.request_software_info()

    def __on_message(self, client, userdata, msg):
        update_response_pattern = "v2/sw/response/" + str(self.__software_request_id) + "/chunk/"
        if msg.topic.startswith("v1/devices/me/attributes"):
            software_info = loads(msg.payload)
            if "/response/" in msg.topic:
                self.latest_software_info = software_info.get("shared", {}) if isinstance(software_info, dict) else {}
            else:
                self.latest_software_info = software_info 
            if (self.latest_software_info.get(SW_VERSION_ATTR) is not None and self.latest_software_info.get(SW_VERSION_ATTR) != self.current_software_info.get("current_" + SW_VERSION_ATTR)) or \
                    (self.latest_software_info.get(SW_TITLE_ATTR) is not None and self.latest_software_info.get(SW_TITLE_ATTR) != self.current_software_info.get("current_" + SW_TITLE_ATTR)):
                requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'New Updates available!'}, proxies=proxies)
                print("New Updates available!", flush=True)

                requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Downloading Updates...'}, proxies=proxies)
                self.current_software_info[SW_STATE_ATTR] = "DOWNLOADING"
                self.send_telemetry(self.current_software_info)
                sleep(1)

                self.__software_request_id = self.__software_request_id + 1
                self.__target_software_length = self.latest_software_info[SW_SIZE_ATTR]
                self.get_software()

        elif msg.topic.startswith(update_response_pattern):
            software_data = msg.payload
            self.software_data = software_data
            if len(self.software_data) == self.__target_software_length:
                self.process_software()
            else:
                self.get_software()

    def process_software(self):
        requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Updates downloaded'}, proxies=proxies)
        self.current_software_info[SW_STATE_ATTR] = "DOWNLOADED"
        self.send_telemetry(self.current_software_info)
        sleep(1)
        verification_result = verify_checksum(self.software_data, self.latest_software_info.get(SW_CHECKSUM_ALG_ATTR), self.latest_software_info.get(SW_CHECKSUM_ATTR))
        requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Verifying Checksum...'}, proxies=proxies)
        if verification_result:
            print("Checksum verified!", flush=True)
            self.current_software_info[SW_STATE_ATTR] = "VERIFIED"
            self.send_telemetry(self.current_software_info)
            sleep(1)
        else:
            print("Checksum verification failed!", flush=True)
            self.current_software_info[SW_STATE_ATTR] = "FAILED"
            self.send_telemetry(self.current_software_info)
            self.request_software_info()
            return
        self.software_received = True

    def get_software(self):
        payload = '' 
        self.publish(f"v2/sw/request/{self.__software_request_id}/chunk/0", payload=payload, qos=1)

    def send_telemetry(self, telemetry):
        return self.publish("v1/devices/me/telemetry", dumps(telemetry), qos=1)

    def request_software_info(self):
        self.__request_id = self.__request_id + 1
        self.publish(f"v1/devices/me/attributes/request/{self.__request_id}", dumps({"sharedKeys": REQUIRED_SHARED_KEYS}))

    def __update_thread(self):
        while True:
            if self.software_received:
                requests.post(f'{MESSENGER_URL}/update-data', json={'source': 'thingsboard', 'msg': 'Updating Device...'}, proxies=proxies)
                self.current_software_info[SW_STATE_ATTR] = "UPDATING"
                self.send_telemetry(self.current_software_info)
                sleep(1)

                with open(self.latest_software_info.get(SW_TITLE_ATTR), "wb") as software_file:
                    software_file.write(self.software_data)

                upgrade(self.latest_software_info.get(SW_TITLE_ATTR), self.current_software_info.get("current_" + SW_VERSION_ATTR), self.latest_software_info.get(SW_VERSION_ATTR))

                self.current_software_info = {
                    "current_" + SW_TITLE_ATTR: self.latest_software_info.get(SW_TITLE_ATTR),
                    "current_" + SW_VERSION_ATTR: self.latest_software_info.get(SW_VERSION_ATTR),
                    SW_STATE_ATTR: "UPDATED"
                }
                self.send_telemetry(self.current_software_info)

                self.software_received = False
                if set_client_attributes(self.latest_software_info):
                    print('Current client attributes updated', flush=True)
                sleep(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default = '10.99.115.211', help='Enter Thingsboard Host')
    parser.add_argument("--http", default = '8080', help='Enter Thingsboard HTTP port')
    parser.add_argument("--mqtt", default = '1883', help='Enter Thingsboard MQTT port')
    parser.add_argument("--token", default = 'AbJHktIFFy5DPf8fu86t', help='Enter device token')
    args = parser.parse_args()

    THINGSBOARD_HOST = args.host
    THINGSBOARD_MQTT_PORT = args.mqtt
    THINGSBOARD_HTTP_PORT = args.http
    TOKEN = args.token

    client = softwareClient()
    client.username_pw_set(TOKEN)
    THINGSBOARD_MQTT_PORT = THINGSBOARD_MQTT_PORT if isinstance(THINGSBOARD_MQTT_PORT, int) else int(THINGSBOARD_MQTT_PORT)
    client.connect(THINGSBOARD_HOST, THINGSBOARD_MQTT_PORT)
    client.loop_forever()