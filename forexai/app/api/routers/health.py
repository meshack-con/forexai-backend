from fastapi import APIRouter
from app.supabase_client import get_supabase

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "ForexAI"}


@router.get("/health/supabase")
def health_supabase():
    client = get_supabase()
    try:
        response = client.rpc("pg_sleep", {"seconds": 0}).execute()
        rows_affected = getattr(response, "count", None)
        data_info = response.data if hasattr(response, "data") else None
        return {
            "status": "ok",
            "supabase_check": True,
            "detail": {
                "data": data_info,
                "rows_affected": rows_affected,
            },
        }
    except Exception as exc:
        return {"status": "error", "supabase_check": False, "detail": str(exc)}
