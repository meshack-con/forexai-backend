from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.core.logger import logger
from app.models.db import insert_backtest_result, insert_trade


class BacktestReport:
    def __init__(self, symbol: str, period_start: datetime, period_end: datetime, trades: list[dict[str, Any]]):
        self.symbol = symbol
        self.period_start = period_start
        self.period_end = period_end
        self.trades = trades

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def winning_trades(self) -> int:
        return sum(1 for trade in self.trades if trade["profit_loss"] > 0)

    @property
    def losing_trades(self) -> int:
        return sum(1 for trade in self.trades if trade["profit_loss"] <= 0)

    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return round(self.winning_trades / self.total_trades * 100, 2)

    @property
    def profit_factor(self) -> float:
        wins = sum(trade["profit_loss"] for trade in self.trades if trade["profit_loss"] > 0)
        losses = abs(sum(trade["profit_loss"] for trade in self.trades if trade["profit_loss"] <= 0))
        return round(wins / losses, 2) if losses > 0 else float("inf")

    @property
    def max_drawdown(self) -> float:
        returns = [trade["profit_loss"] for trade in self.trades]
        if not returns:
            return 0.0
        equity = np.cumsum(returns)
        peak = np.maximum.accumulate(equity)
        drawdown = peak - equity
        return round(float(np.max(drawdown)), 2)

    @property
    def sharpe_ratio(self) -> float:
        returns = np.array([trade["profit_loss"] for trade in self.trades], dtype=float)
        if len(returns) < 2 or np.std(returns) == 0:
            return 0.0
        return round(float(np.mean(returns) / np.std(returns)) * np.sqrt(252), 2)

    def report_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }


class Backtester:
    def __init__(
        self,
        account_id: str,
        symbol: str,
        timeframe: str = "M15",
        strategy_version: int = 0,
        label: str | None = None,
    ):
        self.account_id = account_id
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy_version = strategy_version
        # `label` is what gets stored in backtest_results/trades.symbol so that
        # different strategy versions on the same real MT5 symbol can be
        # compared side by side without overwriting each other's data.
        # `self.symbol` is still used for the real MT5 lookup.
        self.label = label or symbol

    def _symbol_to_mt5(self) -> str:
        return self.symbol.replace("/", "")

    def _fetch_historical_data(self, days: int = 365) -> pd.DataFrame:
        import MetaTrader5 as mt5

        initialized = mt5.initialize()
        if not initialized:
            last_error = mt5.last_error()
            raise RuntimeError(f"MT5 initialization failed: {last_error}")

        mt5_symbol = self._symbol_to_mt5()
        timeframe = getattr(mt5, f"TIMEFRAME_{self.timeframe}")
        utc_from = datetime.utcnow() - timedelta(days=days)
        rates = mt5.copy_rates_from(mt5_symbol, timeframe, utc_from, 10000)
        if rates is None:
            raise RuntimeError(f"Failed to download historical data for {mt5_symbol}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.set_index("time")
        return df

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR)"""
        high_low = df["high"] - df["low"]
        high_close = np.abs(df["high"] - df["close"].shift())
        low_close = np.abs(df["low"] - df["close"].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr

    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)"""
        high_diff = df["high"].diff()
        low_diff = -df["low"].diff()

        plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
        minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

        tr = self._calculate_atr(df, 1)

        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / tr.rolling(window=period).mean()
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / tr.rolling(window=period).mean()

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = dx.rolling(window=period).mean()
        return adx

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["ema9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema21"] = df["close"].ewm(span=21, adjust=False).mean()

        # Calculate RSI
        delta = df["close"].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi"] = 100 - (100 / (1 + rs))

        # HATUA 1: Add EMA200 for trend filter
        if self.strategy_version >= 1:
            df["ema200"] = df["close"].ewm(span=200, adjust=False).mean()

        # HATUA 2: Add ADX for trend strength
        if self.strategy_version >= 2:
            df["adx"] = self._calculate_adx(df, 14)

        # HATUA 3: Add ATR for dynamic SL/TP
        if self.strategy_version >= 3:
            df["atr"] = self._calculate_atr(df, 14)

        return df

    def _generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy().dropna()
        df["signal"] = 0

        # Base conditions: EMA9/21 crossover + RSI
        buy_base = (df["ema9"] > df["ema21"]) & (df["ema9"].shift(1) <= df["ema21"].shift(1)) & (df["rsi"] < 70)
        sell_base = (df["ema9"] < df["ema21"]) & (df["ema9"].shift(1) >= df["ema21"].shift(1)) & (df["rsi"] > 30)

        # HATUA 1: Add EMA200 trend filter
        if self.strategy_version >= 1:
            buy_base = buy_base & (df["close"] > df["ema200"])
            sell_base = sell_base & (df["close"] < df["ema200"])

        # HATUA 2: Add ADX filter (only trade in trending markets)
        if self.strategy_version >= 2:
            buy_base = buy_base & (df["adx"] > 25)
            sell_base = sell_base & (df["adx"] > 25)

        # HATUA 4: Candle confirmation (check if next candle closes on right side)
        if self.strategy_version >= 4:
            buy_confirmation = df["close"].shift(-1) > df["ema21"].shift(-1)
            sell_confirmation = df["close"].shift(-1) < df["ema21"].shift(-1)
            buy_base = buy_base & buy_confirmation.fillna(False)
            sell_base = sell_base & sell_confirmation.fillna(False)

        df.loc[buy_base, "signal"] = 1
        df.loc[sell_base, "signal"] = -1

        return df

    def _simulate_trades(
        self, df: pd.DataFrame, stop_loss_pct: float = 0.5, take_profit_pct: float = 1.0
    ) -> list[dict[str, Any]]:
        trades: list[dict[str, Any]] = []
        position = None
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0

        for timestamp, row in df.iterrows():
            signal = row["signal"]
            if position is None and signal in (1, -1):
                position = "buy" if signal == 1 else "sell"
                entry_price = row["close"]

                # HATUA 3: Use ATR-based SL/TP
                if self.strategy_version >= 3:
                    atr = row.get("atr", 0.0)
                    if atr > 0:
                        if position == "buy":
                            stop_loss = entry_price - (1.5 * atr)
                            take_profit = entry_price + (2.5 * atr)
                        else:
                            stop_loss = entry_price + (1.5 * atr)
                            take_profit = entry_price - (2.5 * atr)
                    else:
                        # Fallback to percentage-based if ATR not available
                        stop_loss = (
                            entry_price * (1 - stop_loss_pct / 100)
                            if position == "buy"
                            else entry_price * (1 + stop_loss_pct / 100)
                        )
                        take_profit = (
                            entry_price * (1 + take_profit_pct / 100)
                            if position == "buy"
                            else entry_price * (1 - take_profit_pct / 100)
                        )
                else:
                    # Original percentage-based SL/TP
                    stop_loss = (
                        entry_price * (1 - stop_loss_pct / 100)
                        if position == "buy"
                        else entry_price * (1 + stop_loss_pct / 100)
                    )
                    take_profit = (
                        entry_price * (1 + take_profit_pct / 100)
                        if position == "buy"
                        else entry_price * (1 - take_profit_pct / 100)
                    )

                trades.append(
                    {
                        "symbol": self.label,
                        "mode": "backtest",
                        "type": position,
                        "entry_time": timestamp.isoformat(),
                        "exit_time": None,
                        "entry_price": float(entry_price),
                        "exit_price": None,
                        "lot_size": 0.01,
                        "stop_loss": float(stop_loss),
                        "take_profit": float(take_profit),
                        "profit_loss": 0.0,
                        "status": "open",
                        "reason": "signal",
                    }
                )
            elif position is not None:
                current_price = row["close"]
                trade = trades[-1]
                if position == "buy" and (current_price <= stop_loss or current_price >= take_profit):
                    profit_loss = current_price - entry_price
                    trade.update(
                        {
                            "exit_time": timestamp.isoformat(),
                            "exit_price": float(current_price),
                            "profit_loss": float(profit_loss),
                            "status": "closed",
                            "reason": "tp" if current_price >= take_profit else "sl",
                        }
                    )
                    position = None
                elif position == "sell" and (current_price >= stop_loss or current_price <= take_profit):
                    profit_loss = entry_price - current_price
                    trade.update(
                        {
                            "exit_time": timestamp.isoformat(),
                            "exit_price": float(current_price),
                            "profit_loss": float(profit_loss),
                            "status": "closed",
                            "reason": "tp" if current_price <= take_profit else "sl",
                        }
                    )
                    position = None
        return [trade for trade in trades if trade["status"] == "closed"]

    def run(self, days: int = 180, stop_loss_pct: float = 0.5, take_profit_pct: float = 1.0) -> dict:
        df = self._fetch_historical_data(days)
        df = self._calculate_indicators(df)
        df = self._generate_signals(df)
        trades = self._simulate_trades(df, stop_loss_pct=stop_loss_pct, take_profit_pct=take_profit_pct)

        period_start = df.index[0].to_pydatetime()
        period_end = df.index[-1].to_pydatetime()
        # NOTE: report uses self.label (not self.symbol) so different
        # strategy_version runs against the same real symbol don't collide.
        report = BacktestReport(symbol=self.label, period_start=period_start, period_end=period_end, trades=trades)

        backtest_row = self._save_backtest(report)
        logger.info(f"Backtest completed for {self.label} (v{self.strategy_version}) with win_rate={report.win_rate}")
        return {"report": report, "backtest_row": backtest_row}

    def _save_backtest(self, report: BacktestReport) -> dict:
        payload = {
            "account_id": self.account_id,
            "symbol": report.symbol,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "win_rate": report.win_rate,
            "profit_factor": report.profit_factor,
            "max_drawdown": report.max_drawdown,
            "sharpe_ratio": report.sharpe_ratio,
            "total_trades": report.total_trades,
            "winning_trades": report.winning_trades,
            "losing_trades": report.losing_trades,
            "report_json": report.report_json(),
        }
        inserted = insert_backtest_result(payload)
        if isinstance(inserted, dict):
            backtest_row = inserted
        elif isinstance(inserted, list) and inserted:
            backtest_row = inserted[0]
        else:
            raise RuntimeError("Unexpected backtest insert response")

        backtest_id = backtest_row.get("id")
        if not backtest_id:
            raise RuntimeError("Backtest insert did not return an id")
        self._persist_trades(backtest_id, report.trades)
        return backtest_row

    def _persist_trades(self, backtest_id: str, trades: list[dict[str, Any]]) -> None:
        for trade in trades:
            trade_payload = {
                "account_id": self.account_id,
                "backtest_id": backtest_id,
                "symbol": trade["symbol"],
                "mode": trade["mode"],
                "type": trade["type"],
                "entry_time": trade["entry_time"],
                "exit_time": trade["exit_time"],
                "entry_price": trade["entry_price"],
                "exit_price": trade["exit_price"],
                "lot_size": trade["lot_size"],
                "stop_loss": trade["stop_loss"],
                "take_profit": trade["take_profit"],
                "profit_loss": trade["profit_loss"],
                "status": trade["status"],
                "reason": trade["reason"],
            }
            insert_trade(trade_payload)