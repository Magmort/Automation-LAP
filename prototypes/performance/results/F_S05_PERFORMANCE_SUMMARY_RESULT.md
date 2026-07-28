# F-S05 - Synthese charge et acceleration

- **Experience :** F - Charge et acceleration
- **Scenario :** F-S05
- **Statut :** validee avec reserves
- **Date :** 2026-07-28T17:26:15Z
- **Objectif :** consolider F-S01 a F-S04 et produire la decision de cloture de l'experience F.
- **Reserve :** synthese de benchmarks Python hors Unity ; la performance finale reste a confirmer dans le runtime produit.

## Decision

- Conclusion : validee avec reserves
- Niveau de confiance : moyen
- Blocages : 0

## Resultats consolides

| Preuve | Resultat | Valeur cle |
| --- | --- | ---:|
| F-S01 harnais | valide avec reserves | stress 40 voitures 307.2x |
| F-S02 temps reel | valide avec reserves | 20 voitures p95 0.3744 ms, 73.4x |
| F-S03 accelere | valide avec reserves | 20 voitures 36.3x |
| F-S04 replay | valide avec reserves | 4 Hz: 6.0 %, 5021 octets/s |

## Parametres candidats

- cible voitures : `12` a `20` ;
- stress suivi : `40` voitures ;
- tick simulation : `60 Hz` ;
- frequence replay compacte : `4 Hz` ;
- replay `20 Hz` : garde comme option detaillee couteuse, part replay `23.1 %`.

## Reserves

- mesures Python hors Unity et hors rendu reel ;
- voitures dupliquees depuis E-S01, sans comportements independants complets ;
- replay compact JSON en memoire, sans ecriture disque continue ni format binaire ;
- pics de scheduling Windows/Python visibles sur certains runs longs ;
- couts GPU, UI, audio, cameras et multithreading non mesures ;

## Conclusion

L'experience F est validee avec reserves. Les mesures reduisent le risque de charge pour le vertical slice, mais ne remplacent pas un profilage Unity reel.
