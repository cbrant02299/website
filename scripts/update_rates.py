#!/usr/bin/env python3
"""Pull the latest rates from FRED and save them to data/rates.json.

GitHub runs this every weekday (see .github/workflows/site.yml), so the
rates on the site update by themselves. It reads FRED's free public CSV
downloads, so there is no API key to manage, and it uses only Python's
standard library, so there is nothing to install.

If one rate can't be reached, the last saved value for it is kept and the
rest still update. If nothing can be reached, the old file is left alone.
"""

import csv
import io
import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "rates.json"

CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={start}"
SERIES_PAGE = "https://fred.stlouisfed.org/series/{id}"
USER_AGENT = "carson-brantley-site/1.0 (weekday rate update)"

# The chart on the Rates page starts here.
HISTORY_START = date(2021, 1, 1)

# Site key -> FRED series. The Fed target is a range, so it uses two series.
SERIES = {
    "fed": ["DFEDTARL", "DFEDTARU"],
    "prime": ["DPRIME"],
    "sofr": ["SOFR"],
    "t5": ["DGS5"],
    "t10": ["DGS10"],
    "mort30": ["MORTGAGE30US"],
}

# These rates also get a weekly history for the chart.
HISTORY_KEYS = ("t10", "sofr")


def fetch_series(series_id, start):
    """Return [(date, value), ...] for one FRED series, oldest first."""
    url = CSV_URL.format(id=series_id, start=start.isoformat())
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return parse_csv(response.read().decode("utf-8"))
        except Exception as error:  # network hiccup, FRED busy, bad file
            last_error = error
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{series_id}: {last_error}")


def parse_csv(text):
    """Parse a FRED CSV (date column, value column). Skips blank or '.' values."""
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 2:
        raise ValueError("unexpected file: no header row")
    rows = []
    for row in reader:
        if len(row) < 2:
            continue
        day, value = row[0].strip(), row[1].strip()
        if not value or value == ".":
            continue
        try:
            rows.append((date.fromisoformat(day), float(value)))
        except ValueError:
            continue
    if not rows:
        raise ValueError("unexpected file: no readings")
    rows.sort()
    return rows


def reading_on_or_before(rows, day):
    """The latest reading on or before `day`, or None."""
    found = None
    for row_day, value in rows:
        if row_day > day:
            break
        found = (row_day, value)
    return found


def summarize(rows):
    """Latest value, its date, and the change over a week and a year."""
    last_day, last_value = rows[-1]
    week_ago = reading_on_or_before(rows, last_day - timedelta(days=7))
    year_ago = reading_on_or_before(rows, last_day - timedelta(days=365))
    return {
        "value": round(last_value, 2),
        "date": last_day.isoformat(),
        "change_1w": round(last_value - week_ago[1], 2) if week_ago else None,
        "change_1y": round(last_value - year_ago[1], 2) if year_ago else None,
    }


def weekly(rows, start):
    """One reading per week (the last one in each week) from `start` on."""
    by_week = {}
    for row_day, value in rows:
        if row_day >= start:
            iso_year, iso_week, _ = row_day.isocalendar()
            by_week[(iso_year, iso_week)] = (row_day, value)
    return [[row_day.isoformat(), round(value, 2)] for row_day, value in sorted(by_week.values())]


def build(previous, today=None):
    """Fetch every series and return the new data, keeping old values on failures."""
    today = today or date.today()
    recent_start = today - timedelta(days=400)
    old_rates = previous.get("rates", {})
    old_history = previous.get("history", {})
    rates, history, problems = {}, {}, []

    for key, ids in SERIES.items():
        try:
            if key == "fed":
                lower = summarize(fetch_series(ids[0], recent_start))
                upper = summarize(fetch_series(ids[1], recent_start))
                rates[key] = {
                    "lower": lower["value"],
                    "upper": upper["value"],
                    "date": upper["date"],
                    "change_1w": upper["change_1w"],
                    "change_1y": upper["change_1y"],
                    "source": SERIES_PAGE.format(id=ids[1]),
                }
                continue
            start = HISTORY_START if key in HISTORY_KEYS else recent_start
            rows = fetch_series(ids[0], start)
            rates[key] = summarize(rows)
            rates[key]["source"] = SERIES_PAGE.format(id=ids[0])
            if key in HISTORY_KEYS:
                history[key] = weekly(rows, HISTORY_START)
        except Exception as error:
            problems.append(f"{key}: {error}")
            if key in old_rates:
                rates[key] = old_rates[key]
            if key in old_history:
                history[key] = old_history[key]

    return rates, history, problems


def main():
    previous = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text())
        except ValueError:
            previous = {}

    rates, history, problems = build(previous)
    for problem in problems:
        print(f"warning: could not update {problem} (the last saved value stays up)", file=sys.stderr)

    if len(problems) == len(SERIES):
        print("Could not reach FRED for any rate. Leaving the old file alone.", file=sys.stderr)
        sys.exit(1)

    unchanged = rates == previous.get("rates") and history == previous.get("history")
    if unchanged and not previous.get("preview"):
        print("Rates unchanged.")
        return

    data = {
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "source": "FRED, Federal Reserve Bank of St. Louis",
        "rates": rates,
        "history": history,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n")
    print("Saved", ", ".join(f"{k} {v.get('value', v.get('upper'))}" for k, v in rates.items()))


if __name__ == "__main__":
    main()
