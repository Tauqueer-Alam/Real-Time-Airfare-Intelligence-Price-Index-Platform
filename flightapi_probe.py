"""Probe /schedule with exact documented param names + near dates."""
import urllib.request
import urllib.error

API_KEY = "6aaaf19a703b0cec8ded2156"


def call(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read().decode()[:4000]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore")[:400]
    except Exception as e:
        return -1, repr(e)


probes = [
    # schedule: departureDate, airport1, airport2, currency, mode=departure
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=departure",
    # schedule: departureDate, airport1, airport2, currency, mode=arrival
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=arrival",
    # schedule: departureDate, airport1, airport2, currency, mode=schedule
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=schedule",
    # schedule: departureDate, airport1, airport2, currency, mode=oneway
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=oneway",
    # schedule: departureDate, airport1, airport2, currency, mode=roundtrip
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=roundtrip",
    # schedule: departureDate, airport1, airport2, currency, mode=multi
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=multi",
    # schedule: departureDate, airport1, airport2, currency, mode=all
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=all",
    # schedule: departureDate, airport1, airport2, currency, mode=both
    f"https://api.flightapi.io/schedule/{API_KEY}?departureDate=2026-09-18&airport1=DEL&airport2=BLR&currency=INR&mode=both",
]

lines = []
for url in probes:
    status, body = call(url)
    short = url.replace(API_KEY, "<KEY>").replace("https://api.flightapi.io", "")[:100]
    lines.append(f"=== {status} {short}")
    lines.append(body[:800])
    lines.append("")
    print(status, short)

with open("flightapi_endpoints.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("done")