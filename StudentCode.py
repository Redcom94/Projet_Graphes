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
instance_num=1     #### Entre 1 et 9 inclue

backend,circuit,n,m = instance_selector(instance_num)

##-------------------------------------------------------
##     A vous de jouer !  
##-------------------------------------------------------

import random
import time

numero_du_groupe = 1  # <-- Mettre votre numéro de groupe ici
time_limit = 30.0     # <-- Temps max d'exécution en secondes


def is_feasible(mapping, n, m):
    return (
        len(mapping) == n
        and len(set(mapping)) == n
        and all(0 <= q < m for q in mapping)
    )


def evaluate(mapping, cache):
    key = tuple(mapping)
    if key not in cache:
        cache[key] = fitness(mapping)
    return cache[key]


def swap_move(mapping):
    """Échange deux qubits logiques dans le mapping."""
    res = mapping.copy()
    i, j = random.sample(range(len(res)), 2)
    res[i], res[j] = res[j], res[i]
    return res


def replace_move(mapping, m):
    """Remplace un qubit physique utilisé par un qubit libre (si n < m)."""
    used = set(mapping)
    free = [q for q in range(m) if q not in used]
    if not free:
        return swap_move(mapping)
    res = mapping.copy()
    idx = random.randrange(len(res))
    res[idx] = random.choice(free)
    return res


def init_solution(n, m, cache, nb_starts=5):
    """Génère une bonne solution initiale parmi quelques candidats."""
    candidates = [list(range(n))]
    for _ in range(nb_starts - 1):
        candidates.append(random.sample(range(m), n))

    best_map = candidates[0]
    best_cost = evaluate(best_map, cache)
    for cand in candidates[1:]:
        cost = evaluate(cand, cache)
        if cost < best_cost:
            best_map, best_cost = cand, cost
    return best_map, best_cost


def local_search(mapping, best_cost, m, cache, start_time, time_limit, max_evals=25):
    """Recherche locale (first-improvement) par échanges et remplacements."""
    current = mapping.copy()
    current_cost = best_cost
    n_qubits = len(current)

    improved = True
    while improved and (time.time() - start_time) < time_limit:
        improved = False
        used = set(current)
        free = [q for q in range(m) if q not in used]

        # Liste de voisins possibles (swaps + remplacements par qubits libres)
        neighbors = []
        for i in range(n_qubits):
            for j in range(i + 1, n_qubits):
                neighbors.append(("swap", i, j))
        for i in range(n_qubits):
            for q in free:
                neighbors.append(("replace", i, q))

        random.shuffle(neighbors)

        for move in neighbors[:max_evals]:
            if (time.time() - start_time) >= time_limit:
                break

            cand = current.copy()
            if move[0] == "swap":
                _, i, j = move
                cand[i], cand[j] = cand[j], cand[i]
            else:
                _, i, q = move
                cand[i] = q

            cost = evaluate(cand, cache)
            if cost < current_cost:
                current = cand
                current_cost = cost
                improved = True
                break

    return current, current_cost


def shaking(mapping, k, m):
    """Perturbation dans le voisinage N_k."""
    res = mapping.copy()
    n_qubits = len(res)

    if k == 1:
        nb_ops = 1
    elif k == 2:
        nb_ops = 2
    elif k == 3:
        nb_ops = max(3, n_qubits // 4)
    else:
        # Perturbation forte : mélange d'une partie du mapping
        nb_ops = max(4, n_qubits // 2)

    for _ in range(nb_ops):
        if m > n_qubits and random.random() < 0.4:
            res = replace_move(res, m)
        else:
            res = swap_move(res)

    return res


def vns(n, m, time_limit=30.0):
    """Recherche à voisinage variable (VNS)."""
    start_time = time.time()
    cache = {}
    k_max = 4

    best_mapping, best_cost = init_solution(n, m, cache)
    best_mapping, best_cost = local_search(
        best_mapping, best_cost, m, cache, start_time, time_limit
    )

    while (time.time() - start_time) < time_limit:
        k = 1
        while k <= k_max and (time.time() - start_time) < time_limit:
            shaken = shaking(best_mapping, k, m)
            shaken_cost = evaluate(shaken, cache)
            loc_mapping, loc_cost = local_search(
                shaken, shaken_cost, m, cache, start_time, time_limit
            )

            if loc_cost < best_cost:
                best_mapping, best_cost = loc_mapping, loc_cost
                k = 1
            else:
                k += 1

    return best_mapping, best_cost


best_mapping, best_cost = vns(n, m, time_limit=time_limit)

assert is_feasible(best_mapping, n, m), "Mapping invalide !"
print(f"Instance {instance_num} | n={n}, m={m} | Meilleure profondeur = {best_cost}")
print(f"Mapping : {best_mapping}")

# Pour les instances 1-9 : GroupeX_Instance_Y.txt | Pour le challenge : GroupeX_Challenge_Y.txt
output_filename = f"Groupe{numero_du_groupe}_Instance_{instance_num}.txt"
with open(output_filename, "w", encoding="utf-8") as f:
    f.write(" ".join(str(q) for q in best_mapping) + f" {best_cost}\n")
print(f"Solution enregistrée dans {output_filename}")
