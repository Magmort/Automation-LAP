# Expérience G — Import du modèle minimal de circuit depuis UR2D2

- **Statut :** bloquée par l’expérience C
- **Ticket :** #10
- **Responsable :** à renseigner
- **Date de début :** à renseigner
- **Date de conclusion :** à renseigner
- **Version du protocole :** 0.1

## 1. Question testée

Pouvons-nous reconstruire automatiquement un `TrackDefinition` minimal validé par l’expérience C à partir des fichiers produits par le Track Editor d’Ultimate Racing 2D 2 ?

## 2. Hypothèse

Le Track Editor doit conserver suffisamment d’informations géométriques et fonctionnelles pour rouvrir et exécuter un circuit. Une partie de ces informations devrait permettre de reconstruire au moins la boucle, le sens, les limites et les éléments de chronométrage requis par notre modèle minimal.

L’hypothèse ne suppose ni que tous les fichiers soient documentés, ni que toutes les informations puissent être récupérées sans calibration ou perte.

## 3. Dépendance envers l’expérience C

G ne définit pas la forme de `TrackDefinition`.

Avant son démarrage, C doit fournir :

- le schéma minimal et sa version ;
- les conventions de coordonnées et unités ;
- les invariants de fermeture et de continuité ;
- la représentation des limites ;
- les règles de chronométrage minimal ;
- une piste canonique ;
- un validateur ;
- un contrôleur capable d’utiliser ce contrat.

## 4. Hors périmètre

Cette expérience ne cherche pas à :

- importer les graphismes ou objets décoratifs complets ;
- reproduire la physique d’UR2D2 ;
- garantir la compatibilité avec toutes les versions historiques du jeu ;
- redistribuer des circuits officiels ou des ressources protégées ;
- transformer le format UR2D2 en format runtime permanent ;
- démontrer la viabilité du contrôleur, déjà traitée par C.

## 5. Architecture expérimentale

```text
Fichiers UR2D2
      ↓
Inspecteur binaire / lecteur provisoire
      ↓
UR2D2RawTrackData
      ↓
Convertisseur versionné
      ↓
TrackDefinition minimal
      ↓
Validateur et prétraitement issus de C
      ↓
Contrôleur autonome issu de C
```

Les données brutes doivent rester distinctes du contrat interne. Une valeur absente, estimée ou corrigée manuellement doit être marquée explicitement.

## 6. Jeu différentiel

Créer dans le Track Editor une série où chaque étape ne modifie qu’une seule famille de données :

| Fixture | Modification unique | But |
|---|---|---|
| T00 | Circuit vide enregistré | Identifier l’en-tête et les valeurs par défaut |
| T01 | Route droite unique | Localiser les points ou segments de route |
| T02 | Boucle simple fermée | Identifier fermeture, ordre et sens |
| T03 | Ligne IA ajoutée | Identifier la trajectoire de référence |
| T04 | Limites ou murs ajoutés | Identifier largeur ou géométrie des bords |
| T05 | Départ et checkpoints | Identifier les éléments de chronométrage |
| T06 | Voie des stands | Évaluer les chemins secondaires |
| T07 | Surfaces distinctes | Évaluer les zones de surface et d’adhérence |

Pour chaque fixture :

- conserver le dossier complet ;
- enregistrer la version exacte d’UR2D2 ;
- calculer les empreintes SHA-256 ;
- consigner la manipulation réalisée ;
- comparer les fichiers à la fixture précédente ;
- ne pas committer de contenu dont la redistribution n’est pas autorisée.

## 7. Étapes

### G0 — Inventaire

1. Localiser les dossiers et fichiers produits par l’éditeur.
2. Relever noms, tailles, dates et empreintes.
3. Identifier les fichiers modifiés lors d’un simple enregistrement.
4. Rechercher signatures, chaînes lisibles, en-têtes et compression éventuelle.

### G1 — Analyse différentielle

1. Comparer T00 et T01.
2. Déplacer un unique point puis comparer de nouveau.
3. Répéter pour chaque famille d’éléments.
4. Établir une carte hypothétique des structures.

### G2 — Lecteur brut

1. Lire les structures identifiées sans interprétation métier excessive.
2. Produire `UR2D2RawTrackData` sérialisable.
3. Associer à chaque champ son fichier, son offset ou sa méthode d’extraction.
4. Détecter explicitement les champs inconnus ou non pris en charge.

### G3 — Conversion

1. Convertir les coordonnées vers les conventions de C.
2. Déterminer ou calibrer l’échelle.
3. Reconstruire la boucle et le sens.
4. Convertir limites, départ et checkpoints.
5. Importer la ligne IA comme trajectoire de référence facultative.
6. Valider le résultat avec le validateur de C.

### G4 — Validation visuelle

Superposer sur une même vue :

- l’image de référence du circuit, lorsqu’elle est disponible ;
- les points et segments décodés ;
- la ligne centrale ;
- les limites ;
- la ligne IA ;
- le départ et les checkpoints ;
- le sens de circulation.

La vue doit permettre de détecter inversion d’axe, origine incorrecte, rotation, miroir, échelle incohérente et ordre incorrect des points.

### G5 — Validation fonctionnelle

1. Charger le `TrackDefinition` converti.
2. Exécuter le prétraitement issu de C.
3. Faire parcourir plusieurs tours au contrôleur de C.
4. Comparer les métriques obtenues avec la piste canonique ou une reconstruction manuelle équivalente.

## 8. Métriques

| Métrique | Unité | Attente |
|---|---|---|
| Champs obligatoires reconstruits | % | 100 % ou limitation explicitement acceptable |
| Intervention manuelle | opérations par circuit | Aussi proche de zéro que possible |
| Erreur de superposition | unité source et mètres | Mesurée, seuil à fixer après C |
| Écart de longueur de boucle | % | Mesuré et expliqué |
| Résultat du validateur | succès / erreurs | Succès sans correction cachée |
| Déterminisme | empreinte de sortie | Identique pour des entrées identiques |
| Temps d’import | secondes | Mesuré, non critique au prototype |
| Versions testées | nombre | Au moins la version installée de référence |

## 9. Critères de réussite

- [ ] un circuit simple est converti sans édition point par point ;
- [ ] la sortie respecte le schéma minimal et ses invariants ;
- [ ] la boucle et le sens sont corrects ;
- [ ] les limites nécessaires au contrôleur sont disponibles ;
- [ ] le départ et les checkpoints sont récupérés ou une méthode de complément bornée est définie ;
- [ ] l’échelle et les transformations sont documentées ;
- [ ] la conversion est déterministe et versionnée ;
- [ ] le contrôleur de C parcourt le circuit importé ;
- [ ] les pertes et corrections manuelles sont quantifiées ;
- [ ] les fichiers UR2D2 ne sont plus nécessaires après conversion.

## 10. Conditions de révision ou d’échec

L’hypothèse doit être révisée si :

- la géométrie ne peut être reconstruite qu’à partir d’une image avec une intervention importante ;
- l’échelle reste indéterminable sans saisie manuelle pour chaque circuit ;
- les limites nécessaires au contrôle sont absentes et non dérivables ;
- le format change sans mécanisme de version détectable ;
- l’extraction exige une redistribution non autorisée ;
- la conversion produit des circuits trop imprécis pour le contrôleur.

Un échec ne remet pas en cause `TrackDefinition` ni l’expérience C. Il implique de choisir une autre source ou de développer ultérieurement un éditeur propre.

## 11. Conclusions possibles

- **Validée :** import automatique suffisant pour le vertical slice.
- **Validée avec réserves :** import viable avec calibration ou corrections limitées et documentées.
- **À modifier :** une autre méthode d’extraction ou un outil assisté est nécessaire.
- **Non viable :** UR2D2 n’est pas retenu comme source de circuits.

## 12. Livrables

- rapport complété dans ce document ;
- inventaire des fichiers et versions ;
- schéma provisoire `UR2D2RawTrackData` ;
- inspecteur ou importeur expérimental ;
- visualiseur de superposition ;
- fixtures redistribuables ou procédure reproductible avec empreintes ;
- exemples de sortie `TrackDefinition` ;
- décision d’adoption ou de rejet d’UR2D2.