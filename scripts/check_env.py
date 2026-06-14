from dotenv import load_dotenv
import os

load_dotenv()

g = os.getenv("GEMINI_API_KEY", "")
u = os.getenv("SUPABASE_URL", "")
s = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


def show(name, v):
    if not v:
        print(f"{name}: MISSING")
        return
    prefix = v[:10] if len(v) > 10 else v
    has_quotes = v[0] in ('"', "'") or v[-1] in ('"', "'")
    trailing_ws = v != v.strip()
    print(f"{name}: len={len(v)} prefix={prefix!r}... trailing_ws={trailing_ws} has_quotes={has_quotes}")


show("GEMINI_API_KEY", g)
show("SUPABASE_URL", u)
show("SUPABASE_SERVICE_ROLE_KEY", s)
