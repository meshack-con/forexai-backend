from postgrest.exceptions import APIError
from app.supabase_client import get_supabase


def insert_backtest_result(payload: dict) -> list[dict] | dict:
    supabase = get_supabase()
    response = supabase.table("backtest_results").insert(payload).select("*").execute()
    data = response.data
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        return data
    raise RuntimeError("Supabase insert did not return any backtest row")


def insert_trade(payload: dict) -> dict:
    supabase = get_supabase()
    response = supabase.table("trades").insert(payload).select("*").execute()
    data = response.data
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    raise RuntimeError("Supabase insert did not return a trade row")


def update_trade(trade_id: str, updates: dict) -> dict:
    supabase = get_supabase()
    response = supabase.table("trades").update(updates).eq("id", trade_id).select("*").execute()
    data = response.data
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    raise RuntimeError("Supabase update did not return the trade row")


def get_open_trades(account_id: str, symbol: str, mode: str = "demo") -> list[dict]:
    supabase = get_supabase()
    response = (
        supabase.table("trades")
        .select("*")
        .eq("account_id", account_id)
        .eq("symbol", symbol)
        .eq("mode", mode)
        .eq("status", "open")
        .execute()
    )
    return response.data


def get_backtest_results(account_id: str, limit: int = 20) -> list[dict]:
    supabase = get_supabase()
    response = supabase.table("backtest_results").select("*").eq("account_id", account_id).order("created_at", desc=True).limit(limit).execute()
    return response.data


def get_bot_status(account_id: str) -> dict | None:
    supabase = get_supabase()
    try:
        response = supabase.table("bot_status").select("*").eq("account_id", account_id).single().execute()
        return response.data
    except APIError as e:
        if e.resp.status_code == 406:
            return None
        raise RuntimeError(f"Supabase fetch failed: {str(e)}")


def update_bot_status(account_id: str, status: str, current_mode: str | None = None, notes: str | None = None) -> dict:
    supabase = get_supabase()
    payload = {"status": status}
    if current_mode is not None:
        payload["current_mode"] = current_mode
    if notes is not None:
        payload["notes"] = notes
    response = supabase.table("bot_status").upsert({"account_id": account_id, **payload}).execute()
    return response.data


def get_risk_settings(account_id: str) -> dict | None:
    supabase = get_supabase()
    try:
        response = supabase.table("risk_settings").select("*").eq("account_id", account_id).single().execute()
        return response.data
    except APIError as e:
        if e.resp.status_code == 406:
            return None
        raise RuntimeError(f"Supabase fetch failed: {str(e)}")


def update_risk_settings(account_id: str, updates: dict) -> dict:
    supabase = get_supabase()
    response = supabase.table("risk_settings").update(updates).eq("account_id", account_id).execute()
    return response.data


def get_strategy_config(account_id: str, symbol: str) -> dict | None:
    """Fetch the frozen, validated strategy parameters for a given account+symbol.
    Only returns configs marked is_active=true - this is the single source of
    truth for what parameters the live/demo bot is allowed to trade with."""
    supabase = get_supabase()
    try:
        response = (
            supabase.table("strategy_configs")
            .select("*")
            .eq("account_id", account_id)
            .eq("symbol", symbol)
            .eq("is_active", True)
            .single()
            .execute()
        )
        return response.data
    except APIError as e:
        if e.resp.status_code == 406:
            return None
        raise RuntimeError(f"Supabase fetch failed: {str(e)}")


def get_trades_closed_today(account_id: str, symbol: str, mode: str = "demo") -> list[dict]:
    """Used for daily loss limit checks - trades closed since UTC midnight today."""
    from datetime import datetime, timezone

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    supabase = get_supabase()
    response = (
        supabase.table("trades")
        .select("*")
        .eq("account_id", account_id)
        .eq("symbol", symbol)
        .eq("mode", mode)
        .eq("status", "closed")
        .gte("exit_time", today_start)
        .execute()
    )
    return response.data