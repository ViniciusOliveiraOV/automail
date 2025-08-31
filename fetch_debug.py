import requests, json
try:
    r = requests.post('http://127.0.0.1:5000/fetch-emails', timeout=30)
    print(json.dumps(r.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print('error', e)
