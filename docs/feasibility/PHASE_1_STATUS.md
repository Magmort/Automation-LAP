# Phase 1 — Tableau de bord de faisabilité

- **Statut :** active
- **Début :** 25 juillet 2026
- **Ticket directeur :** #2
- **Branche de préparation :** `agent/phase-1-feasibility`
- **Décision de sortie attendue :** `Go`, `Go avec réserves`, `Rework` ou `No-Go`

Ce document donne l’état synthétique de la Phase 1. Les protocoles détaillés, mesures et conclusions restent conservés dans les rapports d’expérience et les tickets associés.

## Chaîne critique

```text
A — Données Automation
        ↓
B — Dynamique d’une voiture
        ↓
C — Tour autonome
        ↓
E — Replay minimal
        ↓
D — Trafic et dépassement
        ↓
F — Charge et accélération
```

Le replay est volontairement introduit avant le trafic afin de rendre les interactions complexes observables et analysables.

## État des expériences

| Expérience | Ticket | État | Dépendances | Prochaine preuve attendue |
|---|---:|---|---|---|
| A — Extraction Automation | #3 | Prête à démarrer | Installation locale d’Automation et du SDK | Export JSON minimal avec versions |
| B — Dynamique d’une voiture | #4 | Bloquée | Données représentatives de A | Scénarios physiques reproductibles |
| C — Tour autonome | #5 | Bloquée | Modèle dynamique candidat de B | Tours consécutifs mesurés |
| D — Trafic et dépassement | #6 | Bloquée | C et replay minimal E | Scénarios de trafic statistiques |
| E — Replay minimal | #7 | Bloquée | États dynamiques de B | Fichier autonome navigable |
| F — Charge et accélération | #8 | Bloquée | Boucle représentative B à E | Profils 1, 12, 20 et 40 voitures |

## Règles de phase

1. Les prototypes sont jetables et ne deviennent pas automatiquement du code de production.
2. Une expérience ne peut être déclarée réussie sans mesures et procédure reproductible.
3. Les données d’essai doivent être identifiables par version, origine et empreinte.
4. Une hypothèse invalidée doit être documentée ; elle ne doit pas être masquée par une règle spécifique.
5. Toute conséquence structurante doit mettre à jour le plan, une spécification ou un ADR.
6. Les résultats négatifs sont des résultats utiles dès lors qu’ils réduisent une incertitude.

## Critères de sortie de la Phase 1

- [ ] les six expériences possèdent une conclusion explicite ;
- [ ] les paramètres candidats et leurs limites sont documentés ;
- [ ] les risques résiduels sont classés ;
- [ ] le format brut Automation et sa stratégie de versionnement sont définis ;
- [ ] un modèle dynamique candidat est retenu ou rejeté avec justification ;
- [ ] l’architecture IA est confirmée ou ajustée ;
- [ ] le principe de replay hybride est mesuré ;
- [ ] la cible de douze à vingt voitures est évaluée sur une machine de référence ;
- [ ] le rapport consolidé est validé ;
- [ ] la décision de passage au vertical slice est enregistrée.
