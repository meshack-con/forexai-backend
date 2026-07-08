import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "forexai"))

from app.services.backtester import Backtester

ACCOUNT_ID = "00000000-0000-0000-0000-000000000001"
SYMBOL = "EURUSD"
TIMEFRAME = "M15"
DAYS = 365
STRATEGY_VERSION = 4

# Fixed at the best ATR ratio found so far (1.25 SL / 2.0 TP, R:R 1:1.6)
SL_MULT = 1.25
TP_MULT = 2.0

# Sweep how strict the ADX trend-strength requirement is
ADX_THRESHOLDS = [20.0, 25.0, 30.0, 35.0, 40.0]


def main():
    results = []
    for adx_th in ADX_THRESHOLDS:
        label = f"EURUSD_adx_{int(adx_th)}"
        print(f"\n=== Running ADX > {adx_th} (SL={SL_MULT}x / TP={TP_MULT}x) ({label}) ===")
        backtester = Backtester(
            account_id=ACCOUNT_ID,
            symbol=SYMBOL,
            timeframe=TIMEFRAME,
            strategy_version=STRATEGY_VERSION,
            label=label,
            sl_atr_mult=SL_MULT,
            tp_atr_mult=TP_MULT,
            adx_threshold=adx_th,
        )
        try:
            result = backtester.run(days=DAYS)
            report = result["report"]
            row = result["backtest_row"]
            results.append(
                {
                    "label": label,
                    "adx_th": adx_th,
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
                    "adx_th": adx_th,
                    "total_trades": "ERR",
                    "win_rate": "ERR",
                    "profit_factor": "ERR",
                    "max_drawdown": "ERR",
                    "sharpe_ratio": "ERR",
                    "passed_validation": "ERR",
                }
            )

    print("\n\n===== ADX THRESHOLD SWEEP TABLE (SL=1.25x / TP=2.0x ATR) =====")
    header = f"{'Label':<20}{'ADX>':<7}{'Trades':<8}{'WinRate%':<10}{'ProfitF':<9}{'MaxDD':<8}{'Sharpe':<8}{'Passed':<8}"
    print(header)
    print("-" * len(header))
    for r in results:
        print(
            f"{r['label']:<20}{r['adx_th']!s:<7}{r['total_trades']!s:<8}{r['win_rate']!s:<10}"
            f"{r['profit_factor']!s:<9}{r['max_drawdown']!s:<8}{r['sharpe_ratio']!s:<8}{r['passed_validation']!s:<8}"
        )


if __name__ == "__main__":
    main()