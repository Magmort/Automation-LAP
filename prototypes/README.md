# Prototypes de faisabilité

Ce répertoire contient uniquement les expériences jetables de la Phase 1.

Un prototype sert à répondre à une question technique et à produire des mesures. Il ne constitue pas automatiquement la base du code de production.

## Règles

Chaque prototype doit fournir :

- un lien vers son ticket ;
- la question et l’hypothèse testées ;
- les prérequis ;
- une procédure de compilation et d’exécution ;
- les scénarios reproductibles ;
- les métriques collectées ;
- les limites connues ;
- l’emplacement des résultats ;
- une conclusion dans la documentation de faisabilité.

## Contraintes

- Ne pas créer de dépendance du futur cœur de simulation vers le code d’un prototype.
- Ne pas committer de binaires, SDK tiers, fichiers d’installation ou contenus Automation non redistribuables.
- Ne pas introduire Unity lorsque la question peut être testée sans Unity.
- Ne pas optimiser avant d’avoir mesuré.
- Ne pas masquer un paramètre manquant par une constante non documentée.

## Expériences prévues

```text
prototypes/
  automation-exporter/   # Expérience A
  vehicle-dynamics/      # Expérience B
  autonomous-lap/        # Expérience C
  traffic/               # Expérience D
  replay/                # Expérience E
  performance/           # Expérience F
  ur2d2-track-import/    # Expérience G
  ur2d2-runtime-track-import/ # Expérience H
```

Seul le répertoire de l’expérience active doit être créé en détail. G analyse les sauvegardes éditeur UR2D2 ; H analyse les vrais fichiers de tracks UR2D2.
