# -*- coding: utf-8 -*-
"""
Created on Tue Nov 14 11:08:40 2023

@author: Jérôme
"""

from source import instance_selector, fitness_inner

##-------------------------------------------------------
##     Definition de la fonction objetif à minimiser
##-------------------------------------------------------
def fitness(mapping):
    return fitness_inner(mapping, circuit, backend)

##-------------------------------------------------------
##     Pour choisir une instance: 
##     Modifier instance_num ET RIEN D'AUTRE   
##     La fonction instance_selector revoie n et m
##     ainsi que "backend" et "circuit" qui sont 
##     utiliser dans la fonction objectif (voir fitness) 
##-------------------------------------------------------
instance_num=9     #### Entre 1 et 9 inclue

backend,circuit,n,m = instance_selector(instance_num)

##-------------------------------------------------------
##     A vous de jouer !  
##-------------------------------------------------------

import math
import random
from pathlib import Path
from time import perf_counter


# Paramètres à adapter après les premiers essais.
NUMERO_GROUPE = "X"
DUREE_SECONDES = 300  # 5 minutes par exécution
TEMPERATURE_INITIALE = 20.0
TEMPERATURE_FINALE = 0.1
GRAINE = 42  # Fixe les mouvements, mais pas l'aléatoire interne de Qiskit.


def generer_voisin(solution, nb_positions, rng):
    """Échange deux qubits ou utilise une position physique encore libre."""
    voisin = solution.copy()
    libres = sorted(set(range(nb_positions)) - set(solution))

    if libres and (len(solution) == 1 or rng.random() < 0.5):
        i = rng.randrange(len(solution))
        voisin[i] = rng.choice(libres)
    elif len(solution) >= 2:
        i, j = rng.sample(range(len(solution)), 2)
        voisin[i], voisin[j] = voisin[j], voisin[i]

    return voisin


def recuit_simule(evaluer, nb_qubits, nb_positions, duree_secondes=300,
                  temperature_initiale=20.0, temperature_finale=0.1,
                  graine=42, afficher=True):
    """Recherche limitée en temps réel écoulé, initialisation comprise.

    Une évaluation commencée peut dépasser l'échéance ; aucun nouvel appel
    n'est lancé ensuite. Le meilleur placement évalué est toujours renvoyé.
    """
    if not 1 <= nb_qubits <= nb_positions:
        raise ValueError("Il faut 1 <= nb_qubits <= nb_positions.")
    if not math.isfinite(duree_secondes) or duree_secondes <= 0:
        raise ValueError("La durée doit être positive et finie.")
    if not (math.isfinite(temperature_initiale) and math.isfinite(temperature_finale)
            and 0 < temperature_finale <= temperature_initiale):
        raise ValueError("Il faut 0 < température finale <= température initiale, finies.")
    debut = perf_counter()
    echeance = debut + duree_secondes
    rng = random.Random(graine)
    solution = rng.sample(range(nb_positions), nb_qubits)
    # Toujours évaluer un placement initial pour pouvoir renvoyer une solution.
    cout = evaluer(solution)
    evaluations = 1
    meilleure_solution, meilleur_cout = solution.copy(), cout
    if afficher:
        print(f"Budget : {duree_secondes:.1f} s | coût initial : {cout}")
    debut_phase = perf_counter()
    temperature_phase = temperature_initiale
    dernier_affichage = debut_phase
    derniere_amelioration = debut_phase
    relances = 0
    while True:
        maintenant = perf_counter()
        if maintenant >= echeance:
            break
        progression = min(1.0, max(0.0,
            (maintenant - debut_phase) / max(echeance - debut_phase, 1e-12)))
        temperature = temperature_phase * (
            temperature_finale / temperature_phase
        ) ** progression
        voisin = generer_voisin(solution, nb_positions, rng)
        if perf_counter() >= echeance:
            break
        cout_voisin = evaluer(voisin)
        evaluations += 1
        delta = cout_voisin - cout
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            solution, cout = voisin, cout_voisin
        if cout < meilleur_cout:
            meilleure_solution, meilleur_cout = solution.copy(), cout
            derniere_amelioration = perf_counter()
        maintenant = perf_counter()
        if afficher and maintenant - dernier_affichage >= 10:
            print(f"Temps {maintenant - debut:.1f}/{duree_secondes:.1f} s | "
                  f"évaluations = {evaluations} | T = {temperature:.3f} | "
                  f"meilleur coût = {meilleur_cout} | relances = {relances}")
            dernier_affichage = maintenant
    if afficher:
        print(f"Terminé : {perf_counter() - debut:.2f} s | "
              f"{evaluations} évaluations | meilleur coût = {meilleur_cout} | "
              f"relances = {relances}")
    return meilleure_solution, meilleur_cout


if __name__ == "__main__":
    debut = perf_counter()
    print(f"Instance {instance_num} : {n} qubits à placer sur {m} positions")
    placement, cout = recuit_simule(
        fitness, n, m,
        duree_secondes=DUREE_SECONDES,
        temperature_initiale=TEMPERATURE_INITIALE,
        temperature_finale=TEMPERATURE_FINALE,
        graine=GRAINE,
    )
    print(f"Meilleur placement : {placement}")
    print(f"Coût observé : {cout}")
    print(f"Temps : {perf_counter() - debut:.2f} s")

    # Format de la présentation : placement puis coût, sur une seule ligne.
    fichier = Path(__file__).resolve().parent / "resultats_v0" / (
        f"Groupe{NUMERO_GROUPE}_Challenge_{instance_num}.txt"
    )
    fichier.parent.mkdir(exist_ok=True)
    fichier.write_text(" ".join(map(str, placement + [cout])) + "\n",
                       encoding="utf-8")
    print(f"Résultat enregistré dans {fichier}")
   
