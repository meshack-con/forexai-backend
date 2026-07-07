import sys
from pathlib import Path
# ensure project root is on sys.path so scripts run without PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import traceback
from app.services.backtester import Backtester

try:
    b = Backtester(account_id='your-account-id', symbol='EUR/USD', timeframe='M15')
    result = b.run()
    print('OK', result)
except Exception:
    traceback.print_exc()
