# Recuit simulé avec tirage uniforme des voisins

## Mode actuel : budget de cinq minutes

Depuis la modification du 26 novembre 2026, le programme utilise `DUREE_SECONDES = 300` par défaut (5 minutes). L'argument de `recuit_simule` est désormais `duree_secondes=300` ; `nb_iterations` a été supprimé. Le nombre d'évaluations est affiché à titre de mesure, sans servir de limite.

Le budget est du temps réel écoulé mesuré par `perf_counter`, pas du temps CPU. Il inclut l'évaluation initiale, la recherche et ses affichages, mais exclut le chargement préalable de l'instance et l'écriture finale du fichier. La limite est vérifiée avant chaque nouvelle évaluation après l'initialisation. Une évaluation Qiskit déjà commencée termine normalement : le temps final peut dépasser légèrement le budget, voire davantage si cet appel est long. Un premier placement est toujours évalué pour garantir un résultat, même avec une durée très courte.

Le refroidissement géométrique dépend de la fraction du temps de recherche écoulé, et non du nombre d'itérations. La température tend vers la température finale à l'échéance ; la dernière évaluation peut commencer avant de l'atteindre exactement.

La calibration utilise `FRACTION_CALIBRATION = 0.05` : sa limite est fixée à 15 secondes après le début de la recherche pour un budget de 300 secondes, évaluation initiale comprise. Son nombre de mouvements est variable. Un appel de calibration en cours peut dépasser cette limite ; ce temps est déduit du temps restant pour le recuit. La calibration cesse toujours de lancer des appels à sa propre échéance. S'il n'y a aucune hausse observée, la température de secours est utilisée.

**Les sections suivantes décrivent le protocole historique à nombre d'itérations fixé.** Les résultats déjà enregistrés sont conservés et ne doivent pas être présentés comme des essais à cinq minutes. Les anciennes signatures et limites en évaluations qui y sont citées sont remplacées par les paramètres ci-dessus. Il faudra une nouvelle campagne pour comparer les versions à durée égale. Les commandes de lancement et dossiers de sortie restent identiques ; une nouvelle exécution peut remplacer une ancienne solution du même groupe et de la même instance.

## Historique avant le passage au budget temporel

La V3 se lance avec `StudentCodeV3.py`. Elle reprend la V2 et change uniquement la manière de tirer un mouvement. Les versions précédentes et `source.py` sont conservés.

## Modification du voisinage

La V2 choisit à parts égales entre échange et remplacement lorsqu'une position libre existe. Elle choisit ensuite un mouvement dans la catégorie retenue. Si les catégories ont des tailles différentes, les mouvements individuels n'ont donc pas la même probabilité.

Pour n qubits placés sur m positions, le nombre de mouvements est :

```text
Échanges       E = n × (n - 1) / 2
Remplacements  R = n × (m - n)
Total          E + R
```

La V3 attribue un numéro unique à chaque mouvement et tire un entier uniformément entre 0 et E + R - 1. Chaque voisin a ainsi une probabilité de 1 / (E + R). Les échanges sont énumérés sans doublon ; chaque remplacement correspond à une paire unique formée d'un qubit logique et d'une position libre.

| Instance | Échanges | Remplacements | Probabilité d'échange V2 | Probabilité d'échange V3 |
| --- | ---: | ---: | ---: | ---: |
| 4 | 171 | 19 | 50 % | 90 % |
| 8 | 190 | 140 | 50 % | 57,58 % |
| 9 | 300 | 50 | 50 % | 85,71 % |

Ce changement s'applique pendant la calibration et pendant le recuit. Il peut donc aussi changer la température calibrée. La méthode de calibration reste identique. Aucun placement connu ni score de référence n'est utilisé.

Quand n = m, seuls les échanges sont possibles, comme en V2. Le mécanisme de tirage ayant changé, une même graine ne garantit toutefois pas les mêmes mouvements entre versions. Si aucun mouvement n'existe (n = m = 1), la fonction renvoie une copie du placement.

## Paramètres conservés

- 1 000 mouvements : 50 de calibration puis 950 de recuit.
- 1 001 évaluations au total, placement initial compris.
- Probabilité cible de calibration : 0,8.
- Température finale : 0,1 ; température de secours : 20.
- Refroidissement géométrique et conservation du meilleur placement.
- Graine Python : 42 ; le hasard interne de Qiskit n'est pas fixé.

Il n'y a pas encore de relance après stagnation. L'objectif est d'isoler l'effet du tirage uniforme avant d'ajouter un autre mécanisme. Ce tirage ne garantit pas une meilleure performance que celui de la V2.

## Lancement

Choisir `instance_num` dans `StudentCodeV3.py`, enregistrer le fichier, puis lancer depuis le dossier du projet :

```powershell
.\.venv310\Scripts\python.exe StudentCodeV3.py
```

Le fichier est initialement réglé sur l'instance 9. Les résultats sont enregistrés dans `resultats_v3/GroupeX_Challenge_<instance>.txt` au même format que les versions précédentes. Une nouvelle exécution de la V3 pour le même groupe et la même instance remplace le résultat V3 correspondant : conserver une copie avant de changer la graine si l'on souhaite comparer les essais.

## Premiers résultats au budget complet

Les sorties du terminal transmises par l'utilisateur donnent les résultats suivants pour les neuf instances. Chaque essai comporte 50 mouvements de calibration et 950 mouvements de recherche, soit 1 001 évaluations avec l'initialisation. Les temps, températures et coûts ci-dessous sont ceux de ces sorties ; aucune recherche ni réévaluation supplémentaire n'a été lancée pour cette mise à jour.

| Instance | n | m | Coût initial | Hausses sur 50 mouvements | Température initiale | Meilleur coût V3 | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12 | 16 | 52 | 23 | 28,412 | 29 | 50,78 |
| 2 | 16 | 16 | 119 | 24 | 135,050 | 66 | 355,37 |
| 3 | 10 | 16 | 179 | 28 | 73,976 | 126 | 119,34 |
| 4 | 19 | 20 | 66 | 28 | 18,768 | 33 | 37,91 |
| 5 | 12 | 20 | 390 | 23 | 82,445 | 314 | 123,76 |
| 6 | 14 | 20 | 110 | 26 | 49,726 | 28 | 30,44 |
| 7 | 20 | 27 | 99 | 24 | 69,926 | 31 | 67,38 |
| 8 | 20 | 27 | 76 | 23 | 49,866 | 34 | 84,39 |
| 9 | 25 | 27 | 160 | 25 | 75,310 | 64 | 101,47 |

### Placements obtenus

Instance 1 — coût 29 :

```text
[3, 5, 0, 2, 15, 13, 7, 11, 12, 14, 10, 4]
```

Instance 2 — coût 66 :

```text
[0, 14, 15, 1, 3, 2, 11, 6, 5, 8, 7, 10, 9, 12, 13, 4]
```

Instance 3 — coût 126 :

```text
[14, 0, 1, 7, 15, 8, 10, 12, 6, 4]
```

Instance 4 — coût 33 :

```text
[12, 8, 13, 7, 5, 6, 15, 1, 18, 3, 11, 14, 16, 0, 17, 4, 10, 9, 19]
```

Instance 5 — coût 314 :

```text
[17, 10, 13, 9, 8, 1, 14, 16, 19, 12, 11, 4]
```

Instance 6 — coût 28 :

```text
[7, 13, 4, 2, 19, 16, 12, 18, 11, 14, 8, 0, 9, 6]
```

Instance 7 — coût 31 :

```text
[24, 14, 1, 23, 18, 10, 25, 21, 16, 22, 13, 15, 12, 7, 6, 4, 3, 5, 9, 11]
```

Instance 8 — coût 34 :

```text
[8, 3, 17, 15, 4, 7, 24, 19, 13, 10, 6, 25, 22, 23, 12, 21, 16, 5, 11, 2]
```

Instance 9 — coût 64 :

```text
[3, 21, 9, 4, 14, 10, 18, 13, 11, 19, 22, 0, 25, 26, 17, 15, 7, 23, 1, 24, 20, 16, 12, 5, 8]
```

### Comparaison aux versions précédentes

Les résultats V1 et V2 sont repris des documentations correspondantes pour les essais à 1 000 mouvements. La version de base est appelée V1 dans les documents et ses sorties sont rangées dans `resultats_v0/`.

| Instance | Coût V1 | Coût V2 | Coût V3 | Écart V3 - V2 | Temps V1 | Temps V2 | Temps V3 |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| 1 | 20 | 29 | 29 | 0 | Non consigné | 37,64 s | 50,78 s |
| 2 | 62 | 60 | 66 | +6 | Environ 180 s | 298,13 s | 355,37 s |
| 3 | 129 | 119 | 126 | +7 | 103,61 s | 107,83 s | 119,34 s |
| 4 | 34 | 32 | 33 | +1 | 37,33 s | 54,45 s | 37,91 s |
| 5 | 316 | 315 | 314 | -1 | 173,69 s | 147,69 s | 123,76 s |
| 6 | 31 | 31 | 28 | -3 | 56,81 s | 51,67 s | 30,44 s |
| 7 | 42 | 38 | 31 | -7 | 66,87 s | 65,15 s | 67,38 s |
| 8 | 28 | 36 | 34 | -2 | 76,63 s | 75,25 s | 84,39 s |
| 9 | 74 | 61 | 64 | +3 | 82,48 s | 118,98 s | 101,47 s |

Sur ces neuf essais, la V3 améliore la V2 sur les instances 5, 6, 7 et 8, l'égale sur l'instance 1 et obtient un coût plus élevé sur les instances 2, 3, 4 et 9. Elle est plus lente sur les instances 1, 2, 3, 7 et 8, mais plus rapide sur les instances 4, 5, 6 et 9. Sur l'instance 3, elle reste meilleure que la V1 (126 contre 129), mais la V2 conserve le meilleur résultat observé des trois versions (119).

Sur l'instance 7, le coût passe de 38 à 31, soit une baisse de 18,42 % par rapport à la V2, pour un temps passant de 65,15 à 67,38 s. Sur l'instance 9, la V3 reste meilleure que la V1 (64 contre 74), mais moins bonne que la V2 (64 contre 61), avec un temps inférieur de 17,51 s à celui de la V2. Il s'agit de comparaisons entre essais uniques, sans garantie de reproduction.

Pour les instances 1, 2 et 3, les meilleures références du support sont respectivement 31, 59 et 108. Les écarts relatifs de la V3 sont donc -6,45 %, +11,86 % et +16,67 %. Parmi ces trois références, seule la valeur 59 de l'instance 2 est indiquée comme un optimum exact. Un coût inférieur à une référence non prouvée, comme 29 contre 31 sur l'instance 1, ne prouve pas l'optimalité.

Pour l'instance 7, la référence exacte est 22 : le résultat 31 reste supérieur de 9, soit +40,91 %. Pour l'instance 9, la meilleure référence du support est 36, sans indication d'optimalité exacte : 64 représente un écart de +77,78 %.

Sur l'instance 4, la V3 obtient 33 contre 32 pour la V2, avec un temps inférieur de 16,54 s. Elle reste légèrement meilleure que la V1 (34). L'écart à la référence du cours de 30 est de +10 %.

Sur l'instance 8, la V3 améliore la V2 de 36 à 34 (baisse de 5,56 %), mais le temps augmente de 9,14 s. La V1 reste la meilleure des trois sur cet essai avec 28. Le coût V3 est supérieur de 100 % à la référence du cours de 17. Les références des instances 4 et 8 ne sont pas indiquées comme exactes dans le support.

Sur l'instance 5, la V3 obtient 314 contre 315 en V2 et 316 en V1. Le gain face à la V2 est de 0,32 %, avec un temps inférieur de 23,93 s. L'écart à la référence du cours de 308 est de +1,95 %.

Sur l'instance 6, elle atteint 28 contre 31 dans les deux versions précédentes : baisse de 9,68 % face à la V2, avec un temps inférieur de 21,23 s. L'écart à la référence de 25 est de +12 %. Ces deux références ne sont pas indiquées comme exactes dans le support.

Au total, la V3 fait mieux que la V2 sur quatre instances, pareil sur une et moins bien sur quatre. Parmi les trois versions, les meilleurs coûts observés proviennent de la version de base pour les instances 1 et 8, de la V2 pour 2, 3, 4 et 9, et de la V3 pour 5, 6 et 7. Ce bilan décrit ces essais uniques et ne permet pas de sélectionner une méthode universellement meilleure.

### Interprétation et limites

Sur l'instance 2, toutes les positions sont occupées : les deux versions tirent uniquement des échanges uniformes. La V3 ne modifie donc pas la distribution des voisins pour cette instance, mais le tirage consomme les nombres aléatoires différemment. La trajectoire et l'échantillon de calibration peuvent ainsi changer avec la même graine. Le résultat 66 contre 60 ne mesure pas un effet de rééquilibrage entre échanges et remplacements.

Sur l'instance 1, la probabilité d'échange passe de 50 % à 57,89 % ; sur l'instance 3, elle passe à 42,86 %. Sur l’instance 7, elle passe à 57,58 %, et sur l’instance 9 à 85,71 %. L’essai complet de l’instance 9 ne montre pas de gain de qualité face à la V2 malgré ce rééquilibrage plus marqué. Sur l'instance 4, la probabilité d'échange passe à 90 %, sans amélioration du coût par rapport à la V2 sur cet essai. Sur l'instance 8, elle passe à 57,58 %, avec un gain de deux unités. Ces résultats ne permettent pas de relier directement l'ampleur du rééquilibrage au gain obtenu.

La température calibrée de l'instance 2 passe de 108,780 en V2 à 135,050 en V3. À dégradation égale, une température plus élevée augmente la probabilité d'acceptation, mais cela ne suffit pas à expliquer le résultat final. Sur l'instance 3, les coûts initiaux diffèrent également (209 en V2, 179 en V3) : le hasard interne de Qiskit n'est pas contrôlé.

Les traces V3 ne montrent plus d'amélioration entre les affichages 600 et 950 pour l'instance 2, ni entre 800 et 950 pour l'instance 3. Ces plateaux ne prouvent pas que tous les voisins sont moins bons. Avec un seul essai rapporté par version et par instance, aucun avantage général du tirage uniforme n'est établi. Les différences de temps ne sont pas attribuables avec certitude au changement de tirage sans profilage et répétitions contrôlées.

L'instance 7 progresse encore entre les affichages 900 et 950, de 34 à 31. Sur l'instance 9, le meilleur coût passe de 70 à 64 entre 800 et 900, puis reste à 64 au dernier affichage. Ces améliorations tardives montrent que le budget peut interrompre une recherche encore productive ; elles ne garantissent pas qu'un budget supérieur produirait un gain.

Sur l'instance 4, le meilleur coût passe de 34 à 33 entre les affichages 800 et 900, puis reste stable. Sur l'instance 8, le meilleur coût reste à 34 entre les affichages 800 et 950. Sur l'instance 5, le meilleur coût passe de 316 à 314 entre les affichages 800 et 900. Sur l'instance 6, il atteint 28 à l'affichage 800 puis reste stable jusqu'à 950. Les neuf instances disposent désormais d'un essai complet documenté.

## Vérification et comparaison à poursuivre

Une vérification exhaustive des numéros de mouvements a confirmé que chaque voisin apparaît exactement une fois, sur les dimensions (1,1), (1,5), (3,5), (5,5), (19,20) et (25,27). Un essai sur une fonction déterministe a aussi vérifié la validité des placements, la conservation du meilleur coût et le budget exact de 1 001 évaluations. Ces contrôles ont été exécutés directement, sans ajouter de fichier de tests au projet.

Les essais courts avec Qiskit sur les instances 4, 8 et 9 servent uniquement à vérifier l'exécution. Un gain de coût face à la V2 au budget complet est observé sur les instances 5, 6, 7 et 8, mais aucun avantage général de la V3 n'est établi.

Pour comparer V2 et V3, utiliser d'abord les instances 4, 8 et 9 avec les graines 42, 43 et 44, à 1 001 évaluations par recherche. Consigner le coût et le temps de chaque essai, puis comparer les médianes et les meilleurs coûts. Les températures calibrées doivent également être relevées. Trois graines constituent un premier contrôle, pas une preuve statistique définitive.
