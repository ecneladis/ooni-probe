# Information-leakage check: reservations.grandhotelkielce.pl (Bookassist booking engine)

Date of test: 2026-09-30. Scope: passive observation of the public "ChooseRooms" page
for one query (1 adult, 1 room, 2026-10-09 to 2026-10-10) plus a three-request replay of
the page's own call sequence with a plain HTTP client. No other dates, hotels or
endpoints were probed.

## How the page works (observed)

The front end is a Next.js app. On load it calls, in order:

| Call | Purpose |
|---|---|
| `GET /__ENV.js` | Front-end config (CDN hosts, Clarity id, Google Maps key) |
| `GET /api/engineCheck?...` | Creates the booking session, returns hotel/engine config |
| `GET /api/engineResult?...` | Rates and rooms for the searched dates |
| `GET /api/roomStuff?rpId=...`, `GET /api/roomConfig?rpId=...` | Per-rate details |
| `POST /api/spoor` | Bookassist analytics (client IP, UA, fingerprint, cookies) |
| `webapi-prod.bookassist.com/api/v1/i18n/...` | Translation bundles |

## Findings

### 1. Remaining-room counts per room group are exposed (confirmed)

`GET /api/engineResult` returns a top-level field `lowestAvailabilities` that maps each
room group id to a number. For the tested night it contained seven room groups with
values between 1 and 35. The UI does not display these numbers, but any visitor can read
them from the network tab. Together with the room-group names in `roomPrices[]` this
tells a visitor how many rooms of each type are still open for the searched dates, and
therefore, combined with finding 2, an approximate occupancy figure for the hotel.

Related fields in the same response that also describe inventory state:

- `roomPrices[].notBookableReasons[]` carries the internal cause code (`STOP_SELL`) and
  the date, not just the customer-facing "no availability" text.
- `roomPriceDatesCalculated[*][].stopSale`, `closeForArrival`, `minNights`, `rackRef`
  (rack rate) and `dynamicDiscountId` expose per-day revenue-management settings.
- `dynamicDiscounts[*]` exposes discount percentages, `defaultAvailability` and
  `lastEarly`/`minStay` rules, plus internal English descriptions.

### 2. Total hotel capacity and internal contact data are exposed (confirmed)

`GET /api/engineCheck` returns `engine.hotel.numberOfRooms` (122) and
`numberOfSuites`, plus `bookingEmail` and `voucherEmail` (the hotel's booking mailbox),
`hotelOptions.maxRoomsPerBooking`, `minHoursAhead`, `maxMonthBookAhead`,
`maxStayNights`, and ~80 `hotelOptionOfHotel[].nameKey` feature flags. It also contains
an empty `customer` template that includes a `password` field name, which suggests the
same object is used server-side for authenticated customers.

### 3. Backend and vendor details are exposed (confirmed, low impact)

- `engineCheck` reports `identity.ip` / `analytics.clientIP` as `63.33.237.177` with
  `userAgent: "node"`. That is the egress IP of the Next.js server calling Bookassist,
  not the visitor's IP. It also returns `configuration.sessionId`, `identity.baSessionId`
  and `identity.uuid` for the server-side session, and a gzip+base64 `hash` blob.
- The `bp4014_823` cookie set on the first redirect contains `https://localhost:3000/...`,
  an internal development origin baked into production.
- `__ENV.js` publishes a Google Maps API key in clear text. It is normal for a browser
  key to be public, but it should be restricted by HTTP referrer in Google Cloud Console.
- `/api/spoor` posts the visitor's full cookie string, user agent, ad-block status and a
  fingerprint id to Bookassist analytics.

### 4. Not reachable without the front end's handshake (partially confirmed)

Replaying the page's sequence (page load, `engineCheck`, `engineResult`) with a plain
HTTP client returned `engineResult returned 500`. The browser gets a 200 for the identical
URL, so the API relies on something the front end adds (most likely a header or a
session value derived from `engineCheck`). This is not a security control, only friction;
a headless browser (script 01) receives the full response.

## Recommendations

1. Ask Bookassist to remove `lowestAvailabilities`, `hotel.numberOfRooms`,
   `numberOfSuites`, `bookingEmail`, `voucherEmail` and the raw `notBookableReasons.cause`
   from responses served to the public front end, or to reduce `lowestAvailabilities` to
   a boolean or a capped value (for example "3+").
2. Ask them to strip `identity.ip`, `sessionId`, `baSessionId`, `hash`, and the
   per-day `rackRef`/`stopSale`/`closeForArrival` fields from the client payload.
3. Fix the `bp4014_823` cookie so it does not reference `localhost:3000`.
4. Restrict the Google Maps key by referrer to `reservations.grandhotelkielce.pl`.
5. Review whether the `/api/spoor` payload (full cookies, fingerprint) is covered by the
   privacy notice.

## Scripts

- `01_capture.py`: loads the page in headless Chromium, records every request and
  response into `capture.json`, saves `page.html` and `page.png`.
- `02_confirm_plain_http.py`: replays the page's three-call sequence with `requests`.
- `03_two_weeks.py`: one page load per night for 14 nights, records `lowestAvailabilities` into `two_weeks.json`.
- `04_build_report.py` + `report_template.html`: builds `report.html`, the HTML report with the two-week board.

Run with `pip install playwright requests` and a Chromium available to Playwright.
Raw single-page captures are not committed because they contain session identifiers. `two_weeks.json` holds only the per-night availability counts and rate flags.
