"""Vale of White Horse V1 Tuesday waste calendar — next collection from public ICS."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
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
    try:
        data = fetch_ics()
    except URLError as e:
        print(f"Could not download calendar: {e}")
        raise SystemExit(1) from e
    nxt = next_collection(data)
    if nxt is None:
        print("No upcoming collection found in calendar.")
        return
    d, summary = nxt
    print(f"Next collection: {d.isoformat()} — {summary}")


if __name__ == "__main__":
    main()
