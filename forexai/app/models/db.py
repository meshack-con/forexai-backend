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
    response = supabase.table("trades").insert(payload).execute()
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
