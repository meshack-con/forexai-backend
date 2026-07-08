import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "forexai"))

from app.services.backtester import Backtester

ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"
SYMBOL = "EURUSD"
TIMEFRAME = "M15"
DAYS = 180

VERSIONS = [
    (0, "EURUSD_v0_baseline"),
    (1, "EURUSD_v1_trend"),
    (2, "EURUSD_v2_adx"),
    (3, "EURUSD_v3_atr"),
    (4, "EURUSD_v4_confirm"),
]


def main():
    results = []
    for version, label in VERSIONS:
        print(f"\n=== Running strategy_version={version} ({label}) ===")
        backtester = Backtester(
            account_id=ACCOUNT_ID,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            strategy_version=version,
            label=label,
        )
        try:
            result = backtester.run(days=DAYS)
            report = result["report"]
            row = result["backtest_row"]
            results.append(
                {
                    "label": label,
                    "total_trades": report.total_trades,
                    "win_rate": report.win_rate,
                    "profit_factor": report.profit_factor,
                    "max_drawdown": report.max_drawdown,
                    "sharpe_ratio": report.sharpe_ratio,
                    "passed_validation": row.get("passed_validation"),
                }
            )
        except Exception as e:
            print(f"FAILED for {label}: {e}")
            results.append(
                {
                    "label": label,
                    "total_trades": "ERR",
                    "win_rate": "ERR",
                    "profit_factor": "ERR",
                    "max_drawdown": "ERR",
                    "sharpe_ratio": "ERR",
                    "passed_validation": "ERR",
                }
            )

    print("\n\n===== COMPARISON TABLE =====")
    header = f"{'Label':<22}{'Trades':<8}{'WinRate%':<10}{'ProfitF':<9}{'MaxDD':<8}{'Sharpe':<8}{'Passed':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['label']:<22}{r['total_trades']!s:<8}{r['win_rate']!s:<10}"
            f"{r['profit_factor']!s:<9}{r['max_drawdown']!s:<8}{r['sharpe_ratio']!s:<8}{r['passed_validation']!s:<8}"
        )


if __name__ == "__main__":
    main()