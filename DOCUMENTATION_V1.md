# Première version du recuit simulé

Cette documentation décrit la première version de `StudentCode.py` et les essais réalisés sur les instances 1 et 2 du problème d'allocation de qubits. 

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
