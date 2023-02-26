import requests

BKC_HOST = '10.99.115.211'
BKC_PORT  = '5200'

# LTS kernel 5.15.85
url = 'http://oak-07.jf.intel.com/ikt_kernel_deb_repo/pool/main/l/linux-5.15.85-lts-bullpen-230113t035248z/linux-image-5.15.85-lts-bullpen-230113t035248z_5.15.85-16_amd64.deb'

proxies = {
  "http": "",
  "https": "",
}
data = {
    'version': '2.3',
    'profile': 'RT',
    'platform': 'ADL-PS',
    'url': url
}
response = requests.post(f'http://{BKC_HOST}:{BKC_PORT}/update-new', json=data, proxies=proxies)
print(response.status_code, response.content)