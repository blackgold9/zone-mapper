# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

Zone Mapper is a Home Assistant custom integration (HACS-compatible) that serves as the backend for the Zone Mapper Lovelace card. It persists zone shape definitions and exposes per-zone occupancy sensors based on tracked X/Y coordinate entities.

## Commands

```sh
scripts/bootstrap   # Install dependencies and pre-commit hooks (run once)
scripts/lint        # Format and lint with Ruff (auto-fixes applied)
scripts/develop     # Start a local Home Assistant instance for manual testing
```

Lint without auto-fix:
```sh
uv run ruff check .
uv run ruff format --check .
```

There is no automated test suite. Testing is done by running a local HA instance via `scripts/develop`.

## Architecture

All integration code lives in `custom_components/zone_mapper/`. The integration supports both YAML (`zone_mapper:` in `configuration.yaml`) and UI-based setup (config flow).

### State model

All runtime state is stored in `hass.data[DOMAIN]` under this structure:
```
hass.data["zone_mapper"] = {
    "locations": {
        "<location_name>": {
            "zones": { <zone_id>: { "shape": ..., "data": ..., "name": ... } },
            "entities": [ { "x": "<entity_id>", "y": "<entity_id>" }, ... ],
            "rotation_deg": <int>   # optional, per-location
        }
    },
    "platforms_loaded": set()   # tracks which locations have had platforms loaded
}
```

Location names are stored in friendly form (e.g. `"Office"`). Slugified versions (e.g. `office`) are used only for entity unique IDs and entity IDs.

### Data flow

1. The Lovelace card calls `zone_mapper.update_zone` service with shape/entity/rotation data.
2. `__init__.py` validates and normalizes the payload, updates `hass.data`, then fires `zone_mapper_zone_updated` on the event bus.
3. `sensor.py` (`ZoneCoordsSensor`) and `binary_sensor.py` (`ZonePresenceBinarySensor`) both listen for `zone_mapper_zone_updated` and refresh accordingly.
4. On HA startup, `__init__.py` bootstraps by scanning the entity registry for existing `zone_mapper_*_zone_*` sensors and calling `async_load_platform` for each discovered location — this restores state without any service call.
5. `ZoneCoordsSensor` extends `RestoreEntity` so it can re-seed `hass.data` from its persisted attributes on restart, before the binary sensors need to evaluate presence.

### Platforms

- **`sensor.py`** — `ZoneCoordsSensor`: one per zone. State = zone ID (integer). Attributes store the zone definition (`shape`, `data`), tracked entity pairs (`entities`), and `rotation_deg`. Acts as the persistence layer via `RestoreEntity`.
- **`binary_sensor.py`** — `ZonePresenceBinarySensor`: one per zone. Evaluates presence by reading X/Y entity states, applying `rotation_deg` rotation, then doing point-in-shape math (`_point_in_rect`, `_point_in_ellipse`, `_point_in_polygon`). Device class: `occupancy`.

### Coordinate system

The card uses a Y-down coordinate system (Y increases downward). Rotation is applied to tracked points before hit-testing, not to the zone shapes. The rotation formula in `_build_point_rotator` matches the card's visual rotation.

### Key constants (`const.py`)

- `POLYGON_MAX_POINTS = 32`, `POLYGON_MIN_POINTS = 3`
- Entity unique ID formats: `zone_mapper_{location}_zone_{zone_id}` (sensor), `zone_mapper_{location}_zone_{zone_id}_presence` (binary sensor)
- All shape coordinate values are rounded to integers (whole mm) at normalization time

### Linting

Ruff is configured with `select = ["ALL"]` and a small ignore list — this is strict. Pre-commit hooks run Ruff automatically. Run `scripts/lint` before committing.
