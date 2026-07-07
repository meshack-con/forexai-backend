import os
import unittest
from datetime import datetime
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "dummy")

from app.services.backtester import Backtester


class BacktestPayloadTests(unittest.TestCase):
    def test_save_backtest_uses_supabase_row_with_passed_validation(self):
        backtester = Backtester(account_id="acct-1", symbol="EUR/USD", timeframe="M15")
        report = type("Report", (), {})()
        report.period_start = datetime(2024, 1, 1, 0, 0, 0)
        report.period_end = datetime(2024, 1, 2, 0, 0, 0)
        report.win_rate = 60.0
        report.profit_factor = 1.5
        report.max_drawdown = 2.0
        report.sharpe_ratio = 1.2
        report.total_trades = 3
        report.winning_trades = 2
        report.losing_trades = 1
        report.trades = []
        report.report_json = lambda: {"win_rate": 60.0}

        with patch("app.services.backtester.insert_backtest_result", return_value={"id": "row-1", "passed_validation": True}) as mock_insert, \
             patch.object(backtester, "_persist_trades") as mock_persist:
            backtest_row = backtester._save_backtest(report)

        self.assertEqual(backtest_row["id"], "row-1")
        self.assertTrue(backtest_row["passed_validation"])
        mock_insert.assert_called_once()
        mock_persist.assert_called_once_with("row-1", [])


if __name__ == "__main__":
    unittest.main()
