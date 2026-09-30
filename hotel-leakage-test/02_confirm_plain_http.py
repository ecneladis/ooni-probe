"""Confirm the engineResult JSON (already observed in the browser capture) is served to a
plain HTTP client. Mirrors exactly what the page does: page load (cookies), engineCheck
(server session), then engineResult. Three requests only."""
import requests
BASE = "https://reservations.grandhotelkielce.pl"
Q = ("adults=1&children=0&date_in=2026-10-09&date_out=2026-10-10&guide_id=823&hotel_id=4014"
     "&price_group=2&rms=1&service_model=5&user_currency=PLN&user_language=pl")
s = requests.Session(); s.verify = True
s.headers["User-Agent"] = "Mozilla/5.0 (X11; Linux x86_64) leakage-check/1.0"
p = s.get(f"{BASE}/pl/4014_823/ChooseRooms?{Q}", timeout=60)
print("page", p.status_code, "cookies:", list(s.cookies.keys()))
h = {"Referer": p.url, "Accept": "application/json"}
c = s.get(f"{BASE}/api/engineCheck?{Q}", timeout=60, headers=h)
print("engineCheck", c.status_code, "cookies now:", list(s.cookies.keys()))
r = s.get(f"{BASE}/api/engineResult?{Q}", timeout=60, headers=h)
print("engineResult", r.status_code, "cache-control:", r.headers.get("cache-control"))
if r.ok:
    d = r.json()
    print("lowestAvailabilities:", d.get("lowestAvailabilities"))
else:
    print(r.text[:300])
