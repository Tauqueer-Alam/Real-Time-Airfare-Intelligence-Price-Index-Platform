"""Search docs text for API documentation sections."""
import re

with open("flightapi_docs_text.txt", encoding="utf-8", errors="ignore") as f:
    text = f.read()

out = []
# Find sections mentioning endpoints
for kw in ["flightapi.io", "onewaytrip", "tracksearch", "air-fares", "schedule", "airline", "Endpoint", "endpoint", "Request", "request", "GET ", "POST "]:
    for m in re.finditer(re.escape(kw), text):
        start = max(0, m.start() - 150)
        end = min(len(text), m.end() + 300)
        snippet = text[start:end]
        snippet = re.sub(r"\s+", " ", snippet)
        out.append(f"[{kw}] {snippet}")

seen = set()
unique = []
for line in out:
    key = line[:80]
    if key not in seen:
        seen.add(key)
        unique.append(line)

with open("flightapi_endpoints.txt", "w", encoding="utf-8") as f:
    f.write("\n\n====\n\n".join(unique[:60]))
print("matches:", len(unique))