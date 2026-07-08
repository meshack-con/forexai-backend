from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "forexai"))

from app.services.backtester import Backtester

ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"
SYMBOL = "EURUSD"
TIMEFRAME = "M15"
STRATEGY_VERSION = 4

# The parameters that "won" the sweep on the last 365 days - we do NOT
# change these here. The whole point of this test is to check whether
# they hold up on data that had zero influence on choosing them.
SL_MULT = 1.25
TP_MULT = 2.0
ADX_THRESHOLD = 30.0

# Window A ("tuning window"): the same last 365 days used for the sweep.
# Window B ("out-of-sample window"): an OLDER, non-overlapping block of
# time that was never looked at while choosing SL_MULT/TP_MULT/ADX_THRESHOLD.
TUNING_DAYS = 365
OOS_DAYS = 240  # length of the older test block
OOS_END = datetime.utcnow() - timedelta(days=TUNING_DAYS)  # ends where tuning window begins


def run_one(label: str, days: int, date_to):
    print(f"\n=== {label} | days={days} | date_to={date_to} ===")
    backtester = Backtester(
        account_id=ACCOUNT_ID,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        strategy_version=STRATEGY_VERSION,
        label=label,
        sl_atr_mult=SL_MULT,
        tp_atr_mult=TP_MULT,
        adx_threshold=ADX_THRESHOLD,
    )
    try:
        result = backtester.run(days=days, date_to=date_to)
        report = result["report"]
        row = result["backtest_row"]
        return {
            "label": label,
            "total_trades": report.total_trades,
            "win_rate": report.win_rate,
            "profit_factor": report.profit_factor,
            "max_drawdown": report.max_drawdown,
            "sharpe_ratio": report.sharpe_ratio,
            "passed_validation": row.get("passed_validation"),
        }
    except Exception as e:
        print(f"FAILED for {label}: {e}")
        return {
            "label": label,
            "total_trades": "ERR",
            "win_rate": "ERR",
            "profit_factor": "ERR",
            "max_drawdown": "ERR",
            "sharpe_ratio": "ERR",
            "passed_validation": "ERR",
        }


def main():
    results = []
    # Re-confirm the tuning-window result (should match earlier run)
    results.append(run_one("EURUSD_tuning_window_365d", TUNING_DAYS, date_to=None))
    # The real test: fixed params on an OLDER block never used for tuning
    results.append(run_one("EURUSD_OOS_older_240d", OOS_DAYS, date_to=OOS_END))

    print("\n\n===== TIME-SPLIT OUT-OF-SAMPLE VALIDATION =====")
    header = f"{'Label':<28}{'Trades':<8}{'WinRate%':<10}{'ProfitF':<9}{'MaxDD':<8}{'Sharpe':<8}{'Passed':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['label']:<28}{r['total_trades']!s:<8}{r['win_rate']!s:<10}"
            f"{r['profit_factor']!s:<9}{r['max_drawdown']!s:<8}{r['sharpe_ratio']!s:<8}{r['passed_validation']!s:<8}"
        )

    print(
        "\nNote: 'OOS_older_240d' is the meaningful test. If its profit_factor and "
        "win_rate collapse compared to the tuning window, the strategy is likely "
        "overfit to the specific 365-day period and should NOT be trusted for demo/live."
    )


if __name__ == "__main__":
    main()