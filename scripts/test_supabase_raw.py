from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_URL", "")

# Show the URL structure (mask middle of project ref for privacy)
if url:
    # parts
    scheme_split = url.split("://", 1)
    print(f"Scheme: {scheme_split[0] if len(scheme_split) > 1 else 'MISSING'}")
    if len(scheme_split) > 1:
        rest = scheme_split[1]
        if "." in rest:
            host, *path = rest.split("/", 1)
            parts = host.split(".")
            print(f"Hostname parts: {len(parts)}")
            print(f"Project ref length: {len(parts[0])}  (typical Supabase ref: 20 chars)")
            print(f"Project ref masked: {parts[0][:3]}...{parts[0][-3:]}")
            print(f"Domain: {'.'.join(parts[1:])}")
            print(f"Path after host: '/{path[0] if path else ''}'")
        else:
            print(f"No domain found in: {rest!r}")
print(f"Total URL length: {len(url)}")
print(f"Trailing slash: {url.endswith('/')}")
