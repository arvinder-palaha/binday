# bin day

I want to automatically fetch the next schedule bin collection for my address.

## Binzone

[Binzone - Vale of White Horse](https://eform.whitehorsedc.gov.uk/ebase/BINZONE_DESKTOP.eb?SOVA_TAG=VALE&ebd=0&ebz=1_1774481007672)

1. Input postcode and click search
2. Select address
3. Next collection date and rubbish type displayed

## bin schedule calendar

[Add waste calendar to google calendar or iCal](https://www.whitehorsedc.gov.uk/vale-of-white-horse-district-council/recycling-rubbish-and-waste/when-is-your-collection-day/waste-collections-calendar/add-your-waste-calendar-to-google-calendar-or-ical/)

## Home Assistant

This project outputs the **next bin collection** for **Vale V1 Tuesdays** by downloading the council's public `.ics` calendar.

### Run locally

```bash
uv run python main.py
```

### Cached fetch (recommended)

Fetches the calendar at most once every 7 days (default) and stores it on disk.

```bash
# Local dev (any writable path)
uv run python main.py --format json --cache-path ./.cache/vale-v1-tuesday.ics --max-age-days 7

# Home Assistant OS / Container (use /config)
# uv run python main.py --format json --cache-path /config/binday/vale-v1-tuesday.ics --max-age-days 7
```

### Home Assistant `command_line` sensor

Run the script from Home Assistant and parse the JSON.

```yaml
command_line:
  - sensor:
      name: "Next bin collection"
      unique_id: next_bin_collection
      command: "python3 /config/binday/main.py --format json --cache-path /config/binday/vale-v1-tuesday.ics --max-age-days 7"
      value_template: "{{ value_json.summary }}"
      json_attributes:
        - date
        - days_until
        - ok
```

Then add the sensor to a dashboard card (Entities card or Markdown card).
