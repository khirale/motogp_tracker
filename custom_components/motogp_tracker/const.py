from datetime import timedelta

DOMAIN = "motogp_tracker"

BASE_URL = "https://api.motogp.pulselive.com/motogp/v1"

INTERVAL_CONFIG    = timedelta(hours=6)
INTERVAL_STANDINGS = timedelta(hours=3)
INTERVAL_EVENT     = timedelta(hours=1)
INTERVAL_LIVE      = timedelta(seconds=30)

TZ_PARIS = "Europe/Paris"

KEY_COORDINATORS = "coordinators"

COORD_CONFIG    = "config"
COORD_STANDINGS = "standings"
COORD_EVENT     = "event"
COORD_LIVE      = "live"

SESSION_TYPES_KEPT = {"FP", "PR", "Q", "SPR", "RAC"}

LIVE_STATUSES = {"started", "on track", "formation lap", "warm up lap", "in progress", "live", "s"}

CIRCUIT_SVG_PATH = "/local/motogp/circuits/{slug}-info.svg"

CIRCUIT_SLUGS: dict[str, str] = {

    "circuito de jerez - angel nieto":                    "jerez",
    "circuito de jerez - \u00e1ngel nieto":               "jerez",

    "le mans":                                            "lemans",
    "circuit bugatti":                                    "lemans",

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
    "autódromo internacional de goiânia - ayrton senna":  "goiania",
}
