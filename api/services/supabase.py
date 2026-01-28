"""
Supabase client configuration
"""

import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase() -> Client:
    """Get Supabase client singleton."""
    global _client

    if _client is None:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        _client = create_client(url, key)

    return _client


def get_user_client(access_token: str) -> Client:
    """Get Supabase client with user's access token for RLS."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")

    client = create_client(url, key)
    client.auth.set_session(access_token, "")
    return client
