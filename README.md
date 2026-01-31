correction de bug en cours pour la prochaine saison

<p align="center">
  <a href="https://buymeacoffee.com/khirale">
    <img
      src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
      alt="Buy Me a Coffee"
      height="45"
    >
  </a>
</p>

**MotoGP Tracker :**

MotoGP Tracker est une intégration personnalisée pour Home Assistant permettant d’afficher les données officielles MotoGP directement dans votre tableau de bord.
Elle fournit le live timing, les classements pilotes et équipes, les prochaines sessions et les informations sur le prochain Grand Prix.
Toutes les données proviennent de l’API officielle MotoGP Pulse Live.

Source API : https://api.motogp.pulselive.com/motogp/v1

**Fonctionnalités :**

- Classement en direct des courses

- Informations sur le prochain Grand Prix et les sessions à venir

- Classements pilotes et équipes

- Actualisation automatique des données

- Configuration complète via l’interface Home Assistant

- Images de circuits affichables depuis le dossier www/motogp/

**Installation :**

- Option 1 – via HACS (recommandé)

    Ouvrir HACS dans Home Assistant.

    Aller dans Intégrations → “+ Explorer et télécharger les dépôts”.

    Rechercher “MotoGP Tracker”.

    Télécharger puis redémarrer Home Assistant.

- Option 2 – installation manuelle

    Copier le dossier motogp_tracker dans custom_components.

    Copier le dossier motogp dans www/.

    Redémarrer Home Assistant.

**Configuration :**

- Aller dans Paramètres → Appareils et services → Ajouter une intégration.

- Rechercher “MotoGP Tracker”.

- Suivre les étapes de configuration.
  Aucune configuration YAML n’est requise.

 **Capteurs créés :**

- sensor.motogp_configuration — Informations internes de configuration

- sensor.motogp_teams_standings — Classement des équipes

 -sensor.motogp_live_timing — Données en direct de la course

- sensor.motogp_next_sessions — Sessions à venir

- sensor.motogp_standings — Classement pilotes

- sensor.motogp_next_event — Détails du prochain Grand Prix

- sensor.motogp_next_race_start — Compte à rebours avant la course

**Images des circuits :**

Pour afficher les images des circuits dans vos cartes ou capteurs HTML, placez-les dans :
/config/www/motogp/

Elles seront accessibles dans Home Assistant via :
/local/motogp/<nom_image>.png

Exemple :
/config/www/motogp/losail.png → /local/motogp/losail.png

**Détails techniques :**

- Nom de l’intégration : motogp_tracker
- Domaine : motogp_tracker
- Plateforme : sensor
- Dépendances : aucune
- API : https://api.motogp.pulselive.com/motogp/v1

Intervalle de mise à jour : défini dans la constante UPDATE_INTERVAL_CONFIG

**Structure du dossier :**

custom_components/motogp_tracker

├── init.py

├── config_flow.py

├── const.py

├── entity.py

├── manifest.json

├── sensor.py

└── translations

  ├── en.json
  
  └── fr.json

www/motogp

├── losail.png

├── jerez.png

├── mugello.png

└── ... (une par circuit)

**Crédits :**

- Développé par Khirale
- Données fournies par MotoGP Pulse Live API

Licence : MIT
