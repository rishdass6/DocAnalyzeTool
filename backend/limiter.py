from fastapi import Cookie, Request
from slowapi import Limiter

def get_session_cookie_key(request: Request) -> str:
    return request.cookies.get("session_id") or request.client.host


limiter = Limiter(key_func=get_session_cookie_key)
