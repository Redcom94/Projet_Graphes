# V5 Construction structurelle et recherche locale avec mémoire

La V5 est implémentée dans `StudentCodeV5.py`. Elle construit des placements à partir du circuit et de la machine, puis utilise une recherche locale avec mémoire tabou et un ensemble de solutions élites. Elle ne modifie ni le circuit, ni le backend, ni `source.py`. Les affectations ne dépendent jamais du numéro de l'instance et aucune solution connue n'est injectée.

## Essais courts de fonctionnement

Deux essais Qiskit avec un budget de seulement 5 secondes et la graine 42 ont donné :

| Instance | Médiane retenue | Observations du placement | Temps réel | Évaluations |
| --- | ---: | --- | ---: | ---: |
| 2 | 59 | 59, 59, 59 | 5,93 s | 13 |
| 7 | 87 | 87, 87, 84 | 5,06 s | 26 |

Ces essais vérifient l'exécution et la validité des placements, pas la supériorité de V5. Le résultat de l'instance 7 montre notamment qu'un budget aussi court ne suffit pas à juger la méthode. Le dépassement correspond à une évaluation déjà engagée. Aucun comparatif complet à 300 secondes n'est encore établi pour cette version.

## Résultat historique avant correction du critère (budget de 300 secondes)

Essai de l'instance 1 transmis par l'utilisateur :

| Coût initial | Médiane finale | Coût exporté | Temps réel | Évaluations |
| ---: | ---: | ---: | ---: | ---: |
| 51 | 28 | 32 | 270,46 s | 7 239 |

Placement retenu : `[5, 9, 11, 6, 8, 12, 4, 14, 13, 3, 2, 10]`.

Ses cinq coûts observés sont `[28, 39, 28, 28, 32]`. Après tri (`28, 28, 28, 32, 39`), la médiane vaut **28**. Le fichier `resultats_v5/GroupeX_Challenge_1.txt` contient **32**, car le programme exporte la dernière observation de ce placement. Le minimum observé pour ce placement est 28 et son maximum est 39.

La meilleure médiane élite affichée pendant la recherche atteint 27. Il s'agit d'un score provisoire avant validation, qui n'est pas la médiane finale du placement retenu. Le journal seul ne permet pas de déterminer les observations finales du candidat qui avait ce score.

La recherche s'arrête vers 270 secondes (90 % du budget), puis la validation se termine rapidement après avoir complété les mesures des finalistes. Le programme n'utilise donc pas les 30 secondes restantes en totalité. Cet essai ne démontre pas un gain à temps égal face aux versions précédentes.

## Campagne utilisateur après correction : neuf instances

Budget annoncé : 300 secondes par instance. Résultats transmis par l'utilisateur ; une exécution par instance. Le critère est le minimum observé, également exporté dans la solution.

| Instance | Coût initial | Meilleur coût | Mesures du placement retenu | Temps réel (s) | Évaluations |
| --- | ---: | ---: | --- | ---: | ---: |
| 1 | 55 | 27 | 27, 27, 28, 29, 31 | 270,36 | 7 433 |
| 2 | 119 | 59 | 59, 59, 59, 59, 59 | 272,08 | 1 035 |
| 3 | 200 | 115 | 115, 143, 150, 124, 124 | 271,08 | 2 641 |
| 4 | 66 | 28 | 28, 30, 28, 33, 36 | 270,47 | 7 619 |
| 5 | 370 | 308 | 317, 308, 334, 334, 334 | 272,43 | 1 622 |
| 6 | 113 | 25 | 25, 25, 25, 25, 25 | 270,51 | 6 048 |
| 7 | 99 | 22 | 22 | 270,26 | 5 350 |
| 8 | 76 | 18 | 18, 18, 18, 18, 18 | 270,41 | 4 032 |
| 9 | 154 | 35 | 35, 35, 35, 35, 35 | 270,54 | 5 065 |

Placements retenus, dans l'ordre des qubits logiques :

```text
1 : [3, 5, 12, 11, 10, 14, 13, 2, 15, 9, 1, 4]
2 : [0, 15, 14, 1, 2, 13, 12, 3, 4, 11, 10, 5, 6, 7, 8, 9]
3 : [10, 6, 11, 12, 14, 1, 4, 13, 2, 3]
4 : [7, 8, 1, 12, 13, 6, 3, 15, 5, 19, 11, 4, 18, 0, 16, 14, 2, 9, 10]
5 : [13, 12, 9, 5, 8, 2, 3, 0, 10, 7, 6, 1]
6 : [1, 10, 8, 3, 13, 18, 17, 14, 12, 11, 6, 2, 5, 7]
7 : [0, 4, 7, 10, 12, 15, 18, 21, 23, 24, 25, 16, 19, 22, 14, 11, 8, 5, 3, 2]
8 : [7, 4, 12, 15, 5, 8, 19, 22, 18, 21, 23, 25, 13, 11, 14, 20, 10, 2, 1, 3]
9 : [20, 9, 24, 11, 26, 23, 21, 18, 15, 6, 12, 25, 22, 5, 8, 3, 2, 1, 4, 7, 10, 13, 14, 16, 19]
```

### Points de comparaison et limites

Un collègue a obtenu, selon l'utilisateur, **26, 59 et 110** sur les trois premières instances avec une combinaison recuit simulé/génétique. Les écarts V5 sont donc **+1, 0 et +5**. Le budget, le matériel et le protocole de ces essais ne sont pas connus : ce sont des résultats atteignables rapportés, pas une comparaison contrôlée ni des optima prouvés. Cette information ne prescrit pas d'utiliser les mêmes algorithmes.

Les coûts V5 sont inférieurs aux résultats historiques V2 et V3 sur les neuf instances, mais ces anciennes campagnes étaient limitées à 1 000 évaluations : cela ne démontre pas la supériorité de V5 à temps égal. Le résultat historique V1 de 20 pour l'instance 1 reste inférieur à 27 ; il mérite aussi une vérification dans des conditions comparables.

Les placements des instances 2, 6, 8 et 9 reproduisent leur minimum sur leurs cinq mesures. Ceux des instances 3 et 5 ont une dispersion importante. Le placement finalement retenu pour l'instance 7 n'a qu'une mesure : la sélection globale peut choisir un placement extérieur aux quatre finalistes réévalués. Cela reste conforme au critère du minimum observé, mais ne constitue pas cinq confirmations.

Les journaux montrent des plateaux longs, notamment sur les instances 2, 5, 6, 7 et 8. Ils ne prouvent pas l'optimalité. Deux pistes à évaluer sont l'utilisation du temps laissé libre après validation (environ 28 à 30 secondes ici) et une diversification mieux adaptée à la stagnation. Aucune modification algorithmique n'est effectuée à partir de cette seule campagne.

## Lancement

Modifier `instance_num`, enregistrer le fichier, puis lancer depuis le dossier du projet :

```powershell
.\.venv310\Scripts\python.exe StudentCodeV5.py
```

`DUREE_SECONDES = 300` fixe un budget maximal de cinq minutes. `GRAINE = 42` contrôle le générateur Python mais pas le hasard interne de Qiskit. `NUMERO_GROUPE` est à renseigner avant le rendu. Le fichier est initialement réglé sur l'instance 1.

## Construction des placements

Une solution aléatoire est évaluée avant le prétraitement pour garantir un résultat même avec une durée très courte. La V5 lit ensuite les interactions à deux qubits et les connexions physiques. Les distances sont calculées sur le graphe physique non orienté : il s'agit d'une approximation pour proposer des placements, pas d'un remplacement du compilateur.

Deux indicateurs rapides sont utilisés en alternance : somme des distances pondérées par les fréquences d'interaction, et somme des distances pondérées en faveur des interactions précoces. Le second utilise l'ordre des portes à deux qubits et une pondération exponentielle. Il ne simule ni le routage dynamique, ni la profondeur finale.

Les composantes logiques en chaîne ou cycle sont détectées par leurs connexions. Une recherche de chemin physique est limitée à 0,08 seconde par composante, dans le budget restant. Pour un cycle, la fermeture est recherchée. Si la recherche échoue, le meilleur chemin partiel trouvé est utilisé ; cela ne prouve pas qu'un chemin complet n'existe pas. Les qubits restants sont placés par construction gloutonne aléatoire, avec priorité aux qubits fortement connectés. Les étoiles et graphes généraux utilisent cette construction, sans règle codée pour une instance particulière.

Au maximum 16 candidats sont proposés pendant la phase initiale, limitée aux 12 premiers pour cent du temps total. Les candidats alternent construction structurelle, construction générale et placements entièrement aléatoires. Les doublons ne sont pas réévalués pendant cette phase.

## Recherche locale et diversité

La recherche conserve jusqu'à six solutions élites. Une distance minimale entre leurs affectations évite de remplir l'archive de placements presque identiques. Il s'agit d'une diversité de représentations, pas d'une preuve de diversité des circuits compilés.

À chaque étape, les voisins possibles sont les échanges de deux positions utilisées et les remplacements par une position libre. Les voisins déjà évalués sont écartés de cette génération. Les affectations récemment abandonnées sont temporairement taboues pendant sept tours, pour éviter les retours immédiats. Ce sont des paramètres internes de la recherche ; l'arrêt global reste uniquement temporel.

Deux voisins bien classés par l'indicateur rapide et un voisin aléatoire sont proposés à `fitness`. Le candidat aléatoire limite le risque de suivre aveuglément une approximation imparfaite. La meilleure proposition réellement évaluée devient la solution courante, même en cas de détérioration ; les élites restent conservées. Après 18 tours sans amélioration du meilleur score élite, une nouvelle construction diversifie la recherche.

Toutes les 15 étapes, si deux élites sont disponibles, un court chemin de recombinaison effectue au plus quatre pas vers les affectations d'un autre placement. Chaque pas conserve la validité par échange ou remplacement. Les placements intermédiaires nouveaux sont évalués. Ce mécanisme peut être désactivé avec `ACTIVER_RELIAGE = False` pour mesurer sa contribution indépendamment.

## Coûts variables et validation

`fitness` est utilisée sans modification. Un placement peut recevoir plusieurs coûts à cause du hasard interne de Qiskit. Après correction demandée par l'utilisateur, V5 classe les placements par **meilleur coût réellement observé**, et non par médiane. Une mesure ultérieure plus élevée ne peut plus effacer un record.

Les candidats prometteurs sont réévalués jusqu'à trois fois si le temps le permet. Les dix derniers pour cent du budget sont réservés à quatre finalistes, réévalués jusqu'à cinq mesures chacun. Ces appels peuvent améliorer leur record. La solution finale est choisie parmi **tous** les placements observés selon leur minimum, avec la médiane comme seul départage en cas d'égalité. La médiane reste informative ; elle ne remplace jamais un minimum inférieur.

Le coût exporté est le minimum effectivement mesuré pour le placement retenu. Cela ne garantit pas qu'un nouvel appel Qiskit reproduise ce coût : seul le placement est exporté, pas le circuit compilé qui a obtenu le record.

Le programme peut finir avant cinq minutes si la validation est terminée. Une évaluation commencée termine normalement même si elle dépasse l'échéance ; aucun nouvel appel n'est commencé après. Le prétraitement, les constructions, la recherche et la validation sont inclus dans le budget, contrairement au chargement initial de l'instance et à l'écriture finale des fichiers.

## Fichiers produits

Les sorties sont dans `resultats_v5/` :

- `GroupeX_Challenge_<instance>.txt` : placement puis **meilleur coût réellement observé pour ce placement**, au format du professeur.
- `GroupeX_Challenge_<instance>_bilan.txt` : médiane informative, toutes ses observations, finalistes, temps, nombre d'évaluations et répartition par phase.

Le coût exporté correspond désormais au meilleur coût observé de toute la recherche et appartient au placement retenu. Les résultats historiques ci-dessus restent ceux de l'ancienne sélection par médiane. Une nouvelle exécution de la même instance et du même groupe remplace les deux fichiers correspondants. Les résultats V0 à V4 restent intacts.

## Vérifications et limites

Des contrôles exécutés directement ont vérifié la validité et la cardinalité des voisinages, les pas de recombinaison, les constructeurs sur les neuf instances, le respect de l'échéance avant les évaluations, les paramètres invalides et la cohérence des observations et médianes. Un budget très court et une évaluation dépassant seule la durée ont aussi été vérifiés. Aucun fichier de tests supplémentaire n'est nécessaire pour lancer la V5.

La recherche de chemin est bornée, la présélection peut écarter de bons voisins et le classement reste sensible au bruit. Cette V5 est une hypothèse expérimentale : aucun optimum général ni avantage systématique en cinq minutes n'est revendiqué. Les résultats historiques à nombre d'itérations fixé ne constituent pas une comparaison à durée égale. Il faut comparer les versions sur les mêmes ressources, à durée égale, avec plusieurs graines et des réévaluations finales comparables.

## Inspirations et différences

La combinaison de construction de placements et de mémoire tabou est motivée notamment par [Qubit Mapping Based on Tabu Search, 2024](https://jcst.ict.ac.cn/article/doi/10.1007/s11390-023-2121-5). Cet article traite aussi du routage : V5 n'en reproduit pas l'algorithme complet et conserve le routage fourni par le professeur.

L'archive et les chemins entre solutions s'inspirent de [la revue GRASP avec Path Relinking, 2025](https://doi.org/10.1016/j.ejor.2025.02.022). Notre chemin court et notre présélection sont des choix d'implémentation spécifiques au budget disponible, pas une configuration optimale démontrée par cette revue.

L'attention portée au coût des évaluations rejoint [FAT-RLS, 2022](https://ricerca.unistrapg.it/retrieve/63ebbac6-649e-4cbf-8a38-dea541a4792d/_IEEE_WCCI_2022____Low_Budget_Permutation.pdf). V5 n'est pas une implémentation de FAT-RLS : les mouvements, constructions et règles de sélection diffèrent.
