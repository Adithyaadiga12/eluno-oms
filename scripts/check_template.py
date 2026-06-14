import httpx
import re

r = httpx.get("http://127.0.0.1:8000/")
print("Status:", r.status_code)
nums = re.findall(r'class="text-3xl[^"]*">(\d+)<', r.text)
print("KPI numbers found:", nums)
print("Title:", re.search(r"<title>(.*?)</title>", r.text).group(1))
