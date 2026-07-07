from datetime import datetime
from app.core.logger import logger


def calculate_position_size(account_balance: float, risk_pct: float, stop_loss_pips: float, pip_value: float = 10.0) -> float:
    if account_balance <= 0 or risk_pct <= 0 or stop_loss_pips <= 0:
        raise ValueError("Invalid risk management inputs")
    risk_amount = account_balance * (risk_pct / 100.0)
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    return round(lot_size, 2)


def check_daily_loss_limit(account_balance: float, daily_loss_limit_pct: float, current_daily_loss: float) -> bool:
    if daily_loss_limit_pct <= 0:
        return False
    limit_amount = account_balance * (daily_loss_limit_pct / 100.0)
    return abs(current_daily_loss) >= limit_amount


def check_max_drawdown(account_balance: float, max_drawdown_pct: float, peak_balance: float) -> bool:
    if max_drawdown_pct <= 0:
        return False
    drawdown_amount = peak_balance - account_balance
    return drawdown_amount >= peak_balance * (max_drawdown_pct / 100.0)


def log_trade_decision(message: str, metadata: dict | None = None) -> None:
    logger.info(message)
    if metadata:
        logger.debug(metadata)
