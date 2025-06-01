# Instructions pour GitHub Copilot

## Objectif Général
Aide-moi à écrire du code Python (Flask pour le backend) et JavaScript (pour le frontend), ainsi que du HTML/CSS.
Le projet est un lanceur de workflow avec gestion de processus, GPU, séquences, et une interface web.

## Comportements à Éviter
- Ne suggère PAS de modifications automatiques aux docstrings de haut niveau (modules, classes) ou aux fichiers README.md, sauf si je le demande explicitement. Je gérerai la documentation globale séparément.
- Ne propose PAS d'ajouter des logs `APP_LOGGER.info(...)` ou `console.log(...)` à chaque nouvelle fonction ou modification mineure, sauf si je suis en train de déboguer ou si je demande une journalisation plus verbeuse.
- Évite de reformater massivement le code existant juste pour des questions de style, sauf si je demande un refactoring stylistique.
- Ne propose pas de tests unitaires automatiquement, je les demanderai au besoin.

## Tâches Courantes (je te les demanderai explicitement)
- Aide à la génération de docstrings pour des fonctions spécifiques quand je le demande.
- Aide au refactoring de fonctions ou classes spécifiques.
- Aide à la création de nouvelles routes Flask ou de fonctions JavaScript pour l'API.

## Contexte Spécifique
- Pour `app_new.py` : ce fichier est le cœur de l'application Flask. Il gère les routes, la configuration, et l'orchestration.
- Pour `process_manager.py` : gère le lancement et le suivi des sous-processus.
- Pour `gpu_manager.py` : gère l'accès exclusif au GPU.
- Pour `sequence_manager.py` : gère l'exécution séquentielle des étapes du workflow.
- Pour `main.js` (et autres fichiers JS frontend) : gère la logique de l'interface utilisateur, les appels API, et la mise à jour du DOM.
- Les fichiers `*.css` concernent le style.
- `COMMANDS_CONFIG` dans `app_new.py` est une structure de données centrale définissant les étapes du workflow.

## Mode Agent
Lorsque j'utilise le mode agent pour des tâches comme "/implement", concentre-toi sur la logique métier demandée. Je m'occuperai des détails de documentation ou de logging plus tard si besoin.