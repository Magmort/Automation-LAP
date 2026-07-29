# Expérience G - Import du modèle minimal de circuit depuis UR2D2

- **Statut :** G-S05 validée ; synthèse G à préparer
- **Ticket :** #10
- **Responsable :** Codex / Jérémie
- **Date de début :** 28 juillet 2026
- **Date de conclusion :** à renseigner
- **Version du protocole :** 0.2
- **Dépendance levée :** C-S06 valide avec réserves `TrackDefinition` v0.1 comme contrat cible.

## 1. Question testée

Pouvons-nous reconstruire automatiquement un `TrackDefinition` minimal validé par l'expérience C à partir des fichiers produits par le Track Editor d'Ultimate Racing 2D 2 ?

## 2. Hypothèse

Le Track Editor doit conserver suffisamment d'informations géométriques et fonctionnelles pour rouvrir et exécuter un circuit. Une partie de ces informations devrait permettre de reconstruire au moins la boucle, le sens, les limites et les éléments de chronométrage requis par notre modèle minimal.

L'hypothèse ne suppose ni que tous les fichiers soient documentés, ni que toutes les informations puissent être récupérées sans calibration ou perte.

## 3. Contrat cible issu de C

G ne définit pas la forme de `TrackDefinition`.

Le contrat candidat à reconstruire est celui consolidé par C-S06 :

- identité et version du schéma : `kind`, `schemaVersion`, `trackId`, `name` ;
- unités SI : mètres, radians, secondes ;
- axes 2D : `x` vers la droite, `y` vers l'avant ;
- orientation et sens explicites ;
- boucle fermée ;
- surface principale avec type et coefficient d'adhérence ;
- points ordonnés de ligne centrale avec `x`, `y`, `leftWidth`, `rightWidth` ;
- ligne de départ ;
- checkpoints.

Les grandeurs dérivées par C ne doivent pas être importées comme vérité source : segments, distances cumulées, tangentes, normales, courbures, projections et compteurs de tour.

## 4. Hors périmètre

Cette expérience ne cherche pas à :

- importer les graphismes ou objets décoratifs complets ;
- reproduire la physique d'UR2D2 ;
- garantir la compatibilité avec toutes les versions historiques du jeu ;
- redistribuer des circuits officiels ou des ressources protégées ;
- transformer le format UR2D2 en format runtime permanent ;
- démontrer la viabilité du contrôleur, déjà traitée par C.

## 5. Architecture expérimentale

```text
Fichiers UR2D2
      |
Inspecteur binaire / lecteur provisoire
      |
UR2D2RawTrackData
      |
Convertisseur versionné
      |
TrackDefinition minimal
      |
Validateur et prétraitement issus de C
      |
Contrôleur autonome issu de C
```

Les données brutes doivent rester distinctes du contrat interne. Une valeur absente, estimée ou corrigée manuellement doit être marquée explicitement.

## 6. Jeu différentiel

Créer dans le Track Editor une série où chaque étape ne modifie qu'une seule famille de données :

| Fixture | Modification unique | But |
|---|---|---|
| T00 | Circuit vide enregistré | Identifier l'en-tête et les valeurs par défaut |
| T01 | Route droite unique | Localiser les points ou segments de route |
| T02 | Boucle simple fermée | Identifier fermeture, ordre et sens |
| T03 | Ligne IA ajoutée | Identifier la trajectoire de référence |
| T04 | Limites ou murs ajoutés | Identifier largeur ou géométrie des bords |
| T05 | Départ et checkpoints | Identifier les éléments de chronométrage |
| T06 | Voie des stands | Évaluer les chemins secondaires |
| T07 | Surfaces distinctes | Évaluer les zones de surface et d'adhérence |

Pour chaque fixture :

- conserver le dossier complet ;
- enregistrer la version exacte d'UR2D2 ;
- calculer les empreintes SHA-256 ;
- consigner la manipulation réalisée ;
- comparer les fichiers à la fixture précédente ;
- ne pas committer de contenu dont la redistribution n'est pas autorisée.

## 7. Scénarios

### G-S00 - Inventaire reproductible

1. Localiser les dossiers et fichiers produits par l'éditeur.
2. Relever noms, tailles, dates et empreintes.
3. Identifier les fichiers modifiés lors d'un simple enregistrement.
4. Rechercher signatures, chaînes lisibles, en-têtes et compression éventuelle.
5. Produire une synthèse et une visualisation des différences disponibles.

### G-S01 - Analyse différentielle

1. Comparer T00 et T01.
2. Déplacer un unique point puis comparer de nouveau.
3. Répéter pour chaque famille d'éléments.
4. Établir une carte hypothétique des structures.

### G-S02 - Lecteur brut

1. Lire les structures identifiées sans interprétation métier excessive.
2. Produire `UR2D2RawTrackData` sérialisable.
3. Associer à chaque champ son fichier, son offset ou sa méthode d'extraction.
4. Détecter explicitement les champs inconnus ou non pris en charge.

**Résultat :** G-S02 est validée avec réserves. Le lecteur brut `UR2D2RawTrackData` v0.1.0 extrait une région stable de 17 tableaux `float32` comptés depuis les huit sauvegardes `.sav`, dont 4 segments de route, 3 lignes IA candidates, 3 checkpoints, 1 mur multi-segments, 1 zone de sable et 1 zone d'arbres. Les tracés sont désormais exposés comme clés vectorielles candidates avec positions, angles et poids de poignées. La pitlane, son entrée et sa sortie sont détectées, mais l'attribution entrée/sortie reste en confiance basse. Les unités, axes, payloads d'objets, formule exacte d'interpolation vectorielle et conversion SI restent explicitement non figés.

### G-S03 - Conversion

1. Convertir les coordonnées vers les conventions de C.
2. Déterminer ou calibrer l'échelle.
3. Reconstruire la boucle et le sens.
4. Convertir limites, départ et checkpoints.
5. Importer la ligne IA comme trajectoire de référence facultative.
6. Valider le résultat avec le validateur de C.

**Résultat :** G-S03 est validée avec réserves. Le convertisseur produit `g_s03_track_definition_candidate.json`, un `TrackDefinition` v0.1.0 qui passe les invariants C-S01 avec 16 points échantillonnés depuis 4 clés vectorielles, 272,884 m de boucle et une largeur totale minimale de 10,000 m issue du fichier source. L'échelle est calibrée depuis la grille éditeur : 1056 unités éditeur pour 33 carreaux, soit 32 unités par carreau et `1 m = 12,8 unités éditeur` avec l'hypothèse confirmée `1 carreau = 2,5 m`. L'inversion Y et la formule de Bézier candidate `key[i] + angleA[i]/weightA[i]` vers `key[i+1] + angleB[i]/weightB[i]` restent des hypothèses expérimentales à vérifier sur davantage de fixtures. Les vecteurs de poignées appliquent une inversion verticale globale par rapport aux coordonnées brutes des points.

### G-S04 - Validation visuelle

Superposer sur une même vue :

- l'image de référence du circuit, lorsqu'elle est disponible ;
- les points et segments décodés ;
- la ligne centrale ;
- les limites ;
- la ligne IA ;
- le départ et les checkpoints ;
- le sens de circulation.

La vue doit permettre de détecter inversion d'axe, origine incorrecte, rotation, miroir, échelle incohérente et ordre incorrect des points.

**Résultat :** G-S04 est validée avec réserves. La visualisation `G_S04_VISUAL_VALIDATION.svg` superpose la route convertie, les 4 clés vectorielles, les poignées candidates, les 3 lignes IA, les checkpoints, le mur, `pit1` comme entrée des stands, `pit2` comme sortie, la pitlane droite entre les deux, le sable et les arbres dans le même repère métrique. Les deux segments droits restent alignés avec un écart de 0,000 m, les couches requises sont présentes, la largeur de piste provient du fichier source (`10,000 m`) et la pitlane est affichée comme une bande de 2 carreaux (`5,000 m`). La vue `G_S04_HANDLE_INTERPRETATION.svg` expose la convention corrigée des poignées : `A` part de `key[i]`, tandis que `B` est stockée sur la ligne `i-1` et s'ancre sur `key[i]`. La vue `G_S04_SAND_HANDLE_HYPOTHESES.svg` valide l'inversion verticale globale des vecteurs de poignées pour le sable. Les réserves portent sur l'absence de capture éditeur de référence et la confirmation visuelle de cette convention sur davantage de fixtures.

### G-S05 - Validation fonctionnelle

1. Charger le `TrackDefinition` converti.
2. Exécuter le prétraitement issu de C.
3. Faire parcourir plusieurs tours au contrôleur de C.
4. Comparer les métriques obtenues avec la piste canonique ou une reconstruction manuelle équivalente.

**Résultat :** G-S05 est validée. Le `TrackDefinition` importé passe C-S01, la QFC55 termine 3 tours aux pas `1/60 s` et `1/120 s`, et le run de référence compte 0 tick hors piste. La piste importée mesure 272,884 m avec une largeur source de 10,000 m ; le rendu final `G_S05_FUNCTIONAL_VISUALIZATION.svg` ferme proprement la route au raccord de boucle, affiche la pitlane en bande de 5,000 m et superpose la trajectoire colorée par vitesse. Les réserves restantes sont celles du périmètre G : confirmation sur davantage de fixtures et intégration ultérieure des couches hors `TrackDefinition` v0.1.

## 8. Métriques

| Métrique | Unité | Attente |
|---|---|---|
| Champs obligatoires reconstruits | % | 100 % ou limitation explicitement acceptable |
| Intervention manuelle | opérations par circuit | Aussi proche de zéro que possible |
| Erreur de superposition | unité source et mètres | Mesurée, seuil à fixer après C |
| Écart de longueur de boucle | % | Mesuré et expliqué |
| Résultat du validateur | succès / erreurs | Succès sans correction cachée |
| Déterminisme | empreinte de sortie | Identique pour des entrées identiques |
| Temps d'import | secondes | Mesuré, non critique au prototype |
| Versions testées | nombre | Au moins la version installée de référence |

## 9. Critères de réussite

- [ ] un circuit simple est converti sans édition point par point ;
- [ ] la sortie respecte le schéma minimal et ses invariants ;
- [ ] la boucle et le sens sont corrects ;
- [ ] les limites nécessaires au contrôleur sont disponibles ;
- [ ] le départ et les checkpoints sont récupérés ou une méthode de complément bornée est définie ;
- [ ] l'échelle et les transformations sont documentées ;
- [ ] la conversion est déterministe et versionnée ;
- [ ] le contrôleur de C parcourt le circuit importé ;
- [ ] les pertes et corrections manuelles sont quantifiées ;
- [ ] les fichiers UR2D2 ne sont plus nécessaires après conversion.

## 10. Conditions de révision ou d'échec

L'hypothèse doit être révisée si :

- la géométrie ne peut être reconstruite qu'à partir d'une image avec une intervention importante ;
- l'échelle reste indéterminable sans saisie manuelle pour chaque circuit ;
- les limites nécessaires au contrôle sont absentes et non dérivables ;
- le format change sans mécanisme de version détectable ;
- l'extraction exige une redistribution non autorisée ;
- la conversion produit des circuits trop imprécis pour le contrôleur.

Un échec ne remet pas en cause `TrackDefinition` ni l'expérience C. Il implique de choisir une autre source ou de développer ultérieurement un éditeur propre.

## 11. Conclusions possibles

- **Validée :** import automatique suffisant pour le vertical slice.
- **Validée avec réserves :** import viable avec calibration ou corrections limitées et documentées.
- **À modifier :** une autre méthode d'extraction ou un outil assisté est nécessaire.
- **Non viable :** UR2D2 n'est pas retenu comme source de circuits.

## 12. Livrables

- rapport complété dans ce document ;
- inventaire des fichiers et versions ;
- schéma provisoire `UR2D2RawTrackData` ;
- inspecteur ou importeur expérimental ;
- visualiseur de superposition ;
- fixtures redistribuables ou procédure reproductible avec empreintes ;
- exemples de sortie `TrackDefinition` ;
- décision d'adoption ou de rejet d'UR2D2.
