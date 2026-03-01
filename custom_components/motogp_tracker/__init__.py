"""MotoGP Tracker — intégration Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import (
    COORD_CONFIG,
    COORD_EVENT,
    COORD_LIVE,
    COORD_STANDINGS,
    DOMAIN,
    KEY_COORDINATORS,
)
from .coordinator import (
    MotoGPConfigCoordinator,
    MotoGPEventCoordinator,
    MotoGPLiveTimingCoordinator,
    MotoGPStandingsCoordinator,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


# ──────────────────────────────────────────────────────────────────────────────
# SETUP
# ──────────────────────────────────────────────────────────────────────────────

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    # 1. Config — bloquant : si ça rate, HA retentera automatiquement
    config_coord = MotoGPConfigCoordinator(hass)
    await config_coord.async_config_entry_first_refresh()

    # 2. Standings + Event — best-effort (capteurs "unavailable" si échec)
    standings_coord = MotoGPStandingsCoordinator(hass, config_coord)
    event_coord     = MotoGPEventCoordinator(hass, config_coord)

    for coord, label in [(standings_coord, "standings"), (event_coord, "event")]:
        try:
            await coord.async_config_entry_first_refresh()
        except Exception as err:
            _LOGGER.warning("[MotoGP] Premier refresh %s échoué : %s", label, err)

    # 3. Live — pas de premier refresh forcé (actif uniquement en course)
    live_coord = MotoGPLiveTimingCoordinator(hass, event_coord)

    # 4. Stockage
    hass.data[DOMAIN][entry.entry_id] = {
        KEY_COORDINATORS: {
            COORD_CONFIG:    config_coord,
            COORD_STANDINGS: standings_coord,
            COORD_EVENT:     event_coord,
            COORD_LIVE:      live_coord,
        }
    }

    # 5. Plateformes
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # 6. Services
    _register_services(hass, entry)

    _LOGGER.info("[MotoGP] Intégration initialisée ✅")
    return True


# ──────────────────────────────────────────────────────────────────────────────
# UNLOAD / RELOAD
# ──────────────────────────────────────────────────────────────────────────────

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            for svc in ("refresh_config", "refresh_standings", "refresh_event", "refresh_live"):
                if hass.services.has_service(DOMAIN, svc):
                    hass.services.async_remove(DOMAIN, svc)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# ──────────────────────────────────────────────────────────────────────────────
# SERVICES
# Ces services permettent de forcer un rafraîchissement depuis une automation
# ou un appui de bouton dans le dashboard.
# ──────────────────────────────────────────────────────────────────────────────

def _register_services(hass: HomeAssistant, entry: ConfigEntry) -> None:
    if hass.services.has_service(DOMAIN, "refresh_config"):
        return  # déjà enregistrés (multi-entries protection)

    def _coords() -> dict:
        return hass.data[DOMAIN][entry.entry_id][KEY_COORDINATORS]

    async def refresh_config(call: ServiceCall) -> None:
        await _coords()[COORD_CONFIG].async_request_refresh()

    async def refresh_standings(call: ServiceCall) -> None:
        await _coords()[COORD_STANDINGS].async_request_refresh()

    async def refresh_event(call: ServiceCall) -> None:
        coords = _coords()
        await coords[COORD_EVENT].async_request_refresh()
        if (coords[COORD_EVENT].data or {}).get("race_uuid"):
            await coords[COORD_LIVE].async_request_refresh()

    async def refresh_live(call: ServiceCall) -> None:
        await _coords()[COORD_LIVE].async_request_refresh()

    hass.services.async_register(DOMAIN, "refresh_config",    refresh_config)
    hass.services.async_register(DOMAIN, "refresh_standings", refresh_standings)
    hass.services.async_register(DOMAIN, "refresh_event",     refresh_event)
    hass.services.async_register(DOMAIN, "refresh_live",      refresh_live)
    _LOGGER.debug("[MotoGP] Services enregistrés")
