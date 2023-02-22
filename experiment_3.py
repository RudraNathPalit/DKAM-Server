import requests
data = {
    'source': 'bkc',
    'msg': 'Wefewfdfdsdsfc'
}
proxies = {
   'http': '',
   'https': '',
}
response = requests.post('http://10.99.115.211:5300/update-data', json=data, proxies=proxies)