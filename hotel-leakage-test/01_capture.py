"""Load the booking page in headless Chromium and record every request/response."""
import json, sys, asyncio
from playwright.async_api import async_playwright

URL = ("https://reservations.grandhotelkielce.pl/pl/4014_823/ChooseRooms?adults=1&children=0"
       "&date_in=2026-10-09&date_out=2026-10-10&guide_id=823&hotel_id=4014&price_group=2&rms=1"
       "&service_model=5&user_currency=PLN&user_language=pl")

async def main():
    log = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--no-sandbox"])
        ctx = await b.new_context(locale="pl-PL")
        page = await ctx.new_page()
        async def on_resp(resp):
            req = resp.request
            entry = {"url": resp.url, "method": req.method, "status": resp.status,
                     "type": req.resource_type, "ct": resp.headers.get("content-type",""),
                     "post": req.post_data, "resp_headers": dict(resp.headers)}
            try:
                if any(k in entry["ct"] for k in ("json","javascript","html","text")) and "font" not in entry["ct"]:
                    body = await resp.text()
                    entry["len"] = len(body)
                    entry["body"] = body
            except Exception as e:
                entry["err"] = str(e)
            log.append(entry)
        page.on("response", on_resp)
        await page.goto(URL, wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(5000)
        html = await page.content()
        open("page.html","w").write(html)
        await page.screenshot(path="page.png", full_page=True)
        # dump JS globals that might carry state
        globs = await page.evaluate("""() => Object.keys(window).filter(k => !/^(webkit|on|chrome|__)/.test(k)).slice(-80)""")
        print("window keys tail:", globs)
        await b.close()
    json.dump(log, open("capture.json","w"), ensure_ascii=False, indent=1)
    for e in log:
        print(e["status"], e["method"], e["type"], e.get("len","-"), e["url"][:140])
asyncio.run(main())
