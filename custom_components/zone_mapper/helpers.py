"""Shared helpers for Zone Mapper platform entities."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import entity_registry as er

from .const import DATA_LOCATIONS, DOMAIN, STORE_ENTITIES

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def link_entity_to_tracked_device(
    hass: HomeAssistant, entity_id: str, location_name: str
) -> None:
    """
    Link a zone entity to the device of its first tracked X/Y sensor.

    No-op when tracked entities are not yet set, the source entity has no
    device, or the device link is already correct.
    """
    integration = hass.data.get(DOMAIN, {})
    tracked = (
        integration.get(DATA_LOCATIONS, {})
        .get(location_name, {})
        .get(STORE_ENTITIES, [])
    )
    if not isinstance(tracked, list) or not tracked:
        return
    first_pair = tracked[0]
    x_id = first_pair.get("x") if isinstance(first_pair, dict) else None
    if not isinstance(x_id, str):
        return

    entity_reg = er.async_get(hass)
    source = entity_reg.async_get(x_id)
    if not source or not source.device_id:
        return

    target = entity_reg.async_get(entity_id)
    if not target or target.device_id == source.device_id:
        return

    try:
        entity_reg.async_update_entity(entity_id, device_id=source.device_id)
    except ValueError:
        _LOGGER.debug(
            "Zone Mapper: could not link %s to device %s (device may no longer exist)",
            entity_id,
            source.device_id,
        )
