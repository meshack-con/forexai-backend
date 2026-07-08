import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "forexai"))

from app.services.backtester import Backtester

ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"
SYMBOL = "EURUSD"
TIMEFRAME = "M15"
DAYS = 365
STRATEGY_VERSION = 4

# Based on the previous sweep, tighter SL multipliers performed better.
# Testing finer combos around and below 1.5x ATR for SL.
COMBOS = [
    (1.0, 1.5, "EURUSD_fine_1.0_1.5"),
    (1.0, 2.0, "EURUSD_fine_1.0_2.0"),
    (1.0, 2.5, "EURUSD_fine_1.0_2.5"),
    (1.25, 2.0, "EURUSD_fine_1.25_2.0"),
    (1.25, 2.5, "EURUSD_fine_1.25_2.5"),
    (1.5, 2.5, "EURUSD_fine_1.5_2.5_control"),  # re-run as control/sanity check
]


def main():
    results = []
    for sl_mult, tp_mult, label in COMBOS:
        print(f"\n=== Running SL={sl_mult}x ATR / TP={tp_mult}x ATR ({label}) ===")
        backtester = Backtester(
            account_id=ACCOUNT_ID,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            strategy_version=STRATEGY_VERSION,
            label=label,
            sl_atr_mult=sl_mult,
            tp_atr_mult=tp_mult,
        )
        try:
            result = backtester.run(days=DAYS)
            report = result["report"]
            row = result["backtest_row"]
            results.append(
                {
                    "label": label,
                    "rr": f"1:{round(tp_mult / sl_mult, 2)}",
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
                    "rr": f"1:{round(tp_mult / sl_mult, 2)}",
                    "total_trades": "ERR",
                    "win_rate": "ERR",
                    "profit_factor": "ERR",
                    "max_drawdown": "ERR",
                    "sharpe_ratio": "ERR",
                    "passed_validation": "ERR",
                }
            )

    print("\n\n===== FINE ATR SWEEP COMPARISON TABLE =====")
    header = f"{'Label':<28}{'R:R':<8}{'Trades':<8}{'WinRate%':<10}{'ProfitF':<9}{'MaxDD':<8}{'Sharpe':<8}{'Passed':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['label']:<28}{r['rr']:<8}{r['total_trades']!s:<8}{r['win_rate']!s:<10}"
            f"{r['profit_factor']!s:<9}{r['max_drawdown']!s:<8}{r['sharpe_ratio']!s:<8}{r['passed_validation']!s:<8}"
        )


if __name__ == "__main__":
    main()