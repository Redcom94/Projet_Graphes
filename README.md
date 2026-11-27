
StudentCode.py : implémentation de l'algorithme Tabu Search.

source.py : chargement des instances, configuration des backends et calcul de la fitness.

run_all.py : automatisation des expériences sur les 9 instances.

Instances/ : circuits quantiques au format QASM.

resultats_tabu/ : résultats expérimentaux générés.


EXCSUTION DU PROGRAMME 

Le programme nécessite Python et une version de Qiskit compatible avec les backends utilisés dans source.py.

Version utilisée pour la compatibilité avec les anciens faux backends :

python -m pip install "qiskit==1.3.3"

Pour exécuter Tabu Search sur une instance :

python StudentCode.py

Pour exécuter les expériences sur les 9 instances :

python run_all.py

Pour effectuer plusieurs répétitions, si l'option est disponible dans run_all.py :

python run_all.py --runs 5
