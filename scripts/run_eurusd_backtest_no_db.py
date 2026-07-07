import sys
from pathlib import Path
# ensure project root is on sys.path so scripts run without PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from unittest.mock import patch

from app.services.backtester import Backtester

load_dotenv()

account_id = '00000000-0000-0000-0000-000000000001'
symbol = 'EUR/USD'
timeframe = 'M15'


def fake_insert_backtest_result(payload):
    passed_validation = payload.get('win_rate', 0.0) >= 55.0
    return {
        'id': 'local-backtest-1',
        'account_id': payload.get('account_id'),
        'symbol': payload.get('symbol'),
        'period_start': payload.get('period_start'),
        'period_end': payload.get('period_end'),
        'win_rate': payload.get('win_rate'),
        'profit_factor': payload.get('profit_factor'),
        'max_drawdown': payload.get('max_drawdown'),
        'sharpe_ratio': payload.get('sharpe_ratio'),
        'total_trades': payload.get('total_trades'),
        'winning_trades': payload.get('winning_trades'),
        'losing_trades': payload.get('losing_trades'),
        'report_json': payload.get('report_json'),
        'passed_validation': passed_validation,
    }


def fake_insert_trade(payload):
    return payload


def main():
    backtester = Backtester(account_id=account_id, symbol=symbol, timeframe=timeframe)
    with patch('app.services.backtester.insert_backtest_result', side_effect=fake_insert_backtest_result), \
         patch('app.services.backtester.insert_trade', side_effect=fake_insert_trade):
        result = backtester.run(days=180)

    report = result['report']
    backtest_row = result['backtest_row']

    print('=== EUR/USD Backtest (180 days) ===')
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
    print('trades_saved:', len(report.trades))


if __name__ == '__main__':
    main()
