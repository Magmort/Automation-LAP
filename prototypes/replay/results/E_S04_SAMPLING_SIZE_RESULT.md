# E-S04 - Taille et frequence d'echantillonnage

- **Experience :** E - Replay minimal
- **Scenario :** E-S04
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:24:39Z
- **Objectif :** mesurer la taille brute du replay JSON selon plusieurs frequences de frames.
- **Reserve :** mesure hors compression, hors format binaire et sur un scenario court a trois voitures.

## Entrees

- Replay source : `prototypes/replay/results/e_s01_minimal_replay.replay.json`
- Profils : `prototypes/replay/fixtures/e_s04_sampling_profiles.json`

## Metriques globales

- Profils testes : 5
- Duree replay : 55.00 s
- Vehicules : 3
- Evenements : 3
- Taille min/max : 41831 / 719882 octets
- Debit min/max : 760.6 / 13088.8 octets/s
- Erreurs de validation : 0

## Profils

| Profil | Hz | Intervalle | Frames | Taille | Octets/s | Octets/frame | Ecart evenement max |
| --- | ---:| ---:| ---:| ---:| ---:| ---:| ---:|
| 1hz | 1.00 | 1.000 s | 56 | 41831 | 760.6 | 747.0 | 0.492 s |
| 2hz | 2.00 | 0.500 s | 111 | 77487 | 1408.9 | 698.1 | 0.025 s |
| 4hz_reference | 4.00 | 0.250 s | 221 | 148964 | 2708.4 | 674.0 | 0.025 s |
| 10hz | 10.00 | 0.100 s | 551 | 362682 | 6594.2 | 658.2 | 0.025 s |
| 20hz | 20.00 | 0.050 s | 1101 | 719882 | 13088.8 | 653.8 | 0.025 s |

## Decision

E-S04 est valide avec reserves. Les donnees permettent de choisir une frequence candidate avant de tester la compatibilite E-S05.
