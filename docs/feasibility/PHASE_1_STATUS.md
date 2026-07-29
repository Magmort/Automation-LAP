# Phase 1 — Tableau de bord de faisabilité

- **Statut :** prête pour clôture
- **Début :** 25 juillet 2026
- **Ticket directeur :** #2
- **Branche de préparation :** `agent/phase-1-feasibility`
- **Décision de sortie :** `Go avec réserves`

Ce document donne l’état synthétique de la Phase 1. Les protocoles détaillés, mesures et conclusions restent conservés dans les rapports d’expérience et les tickets associés.

## Graphe de dépendances

```text
A — Données Automation
        ↓
B — Dynamique d’une voiture
        ↓
C — Tour autonome et modèle minimal de circuit
        ├──────────────→ G — Import UR2D2 editor .sav
        ├──────────────→ H — Import UR2D2 vrais tracks
        ↓
E — Replay minimal
        ↓
D — Trafic et dépassement
        ↓
F — Charge et accélération
```

Le replay reste recommandé avant les scénarios de trafic longs afin de rendre les interactions complexes observables et analysables. Le socle statique D-S01 peut toutefois être exécuté sans attendre E.

L’import UR2D2 est séparé du tour autonome : C définit le contrat interne à partir des besoins du contrôleur ; G vérifie les sauvegardes éditeur `.sav`, puis H vérifie les vrais fichiers de tracks. G et H peuvent être exécutées en parallèle d’E, D ou F.

## État des expériences

| Expérience | Ticket | État | Dépendances | Prochaine preuve attendue |
|---|---:|---|---|---|
| A — Extraction Automation | #3 | Validée avec réserves | Installation locale d’Automation et du SDK | Contrat A8 `AutomationRawVehicleData` v0.1 disponible |
| B — Dynamique d’une voiture | #4 | Validée avec réserves | Données A9 des trois voitures | Modèle dynamique candidat disponible pour C |
| C — Tour autonome et circuit minimal | #5 | Validée avec réserves | Modèle dynamique candidat de B | `TrackDefinition` v0.1 consolidé |
| D — Trafic et dépassement | #6 | Validée avec réserves | B et C, replay E utile mais non bloquant | Synthèse D-S06 disponible |
| E — Replay minimal | #7 | Validée avec réserves | États dynamiques de B, contrat C, résultats D | Synthèse E-S06 disponible |
| F — Charge et accélération | #8 | Validée avec réserves | Boucle représentative B à E | Synthèse F-S05 disponible |
| G — Import UR2D2 editor `.sav` | #10 | Validée avec réserves | Contrat `TrackDefinition` v0.1 issu de C | Chemin éditeur utilisable comme référence et outil d'analyse |
| H — Import UR2D2 vrais tracks | #11 | Validée avec réserves | Contrat `TrackDefinition` v0.1 issu de C, comparaison G utile | Replay H-S06 validé sur fond runtime |

## Portée des expériences G et H

G et H sont :

- **non bloquante** pour le contrôleur, le replay, le trafic et la mesure des performances ;
- **bloquante** pour déclarer UR2D2 comme outil officiel de création des circuits du vertical slice ;
- **sans influence directe** sur la forme du modèle interne, qui appartient à C ;
- **responsables** de mesurer les pertes d’information et interventions manuelles nécessaires à la conversion.

## Règles de phase

1. Les prototypes sont jetables et ne deviennent pas automatiquement du code de production.
2. Une expérience ne peut être déclarée réussie sans mesures et procédure reproductible.
3. Les données d’essai doivent être identifiables par version, origine et empreinte.
4. Une hypothèse invalidée doit être documentée ; elle ne doit pas être masquée par une règle spécifique.
5. Toute conséquence structurante doit mettre à jour le plan, une spécification ou un ADR.
6. Les résultats négatifs sont des résultats utiles dès lors qu’ils réduisent une incertitude.
7. Un format externe doit être adapté vers nos contrats internes et ne doit pas les dicter.

## Critères de sortie de la Phase 1

- [x] les huit expériences possèdent une conclusion explicite ;
- [x] les paramètres candidats et leurs limites sont documentés ;
- [x] les risques résiduels sont classés ;
- [x] le format brut Automation et sa stratégie de versionnement sont définis ;
- [x] un modèle dynamique candidat est retenu ou rejeté avec justification ;
- [x] le modèle minimal de circuit et ses invariants sont définis ;
- [x] l’architecture IA est confirmée ou ajustée ;
- [x] le principe de replay hybride est mesuré ;
- [x] la cible de douze à vingt voitures est évaluée sur une machine de référence ;
- [x] la capacité des sauvegardes éditeur UR2D2 à alimenter le modèle de circuit est évaluée ;
- [x] la capacité des vrais fichiers de tracks UR2D2 à alimenter le modèle de circuit est évaluée ;
- [x] une décision explicite est prise sur l’adoption d’UR2D2 ;
- [x] le rapport consolidé est validé ;
- [x] la décision de passage au vertical slice est enregistrée.
