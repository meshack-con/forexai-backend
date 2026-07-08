import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "forexai"))

from app.services.backtester import Backtester

ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"
TIMEFRAME = "M15"
DAYS = 365
STRATEGY_VERSION = 4

# The winning combo found on EURUSD
SL_MULT = 1.25
TP_MULT = 2.0
ADX_THRESHOLD = 30.0

# Test the SAME parameters on a different symbol and implicitly a
# slightly different historical window (data pulled fresh "as of today"),
# to sanity-check whether the edge generalizes or was specific to EURUSD.
SYMBOLS = [
    ("EURUSD", "EURUSD_oos_check"),
    ("GBPUSD", "GBPUSD_oos_check"),
]


def main():
    results = []
    for symbol, label in SYMBOLS:
        print(f"\n=== Out-of-sample check: {symbol} (ADX>{ADX_THRESHOLD}, SL={SL_MULT}x, TP={TP_MULT}x) ===")
        backtester = Backtester(
            account_id=ACCOUNT_ID,
            symbol=symbol,
            timeframe=TIMEFRAME,
            strategy_version=STRATEGY_VERSION,
            label=label,
            sl_atr_mult=SL_MULT,
            tp_atr_mult=TP_MULT,
            adx_threshold=ADX_THRESHOLD,
        )
        try:
            result = backtester.run(days=DAYS)
            report = result["report"]
            row = result["backtest_row"]
            results.append(
                {
                    "label": label,
                    "symbol": symbol,
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
                    "symbol": symbol,
                    "total_trades": "ERR",
                    "win_rate": "ERR",
                    "profit_factor": "ERR",
                    "max_drawdown": "ERR",
                    "sharpe_ratio": "ERR",
                    "passed_validation": "ERR",
                }
            )

    print("\n\n===== OUT-OF-SAMPLE / CROSS-SYMBOL CHECK =====")
    header = f"{'Symbol':<10}{'Trades':<8}{'WinRate%':<10}{'ProfitF':<9}{'MaxDD':<8}{'Sharpe':<8}{'Passed':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['symbol']:<10}{r['total_trades']!s:<8}{r['win_rate']!s:<10}"
            f"{r['profit_factor']!s:<9}{r['max_drawdown']!s:<8}{r['sharpe_ratio']!s:<8}{r['passed_validation']!s:<8}"
        )


if __name__ == "__main__":
    main()