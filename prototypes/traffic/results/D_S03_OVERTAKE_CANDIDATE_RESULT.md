# D-S03 - Declenchement de depassement candidat

- **Experience :** D - Trafic et depassement
- **Scenario :** D-S03
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T20:21:23Z
- **Objectif :** verifier qu'une intention de depassement est declenchee seulement si une voiture lente bloque l'ego et si le corridor candidat est libre.
- **Reserve :** D-S03 ne deplace pas encore la voiture ; il choisit seulement une ligne candidate.

## Reglages

- Offset candidat : -3.00 m
- TTC declencheur : 18.00 s
- Delta vitesse min : 8.00 km/h
- Gap securite avant : 35.00 m
- Gap securite arriere : 20.00 m

## Resultats

| Cas | Attendu | Obtenu | Front | TTC | Blockers | Raisons |
| --- | --- | --- | --- | ---: | --- | --- |
| Clear Overtake | oui | oui | leader | 2.78 | n/a | candidate_clear |
| Blocked Front | non | non | leader | 2.78 | front:front_blocker@17.60m | candidate_blocked_front_front_blocker |
| Blocked Rear | non | non | leader | 2.78 | rear:rear_blocker@10.60m | candidate_blocked_rear_rear_blocker |
| No Need | non | non | leader | 19.44 | n/a | no_slow_front_trigger |

## Metriques

- Cas conformes : 4 / 4
- Decisions positives : 1
- Decisions negatives : 3
- Cas avec blocker candidat : 2

## Decision

D-S03 est valide avec reserves. Le prototype peut passer a D-S04 pour tester deux voitures cote a cote.
