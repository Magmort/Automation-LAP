# A5 — Répétabilité des exports

- **Expérience :** A — Extraction Automation
- **Statut :** validée
- **Date :** 2026-07-26
- **Voiture :** AIXAM Coupe GTI
- **Exporter :** `0.1.8-a4-braking-vgrip-curves`
- **Dossier analysé :** `C:\Users\jerem\Documents\Automation LAP Smoke Test`

## Protocole exécuté

Cinq exports de la même voiture inchangée ont été produits :

- exports 1 et 2 : réalisés à la suite ;
- exports 3, 4 et 5 : réalisés à la suite après redémarrage du jeu.

Chaque dossier contient :

- `automation-lap-vehicle.json` ;
- `automation-lap-field-inventory.json` ;
- `License.txt`.

## Validation contractuelle

Les dix JSON passent les validateurs indépendants :

- `automation-lap-vehicle.json` : succès sur les 5 exports, avec l'avertissement attendu `automation_version_not_exposed` ;
- `automation-lap-field-inventory.json` : succès sur les 5 exports.

## Empreintes brutes

| Export | `exportedAtUtc` | SHA-256 `vehicle` | SHA-256 `field-inventory` |
|---:|---|---|---|
| 1 | `2026-07-26T15:55:44Z` | `F720919CCB742C4848B3E7A56AC5B46586BC7A1DFC217C19BE0EAF1B2DAFFE5D` | `84ABAEB1CA47362EA503697DFD04DC5CC4649C4EC734FCE724541CA19AEE8C6B` |
| 2 | `2026-07-26T15:56:10Z` | `29435F2615AA81601260D121ADAEC67ABE48A6ADBB7476FD1CE581B1DF46BF26` | `E0CFB2AB637AF498D865A5FBCB364B5A65A9E8117F1B9FB8F8CB8EA4C573FE5A` |
| 3 | `2026-07-26T15:57:59Z` | `F4EF5B95034ADF210C3884520116EE8BB50CC7353484628E48F7340B72ECAC35` | `1E7CFBA36F474DB53ED104EF2743A99AC8F8D2F09F91B056A0CF3C425C21BB4A` |
| 4 | `2026-07-26T15:58:18Z` | `DB425E9BF612FD517453825FA9727A27CBC2F4067C9454DA8379C65216E401A4` | `133B99499FAE37E754EC42703A22920DF9BA34F3FB380586C1AC491BB7D4F85F` |
| 5 | `2026-07-26T15:58:31Z` | `A5201F3F15B872AD09A9BDF269D4A9E829B65BDCA8F84C5E832133CC9DC4FC7F` | `A1C3D5FC6123BB1F6945D94AFFB6C5210EE1CCDA235F86FA4858E2E0DA6483B4` |

Les empreintes brutes diffèrent, comme attendu, car `exportedAtUtc` et `lastAccessTime` varient.

## Champs variables

Seuls deux champs changent entre exports :

| Champ | Raison |
|---|---|
| `exportedAtUtc` | horodatage volontairement variable |
| `source.lastAccessTime` / inventaire `source.lastAccessTime.valuePreview` | temps runtime Automation, volontairement variable |

Aucun autre champ ne varie, y compris après redémarrage du jeu.

## Empreintes sémantiques

Normalisation appliquée :

- suppression de `exportedAtUtc` ;
- neutralisation de `source.lastAccessTime` ;
- neutralisation de `fields[source.lastAccessTime].valuePreview` dans l'inventaire.

| Fichier | Empreinte sémantique | Exports uniques |
|---|---|---:|
| `automation-lap-vehicle.json` | `6906C2C4A11957360DA88624CB4D7B88C10843346530F1E80C5F02037BADC923` | 1 / 5 |
| `automation-lap-field-inventory.json` | `AE386D66A83AD955DAFD5EE832C1895F65310EB623411EC30AE713BE38C19AA1` | 1 / 5 |

Conclusion : les exports sont sémantiquement identiques une fois les champs volontairement variables exclus.

## Champs surveillés

| Champ | Résultat |
|---|---|
| `mass.frontDistribution` | stable, présent sur `CarInfo.TrimInfo.Results.cg.WeightDistribution`, valeur `55.0136973565` |
| `mass.weightDistributionSlider` | stable, présent sur `CarInfo.TrimInfo.WeightDistributionFraction`, valeur `0.5` |
| `brakes.brakingVGrip.frontBrakeForceCurve` | stable, présent |
| `brakes.brakingVGrip.frontBrakeGripCurve` | stable, présent |
| `brakes.brakingVGrip.rearBrakeForceCurve` | stable, présent |
| `brakes.brakingVGrip.rearBrakeGripCurve` | stable, présent |
| `brakes.frontBrakeForce` | stable, valeur `90.999999642372` |
| `brakes.rearBrakeForce` | stable, valeur `53.000001907349` |

Les quatre courbes `BrakingVGrip` sont détectées comme tables Lua. Le prototype actuel n'en sérialise encore qu'un aperçu nul, car `preview_value` ne déroule pas les tables. Pour les exploiter, il faudra ajouter une sérialisation bornée des séries numériques.

## Couverture

Chaque inventaire contient `72 / 72` champs présents.

L'augmentation par rapport à A4 vient des nouveaux champs :

- `mass.frontDistribution` ;
- `brakes.brakingVGrip.frontBrakeForceCurve` ;
- `brakes.brakingVGrip.frontBrakeGripCurve` ;
- `brakes.brakingVGrip.rearBrakeForceCurve` ;
- `brakes.brakingVGrip.rearBrakeGripCurve`.

## Décision

A5 est validée.

Les données exportées sont stables pour une voiture inchangée, y compris après redémarrage d'Automation. Les seuls champs non stables sont des métadonnées runtime explicitement variables.

Prochaine étape recommandée :

- définir `AutomationRawVehicleData` v0.1 ;
- ajouter une représentation bornée des courbes numériques, en commençant par `BrakingVGrip`, sans supposer l'unité de l'axe ni des valeurs.

