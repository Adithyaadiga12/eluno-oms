import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import os
import resend

resend.api_key = os.getenv("RESEND_API_KEY")

# The ID from the last send
EMAIL_ID = "8510d416-4277-4b68-9da2-97770869d857"

try:
    r = resend.Emails.get(email_id=EMAIL_ID)
    print(f"Email status:")
    for k in ["last_event", "created_at", "to", "subject", "from"]:
        print(f"  {k}: {r.get(k)}")
except Exception as e:
    print(f"Failed to query: {e}")
