"""Coordinateurs de données MotoGP Tracker."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import aiohttp
import pytz

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.util.dt as dt_util

from .const import (
    BASE_URL,
    CIRCUIT_SLUGS,
    CIRCUIT_SVG_PATH,
    COORD_CONFIG,
    COORD_EVENT,
    COORD_LIVE,
    COORD_STANDINGS,
    DOMAIN,
    INTERVAL_CONFIG,
    INTERVAL_EVENT,
    INTERVAL_LIVE,
    INTERVAL_STANDINGS,
    LIVE_STATUSES,
    SESSION_TYPES_KEPT,
    TZ_PARIS,
)

_LOGGER = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# UTILITAIRE : requête HTTP
# ──────────────────────────────────────────────────────────────────────────────

async def _fetch(endpoint: str, timeout: int = 20) -> Any:
    """GET vers l'API Pulselive.
    - Retourne None sur 404 (session inactive, pas une erreur).
    - Logue l'URL appelée et le JSON brut reçu en DEBUG.
    """
    url = f"{BASE_URL}/{endpoint}"
    _LOGGER.debug("[MotoGP API] --> GET %s", url)
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as session:
        async with session.get(url) as resp:
            if resp.status == 404:
                _LOGGER.debug("[MotoGP API] <-- 404 (inactif) %s", url)
                return None
            resp.raise_for_status()
            data = await resp.json()
            _LOGGER.debug("[MotoGP API] <-- %s JSON: %s", url, data)
            return data


# ──────────────────────────────────────────────────────────────────────────────
# UTILITAIRE : conversion heure Paris
# ──────────────────────────────────────────────────────────────────────────────

def _to_paris(dt_str: str | None) -> str:
    """Convertit une date ISO UTC en heure de Paris (YYYY-MM-DD HH:MM)."""
    if not dt_str:
        return "n/a"
    try:
        tz = dt_util.get_time_zone(TZ_PARIS)
        dt_utc = datetime.fromisoformat(dt_str.replace("Z", "")).replace(tzinfo=pytz.UTC)
        return dt_utc.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "n/a"


# ──────────────────────────────────────────────────────────────────────────────
# COORDINATOR 1 : CONFIG
# Frequence : 6h
# Donnees   : season_id, season_year, category_id
# Utilise par : StandingsCoordinator, EventCoordinator
# ──────────────────────────────────────────────────────────────────────────────

class MotoGPConfigCoordinator(DataUpdateCoordinator[dict]):

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{COORD_CONFIG}",
            update_interval=INTERVAL_CONFIG,
        )

    async def _async_update_data(self) -> dict:
        try:
            seasons: list = await _fetch("results/seasons")
        except Exception as err:
            raise UpdateFailed(f"Saisons inaccessibles : {err}") from err

        current = next((s for s in seasons if s.get("current") is True), None)
        if not current:
            raise UpdateFailed("Aucune saison courante trouvee.")

        season_id   = str(current["id"])
        season_year = str(current.get("year", ""))

        try:
            categories: list = await _fetch(f"results/categories?seasonUuid={season_id}")
        except Exception as err:
            raise UpdateFailed(f"Categories inaccessibles : {err}") from err

        cat = next((c for c in categories if c.get("name") == "MotoGP™"), None)
        if not cat:
            raise UpdateFailed("Categorie MotoGP™ introuvable.")

        _LOGGER.info("[MotoGP Config] Saison %s (%s), categorie %s", season_year, season_id, cat["id"])
        return {
            "season_id":   season_id,
            "season_year": season_year,
            "category_id": str(cat["id"]),
        }


# ──────────────────────────────────────────────────────────────────────────────
# COORDINATOR 2 : STANDINGS
# Frequence : 3h
# Donnees   : classement pilotes (brut API) + classement equipes (calcule)
# Utilise par : MotoGPRiderStandingsSensor, MotoGPTeamStandingsSensor
# ──────────────────────────────────────────────────────────────────────────────

class MotoGPStandingsCoordinator(DataUpdateCoordinator[dict]):

    def __init__(self, hass: HomeAssistant, config: MotoGPConfigCoordinator) -> None:
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{COORD_STANDINGS}",
            update_interval=INTERVAL_STANDINGS,
        )
        self._config = config

    async def _async_update_data(self) -> dict:
        if not self._config.data:
            raise UpdateFailed("Config non disponible.")

        season_id   = self._config.data["season_id"]
        category_id = self._config.data["category_id"]

        try:
            raw = await _fetch(
                f"results/standings?seasonUuid={season_id}&categoryUuid={category_id}"
            )
        except Exception as err:
            raise UpdateFailed(f"Standings inaccessibles : {err}") from err

        # raw peut etre None (404) si pas encore de classement en debut de saison
        if raw is None:
            _LOGGER.debug("[MotoGP Standings] Pas de classement disponible (404)")
            return {"season_year": self._config.data["season_year"], "riders": [], "teams": []}

        # --- Normalisation du format de reponse ---
        if isinstance(raw, dict) and "classification" in raw:
            riders_raw: list = raw["classification"]
        elif isinstance(raw, dict) and "items" in raw:
            riders_raw = raw["items"]
        elif isinstance(raw, list):
            riders_raw = raw
        else:
            _LOGGER.warning("[MotoGP Standings] Format inattendu : %s", type(raw))
            riders_raw = []

        # --- Normalisation pilotes ---
        riders: list[dict] = []
        for r in riders_raw:
            rider_info = r.get("rider") or {}
            team_info  = r.get("team") or {}
            country    = rider_info.get("country") or {}
            riders.append({
                "position":    r.get("position"),
                "full_name":   rider_info.get("full_name", ""),
                "number":      str(rider_info.get("number", "")),
                "country_iso": (country.get("iso", "") or "").lower(),
                "country_name":country.get("name", ""),
                "team":        team_info.get("name", ""),
                "points":      r.get("points", 0),
                "wins":        r.get("race_wins", 0),
                "podiums":     r.get("podiums", 0),
            })

        # --- Calcul classement equipes ---
        teams_pts: dict[str, int] = {}
        for r in riders:
            team = r["team"] or "Unknown"
            teams_pts[team] = teams_pts.get(team, 0) + int(r["points"] or 0)

        teams: list[dict] = [
            {"position": i, "name": name, "points": pts}
            for i, (name, pts) in enumerate(
                sorted(teams_pts.items(), key=lambda x: x[1], reverse=True), start=1
            )
        ]

        _LOGGER.debug("[MotoGP Standings] %d pilotes, %d equipes", len(riders), len(teams))
        return {
            "season_year": self._config.data["season_year"],
            "riders":      riders,
            "teams":       teams,
        }


# ──────────────────────────────────────────────────────────────────────────────
# COORDINATOR 3 : EVENT
# Frequence : 1h
# Donnees   : prochain GP + ses sessions
# Utilise par : MotoGPNextEventSensor, MotoGPNextRaceStartSensor,
#               MotoGPSessionsSensor + indirectement LiveCoordinator
# ──────────────────────────────────────────────────────────────────────────────

class MotoGPEventCoordinator(DataUpdateCoordinator[dict]):

    def __init__(self, hass: HomeAssistant, config: MotoGPConfigCoordinator) -> None:
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{COORD_EVENT}",
            update_interval=INTERVAL_EVENT,
        )
        self._config = config

    async def _async_update_data(self) -> dict:
        if not self._config.data:
            raise UpdateFailed("Config non disponible.")

        season_id   = self._config.data["season_id"]
        category_id = self._config.data["category_id"]

        try:
            events: list = await _fetch(f"results/events?seasonUuid={season_id}")
        except Exception as err:
            raise UpdateFailed(f"Events inaccessibles : {err}") from err

        if not isinstance(events, list):
            raise UpdateFailed(f"Format events inattendu : {type(events)}")

        event = self._pick_next(events)
        if not event:
            _LOGGER.info("[MotoGP Event] Aucun evenement a venir.")
            return {"event": None, "sessions": [], "race_uuid": None}

        # --- Donnees de l'evenement ---
        circuit = event.get("circuit") or {}
        country = event.get("country") or {}
        cname   = (circuit.get("name") or circuit.get("place") or "").strip()
        slug    = CIRCUIT_SLUGS.get(cname.lower(), "")
        iso     = (country.get("iso", "") or "").lower()

        if not slug:
            _LOGGER.warning("[MotoGP Event] Slug inconnu pour '%s'", cname)

        event_data = {
            "uuid":             str(event.get("id") or event.get("uuid") or ""),
            "name":             event.get("name", ""),
            "status":           (event.get("status") or "").upper(),
            "date_start":       event.get("date_start", ""),
            "date_end":         event.get("date_end", ""),
            "date_start_local": _to_paris(event.get("date_start")),
            "date_end_local":   _to_paris(event.get("date_end")),
            "country_name":     country.get("name", ""),
            "country_iso":      iso,
            "flag_url":         f"https://flagcdn.com/48x36/{iso}.png" if iso else "",
            "circuit_name":     cname,
            "circuit_slug":     slug,
            "circuit_svg":      CIRCUIT_SVG_PATH.format(slug=slug) if slug else "",
        }

        # --- Sessions ---
        sessions, race_uuid = await self._fetch_sessions(event_data["uuid"], category_id)

        _LOGGER.info(
            "[MotoGP Event] %s — slug=%s — %d sessions — race_uuid=%s",
            event_data["name"], slug, len(sessions), race_uuid,
        )
        return {
            "event":     event_data,
            "sessions":  sessions,
            "race_uuid": race_uuid,
        }

    @staticmethod
    def _pick_next(events: list) -> dict | None:
        """Retourne le prochain GP (hors tests).
        Priorite a l'evenement CURRENT, sinon le plus proche a venir.
        """
        # On exclut systematiquement les sessions de test
        gps = [e for e in events if not e.get("test", False)]

        for e in gps:
            if (e.get("status") or "").upper() == "CURRENT":
                return e

        now = dt_util.now()
        upcoming: list[tuple[datetime, dict]] = []
        for e in gps:
            ds = e.get("date_start")
            if not ds:
                continue
            try:
                dt = datetime.fromisoformat(ds)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=pytz.UTC)
                if dt > now:
                    upcoming.append((dt, e))
            except Exception:
                continue

        return min(upcoming, key=lambda x: x[0])[1] if upcoming else None

    @staticmethod
    async def _fetch_sessions(event_uuid: str, category_id: str) -> tuple[list[dict], str | None]:
        """Recupere et normalise les sessions d'un evenement."""
        try:
            raw: list = await _fetch(
                f"results/sessions?eventUuid={event_uuid}&categoryUuid={category_id}"
            )
        except Exception as err:
            _LOGGER.warning("[MotoGP Event] Sessions inaccessibles : %s", err)
            return [], None

        if not isinstance(raw, list):
            return [], None

        sessions: list[dict] = []
        race_uuid: str | None = None

        for s in raw:
            s_type = (s.get("type") or "").upper()
            if s_type not in SESSION_TYPES_KEPT:
                continue
            sid = str(s.get("id") or "")
            sessions.append({
                "id":          sid,
                "type":        s_type,
                "start_utc":   s.get("date", ""),
                "start_local": _to_paris(s.get("date")),
                "status":      (s.get("status") or "").upper(),
            })
            if s_type == "RAC":
                race_uuid = sid

        sessions.sort(key=lambda s: s.get("start_utc") or "")
        return sessions, race_uuid


# ──────────────────────────────────────────────────────────────────────────────
# COORDINATOR 4 : LIVE TIMING
# Frequence : 30s — appel API conditionnel (seulement si race_uuid disponible)
# Donnees   : classement complet tous pilotes + infos session
# Utilise par : MotoGPLiveTimingSensor
# ──────────────────────────────────────────────────────────────────────────────

class MotoGPLiveTimingCoordinator(DataUpdateCoordinator[dict]):

    def __init__(self, hass: HomeAssistant, event: MotoGPEventCoordinator) -> None:
        super().__init__(
            hass, _LOGGER,
            name=f"{DOMAIN}_{COORD_LIVE}",
            update_interval=INTERVAL_LIVE,
        )
        self._event = event

    async def _async_update_data(self) -> dict:
        race_uuid = (self._event.data or {}).get("race_uuid")

        # Pas de race_uuid = pas d'appel API
        if not race_uuid:
            return {
                "active":         False,
                "session_status": "inactive",
                "total_laps":     None,
                "current_lap":    None,
                "race_uuid":      None,
                "classification": [],
            }

        try:
            raw = await _fetch(f"timing-gateway/livetiming-lite?sessionUuid={race_uuid}")
        except Exception as err:
            raise UpdateFailed(f"Live timing inaccessible : {err}") from err

        # None = 404 = session pas encore demarree, c'est normal
        if raw is None:
            _LOGGER.debug("[MotoGP Live] 404 — session non demarree (race_uuid=%s)", race_uuid)
            return {
                "active":         False,
                "session_status": "waiting",
                "total_laps":     None,
                "current_lap":    None,
                "race_uuid":      race_uuid,
                "classification": [],
            }

        head           = raw.get("head") or {}
        session_status = (head.get("session_status_name") or "").lower()
        total_laps     = head.get("num_laps")
        is_active      = session_status in LIVE_STATUSES

        # --- Normalisation des pilotes ---
        riders_raw = raw.get("rider") or {}
        classification: list[dict] = []

        for _, r in riders_raw.items():
            classification.append({
                "pos":       r.get("pos"),
                "number":    str(r.get("rider_number", "")),
                "name":      f"{r.get('rider_name', '')} {r.get('rider_surname', '')}".strip(),
                "nation":    r.get("rider_nation", ""),
                "team":      r.get("team_name", ""),
                "bike":      r.get("bike_name", ""),
                "laps":      r.get("num_lap"),
                "gap_first": r.get("gap_first", "—"),
                "last_lap":  r.get("last_lap_time", ""),
                "status":    r.get("status_name", ""),
            })

        classification.sort(
            key=lambda x: x["pos"] if isinstance(x["pos"], int) and x["pos"] > 0 else 999
        )

        leader      = next((r for r in classification if r["pos"] == 1), None)
        current_lap = leader["laps"] if leader else None

        _LOGGER.debug(
            "[MotoGP Live] status=%s active=%s pilotes=%d tour=%s/%s",
            session_status, is_active, len(classification), current_lap, total_laps,
        )
        return {
            "active":         is_active,
            "session_status": session_status,
            "total_laps":     total_laps,
            "current_lap":    current_lap,
            "race_uuid":      race_uuid,
            "classification": classification,
        }
