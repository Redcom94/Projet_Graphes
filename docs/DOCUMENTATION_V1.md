# Première version du recuit simulé

## Mode actuel : budget de cinq minutes

Depuis la modification du 26 novembre 2026, le programme utilise `DUREE_SECONDES = 300` par défaut (5 minutes). L'argument de `recuit_simule` est désormais `duree_secondes=300` ; `nb_iterations` a été supprimé. Le nombre d'évaluations est affiché à titre de mesure, sans servir de limite.

Le budget est du temps réel écoulé mesuré par `perf_counter`, pas du temps CPU. Il inclut l'évaluation initiale, la recherche et ses affichages, mais exclut le chargement préalable de l'instance et l'écriture finale du fichier. La limite est vérifiée avant chaque nouvelle évaluation après l'initialisation. Une évaluation Qiskit déjà commencée termine normalement : le temps final peut dépasser légèrement le budget, voire davantage si cet appel est long. Un premier placement est toujours évalué pour garantir un résultat, même avec une durée très courte.

Le refroidissement géométrique dépend de la fraction du temps de recherche écoulé, et non du nombre d'itérations. La température tend vers la température finale à l'échéance ; la dernière évaluation peut commencer avant de l'atteindre exactement.

**Les sections suivantes décrivent le protocole historique à nombre d'itérations fixé.** Les résultats déjà enregistrés sont conservés et ne doivent pas être présentés comme des essais à cinq minutes. Les anciennes signatures et limites en évaluations qui y sont citées sont remplacées par les paramètres ci-dessus. Il faudra une nouvelle campagne pour comparer les versions à durée égale. Les commandes de lancement et dossiers de sortie restent identiques ; une nouvelle exécution peut remplacer une ancienne solution du même groupe et de la même instance.

## Historique avant le passage au budget temporel

Cette documentation décrit la première version de `StudentCode.py` et les essais réalisés sur les neuf instances du problème d'allocation de qubits. 

## Objectif et représentation

Le programme cherche à minimiser la fonction `fitness` fournie par le professeur. Dans `source.py`, cette fonction renvoie la profondeur du circuit obtenu après transformation par Qiskit.

Une solution est une liste de `n` entiers distincts compris entre `0` et `m - 1`. L'indice désigne le qubit logique et la valeur sa position physique. Par exemple, `[2, 0, 4]` place les qubits logiques 0, 1 et 2 sur les positions physiques 2, 0 et 4.

Le fichier `source.py` n'est pas modifié. L'algorithme utilise uniquement les coûts renvoyés par la fonction fournie. Aucun placement connu ni optimum de référence n'est utilisé pour guider la recherche ou déclencher son arrêt.

## Fonctionnement du recuit

1. Générer un placement initial aléatoire, sans répétition, avec `random.sample`.
2. Évaluer ce placement et l'enregistrer comme meilleur résultat initial.
3. Générer un voisin admissible et calculer son coût.
4. Accepter systématiquement un coût inférieur ou égal au coût courant. Pour une augmentation `delta > 0`, accepter avec la probabilité `exp(-delta / T)`.
5. Conserver séparément le meilleur placement rencontré, même si la recherche accepte ensuite une dégradation.
6. Répéter jusqu'à épuisement du nombre d'itérations, puis enregistrer le meilleur placement et son coût observé.

La température décroît géométriquement. Pour `N > 1` itérations, à l'itération `k` numérotée de 0 à `N - 1` :

```text
T(k) = T_initiale × (T_finale / T_initiale) ** (k / (N - 1))
```

Une température élevée facilite l'acceptation de dégradations ; une température basse rend la recherche plus sélective. Les coûts égaux restent acceptés.

### Voisinage

Deux mouvements sont disponibles :

- Échanger les positions de deux qubits logiques.
- Remplacer une position utilisée par une position libre, lorsqu'il en existe.

Pour l'instance 1, les deux mouvements sont sélectionnés avec une probabilité de 50 % chacun. Pour l'instance 2, toutes les positions sont occupées : seuls les échanges sont possibles. Ces opérations préservent la longueur de la liste, l'absence de doublons et les bornes autorisées.

## Paramètres des essais à 1 000 itérations

| Paramètre | Valeur |
| --- | --- |
| Nombre d'itérations | 1 000 |
| Température initiale | 20 |
| Température finale | 0,1 |
| Graine du générateur Python | 42 |
| Initialisation | Placement aléatoire sans répétition |
| Appels à `fitness` | 1 001, initialisation comprise |
| Python utilisé | 3.10 |
| Qiskit | 1.2.4 |

Le lancement principal transmet explicitement `NB_ITERATIONS = 1000`. La valeur par défaut de l'argument de la fonction `recuit_simule` reste 500 : elle ne s'applique que si cet argument est omis lors d'un appel direct.

## Résultats observés

Les références proviennent du tableau de la présentation `Présentation_Qubit_Allocation.pdf`, dernière page. Elles servent à comparer les résultats après exécution.

| Instance | n | m | Itérations | Meilleur coût observé | Temps | Référence du support |
| --- | --- | --- | --- | --- | --- | --- |
| 1, premier essai | 12 | 16 | 500 | 33 | 36,33 s mesurées | 31 (GRASP), 50 (SABRE) |
| 1, essai suivant | 12 | 16 | 1 000 | 20 | Non consigné | 31 (GRASP), 50 (SABRE) |
| 2 | 16 | 16 | 1 000 | 62 | Environ 180 s rapportées par l'utilisateur | 59, indiqué comme optimum exact |

Les coûts 20 et 62 ont été lus respectivement dans `GroupeX_Challenge_1.txt` et `GroupeX_Challenge_2.txt`. Ces fichiers ne contiennent ni les paramètres ni le temps d'exécution ; les paramètres sont ceux de la version utilisée dans les échanges et le code consulté. Le temps de 180 s est une indication de l'utilisateur, pas une mesure enregistrée dans le fichier.

### Instance 1

Placement sauvegardé pour le coût 20 :

```text
[2, 14, 3, 12, 10, 11, 1, 4, 8, 6, 5, 13]
```

Ce placement a été vérifié comme admissible et réévalué 20 fois avec la fonction fournie. Les 20 évaluations ont donné 20 : minimum, moyenne et maximum valent donc tous 20 sur cette vérification.

Ce résultat est inférieur à la référence de 31 indiquée dans le support. Il ne prouve pas que 20 soit optimal et ne suffit pas à établir une supériorité générale du recuit sur GRASP. Les conditions exactes des essais du support ne sont pas documentées ici. Les 20 réévaluations vérifient un même placement ; ce ne sont pas 20 exécutions indépendantes de l'algorithme.

Le passage de 500 à 1 000 itérations a accompagné une amélioration de 33 à 20 sur les essais observés. Comme Qiskit peut introduire de l'aléatoire, ces deux essais ne permettent pas d'attribuer tout le gain au seul nombre d'itérations.

### Instance 2

Placement sauvegardé pour le coût 62 :

```text
[13, 15, 0, 2, 1, 3, 4, 10, 7, 6, 8, 5, 9, 12, 11, 14]
```

L'écart à l'optimum de référence est de 3, soit environ 5,08 % : `(62 - 59) / 59 × 100`. Le coût de ce placement n'a pas fait l'objet de la série de réévaluations réalisée pour l'instance 1.

L'essai est sensiblement plus long. Chaque itération appelle Qiskit, dont le temps de transformation dépend du circuit et du placement. Le nombre de qubits ne suffit pas, à lui seul, à expliquer précisément le temps observé. Aucun profilage n'a encore été réalisé.

Le recuit utilise une seule trajectoire aléatoire et ne garantit pas d'atteindre l'optimum dans un budget de 1 000 itérations. La valeur 59 n'est ni une solution injectée dans l'initialisation, ni un critère d'arrêt de cette version.

## Complément des essais sur les instances 3 à 9

Ces essais proviennent du terminal transmis par l'utilisateur, avec 1 000 itérations, une température initiale de 20, une température finale de 0,1 et la graine 42 du code. Chaque recherche utilise 1 001 évaluations. Les coûts et placements ont été comparés aux fichiers `GroupeX_Challenge_3.txt` à `GroupeX_Challenge_9.txt` : ils concordent et les placements sont admissibles. Les temps sont ceux du terminal ; aucune réévaluation de `fitness` n'a été effectuée pour cette mise à jour.

Le fragment incomplet concernant `StudentCodeV2.py` et l'instance 9, inséré au milieu du texte, n'est pas un résultat V1 et n'est pas compté comme un essai supplémentaire.

La référence ci-dessous est le minimum entre SABRE et GRASP dans le support du cours. Parmi les instances 3 à 9, seule la référence 22 de l'instance 7 y est indiquée comme exacte. L'écart relatif est `(coût V1 - référence) / référence × 100`.

| Instance | n | m | Coût initial | Meilleur coût V1 | Temps (s) | Référence du cours | Écart relatif |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 3 | 10 | 16 | 180 | 129 | 103,61 | 108 | +19,44 % |
| 4 | 19 | 20 | 66 | 34 | 37,33 | 30 | +13,33 % |
| 5 | 12 | 20 | 372 | 316 | 173,69 | 308 | +2,60 % |
| 6 | 14 | 20 | 106 | 31 | 56,81 | 25 | +24,00 % |
| 7 | 20 | 27 | 99 | 42 | 66,87 | 22 | +90,91 % |
| 8 | 20 | 27 | 76 | 28 | 76,63 | 17 | +64,71 % |
| 9 | 25 | 27 | 160 | 74 | 82,48 | 36 | +105,56 % |

La V1 améliore le coût initial sur les sept essais, sans atteindre les références du cours. Les plus grands écarts relatifs concernent les instances 7, 8 et 9. Les traces montrent encore des améliorations entre les affichages 900 et 1 000 sur les instances 4 et 8 ; cela ne permet pas de conclure à une convergence. Il s'agit d'un essai rapporté par instance, pas d'une moyenne sur plusieurs graines.

### Placements conservés

Instance 3 — coût 129 :

```text
[1, 11, 2, 5, 9, 3, 12, 8, 15, 13]
```

Instance 4 — coût 34 :

```text
[7, 12, 13, 3, 6, 16, 5, 15, 8, 0, 14, 18, 17, 2, 11, 1, 10, 4, 19]
```

Instance 5 — coût 316 :

```text
[12, 5, 7, 8, 4, 6, 15, 11, 18, 3, 16, 1]
```

Instance 6 — coût 31 :

```text
[18, 17, 5, 2, 9, 3, 4, 8, 16, 11, 14, 12, 19, 7]
```

Instance 7 — coût 42 :

```text
[23, 5, 22, 15, 13, 24, 11, 4, 1, 12, 6, 21, 17, 10, 3, 16, 2, 9, 7, 0]
```

Instance 8 — coût 28 :

```text
[4, 1, 11, 16, 5, 8, 12, 23, 20, 26, 24, 21, 2, 9, 14, 17, 25, 18, 6, 7]
```

Instance 9 — coût 74 :

```text
[21, 22, 17, 0, 24, 12, 23, 25, 26, 7, 3, 11, 4, 5, 6, 8, 16, 2, 19, 20, 13, 9, 18, 1, 10]
```

La comparaison complète avec la V2 est présentée dans `DOCUMENTATION_V2.md`. Les essais historiques des instances 1 et 2 ci-dessus sont conservés.

## Vérifications et limites

Les vérifications réalisées sur la première version couvrent la validité des voisins, notamment avec ou sans positions libres, le nombre d'évaluations et la conservation du meilleur coût sur une fonction de test déterministe. Une exécution complète sur l'instance 1 a aussi vérifié l'enregistrement du résultat.

La graine 42 fixe le générateur utilisé par le recuit, mais pas celui des passes internes de Qiskit. Les coûts éventuellement différents peuvent modifier les décisions d'acceptation et la trajectoire. Le meilleur coût conservé est une valeur observée lors de la recherche ; il n'est pas systématiquement réévalué par le programme avant l'enregistrement.

Les principales limites actuelles sont une température choisie manuellement et commune aux instances, une seule initialisation, l'absence de redémarrages et l'absence de journal détaillé des essais. Les résultats disponibles ne constituent pas encore une étude statistique des performances.

## Utilisation

Depuis le dossier `Projet_Graphes`, lancer :

```powershell
.\.venv310\Scripts\python.exe StudentCode.py
```

Choisir `instance_num` dans la zone prévue par le professeur. Les paramètres du recuit se trouvent sous la section « À vous de jouer ». Renseigner `NUMERO_GROUPE` avant le rendu.

Le fichier produit suit le nom `GroupeX_Challenge_1.txt` pour le groupe X et l'instance 1. Il contient les positions, puis le coût, sur une ligne. Une nouvelle exécution pour le même groupe et la même instance remplace ce fichier : conserver une copie des résultats que l'on souhaite comparer.


## Dossier de sortie de la version de base

La version de base, appelée V1 dans cette documentation et V0 pour le rangement des sorties, reste exécutée par `StudentCode.py`. Les prochaines exécutions enregistrent les solutions dans `resultats_v0/`, créé automatiquement. Les résultats historiques mentionnés ci-dessus ont également été déplacés dans `resultats_v0/`. Le nom et le contenu des fichiers de solution sont inchangés.
