"""Next waste collection from a public ICS calendar (council iCal / Google public feed)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import recurring_ical_events
from icalendar import Calendar

_ENV_ICS_URL = "BINDAY_ICS_URL"

# Expand RRULEs at least this far ahead (fortnightly collections need a wide window).
_LOOKAHEAD_DAYS = 800

LONDON = ZoneInfo("Europe/London")


def _resolve_ics_url(cli_url: str | None) -> str | None:
    if cli_url and cli_url.strip():
        return cli_url.strip()
    env = os.environ.get(_ENV_ICS_URL, "").strip()
    return env or None


def fetch_ics(url: str, timeout: int = 30) -> bytes:
    req = Request(
        url,
        headers={"User-Agent": "binday/0.1 (public ICS waste calendar fetcher)"},
    )
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
    url: str,
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
        fallback = Path(os.path.expanduser("~/.cache/binday/calendar.ics"))
        try:
            fallback.parent.mkdir(parents=True, exist_ok=True)
            fallback.write_bytes(data)
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
    Next collection event on or after `on_or_after`.

    Many council feeds mix explicit dates with long-running RRULE series; listing only
    raw VEVENT rows misses RRULE-generated dates unless we expand.
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
    parser = argparse.ArgumentParser(
        description="Show the next waste collection from a public ICS URL.",
    )
    parser.add_argument(
        "--ics-url",
        default=None,
        help=f"Calendar feed URL (overrides {_ENV_ICS_URL}).",
    )
    parser.add_argument(
        "--cache-path",
        default=str(Path(".cache") / "calendar.ics"),
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

    ics_url = _resolve_ics_url(args.ics_url)
    if not ics_url:
        print(
            f"binday: set {_ENV_ICS_URL} or pass --ics-url with your public waste calendar URL.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    try:
        data = fetch_ics_cached(
            url=ics_url,
            cache_path=Path(args.cache_path),
            max_age=timedelta(days=args.max_age_days),
        )
    except URLError as e:
        print(f"Could not download calendar: {e}", file=sys.stderr)
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
