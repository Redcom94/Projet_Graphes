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
instance_num=9    #### Entre 1 et 9 inclus

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
NB_CALIBRATION = 50
PROBABILITE_INITIALE = 0.8
TEMPERATURE_SECOURS = 20.0
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


def calibrer_temperature(hausses, probabilite=0.8, secours=20.0):
    """Vise une acceptation moyenne des hausses observées égale à probabilite."""
    if not 0 < probabilite < 1:
        raise ValueError("La probabilité doit être strictement entre 0 et 1.")
    if not math.isfinite(secours) or secours <= 0:
        raise ValueError("La température de secours doit être positive et finie.")
    if any(not math.isfinite(d) or d <= 0 for d in hausses):
        raise ValueError("Les hausses doivent être positives et finies.")
    if not hausses:
        return secours

    # Cette borne garantit que chaque hausse a une probabilité >= à la cible.
    bas = 0.0
    haut = -max(hausses) / math.log(probabilite)
    for _ in range(80):
        milieu = (bas + haut) / 2
        acceptation = sum(math.exp(-d / milieu) for d in hausses) / len(hausses)
        if acceptation < probabilite:
            bas = milieu
        else:
            haut = milieu
    return (bas + haut) / 2


def recuit_simule(evaluer, nb_qubits, nb_positions, nb_iterations=1000,
                  nb_calibration=50, probabilite_initiale=0.8,
                  temperature_secours=20.0, temperature_finale=0.1,
                  graine=42, afficher=True):
    """Budget total : 1 + nb_iterations appels, calibration comprise.

    La calibration suit une marche aléatoire et conserve ses meilleurs résultats.
    Elle mesure les hausses de coût entre deux placements voisins successifs.
    """
    if not 1 <= nb_qubits <= nb_positions:
        raise ValueError("Il faut 1 <= nb_qubits <= nb_positions.")
    if not isinstance(nb_iterations, int) or nb_iterations < 1:
        raise ValueError("Le nombre d'itérations doit être un entier positif.")
    if not isinstance(nb_calibration, int) or not 0 <= nb_calibration < nb_iterations:
        raise ValueError("Il faut 0 <= calibration < nombre d'itérations.")
    if not math.isfinite(temperature_finale) or temperature_finale <= 0:
        raise ValueError("La température finale doit être positive et finie.")
    calibrer_temperature([], probabilite_initiale, temperature_secours)

    rng = random.Random(graine)
    solution = rng.sample(range(nb_positions), nb_qubits)
    cout = evaluer(solution)
    meilleure_solution, meilleur_cout = solution.copy(), cout
    if afficher:
        print(f"Coût initial : {cout}")

    hausses = []
    for _ in range(nb_calibration):
        voisin = generer_voisin(solution, nb_positions, rng)
        cout_voisin = evaluer(voisin)
        if cout_voisin > cout:
            hausses.append(cout_voisin - cout)
        # Pendant la calibration, chaque mouvement est effectué.
        solution, cout = voisin, cout_voisin
        if cout < meilleur_cout:
            meilleure_solution, meilleur_cout = solution.copy(), cout

    temperature_initiale = max(
        temperature_finale,
        calibrer_temperature(hausses, probabilite_initiale, temperature_secours),
    )
    if afficher:
        print(f"Calibration : {nb_calibration} évaluations, {len(hausses)} hausses")
        print(f"Température initiale : {temperature_initiale:.3f}")
        if not hausses:
            print("Aucune hausse observée : température de secours utilisée.")

    nb_recherche = nb_iterations - nb_calibration
    for iteration in range(nb_recherche):
        progression = iteration / max(1, nb_recherche - 1)
        temperature = temperature_initiale * (
            temperature_finale / temperature_initiale
        ) ** progression
        voisin = generer_voisin(solution, nb_positions, rng)
        cout_voisin = evaluer(voisin)
        delta = cout_voisin - cout
        if delta <= 0 or rng.random() < math.exp(-delta / temperature):
            solution, cout = voisin, cout_voisin
        if cout < meilleur_cout:
            meilleure_solution, meilleur_cout = solution.copy(), cout
        if afficher and ((iteration + 1) % 100 == 0
                         or iteration + 1 == nb_recherche):
            print(f"Recherche {iteration + 1}/{nb_recherche} | "
                  f"T = {temperature:.3f} | coût courant = {cout} | "
                  f"meilleur coût = {meilleur_cout}")
    return meilleure_solution, meilleur_cout


if __name__ == "__main__":
    debut = perf_counter()
    print(f"Instance {instance_num} : {n} qubits à placer sur {m} positions")
    placement, cout = recuit_simule(
        fitness, n, m,
        nb_iterations=NB_ITERATIONS,
        nb_calibration=NB_CALIBRATION,
        probabilite_initiale=PROBABILITE_INITIALE,
        temperature_secours=TEMPERATURE_SECOURS,
        temperature_finale=TEMPERATURE_FINALE,
        graine=GRAINE,
    )
    print(f"Meilleur placement : {placement}")
    print(f"Coût observé : {cout}")
    print(f"Temps : {perf_counter() - debut:.2f} s")

    # Format de la présentation : placement puis coût, sur une seule ligne.
    fichier = Path(__file__).resolve().parent / "resultats_v2" / (
        f"Groupe{NUMERO_GROUPE}_Challenge_{instance_num}.txt"
    )
    fichier.parent.mkdir(exist_ok=True)
    fichier.write_text(" ".join(map(str, placement + [cout])) + "\n",
                       encoding="utf-8")
    print(f"Résultat enregistré dans {fichier}")
   
