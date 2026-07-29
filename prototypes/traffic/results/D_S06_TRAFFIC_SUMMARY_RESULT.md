# D-S06 - Synthese statistique trafic

- **Experience :** D - Trafic et depassement
- **Scenario :** D-S06
- **Statut :** validee avec reserves
- **Date :** 2026-07-27T20:21:29Z
- **Objectif :** consolider les preuves D-S01 a D-S05 et conclure l'experience D.

## Resultat global

- Scenarios conformes : 5 / 5
- Temps dynamique simule : 190.00 s
- Contact ticks consolides : 0
- Hors-piste consolides : 0
- Cas de decision conformes : 4 / 4
- Duree de reinsertion D-S05 : 2.98 s

## Scenarios

| Scenario | Statut | Preuve |
| --- | --- | --- |
| D-S01 - Perception voisins | valide | 6 voitures, 6 liens voisins, wrap depart valide |
| D-S02 - Suivi longitudinal | valide avec reserves | 90 s derriere leader lent, gap stabilise, aucun contact |
| D-S03 - Decision depassement | valide avec reserves | 4 cas conformes, declenchement seulement si corridor candidat libre |
| D-S04 - Cote a cote | valide avec reserves | 45 s cote a cote, clearance stabilisee, aucun contact |
| D-S05 - Reinsertion | valide avec reserves | retour corridor cible entre deux voitures, gaps surs, aucun contact |

## Capacites validees

| Capacite | Statut | Preuve |
| --- | --- | --- |
| Projection multi-voitures et perception voisins | validee | 6 voitures, 6 liens, erreur max 0.00 m |
| Suivi longitudinal derriere voiture lente | validee avec reserves | gap min 17.50 m, detection front 100.00 % |
| Decision de depassement candidat | validee avec reserves | 4 / 4 cas conformes, 2 blockers detectes |
| Maintien cote a cote | validee avec reserves | 100.00 % du temps, clearance stable 1.70 m |
| Reinsertion nominale apres ecart | validee avec reserves | reinsertion 2.98 s, gaps min 32.15 m / 29.24 m |

## Limites residuelles

- Les scenarios D restent deterministes et peu nombreux.
- La reinsertion contestee, la defense active et les gaps qui se referment ne sont pas encore testes.
- Les collisions restent detectees par enveloppes simples, sans physique de contact detaillee.
- La densite de grille et la performance appartiennent encore a F.
- Le replay E reste utile pour analyser les interactions longues et diagnostiquer les cas limites.

## Decision

L'experience D est validee avec reserves. Elle reduit le risque principal sur la representation du trafic, la perception, le suivi, la decision candidate et la reinsertion nominale. Elle ne prouve pas encore les interactions longues, denses ou contestees.
