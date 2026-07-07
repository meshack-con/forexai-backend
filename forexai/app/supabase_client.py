import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL must be set in .env")

supabase_key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
if not supabase_key:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY must be set in .env")

if supabase_key.startswith("sb_publishable_"):
    raise RuntimeError(
        "SUPABASE_KEY appears to be a publishable anon key. "
        "For backend writes, set SUPABASE_SERVICE_ROLE_KEY to the service role key from Supabase Project Settings > API."
    )

supabase: Client = create_client(SUPABASE_URL, supabase_key)


def get_supabase() -> Client:
    return supabase
