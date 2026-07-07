from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.db import get_backtest_results, get_bot_status, update_bot_status, get_risk_settings, update_risk_settings
from app.services.backtester import Backtester

router = APIRouter()


class StartBotRequest(BaseModel):
    account_id: str
    symbol: str
    timeframe: str = "M15"


class RiskSettingsUpdate(BaseModel):
    position_size_pct: float | None = None
    stop_loss_pct: float | None = None
    take_profit_pct: float | None = None
    daily_loss_limit_pct: float | None = None
    max_drawdown_pct: float | None = None
    max_concurrent_trades_per_symbol: int | None = None
    allow_live: bool | None = None


@router.post("/bot/start")
def start_bot(request: StartBotRequest):
    bot_status = get_bot_status(request.account_id)
    if bot_status and bot_status.get("status") == "running":
        raise HTTPException(status_code=400, detail="Bot is already running")

    update_bot_status(request.account_id, status="validation_pending", current_mode="backtest", notes="Starting backtest validation")
    backtester = Backtester(account_id=request.account_id, symbol=request.symbol, timeframe=request.timeframe)
    result = backtester.run()
    report = result["report"]
    backtest_row = result["backtest_row"]
    passed = bool(backtest_row.get("passed_validation", False))

    if passed:
        update_bot_status(request.account_id, status="stopped", current_mode="backtest", notes="Validation passed; ready for demo")
    else:
        update_bot_status(request.account_id, status="stopped", current_mode="backtest", notes="Validation failed; do not enable live yet")

    return {
        "message": "Backtest completed",
        "symbol": request.symbol,
        "passed_validation": passed,
        "backtest_id": backtest_row.get("id"),
        "report": report.report_json(),
    }


@router.post("/bot/stop")
def stop_bot(account_id: str):
    update_bot_status(account_id, status="stopped", current_mode="none", notes="Manually stopped")
    return {"message": "Bot stopped"}


@router.get("/bot/status")
def bot_status(account_id: str):
    status = get_bot_status(account_id)
    if not status:
        raise HTTPException(status_code=404, detail="Bot status not found")
    return status


@router.get("/bot/backtests")
def bot_backtests(account_id: str, limit: int = 20):
    return get_backtest_results(account_id=account_id, limit=limit)


@router.get("/bot/risk-settings")
def bot_risk_settings(account_id: str):
    settings = get_risk_settings(account_id)
    if not settings:
        raise HTTPException(status_code=404, detail="Risk settings not found")
    return settings


@router.put("/bot/risk-settings")
def bot_risk_settings_update(account_id: str, updates: RiskSettingsUpdate):
    payload = {k: v for k, v in updates.dict().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No risk settings provided")
    return update_risk_settings(account_id, payload)
