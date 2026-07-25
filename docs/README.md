# Documentation du projet

Cette documentation constitue la mémoire durable d’Automation LAP. Les décisions importantes ne doivent pas rester uniquement dans des discussions : elles doivent être intégrées au plan, à une spécification ou à un ADR.

## Documents de référence

### Pilotage

- [Plan général du projet](PROJECT_PLAN.md) — vision, périmètre, phases, jalons et critères de réussite.
- [Plan d’étude de faisabilité](feasibility/FEASIBILITY_PLAN.md) — prototypes expérimentaux à réaliser avant le code de production.
- [Tableau de bord de la Phase 1](feasibility/PHASE_1_STATUS.md) — état des expériences, dépendances et critères de sortie.
- [Rapport consolidé de faisabilité](feasibility/FEASIBILITY_REPORT.md) — décisions, paramètres candidats, risques résiduels et décision de passage au vertical slice.
- [Modèle de rapport expérimental](feasibility/EXPERIMENT_TEMPLATE.md) — structure commune des protocoles et conclusions.

### Expériences actives

- [Expérience A — Extraction des données Automation](feasibility/experiments/A-AUTOMATION-EXTRACTION.md)
- [Répertoire des prototypes](../prototypes/README.md)
- [Prototype Automation Exporter](../prototypes/automation-exporter/README.md)

### Architecture

- [Vue d’ensemble de l’architecture](architecture/OVERVIEW.md) — composants, dépendances, boucle de simulation et modèle de données.

### Décisions

- [Index des ADR](decisions/README.md)
- [ADR-0001 — Cœur de simulation indépendant de Unity](decisions/ADR-0001-simulation-core-independent-from-unity.md)
- [ADR-0002 — Replay hybride et versionné](decisions/ADR-0002-hybrid-versioned-replay.md)
- [ADR-0003 — Adaptateur versionné pour les données Automation](decisions/ADR-0003-versioned-automation-adapter.md)

## Statuts documentaires

- **Brouillon** : contenu en construction, non engageant.
- **Proposé** : prêt à être discuté dans une pull request.
- **Validé** : référence applicable au projet.
- **Remplacé** : conservé pour l’historique, mais supersédé par un autre document.

## Règle de mise à jour

Toute modification affectant le périmètre, les frontières d’architecture, le format de données, la reproductibilité ou les objectifs du vertical slice doit passer par une pull request. Une décision structurante nouvelle ou modifiée doit également créer ou remplacer un ADR.
