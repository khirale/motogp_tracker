from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COORD_EVENT, COORD_LIVE, COORD_STANDINGS, DOMAIN, KEY_COORDINATORS
from .coordinator import (
    MotoGPEventCoordinator,
    MotoGPLiveTimingCoordinator,
    MotoGPStandingsCoordinator,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coords = hass.data[DOMAIN][entry.entry_id][KEY_COORDINATORS]

    async_add_entities([
        MotoGPNextEventSensor(coords[COORD_EVENT]),
        MotoGPNextRaceStartSensor(coords[COORD_EVENT]),
        MotoGPSessionsSensor(coords[COORD_EVENT]),
        MotoGPRiderStandingsSensor(coords[COORD_STANDINGS]),
        MotoGPTeamStandingsSensor(coords[COORD_STANDINGS]),
        MotoGPLiveTimingSensor(coords[COORD_LIVE]),
    ])

class _MotoGPSensor(CoordinatorEntity, SensorEntity):

    _attr_should_poll = False

    def __init__(self, coordinator: CoordinatorEntity, unique_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = unique_id

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

class MotoGPNextEventSensor(_MotoGPSensor):

    _attr_name = "MotoGP Prochain Événement"
    _attr_icon = "mdi:calendar-star"

    def __init__(self, coordinator: MotoGPEventCoordinator) -> None:
        super().__init__(coordinator, "motogp_next_event")

    @property
    def native_value(self) -> str | None:
        event = (self.coordinator.data or {}).get("event")
        return event["name"] if event else "no_upcoming_event"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = (self.coordinator.data or {}).get("event")
        if not event:
            return {}
        return {
            "event_uuid":       event["uuid"],
            "status":           event["status"],
            "date_start":       event["date_start"],
            "date_end":         event["date_end"],
            "date_start_local": event["date_start_local"],
            "date_end_local":   event["date_end_local"],
            "country_name":     event["country_name"],
            "country_iso":      event["country_iso"],
            "flag_url":         event["flag_url"],
            "circuit_name":     event["circuit_name"],
            "circuit_slug":     event["circuit_slug"],
            "circuit_svg":      event["circuit_svg"],
        }

class MotoGPNextRaceStartSensor(_MotoGPSensor):

    _attr_name = "MotoGP Départ Course"
    _attr_icon = "mdi:flag-checkered"

    def __init__(self, coordinator: MotoGPEventCoordinator) -> None:
        super().__init__(coordinator, "motogp_next_race_start")

    def _race_session(self) -> dict | None:
        sessions = (self.coordinator.data or {}).get("sessions", [])
        return next((s for s in sessions if s["type"] == "RAC"), None)

    @property
    def native_value(self) -> str | None:
        race = self._race_session()
        return race["start_local"] if race else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        race = self._race_session()
        return {
            "start_utc":      race["start_utc"] if race else None,
            "session_status": race["status"] if race else None,
            "race_uuid":      (self.coordinator.data or {}).get("race_uuid"),
        }

class MotoGPSessionsSensor(_MotoGPSensor):

    _attr_name = "MotoGP Sessions"
    _attr_icon = "mdi:timer-sand"

    def __init__(self, coordinator: MotoGPEventCoordinator) -> None:
        super().__init__(coordinator, "motogp_sessions")

    @property
    def native_value(self) -> str:
        sessions = (self.coordinator.data or {}).get("sessions", [])
        return f"{len(sessions)} sessions" if sessions else "no_data"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "race_uuid": data.get("race_uuid"),
            "sessions":  data.get("sessions", []),

        }

class MotoGPRiderStandingsSensor(_MotoGPSensor):

    _attr_name = "MotoGP Classement Pilotes"
    _attr_icon = "mdi:trophy"

    def __init__(self, coordinator: MotoGPStandingsCoordinator) -> None:
        super().__init__(coordinator, "motogp_rider_standings")

    @property
    def native_value(self) -> str | None:
        riders = (self.coordinator.data or {}).get("riders", [])
        return riders[0]["full_name"] if riders else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "season_year": data.get("season_year"),
            "count":       len(data.get("riders", [])),
            "standings":   data.get("riders", []),

        }

class MotoGPTeamStandingsSensor(_MotoGPSensor):

    _attr_name = "MotoGP Classement Équipes"
    _attr_icon = "mdi:racing-helmet"

    def __init__(self, coordinator: MotoGPStandingsCoordinator) -> None:
        super().__init__(coordinator, "motogp_team_standings")

    @property
    def native_value(self) -> str | None:
        teams = (self.coordinator.data or {}).get("teams", [])
        return teams[0]["name"] if teams else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "season_year": data.get("season_year"),
            "count":       len(data.get("teams", [])),
            "standings":   data.get("teams", []),

        }

class MotoGPLiveTimingSensor(_MotoGPSensor):

    _attr_name = "MotoGP Live Timing"
    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: MotoGPLiveTimingCoordinator) -> None:
        super().__init__(coordinator, "motogp_live_timing")

    @property
    def native_value(self) -> str:
        return (self.coordinator.data or {}).get("session_status", "inactive")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return {
            "active":         data.get("active", False),
            "total_laps":     data.get("total_laps"),
            "current_lap":    data.get("current_lap"),
            "race_uuid":      data.get("race_uuid"),
            "classification": data.get("classification", []),

        }
