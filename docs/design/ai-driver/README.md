# Analyse de conception de l’IA pilote

- **Statut :** phase d’analyse ouverte
- **Date d’ouverture :** 8 septembre 2026

Ce répertoire rassemble les architectures candidates étudiées pour redéfinir l’IA pilote d’Automation LAP.

Les documents enregistrent les principes, compatibilités, limites, risques et pistes d’expérimentation de chaque candidat. Ils ne constituent ni des ADR ni des décisions d’implémentation. Une synthèse comparative devra précéder toute modification structurante du plan général ou de l’architecture.

## Candidats

| Identifiant | Candidat | Statut | Conclusion provisoire |
|---|---|---|---|
| [AI-CANDIDATE-001](AI-CANDIDATE-001-ALPHA-RACER.md) | α-RACER | Analysé | Référence prometteuse pour la tactique ; adaptation locale et déterministe à étudier avant le ML |
| [AI-CANDIDATE-002](AI-CANDIDATE-002-RACERAI.md) | RacerAI | Rejeté comme architecture | Apprentissage évolutionnaire retenu pour la calibration, la diversité et les outils |

## Références structurantes

| Identifiant | Référence | Statut | Apport principal |
|---|---|---|---|
| [AI-REFERENCE-001](AI-REFERENCE-001-GAME-DRIVEN-INTELLIGENCE.md) | Game-Driven Intelligence | Retenue | Architecture hiérarchique hybride et grille performance/qualité/robustesse/praticité |

## Grille commune

Les prochaines études doivent, lorsque pertinent, examiner : crédibilité, diversité des pilotes, explicabilité, stabilité, sécurité, compétitivité, scalabilité à 12–20 voitures, simulation accélérée, reproductibilité, intégration architecturale, besoins en données et testabilité.
