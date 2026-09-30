"""Build the HTML report from two_weeks.json + the single-query capture."""
import json, datetime as dt, html
rows = json.load(open("two_weeks.json"))
GROUPS = [("22742","Standard Single"),("22743","Standard Twin"),("22744","Standard Double King"),
          ("22745","Standard Double + Sofa"),("22746","Superior Double"),("22747","Junior Suite"),("22748","Executive Apartment")]
TOTAL_ROOMS = 122
ramp = ["#cde2fb","#b7d3f6","#9ec5f4","#86b6ef","#6da7ec","#5598e7","#3987e5","#2a78d6","#256abf","#1c5cab","#184f95","#104281","#0d366b"]
maxv = max(v for r in rows for v in r["lowestAvailabilities"].values())
def shade(v):
    if v == 0: return "var(--cell-zero)"
    i = round((v / maxv) * (len(ramp)-1)); return ramp[i]
def ink(v):
    return "#0b0b0b" if v == 0 or (v / maxv) < 0.45 else "#ffffff"
peak = {g: max(r["lowestAvailabilities"][g] for r in rows) for g,_ in GROUPS}
# heatmap table
thead = "<th class='date'>Night</th>" + "".join(f"<th>{html.escape(n)}<span class='peak'>peak {peak[g]}</span></th>" for g,n in GROUPS) + "<th class='tot'>Open</th><th class='tot'>Implied occ.</th>"
trs = []
totals = []
for r in rows:
    d = dt.date.fromisoformat(r["date_in"]); la = r["lowestAvailabilities"]
    tot = sum(la.values()); totals.append(tot)
    occ = max(0, min(100, round(100 * (1 - tot / TOTAL_ROOMS))))
    cells = "".join(f"<td style='background:{shade(la[g])};color:{ink(la[g])}' title='{html.escape(n)}, {d:%a %d %b}: {la[g]} open'>{la[g]}</td>" for g,n in GROUPS)
    wk = " class='wkend'" if d.weekday() >= 5 else ""
    trs.append(f"<tr{wk}><td class='date'><b>{d:%a}</b> {d:%d %b}</td>{cells}<td class='tot'>{tot}</td><td class='tot'>{occ}%</td></tr>")
table = f"<table class='heat'><thead><tr>{thead}</tr></thead><tbody>{''.join(trs)}</tbody></table>"
# bar chart svg: total open rooms per night
W, H, padL, padB, padT = 720, 240, 40, 34, 14
n = len(rows); bw = (W - padL - 10) / n; ymax = 140
def y(v): return padT + (H - padT - padB) * (1 - v / ymax)
bars = []
for i, (r, tot) in enumerate(zip(rows, totals)):
    d = dt.date.fromisoformat(r["date_in"]); x = padL + i * bw + 4; w = bw - 8
    top = y(tot); hgt = y(0) - top
    lab = f"<text class='dl' x='{x + w/2:.1f}' y='{top - 5:.1f}' text-anchor='middle'>{tot}</text>" if i in (0, totals.index(max(totals)), totals.index(min(totals)), n-1) else ""
    bars.append(f"<g class='bar'><rect x='{x:.1f}' y='{top:.1f}' width='{w:.1f}' height='{hgt:.1f}' rx='3'/><rect class='hit' x='{padL + i*bw:.1f}' y='{padT}' width='{bw:.1f}' height='{H-padT-padB}' data-tip='{d:%a %d %b}: {tot} rooms open across all types'/>{lab}<text class='ax' x='{x + w/2:.1f}' y='{H-10}' text-anchor='middle'>{d:%d}</text></g>")
grid = "".join(f"<line class='grid' x1='{padL}' x2='{W-10}' y1='{y(v):.1f}' y2='{y(v):.1f}'/><text class='ax' x='{padL-6}' y='{y(v)+4:.1f}' text-anchor='end'>{v}</text>" for v in (0, 40, 80, 120))
cap = f"<line class='cap' x1='{padL}' x2='{W-10}' y1='{y(TOTAL_ROOMS):.1f}' y2='{y(TOTAL_ROOMS):.1f}'/><text class='ax cap-l' x='{W-10}' y='{y(TOTAL_ROOMS)-5:.1f}' text-anchor='end'>hotel capacity 122</text>"
svg = f"<svg viewBox='0 0 {W} {H}' role='img' aria-label='Open rooms per night, 1 to 14 October 2026'>{grid}{cap}{''.join(bars)}</svg>"
first, last = rows[0]["date_in"], rows[-1]["date_in"]
nz = [t for t in totals if t > 0]; lowest_i = totals.index(min(nz)); highest_i = totals.index(max(totals))
ld = dt.date.fromisoformat(rows[lowest_i]["date_in"]); hd = dt.date.fromisoformat(rows[highest_i]["date_in"])
tpl = open("report_template.html").read()
out = (tpl.replace("{{TABLE}}", table).replace("{{SVG}}", svg)
       .replace("{{LOW_DATE}}", f"{ld:%A %d %B}").replace("{{LOW_N}}", str(min(nz)))
       .replace("{{HIGH_DATE}}", f"{hd:%A %d %B}").replace("{{HIGH_N}}", str(max(totals)))
       .replace("{{PEAK_SUM}}", str(sum(peak.values()))))
open("report.html","w").write(out)
print("ok", len(out), "bytes; totals", totals)
