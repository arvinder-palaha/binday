"""Vale of White Horse V1 Tuesday waste calendar — next collection from public ICS."""

from __future__ import annotations

import argparse
import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar

# Tuesday, Vale 1 / South 2 (most of the Vale — not Appleford/Blewbury/Chilton/Harwell V2)
ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "t9khic9tvlktqh81g36c4535mo%40group.calendar.google.com/public/basic.ics"
)

LONDON = ZoneInfo("Europe/London")

# Expand RRULEs at least this far ahead (fortnightly collections need a wide window).
_LOOKAHEAD_DAYS = 800


def fetch_ics(url: str = ICS_URL, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": "binday/0.1 (personal use)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _read_cache(path: Path, *, max_age: timedelta) -> bytes | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None

    age = datetime.now(tz=LONDON) - datetime.fromtimestamp(st.st_mtime, tz=LONDON)
    if age > max_age:
        return None
    return path.read_bytes()


def fetch_ics_cached(
    *,
    url: str = ICS_URL,
    cache_path: Path,
    max_age: timedelta = timedelta(days=7),
    timeout: int = 30,
) -> bytes:
    cached = _read_cache(cache_path, max_age=max_age)
    if cached is not None:
        return cached

    data = fetch_ics(url=url, timeout=timeout)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)
    except OSError:
        # Home Assistant uses /config, but if we're not running inside HA that path may
        # not exist or be writable. Fall back to a user-writable location.
        fallback = Path(os.path.expanduser("~/.cache/binday/vale-v1-tuesday.ics"))
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
            fallback.write_bytes(data)
            cache_path = fallback
        except OSError:
            # If we can't write anywhere, still return fresh data (no cache).
            pass
    return data


def _format_long_date(d: date) -> str:
    """e.g. Tuesday 24th March."""
    day = d.day
    if 10 <= day % 100 <= 20:
        suffix = "th"
    elif day % 10 == 1:
        suffix = "st"
    elif day % 10 == 2:
        suffix = "nd"
    elif day % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"
    return f"{d:%A} {day}{suffix} {d:%B}"


def _occurrence_date(event) -> date:
    dt = event["DTSTART"].dt
    if isinstance(dt, datetime):
        return dt.date()
    return dt


def next_collection(
    ics_bytes: bytes,
    *,
    on_or_after: date | None = None,
) -> tuple[date, str] | None:
    """
    Next bin collection on or after `on_or_after`.

    The council ICS mixes explicit dates with long-running RRULE (fortnightly Tuesday)
    series. Listing only raw VEVENT rows misses RRULE-generated dates unless we expand.
    """
    on_or_after = on_or_after or date.today()
    cal = Calendar.from_ical(ics_bytes)
    start = datetime.combine(on_or_after, time.min, tzinfo=LONDON)
    end = datetime.combine(
        on_or_after + timedelta(days=_LOOKAHEAD_DAYS),
        time.max,
        tzinfo=LONDON,
    )
    occurrences = recurring_ical_events.of(cal).between(start, end)

    best: tuple[date, str] | None = None
    for event in occurrences:
        summary = str(event.get("summary") or "").strip()
        if not summary or "reminder" in summary.lower():
            continue
        d = _occurrence_date(event)
        if d < on_or_after:
            continue
        if best is None or d < best[0]:
            best = (d, summary)
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Show next Vale V1 Tuesday collection.")
    parser.add_argument(
        "--cache-path",
        default=str(Path(".cache") / "vale-v1-tuesday.ics"),
        help="Where to store the downloaded .ics file.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=7,
        help="Re-download calendar if cache older than this many days.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (use json for Home Assistant).",
    )
    args = parser.parse_args()

    try:
        data = fetch_ics_cached(
            cache_path=Path(args.cache_path),
            max_age=timedelta(days=args.max_age_days),
        )
    except URLError as e:
        print(f"Could not download calendar: {e}")
        raise SystemExit(1) from e
    nxt = next_collection(data)
    if nxt is None:
        if args.format == "json":
            print(json.dumps({"ok": False, "error": "No upcoming collection found"}))
        else:
            print("No upcoming collection found in calendar.")
        return
    d, summary = nxt
    if args.format == "json":
        today = date.today()
        print(
            json.dumps(
                {
                    "ok": True,
                    "date": d.isoformat(),
                    "longdate": _format_long_date(d),
                    "summary": summary,
                    "days_until": (d - today).days,
                }
            )
        )
    else:
        print(f"Next collection: {_format_long_date(d)} — {summary}")


if __name__ == "__main__":
    main()
