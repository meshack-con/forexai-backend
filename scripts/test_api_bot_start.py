import sys
from pathlib import Path
# ensure project root is on sys.path so scripts run without PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
import urllib.request
import urllib.error

url = 'http://127.0.0.1:8000/api/bot/start'
data = json.dumps({'account_id': 'your-account-id', 'symbol': 'EUR/USD', 'timeframe': 'M15'}).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('STATUS', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP', e.code)
    print(e.read().decode())
except Exception as exc:
    print('ERR', exc)
