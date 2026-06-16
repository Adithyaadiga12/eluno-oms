"""Verify Resend env vars are set + send a real test email — without revealing values to stdout."""

from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, ".")
load_dotenv()

api_key = os.getenv("RESEND_API_KEY", "")
to = os.getenv("ALERT_EMAIL_TO", "")

# Format check (no values printed)
print("Format check:")
print(f"  RESEND_API_KEY: {'OK' if api_key.startswith('re_') and len(api_key) > 20 else 'BAD FORMAT'} "
      f"(len={len(api_key)}, prefix={api_key[:3]!r})")
print(f"  ALERT_EMAIL_TO: {'OK' if '@' in to and '.' in to.split('@')[-1] else 'BAD FORMAT'} "
      f"(domain={to.split('@')[-1] if '@' in to else 'missing'})")

if not api_key.startswith("re_") or "@" not in to:
    print("\nAbort — fix .env and rerun.")
    sys.exit(1)

# Send a real test email
import resend
resend.api_key = api_key

try:
    r = resend.Emails.send({
        "from": "Eluno OMS <onboarding@resend.dev>",
        "to": [to],
        "subject": "[Eluno OMS] Resend wired — Day 2 test",
        "html": """
        <h2>Resend is working ✓</h2>
        <p>This is a test from your Eluno OMS dev environment.</p>
        <p>If you see this, your <code>RESEND_API_KEY</code> + <code>ALERT_EMAIL_TO</code> are correctly wired.</p>
        <p>Next: TAT scan will fire real breach alerts using this same plumbing.</p>
        """,
    })
    print(f"\n[OK] Email sent. Resend ID: {r.get('id')}")
    print(f"  Check inbox: {to.split('@')[0][:2]}***@{to.split('@')[-1]}")
except Exception as e:
    print(f"\n[FAIL] Send failed: {type(e).__name__}: {e}")
