# C-S05 - Differences de competence pilote

- **Experience :** C - Tour autonome et modele minimal de circuit
- **Scenario :** C-S05
- **Statut :** valide avec reserves
- **Date :** 2026-07-27T17:11:33Z
- **Objectif :** verifier que des profils de controle produisent des comportements mesurablement differents et qu'une sur-vitesse declenche bien une limite de grip.
- **Reserve :** le modele de grip est une saturation laterale minimale ; il ne separe pas encore sous-virage et survirage.

## Donnees vehicule

- Vehicule : QFC55 - Magmort - Carcharhini RCZ
- Exporteur : `0.1.13-a9-steering-raw-graphs`
- Source : `outputs/a9-raw-vehicle-data/QFC55 - Magmort Carcharhini RCZ/automation-lap-raw-vehicle-data.json`
- Limite laterale utilisee : 1.008 g

## Profils testes

| Profil | Vitesse | Marge grip | Lookahead | Reponse vitesse | Direction | Description |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Prudent | 0.78x | 0.72x | 10.0 m | 1.00 s | 1.00x / 0.32 rad | forte marge de grip, vitesse reduite, ligne propre |
| Equilibre | 1.00x | 1.00x | 16.0 m | 0.85 s | 1.00x / 0.32 rad | proche du grip max avec une marge legere |
| Agressif | 1.35x | 1.25x | 16.0 m | 0.62 s | 0.90x / 0.34 rad | proche de la limite pneus, accepte d'elargir |

## Resultats reference 1/120 s

| Profil | Duree | Tour 1 | Tour 2 | Tour 3 | Vitesse moy. | Vitesse max | Erreur lat. moy. | Erreur lat. max | G lat. max | Sat. grip | Sorties | Stable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Prudent | 115.28 | 38.58 | 38.35 | 38.34 | 35.67 | 41.85 | 0.126 | 0.528 | 0.327 | 0.00 % | 0 | oui |
| Equilibre | 83.33 | 28.13 | 27.60 | 27.59 | 49.31 | 62.79 | 0.231 | 0.807 | 0.446 | 0.00 % | 0 | oui |
| Agressif | 56.84 | 19.56 | 18.64 | 18.63 | 72.64 | 92.13 | 0.302 | 1.032 | 1.002 | 0.00 % | 0 | oui |

## Differenciation

- Ordre du plus rapide au plus lent : `aggressive, balanced, cautious`
- Ecart entre profils extreme : 58.44 s sur trois tours
- Seuil attendu : 8.00 s
- Erreur laterale moyenne : prudent 0.126 m, equilibre 0.231 m, agressif 0.302 m
- G lateral maximal : prudent 0.327 g, equilibre 0.446 g, agressif 1.002 g

## Temoin negatif de sur-vitesse

| Cas | Duree | Vitesse max | Erreur lat. max | Sat. grip | Ratio sat. max | Sorties | Resultat attendu |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Temoin sur-vitesse | 55.65 | 104.13 | 24.197 | 84.11 % | 5.87x | 4011 | oui |

## Observations

- Les trois profils terminent trois tours sans sortie de piste.
- Les differences nominales viennent uniquement des parametres de controle, pas de la voiture ni du circuit.
- Le profil prudent conserve une marge de grip importante et reste le plus proche de la ligne cible en moyenne.
- Le profil agressif gagne du temps en montant nettement plus haut en vitesse et en G lateral, avec un ecart de trajectoire plus eleve.
- Le temoin negatif de sur-vitesse sature le grip et sort de la piste ; il confirme que le modele ne peut plus tourner sans limite physique.

## Decision

C-S05 est valide avec reserves. Le prototype peut passer a C-S06 pour consolider le contrat minimal final de C.
