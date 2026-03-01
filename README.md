# MotoGP Tracker — Home Assistant Integration

<p align="center">
  <img src="https://img.shields.io/badge/HACS-Custom-orange?style=for-the-badge" alt="HACS Custom">
  <img src="https://img.shields.io/badge/HA-2026.1+-blue?style=for-the-badge" alt="HA Version">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
</p>

---


<p align="center">
  <a href="https://buymeacoffee.com/khirale">
    <img
      src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
      alt="Buy Me a Coffee"
      height="45"
    >
  </a>
</p>


## 🇬🇧 English

### What it does

MotoGP Tracker integrates live MotoGP data into Home Assistant via the official Pulselive API.  
**No API key required.**

#### 6 sensors provided

| Sensor | State | Key attributes |
|--------|-------|----------------|
| `sensor.motogp_prochain_evenement` | GP name | flag_url, circuit_name, circuit_svg, dates |
| `sensor.motogp_depart_course` | Race start (Paris time) | start_utc, session_status, race_uuid |
| `sensor.motogp_sessions` | Session count | sessions list (type, start_local, status) |
| `sensor.motogp_classement_pilotes` | Leader name | standings (position, full_name, country_iso, team, points, wins) |
| `sensor.motogp_classement_equipes` | Leader team | standings (position, name, points) |
| `sensor.motogp_live_timing` | Session status | active, classification, current_lap, total_laps |

#### Update intervals

| Data | Interval |
|------|----------|
| Season / Category | 6 hours |
| Rider standings | 3 hours |
| Next event + sessions | 1 hour |
| Live timing | 30 seconds |

Live timing only polls the API when a race UUID is available. Outside race weekends, no unnecessary calls are made.

### Requirements

- Home Assistant 2024.1 or later
- Internet access to `api.motogp.pulselive.com`

### Installation via HACS

1. In HACS → **Integrations** → ⋮ → **Custom repositories**
2. URL: `https://github.com/khirale/motogp_tracker` — Category: **Integration**
3. Click **Download** then restart Home Assistant
4. **Settings → Devices & Services → Add Integration** → search **MotoGP Tracker**

### Manual installation

1. Copy `custom_components/motogp_tracker/` to your HA config directory
2. Restart Home Assistant
3. Add the integration via **Settings → Devices & Services**

### Dashboard cards

Companion Lovelace cards are available as a separate HACS Frontend resource:  
👉 [github.com/khirale/motogp-cards](https://github.com/khirale/motogp-cards)

### Services

| Service | Description |
|---------|-------------|
| `motogp_tracker.refresh_config` | Force refresh season & category |
| `motogp_tracker.refresh_standings` | Force refresh rider standings |
| `motogp_tracker.refresh_event` | Force refresh next event & sessions |
| `motogp_tracker.refresh_live` | Force refresh live timing |

---

## 🇫🇷 Français

### Ce que ça fait

MotoGP Tracker intègre les données MotoGP en temps réel dans Home Assistant via l'API officielle Pulselive.  
**Aucune clé API requise.**

#### 6 capteurs fournis

| Capteur | État | Attributs clés |
|---------|------|----------------|
| `sensor.motogp_prochain_evenement` | Nom du GP | flag_url, circuit_name, circuit_svg, dates |
| `sensor.motogp_depart_course` | Heure départ (Paris) | start_utc, session_status, race_uuid |
| `sensor.motogp_sessions` | Nombre de sessions | liste sessions (type, start_local, status) |
| `sensor.motogp_classement_pilotes` | Nom du leader | standings (position, full_name, country_iso, team, points, wins) |
| `sensor.motogp_classement_equipes` | Équipe leader | standings (position, name, points) |
| `sensor.motogp_live_timing` | Statut session | active, classification, current_lap, total_laps |

#### Intervalles de mise à jour

| Données | Intervalle |
|---------|-----------|
| Saison / Catégorie | 6 heures |
| Classement pilotes | 3 heures |
| Prochain événement + sessions | 1 heure |
| Live timing | 30 secondes |

Le live timing n'interroge l'API que si un UUID de course est disponible. En dehors des week-ends de GP, aucun appel inutile n'est effectué.

### Prérequis

- Home Assistant 2024.1 ou supérieur
- Accès Internet vers `api.motogp.pulselive.com`

### Installation via HACS

1. Dans HACS → **Intégrations** → ⋮ → **Dépôts personnalisés**
2. URL : `https://github.com/khirale/motogp_tracker` — Catégorie : **Intégration**
3. Cliquer **Télécharger** puis redémarrer Home Assistant
4. **Paramètres → Appareils et services → Ajouter une intégration** → chercher **MotoGP Tracker**

### Installation manuelle

1. Copier `custom_components/motogp_tracker/` dans votre répertoire de config HA
2. Redémarrer Home Assistant
3. Ajouter l'intégration via **Paramètres → Appareils et services**

### Cartes dashboard

Des cartes Lovelace compagnon sont disponibles comme ressource HACS Frontend séparée :  
👉 [github.com/khirale/motogp-cards](https://github.com/khirale/motogp-cards)

### Services

| Service | Description |
|---------|-------------|
| `motogp_tracker.refresh_config` | Forcer le rafraîchissement saison/catégorie |
| `motogp_tracker.refresh_standings` | Forcer le rafraîchissement du classement |
| `motogp_tracker.refresh_event` | Forcer le rafraîchissement du prochain événement |
| `motogp_tracker.refresh_live` | Forcer le rafraîchissement du live timing |

---

## License

MIT © 2026 khirale
