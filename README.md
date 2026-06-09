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

Copy `main.py` under `/config/binday/` (or your layout).

**Python packages:** The interpreter you run in the `command_line` sensor must have **`icalendar`** and **`recurring-ical-events`** installed — the same ones as in `pyproject.toml`. Use the **same** `python` (or `python3`) binary as in your sensor `command`:

```bash
python3 -m pip install 'icalendar>=6' 'recurring-ical-events>=3.8'
```

How you run that depends on your setup (HA OS, Container, supervised). Common patterns: **SSH & Web Terminal** add-on into the environment that sees `/config`, a small **venv** under `/config/binday/.venv` with `command` pointing to `/config/binday/.venv/bin/python`, or another host path you control. If imports fail, the command prints a traceback instead of JSON and the sensor may stay **unknown**.

Example run (replace the URL; for secrets, use a shell wrapper or `!secret` expanded by your own include):

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
      value_template: >-
        {% if value_json.ok is defined and value_json.ok %}
          {{ value_json.summary }}
        {% else %}
          {{ value_json.error | default('No collection data') }}
        {% endif %}
      json_attributes:
        - date
        - longdate
        - days_until
        - ok
```

Point `BINDAY_ICS_URL` at your real feed (e.g. via a wrapper script that reads `secrets.yaml` if you prefer not to inline it).

**`value_template` and JSON errors:** When the script succeeds but finds no event, it prints `{"ok": false, "error": "..."}` — there is no `summary`. The template above shows **`error`** in that case. If the command fails (network, bad URL, missing Python deps), Home Assistant may not get valid JSON at all; the entity can show **unknown** / **unavailable** until the next successful run. A minimal alternative is `{{ value_json.summary | default(value_json.error | default('Unknown'), true) }}` if you prefer a one-line template.

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

Example **Markdown** card with a table — **When** as `yyyy-mm-dd` and **Day** as the full weekday (e.g. `TUESDAY`):

```yaml
type: markdown
content: |
  | key | value |
  |:----|------:|
  | What | {{ states('sensor.next_bin_collection') }} |
  | When | {{ state_attr('sensor.next_bin_collection','date') }} |
  | Day | {{ as_datetime(state_attr('sensor.next_bin_collection', 'date')).strftime('%A').upper() }} |
  | Days until | {{ state_attr('sensor.next_bin_collection', 'days_until') }} |
```

## License

MIT — see [LICENSE](LICENSE).
