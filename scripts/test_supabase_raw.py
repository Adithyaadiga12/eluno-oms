from dotenv import load_dotenv
import os
import httpx

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing URL or key")
    raise SystemExit(1)

endpoint = f"{url}/rest/v1/"
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
}

try:
    r = httpx.get(endpoint, headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    print(f"Body (first 300 chars): {r.text[:300]}")
    if r.status_code == 200:
        print("\nRaw HTTP works! Issue is the Python SDK version.")
    elif r.status_code == 401:
        print("\nKey rejected at HTTP level — key really is wrong.")
    else:
        print(f"\nUnexpected status. Possibly working though.")
except Exception as e:
    print(f"HTTP call failed: {type(e).__name__}: {e}")
