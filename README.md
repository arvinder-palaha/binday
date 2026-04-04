# binday

Fetch the **next scheduled waste collection** from a **public** `.ics` calendar URL (many councils publish an iCal or Google Calendar link). Output plain text or JSON for a Home Assistant `command_line` sensor.

## Your calendar URL

1. Use your council’s “bin day” or “waste collection” tools until they offer **add to calendar** / **iCal** / **subscribe**.
2. Copy the **public** feed URL (often ends in `.ics` or is a long `calendar.google.com/calendar/ical/...` URL).
3. Do **not** commit that URL to a public repo if you want to avoid tying the repo to a specific property or route. Set it only in local env or Home Assistant secrets.

### Example (Vale of White Horse)

- [Find your collection day / Binzone](https://www.whitehorsedc.gov.uk/vale-of-white-horse-district-council/recycling-rubbish-and-waste/when-is-your-collection-day/)
- [Add waste calendar to Google Calendar or iCal](https://www.whitehorsedc.gov.uk/vale-of-white-horse-district-council/recycling-rubbish-and-waste/when-is-your-collection-day/waste-collections-calendar/add-your-waste-calendar-to-google-calendar-or-ical/)

## Configuration

| Source | Precedence |
|--------|------------|
| `--ics-url` | Highest (overrides env) |
| `BINDAY_ICS_URL` | Used when `--ics-url` is omitted |

## Run locally

```bash
export BINDAY_ICS_URL='https://example.com/your-public-calendar.ics'
uv run python main.py
```

### Cached fetch (recommended)

Fetches the calendar at most once every 7 days (default) and stores it on disk.

```bash
export BINDAY_ICS_URL='https://example.com/your-public-calendar.ics'
uv run python main.py --format json --cache-path ./.cache/calendar.ics --max-age-days 7
```

Override URL for one run:

```bash
uv run python main.py --ics-url 'https://example.com/other.ics'
```

### Home Assistant OS / container

Install dependencies and copy `main.py` under `/config/binday/` (or your layout). Example with env inline (replace the URL; for secrets, use a shell wrapper or `!secret` expanded by your own include):

```bash
BINDAY_ICS_URL='https://example.com/your-public-calendar.ics' \
  python3 /config/binday/main.py --format json --cache-path /config/binday/calendar.ics --max-age-days 7
```

### Home Assistant `command_line` sensor

```yaml
command_line:
  - sensor:
      name: "Next bin collection"
      unique_id: next_bin_collection
      command: >-
        env BINDAY_ICS_URL="https://example.com/your-public-calendar.ics"
        python3 /config/binday/main.py
        --format json
        --cache-path /config/binday/calendar.ics
        --max-age-days 7
      value_template: "{{ value_json.summary }}"
      json_attributes:
        - date
        - longdate
        - days_until
        - ok
```

Point `BINDAY_ICS_URL` at your real feed (e.g. via a wrapper script that reads `secrets.yaml` if you prefer not to inline it).

### Dashboard: Markdown card (`longdate`)

The JSON field **`longdate`** is a readable label (for example `Wednesday 8th April`). Expose it on the sensor with **`longdate`** in `json_attributes` (as above), then use it in a **Markdown** card.

1. Open your dashboard → **Edit dashboard** → **Add card**.
2. Choose **Markdown** (or **Manual** / **YAML** and set `type: markdown`).
3. Set **content** to a template that reads the attribute. Replace `sensor.next_bin_collection` with your sensor’s **entity ID** if you named it differently (Profile → **Developer tools** → **States** to confirm).

Example card (YAML):

```yaml
type: markdown
title: Bin collection
content: |
  Next collection: **{{ state_attr('sensor.next_bin_collection', 'longdate') }}**

  {{ states('sensor.next_bin_collection') }}

  {% set d = state_attr('sensor.next_bin_collection', 'days_until') %}
  {% if d is not none %}
  In **{{ d }}** day{% if d != 1 %}s{% endif %}.
  {% endif %}
```

The first line uses **`longdate`** only. The next lines show the main state (**summary** from `value_template`) and **days_until**. If the sensor is unavailable, the template may render empty; you can wrap the block in `{% if states('sensor.next_bin_collection') not in ['unknown', 'unavailable'] %} … {% endif %}` if you want a fallback message.

## License

MIT — see [LICENSE](LICENSE).
