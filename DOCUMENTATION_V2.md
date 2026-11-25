# Recuit simulé avec calibration de température

La V2 est dans `StudentCodeV2.py`. La V1 reste dans `StudentCode.py` et ses résultats sont conservés. Le code d'évaluation `source.py` reste inchangé.

## Changement par rapport à la V1

La V1 commence à une température fixée à 20. La V2 mesure d'abord les variations de coût sur une marche aléatoire de 50 mouvements admissibles. Chaque mouvement est effectué, puis sa variation de coût est calculée par rapport au placement précédent. Les hausses strictement positives servent à calibrer la température. Le meilleur placement rencontré pendant cette phase est conservé.

La température initiale T est calculée par dichotomie pour satisfaire :

```text
moyenne(exp(-hausse / T)) = 0,8
```

Cela vise une acceptation moyenne de 80 % sur l'échantillon des hausses mesurées. Cela ne garantit pas 80 % d'acceptation pendant la recherche, où les placements et leurs variations changent. La température finale reste 0,1 et le refroidissement reste géométrique.

Si aucune hausse n'est observée, la température de secours est 20. La température initiale est également bornée inférieurement par la température finale : dans ce cas limite, la cible de 80 % peut ne pas être respectée. Aucun score ou placement de référence n'est utilisé.

## Budget et paramètres

Avec `NB_ITERATIONS = 1000`, les deux versions font exactement 1 001 évaluations :

| Version | Initialisation | Calibration | Recherche | Total |
| --- | ---: | ---: | ---: | ---: |
| V1 | 1 | 0 | 1 000 | 1 001 |
| V2 | 1 | 50 | 950 | 1 001 |

La V2 poursuit le recuit depuis la dernière position de la marche aléatoire. Les mouvements, la règle d'acceptation et la conservation du meilleur résultat restent ceux de la V1. La graine 42 contrôle le générateur du recuit, mais pas l'aléatoire interne de Qiskit.

La calibration peut aider à adapter l'exploration à l'échelle des coûts d'une instance. Elle consomme cependant une partie du budget et peut être peu représentative des régions explorées ensuite. Une amélioration de performance n'est donc pas garantie.

## Exécution et résultats

Choisir `instance_num` dans `StudentCodeV2.py`, indépendamment de la V1, puis lancer depuis le dossier du projet :

```powershell
.\.venv310\Scripts\python.exe StudentCodeV2.py
```

Les paramètres réglables comprennent `NB_ITERATIONS`, `NB_CALIBRATION`, `PROBABILITE_INITIALE`, `TEMPERATURE_SECOURS`, `TEMPERATURE_FINALE` et `GRAINE`. La calibration doit être strictement plus petite que le nombre d'itérations.

Les fichiers de solution sont enregistrés dans `resultats_v2/`, au format du professeur. Ils n'écrasent pas les résultats de la V1 à la racine. Une nouvelle exécution V2 pour le même groupe et la même instance remplace le résultat V2 précédent.

## Résultats sur les neuf instances

Les résultats ci-dessous proviennent des sorties du terminal transmises par l'utilisateur. Les neuf coûts et placements concordent avec les fichiers `resultats_v2/GroupeX_Challenge_1.txt` à `GroupeX_Challenge_9.txt`. Les temps et les températures proviennent des sorties du terminal, car les fichiers de solution ne les enregistrent pas. L'instance 4 apparaît deux fois à l'identique dans le message : elle est comptée une seule fois, sans considérer ce doublon comme une répétition indépendante.

Chaque essai utilise 1 000 mouvements, dont 50 de calibration et 950 de recherche, soit 1 001 appels à `fitness`. La graine Python est 42, la cible d'acceptation initiale 0,8 et la température finale 0,1. L'environnement du projet utilise Python 3.10 et Qiskit 1.2.4.

| Instance | n | m | Coût initial | Hausses sur 50 mouvements | Température initiale | Meilleur coût V2 | Temps (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 12 | 16 | 52 | 24 | 25,604 | 29 | 37,64 |
| 2 | 16 | 16 | 119 | 27 | 108,780 | 60 | 298,13 |
| 3 | 10 | 16 | 209 | 26 | 78,933 | 119 | 107,83 |
| 4 | 19 | 20 | 66 | 18 | 22,657 | 32 | 54,45 |
| 5 | 12 | 20 | 371 | 21 | 100,120 | 315 | 147,69 |
| 6 | 14 | 20 | 115 | 24 | 53,618 | 31 | 51,67 |
| 7 | 20 | 27 | 102 | 24 | 56,428 | 38 | 65,15 |
| 8 | 20 | 27 | 76 | 24 | 46,046 | 36 | 75,25 |
| 9 | 25 | 27 | 154 | 28 | 73,366 | 61 | 118,98 |

### Comparaison aux références du cours

Les références sont celles du tableau de la dernière page de `Présentation_Qubit_Allocation.pdf`. La référence retenue est le minimum entre les colonnes SABRE et GRASP du support. Seules les valeurs 59 pour l'instance 2 et 22 pour l'instance 7 sont indiquées comme exactes dans ce tableau ; les autres ne doivent pas être présentées comme des optima prouvés.

L'écart relatif est calculé par `(coût V2 - référence) / référence × 100`. Un écart négatif indique un coût observé inférieur à la référence du support.

| Instance | SABRE | GRASP | Référence retenue | V2 | Écart relatif |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 | 50 | 31 | 31 | 29 | -6,45 % |
| 2 | 59 | 59 | 59 (exact) | 60 | +1,69 % |
| 3 | 108 | 113 | 108 | 119 | +10,19 % |
| 4 | 35 | 30 | 30 | 32 | +6,67 % |
| 5 | 323 | 308 | 308 | 315 | +2,27 % |
| 6 | 25 | 25 | 25 | 31 | +24,00 % |
| 7 | 22 | 22 | 22 (exact) | 38 | +72,73 % |
| 8 | 17 | 17 | 17 | 36 | +111,76 % |
| 9 | 51 | 36 | 36 | 61 | +69,44 % |

La V2 améliore le placement initial sur chaque instance. Elle obtient un coût inférieur à la référence du support sur l'instance 1 et reste à une unité de l'optimum connu sur l'instance 2. Les écarts les plus importants concernent les instances 7, 8 et 9. Ces comparaisons ne démontrent pas une supériorité générale sur les méthodes du support, dont les conditions d'exécution ne sont pas établies ici.

### Comparaison aux essais V1

Les essais V1 sont maintenant documentés pour les neuf instances. Chaque version dispose de 1 001 évaluations par instance ; la V2 en réserve 50 à la calibration. Les résultats V1 des instances 1 et 2 proviennent des premiers essais, ceux des instances 3 à 9 du complément de terminal transmis ensuite.

| Instance | Coût V1 | Coût V2 | Différence V2 - V1 | Temps V1 | Temps V2 |
| --- | ---: | ---: | ---: | --- | --- |
| 1 | 20 | 29 | +9 | Non consigné | 37,64 s |
| 2 | 62 | 60 | -2 | Environ 180 s | 298,13 s |
| 3 | 129 | 119 | -10 | 103,61 s | 107,83 s |
| 4 | 34 | 32 | -2 | 37,33 s | 54,45 s |
| 5 | 316 | 315 | -1 | 173,69 s | 147,69 s |
| 6 | 31 | 31 | 0 | 56,81 s | 51,67 s |
| 7 | 42 | 38 | -4 | 66,87 s | 65,15 s |
| 8 | 28 | 36 | +8 | 76,63 s | 75,25 s |
| 9 | 74 | 61 | -13 | 82,48 s | 118,98 s |

Sur les essais rapportés, la V2 obtient un meilleur coût sur six instances (2, 3, 4, 5, 7 et 9), un coût identique sur l'instance 6 et un coût moins bon sur les instances 1 et 8. Le gain le plus grand en unités de coût concerne l'instance 9 : 74 à 61. Ces unités n'ont pas nécessairement la même portée selon l'instance ; elles ne doivent pas être additionnées pour établir un score global sans justification.

Le temps n'évolue pas uniformément : la V2 est plus lente sur les instances 2, 3, 4 et 9, et plus rapide sur 5, 6, 7 et 8 dans ces mesures. Le temps V1 de l'instance 1 manque. Sur l'instance 2, la hausse est d'environ 118 s, avec un temps V1 seulement approximatif.

Les 50 évaluations de calibration ne sont pas ajoutées au budget. Les écarts de temps ne peuvent donc pas être expliqués simplement par des appels supplémentaires. Le coût de transformation des placements explorés et les conditions d'exécution peuvent intervenir ; aucun profilage n'isole leur contribution.

Ces observations sont encourageantes pour la qualité sur plusieurs instances, mais un seul essai par version et par instance ne démontre pas un gain systématique. Les coûts initiaux peuvent aussi varier avec l'aléatoire interne de Qiskit, même lorsque la graine Python est identique. Les essais n'ont pas été réalisés comme une campagne de répétitions contrôlées.

### Lecture des trajectoires

Les températures calibrées vont de 22,657 à 108,780 : les hausses observées n'ont pas la même échelle selon les instances. Cela confirme que la calibration adapte effectivement la température, mais pas qu'elle améliore systématiquement les résultats.

Plusieurs essais progressent encore tardivement. Sur l'instance 1, le meilleur coût passe de 31 à 29 entre les affichages 900 et 950 ; sur l'instance 7, il passe de 40 à 38 sur le même intervalle. À l'inverse, les instances 8 et 9 ne montrent plus d'amélioration entre les affichages 800 et 950. Ces observations suggèrent des comportements différents, sans prouver la convergence ni justifier à elles seules un changement de paramètres.

## Vérifications et limites

Pendant le développement, quatre tests ont vérifié la calibration de la probabilité moyenne, le budget exact et la validité des placements, la conservation du meilleur résultat trouvé pendant la calibration et le rejet des paramètres invalides avant toute évaluation. Les fichiers auxiliaires de tests et d'essais courts ont ensuite été retirés ; ils ne sont pas nécessaires à l'exécution du recuit.

Les résultats ci-dessus correspondent à un essai rapporté par instance, pas à une moyenne de plusieurs recherches. La graine du recuit ne fixe pas l'aléatoire interne de Qiskit. Les coûts sont les meilleurs coûts observés pendant la recherche ; ces neuf placements V2 n'ont pas fait l'objet ici de réévaluations répétées. Les 20 réévaluations mentionnées dans la documentation V1 concernent uniquement son placement de coût 20 sur l'instance 1.

La calibration seule n'apporte donc pas encore de gain général démontré. Une comparaison plus solide nécessitera plusieurs graines et le même budget total pour chaque version, en comparant à la fois les coûts et les temps. Cette mise à jour consigne les essais sans modifier l'algorithme.
