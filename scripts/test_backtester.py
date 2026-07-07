import traceback
from app.services.backtester import Backtester

try:
    b = Backtester(account_id='your-account-id', symbol='EUR/USD', timeframe='M15')
    result = b.run()
    print('OK', result)
except Exception:
    traceback.print_exc()
