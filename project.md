# geo-sylv — Forest Carbon MRV

## Vision

Construire un système de monitoring satellite pour des projets forestiers
carbone (type Label Bas-Carbone) : détecter des anomalies (incendie,
dépérissement, tempête, coupe non prévue) à partir de séries temporelles
Sentinel-2, pour prioriser les zones à inspecter plutôt que remplacer le
contrôle terrain.

Le problème métier de fond : les audits terrain sont périodiques (souvent
tous les 5 ans côté LBC) — un monitoring satellite continu peut détecter
un événement entre deux audits, bien plus tôt.

## Principes directeurs

- Explorer avant d'architecturer. Pas de package Python tant qu'une
  logique n'a pas (1) fonctionné, (2) été répétée, (3) mérité d'être
  réutilisée.
- Pas de sur-ingénierie prématurée : pas de src/, pas de Docker, pas de
  cloud, pas de deep learning tant que le POC n'a pas prouvé le signal.
- Le notebook (ou script — cf. friction VS Code) est le laboratoire.
  L'extraction en `.py` vient après, pas avant.
- Une anomalie satellite n'est jamais une preuve de causalité. Elle
  priorise une inspection, elle ne la remplace pas.

## État actuel (POC / phase 1)

- Environnement Python (`venv`, `pip`, geopandas/rasterio/xarray/pystac-client)
  en place.
- Premier projet identifié : zone brûlée de Landiras (Gironde), incendie
  du 14/07/2022 — activation Copernicus EMS EMSR592.
  - Geometry.geojson dérivée de la couche `observedEventA` (périmètre
    complet détecté par satellite, ~12-13 000 ha — pas le parcellaire
    LBC exact, non public).
  - `metadata.md` documente le projet LBC associé (Alliance Forêts
    Bois/GCF n°268 - Landiras 2, méthode Reboisement).
- Recherche STAC Sentinel-2 (Planetary Computer) : en cours de test.
- Friction outillage notée : VS Code ne détecte pas le `.venv` — repli
  sur scripts `.py` lancés en ligne de commande plutôt que Jupyter/VS
  Code interactif, le temps de débloquer.

## Trajectoire (état → produit)

```
Projet forestier réel (Landiras)
        ↓
Série temporelle Sentinel-2 (NDVI / NDMI / NBR)
        ↓
Observation du changement (rupture nette : incendie du 14/07/2022)
        ↓
Détection d'anomalie (seuils, ruptures)
        ↓
Validation avec un forestier / expert métier
        ↓
Compréhension métier (dépérissement vs éclaircie vs coupe, etc.)
        ↓
Meilleure détection
        ↓
Monitoring automatisé (plusieurs projets, alertes)
        ↓
Produit MRV forestier
        ↓
Forest Carbon Intelligence
```

Le point clé : la donnée et le métier doivent progresser ensemble. On ne
cherche pas à prouver qu'un modèle est performant, on cherche d'abord à
comprendre à quoi ressemble une forêt vue par satellite quand quelque
chose d'important se passe.

## Décisions techniques prises

| Sujet | Choix | Raison |
|---|---|---|
| Catalogue STAC | Microsoft Planetary Computer | Accès gratuit, signé automatiquement, catalogue Sentinel-2 L2A complet |
| Premier projet | Zone incendiée Landiras | Événement daté précisément (14/07/2022), signal satellite sans ambiguïté, geometry en open data (Copernicus EMS) |
| Géométrie | Dérivée de EMSR592 `observedEventA`, pas du parcellaire LBC | Le parcellaire précis des projets LBC n'est pas public ; suffisant pour un POC |
| Indices | NDVI, NDMI, NBR | Couvrent respectivement vigueur végétale, stress hydrique, sévérité de brûlis — standards en télédétection forestière |
| Interface de travail | Scripts `.py` en CLI (temporairement, au lieu de Jupyter/VS Code) | Blocage outillage (venv non détecté par VS Code) — à débloquer, pas une décision d'architecture définitive |

## Questions ouvertes (métier)

- Comment un forestier définit-il un dépérissement significatif ?
- Quelle durée de baisse du NDVI est réellement pertinente pour déclencher
  une alerte ?
- Comment distinguer une éclaircie planifiée d'un dépérissement subi ?
- Quel rôle joue l'essence, l'âge du peuplement, dans la lecture du signal ?
- Sentinel-2 (optique, cadence ~5j, gaps nuageux fréquents) est-il assez
  riche en données pour un monitoring fiable, ou faut-il envisager une
  fusion avec Sentinel-1 (radar, insensible aux nuages) à terme ?

## Questions ouvertes (produit)

- Le périmètre incendié complet (12 000+ ha) est-il la bonne granularité
  d'analyse, ou faut-il découper en sous-zones plus tôt que prévu pour
  avoir un signal plus propre par projet LBC individuel ?
- À quel moment la V1 mérite-t-elle d'être étendue à plusieurs projets
  (pas seulement Landiras) pour commencer à généraliser la détection ?
- Le monitoring vaut-il mieux comme produit interne (aide à la décision
  pour toi) ou comme produit orienté financeurs/auditeurs LBC ?

## Prochaines étapes immédiates

1. Débloquer VS Code / venv (ou accepter le flux CLI comme mode de travail
   temporaire — pas bloquant pour avancer).
2. Confirmer la recherche STAC (dates disponibles, couverture nuageuse)
   sur la zone Landiras.
3. Calculer une première série temporelle NDVI/NBR et visualiser la
   rupture du 14/07/2022.
4. Journal métier (`docs/domain.md`) : consigner les premières
   observations et questions à poser à un forestier.