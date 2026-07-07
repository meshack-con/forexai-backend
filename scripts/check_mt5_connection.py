import sys
from pathlib import Path
# ensure project root is on sys.path so scripts run without PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mt5_client import mt5_client
import MetaTrader5 as mt5

print('Connecting with mt5_client...')
try:
    client = mt5_client.connect()
    print('mt5_client.connect() returned', client)
    account = mt5.account_info()
    print('account_info:', account)
    if account is not None:
        print('login:', account.login)
        print('balance:', account.balance)
        print('equity:', account.equity)
        print('leverage:', account.leverage)
    else:
        print('No account info available')
finally:
    try:
        mt5.shutdown()
        print('mt5.shutdown() called')
    except Exception as e:
        print('shutdown error', e)
