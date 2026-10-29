import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from zoneinfo import ZoneInfo

DATA_FILE = "data/comed_5min_rolling_60d.json"
API_BASE = "https://hourlypricing.comed.com/api"
ROLLING_DAYS = 60
CHICAGO = ZoneInfo("America/Chicago")

# A complete day has 288 five-minute prices (276/300 on DST change days). ComEd itself
# occasionally drops a few, so only days below this count are re-fetched.
MIN_POINTS_PER_DAY = 270
MAX_BACKFILL_DAYS_PER_RUN = 62   # enough to repair the whole rolling window in one run
REQUEST_PAUSE_S = 0.5            # be polite to the ComEd API between day requests


def utc_now():
    return datetime.now(timezone.utc)


def fmt_api(dt):
    # The ComEd API reads datestart/dateend as Chicago local time (verified: 12:00 -> 17:00Z
    # in CDT). Sending UTC made every run skip ~5 h (6 h in CST), leaving ~70% of the feed empty.
    return dt.astimezone(CHICAGO).strftime("%Y%m%d%H%M")


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


def incomplete_days(items, now):
    """Chicago calendar days in the rolling window (excluding today) with missing prices."""
    counts = {}
    for x in items:
        d = datetime.fromtimestamp(int(x["millisUTC"]) / 1000, tz=CHICAGO).date()
        counts[d] = counts.get(d, 0) + 1
    today = now.astimezone(CHICAGO).date()
    # skip the oldest (partial) day: it is cut by the rolling-window trim anyway
    first = (now - timedelta(days=ROLLING_DAYS)).astimezone(CHICAGO).date() + timedelta(days=1)
    days = []
    d = first
    while d < today:
        if counts.get(d, 0) < MIN_POINTS_PER_DAY:
            days.append(d)
        d += timedelta(days=1)
    return days


def fetch_day(d):
    start = datetime(d.year, d.month, d.day, 0, 0, tzinfo=CHICAGO)
    end = start.replace(hour=23, minute=59)
    return normalize_items(fetch_range(start, end))


def main():
    now = utc_now()
    existing = load_existing()
    items = existing.get("items", [])

    # 1) incremental: everything since the last stored price (or the whole window if empty)
    if items:
        latest_ms = max(int(x["millisUTC"]) for x in items)
        start_dt = datetime.fromtimestamp(latest_ms / 1000, tz=timezone.utc) - timedelta(minutes=10)
    else:
        start_dt = now - timedelta(days=ROLLING_DAYS)
    items = merge_items(items, normalize_items(fetch_range(start_dt, now)))

    # 2) backfill: re-fetch incomplete past days one day at a time
    todo = incomplete_days(items, now)[:MAX_BACKFILL_DAYS_PER_RUN]
    for d in todo:
        try:
            items = merge_items(items, fetch_day(d))
        except Exception as e:
            print(f"backfill {d} failed: {e}")
        time.sleep(REQUEST_PAUSE_S)
    if todo:
        print(f"backfilled {len(todo)} day(s): {todo[0]} .. {todo[-1]}")

    rolled = trim_rolling(items, ROLLING_DAYS)

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
