# Étude de candidat IA pilote — α-RACER

- **Statut :** analyse de conception — candidat étudié, non retenu à ce stade
- **Identifiant :** AI-CANDIDATE-001
- **Date :** 8 septembre 2026
- **Source principale :** [α-RACER: Real-Time Algorithm for Game-Theoretic Motion Planning and Control in Autonomous Racing using α-Potential Function](https://arxiv.org/html/2412.08855v3)
- **Implémentation de référence :** [sastry-group/alpha-RACER](https://github.com/sastry-group/alpha-RACER)
- **Objet :** évaluer α-RACER comme point de départ de la redéfinition de l’IA pilote d’Automation LAP

## 1. Contexte

Les expériences C et D ont démontré qu’un véhicule peut boucler un circuit et réaliser des interactions nominales de trafic. Elles n’établissent cependant pas que l’architecture actuelle puisse produire à terme une conduite suffisamment riche, adaptable et crédible pour la simulation visée.

Automation LAP ouvre donc une phase d’analyse de conception consacrée à l’IA pilote. Cette phase doit comparer plusieurs architectures candidates avant de figer un nouveau plan d’implémentation. Le présent document enregistre l’analyse du premier candidat : α-RACER.

Cette étude n’est ni un ADR ni une autorisation d’introduire immédiatement de l’apprentissage automatique dans le vertical slice.

## 2. Résumé de l’approche

α-RACER formule la course automobile multi-agents comme un jeu dynamique à horizon infini. Chaque voiture cherche à maximiser son progrès relatif face aux autres concurrents.

L’approche est organisée en deux phases :

1. **hors ligne**, des courses simulées avec états initiaux et paramètres de politiques aléatoires servent à apprendre les fonctions de valeur des agents, puis une fonction de potentiel dynamique approchée ;
2. **en ligne**, la fonction de potentiel est maximisée à partir de l’état courant afin de sélectionner les paramètres de politiques correspondant à un équilibre de Nash approché.

Le système n’est pas un pilote neuronal de bout en bout. Le réseau appris ne produit pas directement le volant et l’accélérateur. Il sélectionne des paramètres tactiques interprétables qui modifient une trajectoire de référence ; un contrôleur prédictif MPC suit ensuite cette trajectoire.

## 3. Paramétrisation de la politique

Pour chaque voiture, la politique est décrite par cinq paramètres :

| Paramètre α-RACER | Rôle | Interprétation possible dans Automation LAP |
|---|---|---|
| `q` | poids du suivi de trajectoire dans le MPC | adhérence à la ligne et fermeté du contrôle |
| `ζ` | facteur appliqué à la vitesse de la ligne optimale | rythme et agressivité longitudinale |
| `s1` | amplitude latérale d’évitement/dépassement | dégagement recherché pour dépasser |
| `s2` | décroissance de l’influence selon la distance longitudinale | portée d’anticipation du trafic |
| `s3` | réaction de la trajectoire au concurrent qui suit | intensité et réactivité de la défense |

Ces paramètres produisent des comportements continus plutôt qu’un choix exclusif entre quelques états rigides. Ils permettent notamment le suivi de ligne, le dépassement, la défense et la variation du rythme.

## 4. Chaîne de décision α-RACER

```text
État conjoint de la course
        │
        ▼
Fonction de potentiel apprise Φ
        │ optimisation en ligne
        ▼
Paramètres tactiques q, ζ, s1, s2, s3
        │
        ▼
Modification de la ligne de course optimale
        │
        ▼
Trajectoire de référence
        │
        ▼
Contrôleur MPC
        │
        ▼
Direction et accélérateur
```

Le cœur de la contribution est la séparation entre :

- une décision tactique à horizon long ;
- une trajectoire explicite et interprétable ;
- un contrôle dynamique à horizon court.

## 5. Résultats publiés

L’évaluation principale porte sur des courses à trois voitures :

- jeu de données de 4 000 courses simulées ;
- courses de 50 secondes et pas de 0,1 seconde ;
- fonction de valeur constituée de trois couches cachées de tailles 128, 128 et 64 ;
- fonction de potentiel constituée de trois couches cachées de tailles 384, 384 et 192 ;
- optimisation en ligne par montée de gradient avec réutilisation de la solution du pas précédent ;
- écart médian de la fonction de potentiel annoncé autour de 2 % de la plage de la fonction de valeur ;
- regret de Nash annoncé sous 3 % de cette plage ;
- 73 victoires sur 99 face à la baseline IBR ;
- 91 victoires sur 99 face à la baseline self-play RL.

Ces résultats montrent que la méthode est prometteuse dans son environnement expérimental. Ils ne prouvent pas sa généralisation à un peloton de 12 à 20 voitures, à plusieurs circuits, à des voitures hétérogènes, ni à l’ensemble des contraintes stratégiques d’Automation LAP.

Les auteurs indiquent également que leurs baselines IBR et self-play RL ne constituent pas nécessairement des implémentations entièrement optimisées.

## 6. Compatibilité avec Automation LAP

### 6.1 Compatibilités fortes

| α-RACER | Architecture Automation LAP |
|---|---|
| simulateur indépendant du rendu Unity | cœur de simulation indépendant de Unity |
| ligne de course pré-calculée | `TrackDefinition`, courbure et trajectoires IA |
| modèle bicyclette dynamique | évolution physique déjà prévue |
| décision tactique paramétrée | séparation stratégie, tactique et contrôle |
| calcul hors ligne puis exécution en ligne | simulation headless et campagnes de calibration |
| paramètres tactiques interprétables | causalité lisible et replay des décisions |
| Unity utilisé uniquement pour la visualisation | Unity non autoritaire |

La structure proposée par l’article correspond donc très bien aux frontières conceptuelles du projet.

### 6.2 Écarts importants

1. L’implémentation de référence utilise Python, ROS 2, JAX et éventuellement CUDA, alors que le cœur d’Automation LAP doit rester une bibliothèque C# autonome.
2. α-RACER utilise un MPC non linéaire ; Automation LAP dispose actuellement d’un contrôleur pure-pursuit à vitesse contrainte.
3. Les expériences publiées portent principalement sur trois voitures, contre une cible de 12 à 20.
4. La formulation utilise un état conjoint très informé, alors que les pilotes d’Automation LAP doivent disposer d’une perception imparfaite.
5. L’utilité publiée est essentiellement fondée sur le progrès relatif et ne couvre pas encore l’usure, le carburant, la stratégie, les incidents ou les règles.
6. L’article suppose une ligne optimale avec profil de vitesse, qui n’existe pas encore comme donnée dérivée de production dans Automation LAP.
7. L’apprentissage automatique est hors périmètre du premier vertical slice actuellement défini.
8. Aucune licence logicielle explicite n’a été identifiée à la racine du dépôt de référence lors de cette étude ; les concepts doivent être réimplémentés sans copie de code tant que ce point n’est pas clarifié.

## 7. Limite principale : passage à 12–20 voitures

Une transposition littérale demanderait d’optimiser cinq paramètres par voiture. Le problème passerait de 15 paramètres pour trois voitures à 100 paramètres pour vingt voitures. La dimension de l’état conjoint augmenterait également avec le peloton.

Les performances temps réel annoncées ne peuvent donc pas être extrapolées directement à Automation LAP.

Une adaptation crédible devrait utiliser un contexte local de dimension fixe :

- voiture immédiatement devant ;
- voiture immédiatement derrière ;
- menace latérale principale ;
- éventuelle cible de dépassement ;
- résumé agrégé du trafic plus lointain.

Chaque pilote pourrait alors sélectionner ses propres paramètres à partir de sa perception locale. Cette adaptation sacrifie la prétention à un équilibre de Nash global exact pour obtenir une tactique locale scalable, ce qui paraît plus conforme aux besoins du projet.

## 8. Intégration conceptuelle recommandée

α-RACER ne devrait pas remplacer toute l’IA pilote. Son emplacement naturel est la couche tactique :

```text
Stratégie de course
        │
        ▼
Perception propre au pilote
        │
        ▼
Sélecteur tactique inspiré d’α-RACER
        │
        ▼
Intention et trajectoire cibles
        │
        ▼
Contrôleur de conduite
        │
        ▼
Modèle physique
```

Un contrat candidat pourrait exposer :

```csharp
public readonly record struct TacticalIntent(
    double PaceFactor,
    double LineAdherence,
    double OvertakeClearance,
    double InteractionRange,
    double DefenseResponsiveness,
    TacticalManeuver Maneuver,
    VehicleId? TargetVehicle,
    double Confidence);
```

Correspondances proposées :

- `PaceFactor` dérive de `ζ` ;
- `LineAdherence` dérive de `q` ;
- `OvertakeClearance` dérive de `s1` ;
- `InteractionRange` dérive de `s2` ;
- `DefenseResponsiveness` dérive de `s3`.

Ce contrat n’est qu’une hypothèse de conception. Il doit être comparé aux autres candidats avant stabilisation.

## 9. Personnalité et perception

Les paramètres ne doivent pas être optimisés dans les mêmes bornes pour tous les pilotes.

| Caractéristique du pilote | Influence possible |
|---|---|
| agressivité | bornes de rythme, dépassement et défense |
| précision | bruit et erreur de perception |
| racecraft | qualité de l’évaluation tactique |
| prudence | coût du contact et des marges faibles |
| défense | amplitude et rapidité des réactions |
| adaptabilité | fréquence de réévaluation |
| sang-froid | hystérésis et stabilité de la décision |

Le sélecteur tactique doit recevoir la perception du pilote et non le `RaceState` autoritatif complet. Cela conserve la causalité attendue : une mauvaise décision peut provenir d’une information incomplète, d’une estimation imparfaite ou du profil du pilote.

## 10. Fonction d’utilité à adapter

L’utilité d’α-RACER, centrée sur le progrès relatif, est insuffisante pour Automation LAP. Une future évaluation pourrait combiner :

```text
utilité =
    progrès sur la piste
  + gain ou protection de position
  - risque de contact
  - risque de sortie
  - coût pneus et carburant
  - écart à la stratégie
  - risque mécanique
  - coût réglementaire
```

Les poids devraient dépendre du pilote, de la voiture, de la phase de course et des instructions stratégiques. La fonction doit rester journalisable : le replay doit pouvoir expliquer les principaux termes ayant conduit à une décision.

## 11. Ligne optimale et contrôle

Une adoption complète de l’approche demanderait un pipeline de trajectoire :

1. resampler la ligne centrale ;
2. calculer une ligne à courbure minimale ou temps minimal ;
3. dériver un profil de vitesse par voiture ;
4. produire des corridors ou variantes pour attaque et défense ;
5. versionner les données dérivées avec la piste et le modèle physique.

Le MPC de l’article ne doit pas être adopté par défaut. Le contrôleur actuel peut d’abord exécuter les intentions tactiques. Un MPC ne devrait être étudié qu’après stabilisation du modèle bicyclette dynamique et seulement si des métriques démontrent un bénéfice suffisant.

## 12. Plan d’étude proposé pour ce candidat

### I1 — Paramétrisation tactique déterministe

Implémenter les cinq dimensions tactiques sans réseau neuronal. Les sélectionner par heuristiques ou profils fixes.

**Question :** chaque paramètre produit-il un effet distinct, stable et explicable ?

### I2 — Recherche hors ligne

Tester une grille discrète de paramètres sur des scénarios reproductibles à deux et trois voitures.

**Mesures :** progrès relatif, temps perdu, contacts, sorties, réussite de dépassement, oscillations et stabilité.

### I3 — Contexte local scalable

Rejouer les scénarios avec une représentation locale de taille fixe, puis étendre à 12 et 20 voitures.

**Question :** le coût par voiture et la qualité des décisions restent-ils acceptables en peloton ?

### I4 — Fonction de potentiel apprise

Entraîner hors runtime une fonction de potentiel à partir des simulations stabilisées. L’inférence C# pourrait utiliser un modèle exporté et versionné, par exemple en ONNX, si cette technologie est retenue après étude.

### I5 — Sélection en ligne

Comparer une grille discrète, un catalogue de profils tactiques, une recherche locale warm-startée et une optimisation continue bornée.

### I6 — Campagne statistique

Comparer le candidat à la baseline heuristique sur plusieurs circuits, véhicules, ordres de départ et profils de pilotes, avec graines fixes et métriques de performance p95.

## 13. Critères d’évaluation pour la comparaison future

Tout candidat à la future IA pilote devrait être noté au minimum sur :

| Axe | Question |
|---|---|
| crédibilité | les trajectoires et réactions paraissent-elles plausibles ? |
| diversité | les profils de pilotes restent-ils statistiquement distincts ? |
| explicabilité | une décision peut-elle être justifiée dans le replay ? |
| stabilité | le pilote évite-t-il oscillations et changements tactiques incessants ? |
| sécurité | contacts et sorties sont-ils maîtrisables sans les supprimer artificiellement ? |
| compétitivité | dépassement, défense et adaptation apportent-ils un gain réel ? |
| scalabilité | 12 à 20 voitures restent-elles dans le budget ? |
| accélération | le modèle reste-t-il compatible avec l’exécution headless accélérée ? |
| reproductibilité | une graine et des versions identiques reproduisent-elles le résultat attendu ? |
| intégration | le candidat respecte-t-il les frontières Core/Physics/AI/Strategy/Unity ? |
| données | le volume de simulations et la calibration sont-ils soutenables ? |
| testabilité | les décisions et invariants peuvent-ils être testés isolément ? |

## 14. Conclusion provisoire

α-RACER est un très bon point de départ conceptuel pour redéfinir la couche tactique d’Automation LAP, notamment grâce à :

- ses paramètres continus et interprétables ;
- sa séparation entre tactique, trajectoire et contrôle ;
- son usage de simulations hors ligne ;
- son traitement explicite du dépassement et de la défense ;
- sa proximité avec l’architecture indépendante de Unity du projet.

Une intégration directe n’est toutefois pas recommandée. Les limites principales sont l’écosystème Python/ROS/JAX, le MPC non linéaire, la perception trop complète et l’absence de preuve de scalabilité au-delà de trois voitures.

**Position actuelle :** conserver α-RACER comme candidat de référence. Étudier d’abord une adaptation déterministe et locale de sa paramétrisation tactique. Reporter la fonction de potentiel neuronale jusqu’à la stabilisation du simulateur, des contrats d’IA et des données d’entraînement. Comparer cette approche à d’autres candidats avant toute décision architecturale ou modification du plan de production.
