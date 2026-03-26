"""Vale of White Horse V1 Tuesday waste calendar — next collection from public ICS."""

from __future__ import annotations

from datetime import date, datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

from icalendar import Calendar

# Tuesday, Vale 1 / South 2 (most of the Vale — not Appleford/Blewbury/Chilton/Harwell V2)
ICS_URL = (
    "https://calendar.google.com/calendar/ical/"
    "t9khic9tvlktqh81g36c4535mo%40group.calendar.google.com/public/basic.ics"
)


def fetch_ics(url: str = ICS_URL, timeout: int = 30) -> bytes:
    req = Request(url, headers={"User-Agent": "binday/0.1 (personal use)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _collection_date(event) -> date | None:
    """All-day (DATE) events are the published collection schedule; timed entries are reminders."""
    dt = event.get("dtstart")
    if dt is None:
        return None
    value = dt.dt
    if isinstance(value, datetime):
        return None
    if isinstance(value, date):
        return value
    return None


def next_collection(
    ics_bytes: bytes,
    *,
    on_or_after: date | None = None,
) -> tuple[date, str] | None:
    on_or_after = on_or_after or date.today()
    cal = Calendar.from_ical(ics_bytes)
    best: tuple[date, str] | None = None
    for event in cal.walk("VEVENT"):
        d = _collection_date(event)
        if d is None or d < on_or_after:
            continue
        summary = str(event.get("summary") or "").strip()
        if not summary:
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
