
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 14 11:08:40 2023

@author: Jérôme
"""

from source import instance_selector, fitness_inner
import random
from pathlib import Path
from typing import Callable, Dict, List, Tuple

##-------------------------------------------------------
## Definition de la fonction objectif à minimiser
##-------------------------------------------------------

def fitness(mapping):
    return fitness_inner(mapping, circuit, backend)


##-------------------------------------------------------
## Choix de l'instance : entre 1 et 9
##-------------------------------------------------------

instance_num = 1

backend, circuit, n, m = instance_selector(instance_num)


# -------------------------------------------------------
# ALGORITHME TABU SEARCH
# -------------------------------------------------------

def tabu_search(
    objective: Callable[[List[int]], float],
    n: int,
    m: int,
    max_iterations: int = 80,
    candidate_count: int = 24,
    tabu_tenure: int = 7,
    seed: int = 42,
) -> Tuple[List[int], float]:

    """Minimise objective over injective mappings
    from n logical to m physical qubits."""

    if n < 0 or m < 0 or n > m:
        raise ValueError("n and m must satisfy 0 <= n <= m")

    if max_iterations < 0 or candidate_count < 1 or tabu_tenure < 0:
        raise ValueError(
            "Search limits must be non-negative and "
            "candidate_count must be positive"
        )

    rng = random.Random(seed)

    current = rng.sample(range(m), n)
    current_score = objective(current)

    best = current.copy()
    best_score = current_score

    score_cache: Dict[Tuple[int, ...], float] = {
        tuple(current): current_score
    }

    tabu_moves: List[Tuple[str, int, int]] = []

    for _ in range(max_iterations):

        moves: List[Tuple[str, int, int]] = []

        used_physical = set(current)

        # Remplacement par un qubit physique libre
        moves.extend(
            ("replace", logical, physical)
            for logical in range(n)
            for physical in range(m)
            if physical not in used_physical
        )

        # Echange de deux qubits
        moves.extend(
            ("swap", first, second)
            for first in range(n)
            for second in range(first + 1, n)
        )

        if not moves:
            break

        candidates = rng.sample(
            moves,
            min(candidate_count, len(moves))
        )

        scored_moves: List[
            Tuple[List[int], float, Tuple[str, int, int], bool]
        ] = []

        for move_type, first, second in candidates:

            neighbor = current.copy()

            if move_type == "replace":

                old_physical = neighbor[first]
                neighbor[first] = second

                reverse_move = (
                    "replace",
                    first,
                    old_physical
                )

            else:

                neighbor[first], neighbor[second] = (
                    neighbor[second],
                    neighbor[first]
                )

                reverse_move = (
                    "swap",
                    first,
                    second
                )

            key = tuple(neighbor)

            if key not in score_cache:
                score_cache[key] = objective(neighbor)

            score = score_cache[key]

            candidate_move = (
                move_type,
                first,
                second
            )

            is_admissible = (
                candidate_move not in tabu_moves
                or score < best_score
            )

            scored_moves.append(
                (
                    neighbor,
                    score,
                    reverse_move,
                    is_admissible
                )
            )

        eligible_moves = [
            move for move in scored_moves if move[3]
        ]

        if not eligible_moves:
            eligible_moves = scored_moves

        current, current_score, reverse_move, _ = min(
            eligible_moves,
            key=lambda item: item[1]
        )

        if tabu_tenure:

            tabu_moves.append(reverse_move)

            if len(tabu_moves) > tabu_tenure:
                tabu_moves.pop(0)

        if current_score < best_score:

            best = current.copy()
            best_score = current_score

    return best, best_score


# -------------------------------------------------------
# EXECUTION
# -------------------------------------------------------

if __name__ == "__main__":

    best_mapping, best_fitness = tabu_search(
        fitness,
        n,
        m
    )

    output_file = (
        Path(__file__).resolve().parent
        / f"Groupeabdou_Instance_{instance_num}.txt"
    )

    output_file.write_text(
        f"{best_mapping}\n",
        encoding="utf-8"
    )

    print(f"Meilleure fitness : {best_fitness}")
    print(f"Mapping : {best_mapping}")
    print(
        f"Solution enregistrée dans {output_file.name}"
    )
