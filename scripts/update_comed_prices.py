import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen, Request

DATA_FILE = "data/comed_5min_rolling_60d.json"
API_BASE = "https://hourlypricing.comed.com/api"
ROLLING_DAYS = 60

def utc_now():
    return datetime.now(timezone.utc)

def fmt_api(dt):
    return dt.strftime("%Y%m%d%H%M")

def fetch_json(url):
    req = Request(url, headers={"User-Agent": "github-actions-comed-feed"})
    with urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_range(start_dt, end_dt):
    params = {
        "type": "5minutefeed",
        "datestart": fmt_api(start_dt),
        "dateend": fmt_api(end_dt),
        "format": "json",
    }
    url = f"{API_BASE}?{urlencode(params)}"
    return fetch_json(url)

def load_existing():
    if not os.path.exists(DATA_FILE):
        return {
            "source": "ComEd 5-minute pricing API",
            "source_url": "https://hourlypricing.comed.com/api?type=5minutefeed&format=json",
            "updated_at": None,
            "coverage_start": None,
            "coverage_end": None,
            "items": [],
        }
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_items(raw_items):
    out = []
    for row in raw_items:
        try:
            ts_ms = int(row["millisUTC"])
            price = float(row["price"])
            ts_iso = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
            out.append({
                "millisUTC": str(ts_ms),
                "ts_utc": ts_iso,
                "price": price
            })
        except Exception:
            continue
    return out

def merge_items(existing_items, new_items):
    by_ts = {}
    for item in existing_items:
        by_ts[str(item["millisUTC"])] = item
    for item in new_items:
        by_ts[str(item["millisUTC"])] = item
    merged = list(by_ts.values())
    merged.sort(key=lambda x: int(x["millisUTC"]))
    return merged

def trim_rolling(items, days):
    cutoff = utc_now() - timedelta(days=days)
    cutoff_ms = int(cutoff.timestamp() * 1000)
    trimmed = [x for x in items if int(x["millisUTC"]) >= cutoff_ms]
    return trimmed

def main():
    now = utc_now()
    existing = load_existing()
    existing_items = existing.get("items", [])

    if existing_items:
        latest_ms = max(int(x["millisUTC"]) for x in existing_items)
        start_dt = datetime.fromtimestamp(latest_ms / 1000, tz=timezone.utc) - timedelta(minutes=10)
    else:
        start_dt = now - timedelta(days=ROLLING_DAYS)

    end_dt = now

    raw = fetch_range(start_dt, end_dt)
    new_items = normalize_items(raw)
    merged = merge_items(existing_items, new_items)
    rolled = trim_rolling(merged, ROLLING_DAYS)

    coverage_start = rolled[0]["ts_utc"] if rolled else None
    coverage_end = rolled[-1]["ts_utc"] if rolled else None

    payload = {
        "source": "ComEd 5-minute pricing API",
        "source_url": "https://hourlypricing.comed.com/api?type=5minutefeed&format=json",
        "updated_at": now.isoformat(),
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "item_count": len(rolled),
        "items": rolled
    }

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    main()
