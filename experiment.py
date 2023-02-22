import requests

BKC_HOST = '10.99.115.211'
BKC_PORT  = '5200'
proxies = {
  "http": "",
  "https": "",
}
data = {
    'version': '2.3',
    'profile': 'RT',
    'platform': 'ADL-PS',
    'url': "http://oak-07.jf.intel.com/ikt_kernel_deb_repo/pool/main/l/linux-5.15.71-lts-bullpen-230103t044020z/linux-image-5.15.71-lts-bullpen-230103t044020z-dbg_5.15.71-8_amd64.deb"
}
response = requests.post(f'http://{BKC_HOST}:{BKC_PORT}/update-new', json=data, proxies=proxies)
print(response.status_code, response.content)