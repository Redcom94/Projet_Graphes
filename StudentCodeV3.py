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
instance_num=6    #### Entre 1 et 9 inclus

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
FRACTION_CALIBRATION = 0.05  # 15 s sur un budget de 300 s
PROBABILITE_INITIALE = 0.8
TEMPERATURE_SECOURS = 20.0
TEMPERATURE_FINALE = 0.1
GRAINE = 42  # Fixe les mouvements, mais pas l'aléatoire interne de Qiskit.


def generer_voisin(solution, nb_positions, rng):
    """Tire uniformément un voisin parmi les échanges et remplacements.

    Chaque mouvement possède un numéro unique, choisi avec randrange.
    """
    voisin = solution.copy()
    n = len(solution)
    libres = sorted(set(range(nb_positions)) - set(solution))
    nb_echanges = n * (n - 1) // 2
    nb_remplacements = n * len(libres)
    total = nb_echanges + nb_remplacements
    if total == 0:
        return voisin

    mouvement = rng.randrange(total)
    if mouvement < nb_echanges:
        # Paires (0,1), (0,2), ..., (1,2), ... : chacune une seule fois.
        i = 0
        while mouvement >= n - i - 1:
            mouvement -= n - i - 1
            i += 1
        j = i + 1 + mouvement
        voisin[i], voisin[j] = voisin[j], voisin[i]
    else:
        # Chaque paire (qubit logique, position libre) a un numéro unique.
        i, indice_libre = divmod(mouvement - nb_echanges, len(libres))
        voisin[i] = libres[indice_libre]
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


def recuit_simule(evaluer, nb_qubits, nb_positions, duree_secondes=300,
                  fraction_calibration=0.05, probabilite_initiale=0.8,
                  temperature_secours=20.0, temperature_finale=0.1,
                  graine=42, afficher=True):
    """Recherche limitée en temps réel écoulé, initialisation comprise.

    Une évaluation commencée peut dépasser l'échéance ; aucun nouvel appel
    n'est lancé ensuite. Le meilleur placement évalué est toujours renvoyé.
    """
    if not 1 <= nb_qubits <= nb_positions:
        raise ValueError("Il faut 1 <= nb_qubits <= nb_positions.")
    if not math.isfinite(duree_secondes) or duree_secondes <= 0:
        raise ValueError("La durée doit être positive et finie.")
    if not 0 <= fraction_calibration < 1:
        raise ValueError("La fraction de calibration doit être dans [0, 1[.")
    if not math.isfinite(temperature_finale) or temperature_finale <= 0:
        raise ValueError("La température finale doit être positive et finie.")
    calibrer_temperature([], probabilite_initiale, temperature_secours)
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
    hausses = []
    evaluations_calibration = 0
    fin_calibration = debut + duree_secondes * fraction_calibration
    while perf_counter() < fin_calibration:
        voisin = generer_voisin(solution, nb_positions, rng)
        if perf_counter() >= fin_calibration:
            break
        cout_voisin = evaluer(voisin)
        evaluations += 1
        evaluations_calibration += 1
        if cout_voisin > cout:
            hausses.append(cout_voisin - cout)
        solution, cout = voisin, cout_voisin
        if cout < meilleur_cout:
            meilleure_solution, meilleur_cout = solution.copy(), cout
    temperature_initiale = max(
        temperature_finale,
        calibrer_temperature(hausses, probabilite_initiale, temperature_secours),
    )
    if afficher:
        print(f"Calibration : {evaluations_calibration} évaluations, "
              f"{len(hausses)} hausses | temps écoulé : {perf_counter() - debut:.2f} s")
        print(f"Température initiale : {temperature_initiale:.3f}")
        if not hausses:
            print("Aucune hausse observée : température de secours utilisée.")
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
    print(f"V3 - Instance {instance_num} : {n} qubits à placer sur {m} positions")
    placement, cout = recuit_simule(
        fitness, n, m,
        duree_secondes=DUREE_SECONDES,
        fraction_calibration=FRACTION_CALIBRATION,
        probabilite_initiale=PROBABILITE_INITIALE,
        temperature_secours=TEMPERATURE_SECOURS,
        temperature_finale=TEMPERATURE_FINALE,
        graine=GRAINE,
    )
    print(f"Meilleur placement : {placement}")
    print(f"Coût observé : {cout}")
    print(f"Temps : {perf_counter() - debut:.2f} s")

    # Format de la présentation : placement puis coût, sur une seule ligne.
    fichier = Path(__file__).resolve().parent / "resultats_v3" / (
        f"Groupe{NUMERO_GROUPE}_Challenge_{instance_num}.txt"
    )
    fichier.parent.mkdir(exist_ok=True)
    fichier.write_text(" ".join(map(str, placement + [cout])) + "\n",
                       encoding="utf-8")
    print(f"Résultat enregistré dans {fichier}")
   
