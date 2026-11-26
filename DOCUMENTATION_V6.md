# V6 — Recherche autour des élites et budget intégral

## Lancement

```powershell
.\.venv310\Scripts\python.exe StudentCodeV6.py
```

Modifier `instance_num` (1 par défaut) et enregistrer avant de lancer. Le budget par défaut est `DUREE_SECONDES = 300`. Les solutions et leurs bilans vont dans `resultats_v6/`. Le coût exporté est le minimum effectivement observé pour le placement retenu. La médiane reste informative. Aucun résultat V5 n'est utilisé comme point de départ.

V6 importe les constructeurs et fonctions de voisinage génériques de `StudentCodeV5.py` : conserver ce fichier à côté de V6. L'import ne lance pas V5. `source.py` et l'évaluation du professeur restent inchangés.

## Changements par rapport à V5

- **Budget intégral** : plus de réserve de 10 % suivie d'un arrêt anticipé. La recherche continue jusqu'à l'échéance. Un appel déjà engagé peut dépasser cette échéance. Le chargement de l'instance et l'export restent hors budget ; le prétraitement est inclus. Une première évaluation garantit une solution même si elle dépasse seule le budget.
- **Reprises autour des élites** : après 18 tours sans progrès, ou épuisement du voisinage disponible, deux diversifications sur trois perturbent une élite choisie au hasard ; la troisième construit un nouveau placement indépendant.
- **Amplitude variable** : une permutation cyclique de plusieurs positions change simultanément plusieurs affectations. Les positions libres participent aussi à ces mouvements. La taille passe de deux positions jusqu'à la taille du circuit selon la fraction du budget écoulée sans nouveau record. Cela permet de quitter progressivement le voisinage immédiat d'une bonne solution.
- **Présélection moins restrictive** : évaluation du meilleur voisin selon le guide de distances, d'un voisin tiré parmi les premiers `sqrt(nombre de voisins)` et d'un voisin aléatoire dans tout le voisinage. V5 prenait systématiquement les deux premiers du guide. Le guide reste une approximation, jamais le score final.
- **Réévaluations espacées** : tous les dix tours, au plus un appel supplémentaire sur une élite ayant moins de cinq observations. Une élite avec au moins deux observations toutes identiques n'est plus réévaluée par ce mécanisme. Le temps est davantage consacré aux nouveaux placements. Cette règle peut manquer une variation rare ; deux mesures identiques ne prouvent pas le déterminisme.

L'archive diversifiée, les mouvements tabous et les courts chemins entre élites de V5 sont conservés. Le minimum de toutes les observations détermine toujours le gagnant final ; un mauvais nouvel appel ne supprime pas un record. La liste des finalistes du bilan est descriptive, sans phase finale de validation dédiée.

## Prévention du surajustement

Aucun branchement selon le numéro d'instance, aucun coût cible et aucun placement connu ne sont présents dans la recherche. Les paramètres sont communs aux neuf instances. Les chiffres du collègue ne sont pas utilisés par le code.

Les mécanismes sont proposés avant les essais, sans ajustement sur leurs résultats. Les essais courts sur les instances 4 et 8, graines 17 et 83, servent à vérifier le fonctionnement. Ils ne constituent pas une sélection de paramètres ni une preuve de supériorité. Les instances 1 et 3 ne servent pas à régler V6 malgré leurs écarts connus. Toutes les instances étant déjà connues, ce protocole ne remplace pas une validation sur des circuits nouveaux.

Pour une comparaison de performance : mêmes ressources, même budget de 300 secondes, plusieurs graines fixées à l'avance et mêmes versions logicielles. Conserver tous les résultats, même défavorables, et comparer par instance la distribution des minima obtenus. La graine Python ne fixe pas le hasard interne de Qiskit. Une amélioration sur un seul essai ne suffit pas à conclure.

## Vérifications

Les perturbations ont été vérifiées sur 250 cas couvrant un seul qubit, une occupation partielle et une occupation complète : cardinalité, unicité et bornes des positions. Un budget inférieur à la durée d'une seule évaluation conserve une solution valide. Les essais Qiskit vérifient également que le coût retourné est le minimum de tous les appels et appartient bien au placement retourné.

V6 reste expérimentale : les reprises autour des élites peuvent aussi réduire la diversité et les perturbations peuvent défaire une structure utile. Les paramètres proposés ne sont pas revendiqués comme optimaux.

## Essais courts observés (5 secondes demandées)

| Instance | Graine | V5 minimum | V6 minimum | Temps V5 / V6 (s) |
| --- | --- | ---: | ---: | --- |
| 4 | 17 | 32 | 32 | 4,82 / 5,03 |
| 4 | 83 | 36 | 37 | 5,02 / 5,05 |
| 8 | 17 | 20 | 20 | 5,08 / 5,06 |
| 8 | 83 | 23 | 22 | 5,05 / 5,11 |

Deux égalités, une amélioration et une dégradation. Ces budgets courts ne permettent pas d'évaluer le comportement sur cinq minutes. Aucun réglage n'a été changé à la suite de ces résultats.
