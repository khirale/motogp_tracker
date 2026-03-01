"""Constantes pour l'intégration MotoGP Tracker."""
from datetime import timedelta

DOMAIN = "motogp_tracker"

# ── API ───────────────────────────────────────────────────────────────────────
BASE_URL = "https://api.motogp.pulselive.com/motogp/v1"

# ── Intervalles de mise à jour ────────────────────────────────────────────────
INTERVAL_CONFIG    = timedelta(hours=6)    # saison + categorie
INTERVAL_STANDINGS = timedelta(hours=3)    # classements pilotes/equipes
INTERVAL_EVENT     = timedelta(hours=1)    # prochain GP + sessions
INTERVAL_LIVE      = timedelta(seconds=30) # live timing (conditionnel)

# ── Localisation ──────────────────────────────────────────────────────────────
TZ_PARIS = "Europe/Paris"

# ── Cle de stockage dans hass.data[DOMAIN][entry.entry_id] ───────────────────
KEY_COORDINATORS = "coordinators"

# ── Noms des coordinateurs (cles du dict KEY_COORDINATORS) ───────────────────
COORD_CONFIG    = "config"
COORD_STANDINGS = "standings"
COORD_EVENT     = "event"
COORD_LIVE      = "live"

# ── Sessions ──────────────────────────────────────────────────────────────────
# Types de sessions retenus (WUP et autres ignores)
SESSION_TYPES_KEPT = {"FP", "PR", "Q", "SPR", "RAC"}

# Statuts de session consideres "en cours" (champ session_status_name du live)
LIVE_STATUSES = {"started", "on track", "formation lap", "warm up lap", "in progress", "live"}

# ── Circuits ──────────────────────────────────────────────────────────────────
# Fichiers SVG : /local/motogp/circuits/{slug}-info.svg
CIRCUIT_SVG_PATH = "/local/motogp/circuits/{slug}-info.svg"

# Mapping : nom de circuit API (lowercase) -> slug SVG
# Source des noms : logs API reels 2026
CIRCUIT_SLUGS: dict[str, str] = {
    # Jerez — l'API retourne "Circuito de Jerez - Angel Nieto" avec accent sur Angel
    "circuito de jerez - angel nieto":                    "jerez",
    "circuito de jerez - \u00e1ngel nieto":               "jerez",   # Angel avec accent A
    # Le Mans — l'API retourne "Le Mans" en 2026 (pas "Circuit Bugatti")
    "le mans":                                            "lemans",
    "circuit bugatti":                                    "lemans",   # ancien nom conserve
    # Autres circuits confirmes via logs API 2026
    "circuit de barcelona-catalunya":                     "catalunya",
    "circuit ricardo tormo":                              "valencia",
    "autodromo internazionale del mugello":               "mugello",
    "tt circuit assen":                                   "assen",
    "sachsenring":                                        "sachsenring",
    "lusail international circuit":                       "lusail",
    "circuit of the americas":                            "cota",
    "red bull ring - spielberg":                          "redbullring",
    "misano world circuit marco simoncelli":              "misano",
    "mobility resort motegi":                             "motegi",
    "pertamina mandalika international street circuit":   "mandalika",
    "pertamina mandalika circuit":                        "mandalika",
    "chang international circuit":                        "buriram",
    "phillip island":                                     "phillip_island",
    "phillip island circuit":                             "phillip_island",
    "sepang international circuit":                       "sepang",
    "petronas sepang international circuit":              "sepang",
    "autodromo termas de rio hondo":                      "termas_de_rio_hondo",
    "autodromo internacional do algarve":                 "algarve",
    "autódromo internacional do algarve":                 "algarve",
    "silverstone circuit":                                "silverstone",
    "motorland aragón":                                   "aragon",
    "motorland aragon":                                   "aragon",
    "automotodrom brno":                                  "cze",
    "balaton park circuit":                               "balaton",
    # Brésil 2026 — nouveau circuit, pas de SVG disponible
    # "autódromo internacional de goiânia - ayrton senna": "",
}
