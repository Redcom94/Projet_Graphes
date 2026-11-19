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
instance_num=2     #### Entre 1 et 9 inclue

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
NB_ITERATIONS = 1000
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


def recuit_simule(evaluer, nb_qubits, nb_positions, nb_iterations=500,
                  temperature_initiale=20.0, temperature_finale=0.1,
                  graine=42, afficher=True):
    """Renvoie le meilleur placement rencontré et son coût observé.

    Budget : une évaluation initiale, puis une par itération.
    La température suit une décroissance géométrique.
    """
    if not 1 <= nb_qubits <= nb_positions:
        raise ValueError("Il faut 1 <= nb_qubits <= nb_positions.")
    if nb_iterations < 1:
        raise ValueError("Il faut au moins une itération.")
    if not 0 < temperature_finale <= temperature_initiale:
        raise ValueError("Il faut 0 < température finale <= température initiale.")

    rng = random.Random(graine)
    solution = rng.sample(range(nb_positions), nb_qubits)
    cout = evaluer(solution)
    meilleure_solution = solution.copy()
    meilleur_cout = cout

    if afficher:
        print(f"Coût initial : {cout}")

    for iteration in range(nb_iterations):
        progression = iteration / max(1, nb_iterations - 1)
        temperature = temperature_initiale * (
            temperature_finale / temperature_initiale
        ) ** progression

        voisin = generer_voisin(solution, nb_positions, rng)
        cout_voisin = evaluer(voisin)
        delta = cout_voisin - cout

        # Une hausse du coût peut être acceptée pour sortir d'un optimum local.
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            solution = voisin
            cout = cout_voisin

        # On conserve le meilleur résultat, indépendamment du placement courant.
        if cout < meilleur_cout:
            meilleure_solution = solution.copy()
            meilleur_cout = cout

        if afficher and ((iteration + 1) % 100 == 0
                         or iteration + 1 == nb_iterations):
            print(f"Itération {iteration + 1}/{nb_iterations} | "
                  f"T = {temperature:.3f} | coût courant = {cout} | "
                  f"meilleur coût = {meilleur_cout}")

    return meilleure_solution, meilleur_cout


if __name__ == "__main__":
    debut = perf_counter()
    print(f"Instance {instance_num} : {n} qubits à placer sur {m} positions")
    placement, cout = recuit_simule(
        fitness, n, m,
        nb_iterations=NB_ITERATIONS,
        temperature_initiale=TEMPERATURE_INITIALE,
        temperature_finale=TEMPERATURE_FINALE,
        graine=GRAINE,
    )
    print(f"Meilleur placement : {placement}")
    print(f"Coût observé : {cout}")
    print(f"Temps : {perf_counter() - debut:.2f} s")

    # Format de la présentation : placement puis coût, sur une seule ligne.
    fichier = Path(__file__).resolve().parent / (
        f"Groupe{NUMERO_GROUPE}_Challenge_{instance_num}.txt"
    )
    fichier.write_text(" ".join(map(str, placement + [cout])) + "\n",
                       encoding="utf-8")
    print(f"Résultat enregistré dans {fichier.name}")
   
