"""For each of the next 14 nights, load the ChooseRooms page once (as a normal visitor
would) and record the lowestAvailabilities map and per-rate bookable flags that the
engineResult call returns. Sequential, one load per night, 2 s pause between loads."""
import json, asyncio, datetime as dt
from playwright.async_api import async_playwright

BASE = "https://reservations.grandhotelkielce.pl/pl/4014_823/ChooseRooms"
Q = ("adults=1&children=0&date_in={din}&date_out={dout}&guide_id=823&hotel_id=4014"
     "&price_group=2&rms=1&service_model=5&user_currency=PLN&user_language=pl")
START = dt.date(2026, 10, 1)
NIGHTS = 14

async def main():
    out = []
    async with async_playwright() as p:
        b = await p.chromium.launch(
                args=["--no-sandbox"])
        ctx = await b.new_context(locale="pl-PL")
        page = await ctx.new_page()
        for i in range(NIGHTS):
            din = START + dt.timedelta(days=i); dout = din + dt.timedelta(days=1)
            got = {}
            async def on_resp(resp, got=got):
                if "/api/engineResult" in resp.url and resp.status == 200:
                    try: got["data"] = await resp.json()
                    except Exception as e: got["err"] = str(e)
            page.on("response", on_resp)
            try:
                await page.goto(BASE + "?" + Q.format(din=din, dout=dout), wait_until="networkidle", timeout=90000)
                for _ in range(20):
                    if "data" in got: break
                    await page.wait_for_timeout(500)
            except Exception as e:
                got["err"] = str(e).splitlines()[0]
            page.remove_listener("response", on_resp)
            d = got.get("data")
            rec = {"date_in": str(din), "date_out": str(dout)}
            if d:
                rec["lowestAvailabilities"] = d.get("lowestAvailabilities")
                rec["rates"] = [{"id": rp["id"], "group": rp.get("roomGroupId"), "name": rp.get("shortEnglishDesc"),
                                 "bookable": rp.get("bookable"), "price": rp.get("price"),
                                 "reasons": [r.get("cause") for r in (rp.get("notBookableReasons") or [])]}
                                for rp in d.get("roomPrices", [])]
                lp = d.get("lowestPrices", {})
                rec["lowestPrices"] = {k: v.get("lowestPrice") for k, v in lp.items()}
            else:
                rec["error"] = got.get("err", "no engineResult")
            out.append(rec)
            print(rec["date_in"], rec.get("lowestAvailabilities"), rec.get("error",""))
            await page.wait_for_timeout(2000)
        await b.close()
    json.dump(out, open("two_weeks.json","w"), ensure_ascii=False, indent=1)
asyncio.run(main())
