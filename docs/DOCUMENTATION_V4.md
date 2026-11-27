# Recuit simulé avec relances après stagnation

## Mode actuel : budget de cinq minutes

Depuis la modification du 26 novembre 2026, le programme utilise `DUREE_SECONDES = 300` par défaut (5 minutes). L'argument de `recuit_simule` est désormais `duree_secondes=300` ; `nb_iterations` a été supprimé. Le nombre d'évaluations est affiché à titre de mesure, sans servir de limite.

Le budget est du temps réel écoulé mesuré par `perf_counter`, pas du temps CPU. Il inclut l'évaluation initiale, la recherche et ses affichages, mais exclut le chargement préalable de l'instance et l'écriture finale du fichier. La limite est vérifiée avant chaque nouvelle évaluation après l'initialisation. Une évaluation Qiskit déjà commencée termine normalement : le temps final peut dépasser légèrement le budget, voire davantage si cet appel est long. Un premier placement est toujours évalué pour garantir un résultat, même avec une durée très courte.

Le refroidissement géométrique dépend de la fraction du temps de recherche écoulé, et non du nombre d'itérations. La température tend vers la température finale à l'échéance ; la dernière évaluation peut commencer avant de l'atteindre exactement.

La calibration utilise `FRACTION_CALIBRATION = 0.05` : sa limite est fixée à 15 secondes après le début de la recherche pour un budget de 300 secondes, évaluation initiale comprise. Son nombre de mouvements est variable. Un appel de calibration en cours peut dépasser cette limite ; ce temps est déduit du temps restant pour le recuit. La calibration cesse toujours de lancer des appels à sa propre échéance. S'il n'y a aucune hausse observée, la température de secours est utilisée.

Les relances utilisent désormais `STAGNATION_SECONDES = 45` et `MIN_RESTANT_RELANCE_SECONDES = 15`. Le chronomètre de stagnation commence à la fin de la calibration et repart à zéro après une amélioration du meilleur coût ou une relance. Les trois mouvements de perturbation et le facteur de réchauffage 0,25 restent identiques. Chaque relance refroidit ensuite sur le temps restant, sans repousser l'échéance globale.

Le comparateur `comparer_v2_v4.py` applique lui aussi 300 secondes par recherche, soit environ **90 minutes pour les 18 essais**. Il compare des temps alloués égaux, pas des nombres d'évaluations égaux, et consigne le nombre effectivement réalisé. Aucune campagne complète à cinq minutes n'a été lancée pour valider cette modification.

**Les sections suivantes décrivent le protocole historique à nombre d'itérations fixé.** Les résultats déjà enregistrés sont conservés et ne doivent pas être présentés comme des essais à cinq minutes. Les anciennes signatures et limites en évaluations qui y sont citées sont remplacées par les paramètres ci-dessus. Il faudra une nouvelle campagne pour comparer les versions à durée égale. Les commandes de lancement et dossiers de sortie restent identiques ; une nouvelle exécution peut remplacer une ancienne solution du même groupe et de la même instance.

## Historique avant le passage au budget temporel

La V4 reprend la V2, avec sa calibration et son choix de catégorie de mouvement à 50/50 lorsqu'une position est libre. Elle ajoute une perturbation du meilleur placement après stagnation et un réchauffage temporaire. Elle n'utilise aucun placement ni score de référence du cours.

## Déroulement d'une relance

Le compteur de stagnation augmente à chaque évaluation de recherche sans amélioration stricte du meilleur coût global. Une égalité ne le remet pas à zéro. Après 150 évaluations sans amélioration, une relance est effectuée à l'itération suivante, s'il reste au moins 50 évaluations et qu'un mouvement est possible.

La relance repart d'une copie du meilleur placement et applique trois mouvements aléatoires successifs de la V2. Si ces mouvements reviennent exactement au meilleur placement, un mouvement supplémentaire assure un placement différent. Cela ne garantit pas trois modifications distinctes : des mouvements peuvent partiellement s'annuler.

Le placement final de la perturbation est évalué une seule fois et devient le placement courant, même si son coût est moins bon. Les placements intermédiaires ne sont pas évalués. Le meilleur résultat global est préservé, ou mis à jour si le saut l'améliore.

La température est remontée au maximum entre sa valeur courante, 25 % de la température initiale calibrée et la température finale. Un refroidissement géométrique reprend depuis cette température pour atteindre 0,1 à la dernière évaluation du budget. Le compteur de stagnation est remis à zéro après le saut. Une nouvelle relance est possible si la recherche stagne à nouveau.

## Budget et paramètres

Le budget reste identique à V2 : 1 initialisation + 50 évaluations de calibration + 950 évaluations de recherche = 1 001 appels à `fitness`. Chaque saut remplace une évaluation de voisin ordinaire ; il n'ajoute aucun appel au budget. La calibration n'entre pas dans le compteur de stagnation.

| Paramètre | Valeur initiale |
| --- | ---: |
| `NB_ITERATIONS` | 1 000 |
| `NB_CALIBRATION` | 50 |
| `PROBABILITE_INITIALE` | 0,8 |
| `TEMPERATURE_FINALE` | 0,1 |
| `SEUIL_STAGNATION` | 150 |
| `NB_PERTURBATIONS` | 3 |
| `FACTEUR_RECHAUFFAGE` | 0,25 |
| `MIN_RESTANT_RELANCE` | 50 |
| `GRAINE` | 42 |

Ces valeurs constituent une hypothèse expérimentale, pas un réglage optimal établi. Réchauffer peut aider à quitter une zone peu favorable, mais peut aussi consommer des évaluations qui auraient servi à améliorer le placement courant.

## Lancer une instance

Choisir `instance_num` dans `StudentCodeV4.py`, enregistrer, puis lancer :

```powershell
.\.venv310\Scripts\python.exe StudentCodeV4.py
```

Les résultats manuels sont enregistrés dans `resultats_v4/`. Une nouvelle exécution de la même instance avec le même numéro de groupe remplace le résultat précédent. Le terminal indique chaque relance, le coût du saut et le nombre total de relances.

## Comparaison automatique

```powershell
.\.venv310\Scripts\python.exe comparer_v2_v4.py
```

Ce script réalise 18 recherches : V2 et V4, sur les instances 4, 7 et 9, avec les graines 42, 43 et 44. Le budget de chaque recherche est identique. Les essais sont séquentiels et l'ordre des deux versions est alterné. Il faut prévoir plusieurs minutes pour l'ensemble de la campagne.

Chaque campagne crée un nouveau sous-dossier daté dans `comparaisons_v2_v4/`, avec un `RAPPORT.md` mis à jour après chaque recherche, les journaux et les placements obtenus. Les résultats manuels restent intacts. Si le script est interrompu, les essais terminés sont conservés ; une nouvelle exécution commence une nouvelle campagne, sans reprendre automatiquement l'ancienne.

Les médianes et meilleurs coûts sont comparés par instance, ainsi que les temps médians. Le hasard interne de Qiskit n'est pas fixé et les meilleurs placements ne sont pas réévalués dans cette campagne. Trois graines permettent un premier diagnostic, pas une preuve statistique définitive. Les paramètres de la V4 restent fixés pendant toute la comparaison.

## Vérification du fonctionnement

Les contrôles exécutés directement vérifient le budget exact avec des relances, l'admissibilité des placements, le déclenchement sur un plateau, la conservation d'un meilleur résultat trouvé pendant un saut et les cas limites. Quand le seuil empêche toute relance, V4 reproduit V2 sur la même fonction déterministe et avec la même graine. Aucun fichier de tests supplémentaire n'est nécessaire pour lancer l'algorithme.
