# ----------------------------------------------------------------------
# IMPORTS
# ----------------------------------------------------------------------
import logging
import aiohttp
import html
import pytz
import asyncio
from datetime import datetime
from typing import Any, Dict, Optional, List
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.util import Throttle
from homeassistant.helpers.event import async_call_later
import homeassistant.util.dt as dt_util
from .entity import MotoGPEntityBase
from .const import DOMAIN, _BASE_URL, TZ_PARIS, UPDATE_INTERVAL_CONFIG, ATTRIB_HTML, ATTRIB_LAST_UPDATE

# ----------------------------------------------------------------------
# LOGGER
# ----------------------------------------------------------------------
_LOGGER = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# UTILS
# ----------------------------------------------------------------------

def to_local(dt_str: str) -> str:
    try:
        TZ = dt_util.get_time_zone(TZ_PARIS)
        dt_utc = datetime.fromisoformat(dt_str.replace("Z", "")).astimezone(pytz.UTC)
        return dt_utc.astimezone(TZ).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "n/a"

async def async_fetch_data(endpoint: str, timeout: int = 20):
    url = f"{_BASE_URL}/{endpoint}"
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as resp:
                resp.raise_for_status()
                return await resp.json()
    except Exception as err:
        _LOGGER.error(f"[MotoGP] Erreur HTTP {url}: {err}")
        return None

# ----------------------------------------------------------------------
# SETUP
# ----------------------------------------------------------------------
async def async_setup_entry(hass: HomeAssistant, entry: ConfigType, async_add_entities: AddEntitiesCallback):
    _LOGGER.debug("[MotoGP] Initialisation séquentielle des capteurs")
    config_sensor = MotoGPConfigSensor(hass)
    async_add_entities([config_sensor], update_before_add=False)
    await config_sensor.async_update()
    for _ in range(30):
        if config_sensor.is_ready:
            break
        await asyncio.sleep(1)
    else:
        _LOGGER.warning("[MotoGP] Configuration non prête après délai, autres capteurs non ajoutés.")
        return
    standings_sensor = MotoGPStandingsSensor(hass, config_sensor)
    teams_sensor = MotoGPTeamsStandingsSensor(hass, standings_sensor)
    event_sensor = MotoGPNextEventSensor(hass, config_sensor)
    sessions_sensor = MotoGPNextSessionsSensor(hass, config_sensor, event_sensor)
    race_start_sensor = MotoGPNextRaceStartSensor(hass, sessions_sensor)
    live_timing_sensor = MotoGPLiveTimingSensor(hass, sessions_sensor)
    sensors = [standings_sensor, teams_sensor, event_sensor, sessions_sensor, race_start_sensor, live_timing_sensor]
    async_add_entities(sensors, update_before_add=False)

    for s in sensors:
        hass.async_create_task(s.async_update())

    if sessions_sensor.race_uuid:
        _LOGGER.debug("[MotoGP Setup] Déclenchement initial du Live Timing")
        hass.async_create_task(live_timing_sensor.async_update())
    _LOGGER.info("[MotoGP] Tous les capteurs MotoGP ont été ajoutés avec succès.")

# ----------------------------------------------------------------------
# SENSOR: CONFIG
# ----------------------------------------------------------------------

class MotoGPConfigSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._attr_name = "MotoGP Configuration"
        self._attr_unique_id = "motogp_config"
        self._attr_icon = "mdi:wrench"
        self._attr_should_poll = False
        self._attr_native_value = STATE_UNKNOWN
        self._season_id = None
        self._season_year = None
        self._category_id = None

    async def async_added_to_hass(self):
        _LOGGER.debug("[MotoGP Configuration] async_added_to_hass() appelé")
        self._attr_native_value = "waiting"
        self.async_write_ha_state()
        async def _delayed_update(_):
            _LOGGER.debug("[MotoGP Configuration] Lancement update différé")
            await self.async_update()
        async_call_later(self.hass, 1, _delayed_update)

    @Throttle(UPDATE_INTERVAL_CONFIG)
    async def async_update(self) -> None:
        _LOGGER.debug("[MotoGP Configuration] async_update() lancé")
        try:
            season_data = await async_fetch_data("results/seasons", timeout=15)
            current_season = next((s for s in season_data if s.get("current") is True), None)
            self._season_id = str(current_season.get("id")) if current_season else "unknown"
            self._season_year = str(current_season.get("year")) if current_season else "unknown"
            _LOGGER.debug(f"[MotoGP Configuration] Season id: {self._season_id}, year: {self._season_year}")
        except Exception as e:
            _LOGGER.error(f"[MotoGP Configuration] Erreur récupération season: {e}")
            self._season_id = "unknown"
            self._season_year = "unknown"
        self._category_id = "unknown"
        if self._season_id and self._season_id not in ["unknown", STATE_UNAVAILABLE]:
            try:
                endpoint = f"results/categories?seasonUuid={self._season_id}"
                category_data = await async_fetch_data(endpoint, timeout=15)
                moto_category = next((c for c in category_data if c.get("name") == "MotoGP™"), None)
                self._category_id = str(moto_category.get("id")) if moto_category else "unknown"
                _LOGGER.debug(f"[MotoGP Configuration] Category id: {self._category_id}")
            except Exception as e:
                _LOGGER.error(f"[MotoGP Configuration] Erreur récupération category: {e}")
                self._category_id = "unknown"
        is_ready = self._is_ready()
        self._attr_native_value = "ok" if is_ready else "waiting"
        self._attr_extra_state_attributes = {
            "year": self._season_year,
            "season_id": self._season_id,
            "category_id": self._category_id,
            "is_ready": is_ready,
        }
        self.async_write_ha_state()
        if is_ready:
            _LOGGER.info("[MotoGP Configuration] ✅ Configuration complète — déclenchement capteurs dépendants.")
            if DOMAIN in self.hass.data:
                for key in ("event", "standings"):
                    if key in self.hass.data[DOMAIN]:
                        self.hass.async_create_task(self.hass.data[DOMAIN][key].async_update())

    def _is_ready(self) -> bool:
        return all(x not in ["unknown", STATE_UNAVAILABLE, None] for x in [self._season_id, self._category_id])

    @property
    def is_ready(self) -> bool:
        return self._is_ready()

    @property
    def native_value(self):
        return self._attr_native_value

    @property
    def season_id(self) -> str:
        return self._season_id or "unknown"

    @property
    def category_id(self) -> str:
        return self._category_id or "unknown"

    @property
    def season_year(self) -> str:
        return self._season_year or "unknown"

# ----------------------------------------------------------------------
# SENSOR: STANDINGS
# ----------------------------------------------------------------------

class MotoGPStandingsSensor(MotoGPEntityBase):
    def __init__(self, hass, config_sensor: MotoGPConfigSensor):
        super().__init__(hass, "MotoGP Standings", "motogp_standings", "mdi:trophy")
        self.config_sensor = config_sensor
        self._standings: List[Dict[str, Any]] = []
        self._attr_native_value = STATE_UNKNOWN
        self._attr_available = False

    async def async_update(self):
        if not self.config_sensor.is_ready:
            self._attr_native_value = "waiting"
            self._attr_available = False
            self.async_write_ha_state()
            return

        season_id = self.config_sensor.season_id
        category_id = self.config_sensor.category_id
        endpoint = f"results/standings?seasonUuid={season_id}&categoryUuid={category_id}"
        _LOGGER.debug(f"[MotoGP Standings] Récupération du classement via {endpoint}")
        data = await async_fetch_data(endpoint)

        if not data:
            _LOGGER.warning("[MotoGP Standings] Aucune donnée reçue de l’API.")
            self._attr_native_value = "unavailable"
            self._attr_available = False
            self.async_write_ha_state()
            return

        classement = []
        pdf_url = data.get("file")
        xml_url = data.get("xmlFile")
        if isinstance(data, dict) and "classification" in data:
            classement = data.get("classification", [])
            _LOGGER.debug(f"[MotoGP Standings] Format 'classification' détecté ({len(classement)} entrées)")
        elif isinstance(data, dict) and "items" in data:
            classement = data.get("items", [])
            _LOGGER.debug(f"[MotoGP Standings] Format 'items' détecté ({len(classement)} entrées)")
        elif isinstance(data, list):
            classement = data
            _LOGGER.debug(f"[MotoGP Standings] Format 'list' détecté ({len(classement)} entrées)")
        else:
            _LOGGER.warning(f"[MotoGP Standings] Format inattendu : {type(data)} — contenu brut: {data}")

        table = [
            "<table style='width:100%; border-collapse:collapse; text-align:center;'>",
            "<thead><tr style='background:#222; color:#fff;'>",
            "<th style='padding:4px;'>Pos</th>",
            "<th style='padding:4px;'>Flag</th>",
            "<th style='padding:4px;'>Rider</th>",
            "<th style='padding:4px;'>Team</th>",
            "<th style='padding:4px;'>Points</th>",
            "<th style='padding:4px;'>Wins</th>",
            "<th style='padding:4px;'>Podiums</th>",
            "</tr></thead><tbody>",
        ]

        for row in classement:
            pos = row.get("position", "")
            rider = html.escape(row.get("rider", {}).get("full_name", ""))
            team = html.escape(row.get("team", {}).get("name", "") or "")
            points = row.get("points", "")
            wins = row.get("race_wins", 0)
            podiums = row.get("podiums", 0)
            iso = (row.get("rider", {}).get("country", {}).get("iso", "") or "").lower()
            flag = f"<img src='https://flagcdn.com/24x18/{iso}.png' style='vertical-align:middle;'>"
            
            if str(pos) == "1":
                bg = "#ffd70044"
            elif str(pos) == "2":
                bg = "#c0c0c044"
            elif str(pos) == "3":
                bg = "#cd7f3244"
            else:
                bg = "transparent"

            table.append(
                f"<tr style='background:{bg}; border-bottom:1px solid #555;'>"
                f"<td style='padding:4px;'>{pos}</td>"
                f"<td style='padding:4px;'>{flag}</td>"
                f"<td style='padding:4px; text-align:left;'>{rider}</td>"
                f"<td style='padding:4px; text-align:left;'>{team}</td>"
                f"<td style='padding:4px;'>{points}</td>"
                f"<td style='padding:4px;'>{wins}</td>"
                f"<td style='padding:4px;'>{podiums}</td>"
                "</tr>"
            )

        table.append("</tbody></table>")
        html_table = "\n".join(table)

        self._standings = classement
        self._attr_native_value = "ok"
        self._attr_extra_state_attributes = {
            "count": len(classement),
            "standings": classement,
            "pdf_file": pdf_url,
            "xml_file": xml_url,
            ATTRIB_HTML: html_table,
            "ATTRIB_HTML_TEXT": "Classement MotoGP",
            ATTRIB_LAST_UPDATE: dt_util.now().isoformat(),
        }
        self._attr_available = True
        _LOGGER.debug(f"[MotoGP Standings] Classement récupéré ({len(classement)} entrées)")

        if DOMAIN in self.hass.data and "teams" in self.hass.data[DOMAIN]:
            _LOGGER.debug("[MotoGP Standings] Déclenchement de la mise à jour du classement Teams")
            self.hass.async_create_task(self.hass.data[DOMAIN]["teams"].async_update())

        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return True

# ----------------------------------------------------------------------
# SENSOR: TEAMS
# ----------------------------------------------------------------------

class MotoGPTeamsStandingsSensor(MotoGPEntityBase):
    def __init__(self, hass, standings_sensor: MotoGPStandingsSensor):
        super().__init__(hass, "MotoGP Teams Standings", "motogp_teams_standings", "mdi:racing-helmet")
        self.standings_sensor = standings_sensor
        self._attr_native_value = STATE_UNKNOWN
        self._attr_available = False
        
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["teams"] = self

    async def async_update(self):
        standings = getattr(self.standings_sensor, "_standings", [])
        if not standings:
            self._attr_native_value = "waiting"
            self._attr_available = False
            self.async_write_ha_state()
            return

        teams_points: Dict[str, int] = {}
        for rider in standings:
            team = rider.get("team", {}).get("name") or "Unknown"
            pts = int(rider.get("points") or 0)
            teams_points[team] = teams_points.get(team, 0) + pts

        ordered = sorted(teams_points.items(), key=lambda x: x[1], reverse=True)

        table = [
            "<table style='width:100%; border-collapse:collapse; text-align:center;'>",
            "<thead><tr style='background:#222; color:#fff;'>",
            "<th style='padding:4px;'>Pos</th>",
            "<th style='padding:4px;'>Team</th>",
            "<th style='padding:4px;'>Points</th>",
            "</tr></thead><tbody>",
        ]

        for idx, (team, pts) in enumerate(ordered, start=1):
            if idx == 1:
                bg = "#ffd70044"
            elif idx == 2:
                bg = "#c0c0c044"
            elif idx == 3:
                bg = "#cd7f3244"
            else:
                bg = "transparent"

            table.append(
                f"<tr style='background:{bg}; border-bottom:1px solid #555;'>"
                f"<td style='padding:4px;'>{idx}</td>"
                f"<td style='padding:4px; text-align:left;'>{html.escape(team)}</td>"
                f"<td style='padding:4px;'>{pts}</td>"
                "</tr>"
            )

        table.append("</tbody></table>")
        html_table = "\n".join(table)

        self._attr_native_value = "ok"
        self._attr_extra_state_attributes = {
            "count": len(ordered),
            "teams_standings": ordered,
            ATTRIB_HTML: html_table,
            "ATTRIB_HTML_TEXT": "Classement Équipes MotoGP",
            ATTRIB_LAST_UPDATE: dt_util.now().isoformat(),
        }
        self._attr_available = True
        _LOGGER.debug(f"[MotoGP Teams Standings] Classement équipes calculé ({len(ordered)} équipes)")
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return True

# ----------------------------------------------------------------------
# SENSOR: NEXT EVENT
# ----------------------------------------------------------------------

class MotoGPNextEventSensor(MotoGPEntityBase):
    CIRCUIT_TO_SLUG = {
        "circuito de jerez - angel nieto": "jerez",
        "circuit de barcelona-catalunya": "catalunya",
        "circuit ricardo tormo": "valencia",
        "circuit bugatti": "lemans",
        "autodromo internazionale del mugello": "mugello",
        "tt circuit assen": "assen",
        "sachsenring": "sachsenring",
        "lusail international circuit": "lusail",
        "circuit of the americas": "cota",
        "red bull ring - spielberg": "redbullring",
        "misano world circuit marco simoncelli": "misano",
        "mobility resort motegi": "motegi",
        "pertamina mandalika international street circuit": "mandalika",
        "pertamina mandalika circuit": "mandalika",
        "chang international circuit": "buriram",
        "phillip island": "phillip_island",
        "sepang international circuit": "sepang",
        "petronas sepang international circuit": "sepang",
        "autodromo termas de rio hondo": "termas_de_rio_hondo",
        "autodromo internacional do algarve": "algarve",
        "silverstone circuit": "silverstone",
        "sokol international racetrack": "sokol",
        "motorland aragón": "aragon",
        "motorland aragon": "aragon",
        "automotodrom brno": "cze",
        "balaton park circuit": "balaton",
        "GRAND PRIX OF PORTUGAL": "algarve",
        "autódromo internacional do algarve" : "algarve",
    }

    def __init__(self, hass, config_sensor: MotoGPConfigSensor):
        super().__init__(hass, "MotoGP Next Event", "motogp_next_event", "mdi:calendar-arrow-right")
        self.config_sensor = config_sensor
        self.event_uuid: Optional[str] = None
        self._attr_native_value = STATE_UNKNOWN
        self._attr_available = False
        
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["event"] = self

    async def async_update(self):
        if not self.config_sensor.is_ready:
            _LOGGER.debug("[MotoGP Next Event] En attente de configuration prête…")
            self._attr_native_value = "waiting"
            self._attr_available = False
            self.async_write_ha_state()
            return

        season_id = self.config_sensor.season_id
        endpoint = f"results/events?seasonUuid={season_id}"
        _LOGGER.debug(f"[MotoGP Next Event] Récupération via {endpoint}")
        data = await async_fetch_data(endpoint)

        if not data or not isinstance(data, list):
            _LOGGER.warning("[MotoGP Next Event] Aucune donnée reçue ou format inattendu")
            self._attr_native_value = "unavailable"
            self._attr_available = False
            self.async_write_ha_state()
            return

        now = dt_util.now()
        upcoming = []
        for e in data:
            try:
                status = (e.get("status") or "").upper()
                date_start = e.get("date_start")
                if not date_start:
                    continue
                start_dt = datetime.fromisoformat(date_start)
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=pytz.UTC)

                if status == "CURRENT":
                    ongoing = e
                elif status in ("NOT-STARTED", "UPCOMING") or start_dt > now:
                    upcoming.append(e)

            except Exception as err:
                _LOGGER.debug(f"[MotoGP Next Event] Ignoré ({err}) pour {e.get('name','?')}")
                continue

        if not upcoming:
            _LOGGER.info("[MotoGP Next Event] Aucun événement futur trouvé.")
            self._attr_native_value = "no_upcoming_event"
            self._attr_available = True
            self.async_write_ha_state()
            return

        if 'ongoing' in locals():
            next_event = ongoing
        else:
            next_event = sorted(
                upcoming,
                key=lambda e: datetime.fromisoformat(e["date_start"]).replace(tzinfo=pytz.UTC)
                if datetime.fromisoformat(e["date_start"]).tzinfo is None
                else datetime.fromisoformat(e["date_start"]),
            )[0]


        event_name = next_event.get("name", "Unknown")
        self.event_uuid = next_event.get("id") or next_event.get("uuid")

        country = next_event.get("country", {})
        iso = (country.get("iso", "") or "").lower()
        flag = f"https://flagcdn.com/48x36/{iso}.png" if iso else None
        date_start_local = to_local(next_event.get("date_start", ""))
        date_end_local = to_local(next_event.get("date_end", ""))
        circuit = next_event.get("circuit", {}) or {}
        cname = (circuit.get("name") or circuit.get("place") or "").strip().lower()
        circuit_slug = self.CIRCUIT_TO_SLUG.get(cname, "")
        if not circuit_slug:
            _LOGGER.warning(f"[MotoGP Next Event] Circuit slug introuvable pour '{cname}'")

        html_card = f"""
            <div style="text-align:center;">
            <h3>🏁 {html.escape(event_name)}</h3>
            <p><img src="{flag}" style="vertical-align:middle;"> {country.get('name','')}</p>
            <p>📍 {html.escape(circuit.get('name', 'Unknown'))}</p>
            <p>🗓️ {date_start_local} → {date_end_local}</p>
            </div>
        """

        self._attr_native_value = event_name
        self._attr_extra_state_attributes = {
            "event_id": self.event_uuid,
            "country": country,
            "circuit": circuit,
            "circuit_slug": circuit_slug,
            "date_start": next_event.get("date_start"),
            "date_end": next_event.get("date_end"),
            "status": next_event.get("status"),
            "flag_url": flag,
            ATTRIB_HTML: html_card,
            ATTRIB_LAST_UPDATE: dt_util.now().isoformat(),
        }
        self._attr_available = True
        _LOGGER.info(
            f"[MotoGP Next Event] ✅ Prochain événement: {event_name} ({date_start_local}) — slug={circuit_slug}"
        )
        self.async_write_ha_state()

        if DOMAIN in self.hass.data and "sessions" in self.hass.data[DOMAIN]:
            _LOGGER.debug("[MotoGP Event] Déclenchement de la mise à jour des sessions")
            self.hass.async_create_task(self.hass.data[DOMAIN]["sessions"].async_update())

    @property
    def available(self) -> bool:
        return True

# ----------------------------------------------------------------------
# SENSOR: NEXT SESSIONS
# ----------------------------------------------------------------------
class MotoGPNextSessionsSensor(MotoGPEntityBase):
    def __init__(self, hass, config_sensor: MotoGPConfigSensor, event_sensor: MotoGPNextEventSensor):
        super().__init__(hass, "MotoGP Next Sessions", "motogp_next_sessions", "mdi:timer-sand")
        self.config_sensor = config_sensor
        self.event_sensor = event_sensor
        self.race_uuid: Optional[str] = None
        self._attr_native_value = STATE_UNKNOWN
        self._attr_available = False

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["sessions"] = self

    async def async_update(self):
        if not self.config_sensor.is_ready or not self.event_sensor.event_uuid:
            _LOGGER.debug("[MotoGP Next Sessions] En attente de configuration ou d’événement prêt…")
            self._attr_native_value = "waiting"
            self._attr_available = False
            self.async_write_ha_state()
            return

        event_uuid = self.event_sensor.event_uuid
        category_id = self.config_sensor.category_id
        endpoint = f"results/sessions?eventUuid={event_uuid}&categoryUuid={category_id}"
        _LOGGER.debug(f"[MotoGP Next Sessions] Récupération via {endpoint}")

        data = await async_fetch_data(endpoint)
        if not data or not isinstance(data, list):
            _LOGGER.warning("[MotoGP Next Sessions] Aucune donnée reçue ou format inattendu")
            self._attr_native_value = "unavailable"
            self._attr_available = False
            self.async_write_ha_state()
            return

        sessions_light = []
        for s in data:
            t = (s.get("type") or "").upper()
            if t in ("FP", "PR", "Q", "SPR", "RAC"):
                start = s.get("date")
                start_local = to_local(start) if start else "n/a"
                sessions_light.append({
                    "id": s.get("id"),
                    "type": t,
                    "start": start_local,
                    "status": s.get("status", ""),
                    "circuit": s.get("circuit", ""),
                })

                if t == "RAC":
                    self.race_uuid = s.get("id")

        try:
            sessions_light.sort(
                key=lambda s: datetime.fromisoformat(s["start"].replace("Z", "+00:00"))
                if "start" in s and s["start"] != "n/a" else datetime.max
            )
        except Exception:
            pass

        table = [
            "<table style='width:100%; border-collapse:collapse; text-align:center;'>",
            "<thead><tr style='background:#222; color:#fff;'>",
            "<th style='padding:4px;'>Type</th>",
            "<th style='padding:4px;'>Heure (Locale)</th>",
            "<th style='padding:4px;'>Statut</th>",
            "</tr></thead><tbody>",
        ]

        type_labels = {
            "FP": "Free Practice",
            "PR": "Practice",
            "Q": "Qualif",
            "SPR": "Sprint",
            "RAC": "Course 🏁",
        }

        for s in sessions_light:
            color = {
                "FP": "#00bcd444",
                "PR": "#2196f344",
                "Q": "#9c27b044",
                "SPR": "#ff980044",
                "RAC": "#f4433644",
            }.get(s["type"], "transparent")

            label = type_labels.get(s["type"], s["type"])
            table.append(
                f"<tr style='background:{color}; border-bottom:1px solid #555;'>"
                f"<td style='padding:4px; font-weight:bold;'>{label}</td>"
                f"<td style='padding:4px;'>{s['start']}</td>"
                f"<td style='padding:4px;'>{s['status']}</td>"
                "</tr>"
            )

        table.append("</tbody></table>")
        html_table = "\n".join(table)

        self._attr_native_value = "ok"
        self._attr_extra_state_attributes = {
            "event": self.event_sensor.event_uuid,
            "count": len(sessions_light),
            "sessions": sessions_light,
            "race_uuid": self.race_uuid,
            ATTRIB_HTML: html_table,
            ATTRIB_LAST_UPDATE: dt_util.now().isoformat(),
        }

        self._attr_available = True
        self.async_write_ha_state()

        _LOGGER.info(f"[MotoGP Next Sessions] ✅ {len(sessions_light)} sessions détectées pour {self.event_sensor.event_uuid}")

        if DOMAIN in self.hass.data and "race_start" in self.hass.data[DOMAIN]:
            _LOGGER.debug("[MotoGP Next Sessions] Déclenchement du capteur Race Start")
            self.hass.async_create_task(self.hass.data[DOMAIN]["race_start"].async_update())

    @property
    def available(self) -> bool:
        return True


# ----------------------------------------------------------------------
# SENSOR: NEXT RACE START
# ----------------------------------------------------------------------

class MotoGPNextRaceStartSensor(MotoGPEntityBase):
    def __init__(self, hass, sessions_sensor: "MotoGPNextSessionsSensor"):
        super().__init__(hass, "MotoGP Next Race Start", "motogp_next_race_start", "mdi:flag-checkered")
        self.sessions_sensor = sessions_sensor
        self._attr_native_value = STATE_UNKNOWN
        self._attr_available = False
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["race_start"] = self

    async def async_update(self):
        sessions_data = getattr(self.sessions_sensor, "_attr_extra_state_attributes", {}) or {}
        sessions_list = sessions_data.get("sessions", [])

        if not sessions_list:
            self._attr_native_value = STATE_UNAVAILABLE
            self._attr_available = False
            self.async_write_ha_state()
            return

        race_session = next((s for s in sessions_list if s.get("type") == "RAC"), None)

        if not race_session:
            self._attr_native_value = "no_race_found"
            self._attr_available = True
            self.async_write_ha_state()
            return

        race_start = race_session.get("start", "n/a")

        self._attr_native_value = race_start
        self._attr_extra_state_attributes = {
            "event": self.sessions_sensor.event_sensor.event_uuid
            if hasattr(self.sessions_sensor, "event_sensor")
            else None,
            "race_uuid": self.sessions_sensor.race_uuid,
            "race_session": race_session,
            ATTRIB_LAST_UPDATE: dt_util.now().isoformat(),
        }
        self._attr_available = True
        _LOGGER.info(f"[MotoGP Next Race Start] 🕒 Prochaine course : {race_start}")
        self.async_write_ha_state()

        if DOMAIN in self.hass.data and "live" in self.hass.data[DOMAIN]:
            _LOGGER.debug(
                "[MotoGP Race Start] Déclenchement du capteur Live Timing (ordre Sessions > Race Start > Live)"
            )
            self.hass.async_create_task(self.hass.data[DOMAIN]["live"].async_update())

    @property
    def available(self) -> bool:
        return True

# ----------------------------------------------------------------------
# SENSOR: LIVE TIMING
# ----------------------------------------------------------------------

class MotoGPLiveTimingSensor(MotoGPEntityBase):
    def __init__(self, hass, sessions_sensor: MotoGPNextSessionsSensor):
        super().__init__(hass, "MotoGP Live Timing", "motogp_live_timing", "mdi:speedometer-slow")
        self.sessions_sensor = sessions_sensor
        self._attr_native_value = STATE_UNKNOWN
        self._attr_available = False
        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}
        hass.data[DOMAIN]["live"] = self

    async def async_update(self):
        race_uuid = getattr(self.sessions_sensor, "race_uuid", None)
        if not race_uuid:
            self._attr_native_value = "waiting_race_uuid"
            self._attr_available = False
            self.async_write_ha_state()
            _LOGGER.debug("[MotoGP Live Timing] En attente du race_uuid…")
            return

        endpoint = f"timing-gateway/livetiming-lite?sessionUuid={race_uuid}"
        _LOGGER.info(f"[MotoGP Live Timing] 📡 Récupération du live timing ({endpoint})")
        data = await async_fetch_data(endpoint)

        if not data:
            self._attr_native_value = "unavailable"
            self._attr_available = False
            self.async_write_ha_state()
            return

        session_head = data.get("head", {})
        session_status = session_head.get("session_status_name", "")
        total_laps = session_head.get("num_laps", None)

        riders_data = data.get("rider") or {}
        classement = []
        for _, r in riders_data.items():
            classement.append(
                {
                    "pos": r.get("pos"),
                    "number": r.get("rider_number"),
                    "rider": f"{r.get('rider_name', '')} {r.get('rider_surname', '')}".strip(),
                    "nation": r.get("rider_nation"),
                    "team": r.get("team_name"),
                    "bike": r.get("bike_name"),
                    "laps": r.get("num_lap"),
                    "gap_first": r.get("gap_first"),
                    "last_lap": r.get("last_lap_time"),
                    "status": r.get("status_name"),
                }
            )

        classement.sort(
            key=lambda x: (x["pos"] if isinstance(x["pos"], int) and x["pos"] > 0 else 999)
        )

        table = [
            "<table style='width:100%; border-collapse:collapse; text-align:center;'>",
            "<thead><tr style='background:#222; color:#fff;'>",
            "<th style='padding:4px;'>Pos</th>",
            "<th style='padding:4px;'>#</th>",
            "<th style='padding:4px;'>Rider</th>",
            "<th style='padding:4px;'>Nation</th>",
            "<th style='padding:4px;'>Team</th>",
            "<th style='padding:4px;'>Moto</th>",
            "<th style='padding:4px;'>Gap</th>",
            "<th style='padding:4px;'>Laps</th>",
            "</tr></thead><tbody>",
        ]

        for row in classement:
            pos = row.get("pos", "")
            rider = html.escape(row.get("rider", ""))
            nation = html.escape(row.get("nation", "") or "")
            team = html.escape(row.get("team", "") or "")
            bike = html.escape(row.get("bike", "") or "")
            gap_first = row.get("gap_first", "—")
            laps = row.get("laps", "—")
            status = row.get("status", "")

            if str(pos) == "1":
                bg = "#ffd70044"
            elif str(pos) == "2":
                bg = "#c0c0c044"
            elif str(pos) == "3":
                bg = "#cd7f3244"
            elif status == "RT":
                bg = "#ff000033"
                pos = "❌"
                gap_first = "DNF"
            else:
                bg = "transparent"

            table.append(
                f"<tr style='background:{bg}; border-bottom:1px solid #555;'>"
                f"<td style='padding:4px;'>{pos}</td>"
                f"<td style='padding:4px;'>{row.get('number', '')}</td>"
                f"<td style='padding:4px; text-align:left;'>{rider}</td>"
                f"<td style='padding:4px;'>{nation}</td>"
                f"<td style='padding:4px; text-align:left;'>{team}</td>"
                f"<td style='padding:4px;'>{bike}</td>"
                f"<td style='padding:4px;'>{gap_first}</td>"
                f"<td style='padding:4px;'>{laps}</td>"
                "</tr>"
            )

        table.append("</tbody></table>")
        html_table = "\n".join(table)

        self._attr_native_value = "ok"
        self._attr_extra_state_attributes = {
            "count": len(classement),
            "classification": classement,
            "race_uuid": race_uuid,
            "session_status": session_status,
            "total_laps": total_laps,
            ATTRIB_HTML: html_table,
            ATTRIB_LAST_UPDATE: dt_util.now().isoformat(),
        }
        self._attr_available = True
        _LOGGER.info(f"[MotoGP Live Timing] ✅ {len(classement)} pilotes reçus.")
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return True
