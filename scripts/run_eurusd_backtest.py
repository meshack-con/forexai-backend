import sys
from pathlib import Path
# ensure project root is on sys.path so scripts run without PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from app.services.backtester import Backtester

load_dotenv()

account_id = '00000000-0000-0000-0000-000000000001'
symbol = 'EUR/USD'
timeframe = 'M15'

def main():
    backtester = Backtester(account_id=account_id, symbol=symbol, timeframe=timeframe)
    result = backtester.run(days=180)
    backtest_row = result['backtest_row']
    report = result['report']

    print('=== Backtest Result ===')
    print('symbol:', symbol)
    print('timeframe:', timeframe)
    print('period_start:', report.period_start)
    print('period_end:', report.period_end)
    print('total_trades:', report.total_trades)
    print('win_rate:', report.win_rate)
    print('profit_factor:', report.profit_factor)
    print('max_drawdown:', report.max_drawdown)
    print('sharpe_ratio:', report.sharpe_ratio)
    print('passed_validation:', backtest_row.get('passed_validation'))
    print('backtest_id:', backtest_row.get('id'))
    print('raw backtest row:', backtest_row)

if __name__ == '__main__':
    main()
