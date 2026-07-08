"""
Demo trading engine.

This is intentionally kept separate from the FastAPI web server, because
MetaTrader5's Python API is synchronous/blocking and expects to run in a
long-lived process with a persistent MT5 terminal connection. Running it
as its own worker script (see scripts/run_demo_bot.py) avoids threading
issues with uvicorn's --reload process.

IMPORTANT LIMITATIONS (be aware of these before trusting this in demo):
- Assumes ONE open position per account+symbol at a time (matches
  risk_settings.max_concurrent_trades_per_symbol = 1 default).
- Position sizing assumes a "standard" $10/pip value and 0.0001 pip size,
  which is correct for most USD-quoted pairs like EURUSD but NOT
  universally correct for all symbols (e.g. JPY pairs use 0.01 pip size).
- Relies on polling (checking every N seconds) rather than exact
  candle-close event triggers. This is simple and reliable enough for
  M15/H1 timeframes but introduces a small delay after each candle closes.
- Order filling mode (IOC) may need adjustment depending on your broker.
"""

from datetime import datetime, timezone

from app.core.logger import logger
from app.mt5_client import mt5_client
from app.models.db import (
    get_strategy_config,
    get_open_trades,
    insert_trade,
    update_trade,
    get_risk_settings,
    get_trades_closed_today,
    update_bot_status,
)
from app.services.backtester import Backtester
from app.services.risk_management import (
    calculate_position_size,
    check_daily_loss_limit,
)

MAGIC_NUMBER = 20260708  # arbitrary fixed identifier so we only manage our own orders
PIP_SIZE = 0.0001  # valid for EURUSD and most non-JPY pairs
PIP_VALUE_PER_LOT = 10.0  # approx USD value per pip per standard lot


def _symbol_to_mt5(symbol: str) -> str:
    return symbol.replace("/", "")


def check_and_close_finished_trades(account_id: str, symbol: str) -> None:
    """For any trade we have marked 'open' in the DB, check whether MT5 still
    shows an open position for it. If MT5 no longer shows it, the broker
    closed it (SL or TP was hit) - fetch the closing deal and update the DB."""
    import MetaTrader5 as mt5

    open_trades = get_open_trades(account_id, symbol, mode="demo")
    if not open_trades:
        return

    mt5_symbol = _symbol_to_mt5(symbol)
    live_positions = mt5.positions_get(symbol=mt5_symbol) or ()
    live_tickets = {str(p.ticket) for p in live_positions if p.magic == MAGIC_NUMBER}

    for trade in open_trades:
        ticket = trade.get("reason")  # we store the MT5 position ticket in `reason` at open time
        if ticket in live_tickets:
            continue  # still open on the broker side, nothing to do

        # Position no longer exists on MT5 -> it was closed. Look up the closing deal.
        deals = mt5.history_deals_get(position=int(ticket)) if ticket else None
        if not deals:
            logger.warning(f"Trade {trade['id']} appears closed but no closing deal found for ticket {ticket}")
            continue

        closing_deal = deals[-1]
        update_trade(
            trade["id"],
            {
                "exit_time": datetime.fromtimestamp(closing_deal.time, tz=timezone.utc).isoformat(),
                "exit_price": float(closing_deal.price),
                "profit_loss": float(closing_deal.profit),
                "status": "closed",
                "reason": "tp_or_sl",
            },
        )
        logger.info(f"Closed demo trade {trade['id']} for {symbol}: profit_loss={closing_deal.profit}")


def try_open_new_trade(account_id: str, config: dict, risk_settings: dict) -> None:
    import MetaTrader5 as mt5

    symbol = config["symbol"]
    mt5_symbol = _symbol_to_mt5(symbol)

    open_trades = get_open_trades(account_id, symbol, mode="demo")
    max_concurrent = risk_settings.get("max_concurrent_trades_per_symbol", 1)
    if len(open_trades) >= max_concurrent:
        return  # already at position limit for this symbol, do nothing

    backtester = Backtester(
        account_id=account_id,
        symbol=symbol,
        timeframe=config["timeframe"],
        strategy_version=config["strategy_version"],
        sl_atr_mult=config["sl_atr_mult"],
        tp_atr_mult=config["tp_atr_mult"],
        adx_threshold=config["adx_threshold"],
    )
    latest = backtester.get_latest_signal(days=60)

    if latest["signal"] == 0:
        return  # no signal on the most recent closed candle

    account_info = mt5.account_info()
    if account_info is None:
        raise RuntimeError("Could not read MT5 account info")

    # Daily loss limit check BEFORE opening anything new
    closed_today = get_trades_closed_today(account_id, symbol, mode="demo")
    daily_pl = sum(t["profit_loss"] for t in closed_today)
    if check_daily_loss_limit(account_info.balance, risk_settings["daily_loss_limit_pct"], daily_pl):
        update_bot_status(account_id, status="stopped", current_mode="demo", notes="Daily loss limit hit - trading paused")
        logger.warning(f"Daily loss limit hit for {symbol}, skipping new trades today")
        return

    close = latest["close"]
    atr = latest["atr"] or 0.0
    if atr <= 0:
        logger.warning("ATR unavailable on latest candle, skipping this cycle")
        return

    is_buy = latest["signal"] == 1
    sl_distance = config["sl_atr_mult"] * atr
    tp_distance = config["tp_atr_mult"] * atr
    stop_loss = close - sl_distance if is_buy else close + sl_distance
    take_profit = close + tp_distance if is_buy else close - tp_distance

    sl_pips = sl_distance / PIP_SIZE
    lot_size = calculate_position_size(
        account_balance=account_info.balance,
        risk_pct=risk_settings["position_size_pct"],
        stop_loss_pips=sl_pips,
        pip_value=PIP_VALUE_PER_LOT,
    )
    lot_size = max(0.01, lot_size)  # enforce broker minimum lot

    tick = mt5.symbol_info_tick(mt5_symbol)
    price = tick.ask if is_buy else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": mt5_symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": stop_loss,
        "tp": take_profit,
        "deviation": 20,
        "magic": MAGIC_NUMBER,
        "comment": "forexai-demo",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        logger.error(f"Order send failed for {symbol}: {result}")
        return

    insert_trade(
        {
            "account_id": account_id,
            "backtest_id": None,
            "symbol": symbol,
            "mode": "demo",
            "type": "buy" if is_buy else "sell",
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "exit_time": None,
            "entry_price": float(result.price),
            "exit_price": None,
            "lot_size": lot_size,
            "stop_loss": float(stop_loss),
            "take_profit": float(take_profit),
            "profit_loss": 0.0,
            "status": "open",
            "reason": str(result.order),  # store MT5 position ticket here for later lookup
        }
    )
    logger.info(f"Opened demo {'buy' if is_buy else 'sell'} on {symbol}: lot={lot_size}, sl={stop_loss}, tp={take_profit}")


def run_cycle(account_id: str, symbol: str) -> None:
    """One full check cycle: connect, close finished trades, look for new entry."""
    config = get_strategy_config(account_id, symbol)
    if not config:
        logger.warning(f"No active strategy_configs row for {symbol} - skipping")
        return

    risk_settings = get_risk_settings(account_id)
    if not risk_settings:
        logger.warning("No risk_settings found for account - skipping")
        return

    mt5_client.connect()
    check_and_close_finished_trades(account_id, symbol)
    try_open_new_trade(account_id, config, risk_settings)