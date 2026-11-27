import math
import random
import sys
from time import perf_counter
from source import instance_selector, fitness_inner

# --- PARAMÈTRES DE L'ALGORITHME ---
POPULATION_SIZE = 20      # Nombre de solutions par génération
GENERATIONS = 100           # Nombre max de générations
MUTATION_RATE = 0.5        # Probabilité de mutation (50 %)
TOURNAMENT_SIZE = 3        # Taille du tournoi pour la sélection
PATIENCE = 200              # Arrêt si pas d'amélioration pendant N générations
SEED = 42
TEMPS_MAX_AG = 300.0       # Limite de temps par instance (secondes), None = pas de limite

# --- PARAMÈTRES DU RECUIT (affinage des enfants) ---
LOCAL_SEARCH_RATE = 0.2       # Proportion d'enfants affinés par recuit
LOCAL_SEARCH_SECONDS = 2.0    # Durée du recuit par enfant affiné
SA_NB_CALIBRATION = 30        # Évaluations pour calibrer T (une fois par instance)
SA_PROBA_INITIALE = 0.3       # Acceptation initiale visée
SA_TEMP_SECOURS = 5.0
SA_TEMP_FINALE = 0.1

randomGen = random.Random(SEED)


# ----------------------------------------------------------------------
#  Recuit simulé (version V4 : limité en temps)
# ----------------------------------------------------------------------
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
                  graine=42, afficher=True, stagnation_secondes=45.0,
                  nb_perturbations=3, facteur_rechauffage=0.25,
                  min_restant_relance_secondes=15.0, solution_initiale=None):
    """Recherche limitée en temps réel écoulé, initialisation comprise.

    Si solution_initiale est fournie, le recuit part de ce placement
    au lieu d'un placement aléatoire.
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
    if not math.isfinite(stagnation_secondes) or stagnation_secondes <= 0:
        raise ValueError("La durée de stagnation doit être positive et finie.")
    if not isinstance(nb_perturbations, int) or nb_perturbations < 1:
        raise ValueError("Le nombre de perturbations doit être un entier positif.")
    if not 0 < facteur_rechauffage <= 1:
        raise ValueError("Le facteur de réchauffage doit être dans ]0, 1].")
    if not math.isfinite(min_restant_relance_secondes) or min_restant_relance_secondes <= 0:
        raise ValueError("Le temps minimal restant doit être positif et fini.")

    debut = perf_counter()
    echeance = debut + duree_secondes
    rng = random.Random(graine)
    if solution_initiale is None:
        solution = rng.sample(range(nb_positions), nb_qubits)
    else:
        solution = list(solution_initiale)
    cout = evaluer(solution)
    evaluations = 1
    meilleure_solution, meilleur_cout = solution.copy(), cout
    if afficher:
        print(f"Budget : {duree_secondes:.1f} s | coût initial : {cout}")

    # --- Calibration de la température ---
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

    # --- Recuit avec relances ---
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
        relancer = (maintenant - derniere_amelioration >= stagnation_secondes
                    and echeance - maintenant >= min_restant_relance_secondes
                    and nb_positions > 1)
        if relancer:
            voisin = meilleure_solution.copy()
            for _ in range(nb_perturbations):
                voisin = generer_voisin(voisin, nb_positions, rng)
            if voisin == meilleure_solution:
                voisin = generer_voisin(voisin, nb_positions, rng)
            if perf_counter() >= echeance:
                break
            cout = evaluer(voisin)
            evaluations += 1
            solution = voisin
            relances += 1
            debut_phase = perf_counter()
            derniere_amelioration = debut_phase
            temperature_phase = max(temperature,
                                    temperature_initiale * facteur_rechauffage,
                                    temperature_finale)
            temperature = temperature_phase
            if afficher:
                print(f"Relance {relances} à {debut_phase - debut:.2f} s | "
                      f"évaluation {evaluations} | T = {temperature:.3f} | coût du saut = {cout}")
        else:
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


# ----------------------------------------------------------------------
#  Évaluation avec cache
# ----------------------------------------------------------------------
def evaluate_individual(mapping, circuit, backend, fitness_cache):
    """Évalue un individu avec le cache pour éviter de re-transpiler."""
    mapping_tuple = tuple(mapping)
    if mapping_tuple in fitness_cache:
        return fitness_cache[mapping_tuple]
    score = fitness_inner(mapping, circuit, backend, SEED)
    fitness_cache[mapping_tuple] = score
    return score


# ----------------------------------------------------------------------
#  Calibration unique de la température (par instance)
# ----------------------------------------------------------------------
def calibrer_instance(circuit, backend, n, m, fitness_cache):
    """Marche aléatoire courte pour estimer une température de départ."""
    evaluer = lambda mapping: evaluate_individual(mapping, circuit, backend, fitness_cache)
    solution = randomGen.sample(range(m), n)
    cout = evaluer(solution)
    hausses = []
    for _ in range(SA_NB_CALIBRATION):
        voisin = generer_voisin(solution, m, randomGen)
        cout_voisin = evaluer(voisin)
        if cout_voisin > cout:
            hausses.append(cout_voisin - cout)
        solution, cout = voisin, cout_voisin
    return calibrer_temperature(hausses, SA_PROBA_INITIALE, SA_TEMP_SECOURS)


# ----------------------------------------------------------------------
#  Affinage par recuit V4 (remplace l'ancienne local_search)
# ----------------------------------------------------------------------
def local_search(individual, circuit, backend, n, m, fitness_cache, temperature_depart):
    """Affine un individu par le recuit V4, limité à LOCAL_SEARCH_SECONDS."""
    evaluer = lambda mapping: evaluate_individual(mapping, circuit, backend, fitness_cache)
    meilleure, _ = recuit_simule(
        evaluer, n, m,
        duree_secondes=LOCAL_SEARCH_SECONDS,
        fraction_calibration=0.0,                 # pas de calibration interne
        probabilite_initiale=SA_PROBA_INITIALE,
        temperature_secours=temperature_depart,   # utilisée comme T initiale
        temperature_finale=min(SA_TEMP_FINALE, temperature_depart),
        graine=randomGen.randrange(2**32),
        afficher=False,
        stagnation_secondes=1e9,                  # pas de relance sur un si court recuit
        min_restant_relance_secondes=1e9,
        solution_initiale=individual,
    )
    return meilleure


# ----------------------------------------------------------------------
#  Opérateurs génétiques
# ----------------------------------------------------------------------
def generate_initial_population(pop_size, n, m):
    """Population de départ : listes de n qubits physiques uniques parmi m."""
    return [randomGen.sample(range(m), n) for _ in range(pop_size)]


def select_parent(population, scores):
    """Sélection par tournoi : on garde le meilleur des individus tirés."""
    k = min(TOURNAMENT_SIZE, len(population))
    contenders = randomGen.sample(list(zip(population, scores)), k)
    return min(contenders, key=lambda x: x[1])[0]


def crossover(parent1, parent2, n, m):
    """Croisement sans doublons."""
    if n < 3:
        return parent1.copy()
    cut = randomGen.randint(1, n - 2)
    child = parent1[:cut]

    for gene in parent2:
        if gene not in child:
            child.append(gene)
        if len(child) == n:
            break

    if len(child) < n:
        available = list(set(range(m)) - set(child))
        randomGen.shuffle(available)
        child.extend(available[:n - len(child)])

    return child


def mutate(individual, n, m):
    """Mutation : un voisin (swap ou remplacement par un qubit libre)."""
    if randomGen.random() < MUTATION_RATE:
        return generer_voisin(individual, m, randomGen)
    return individual


# ----------------------------------------------------------------------
#  Boucle principale
# ----------------------------------------------------------------------
def run_evolution(instance_number):
    randomGen.seed(SEED)          # reproductibilité par instance
    fitness_cache = {}
    t_debut = perf_counter()

    print(f"Chargement de l'instance...{instance_number}")
    backend, circuit, n, m = instance_selector(instance_number)
    print(f"Circuit à placer : {n} qubits logiques sur une machine de {m} qubits physiques.")

    temperature_depart = calibrer_instance(circuit, backend, n, m, fitness_cache)
    print(f"Température de départ du recuit : {temperature_depart:.3f}")

    population = generate_initial_population(POPULATION_SIZE, n, m)
    best_overall_mapping = None
    best_overall_score = float('inf')
    stagnation = 0

    for gen in range(GENERATIONS):
        scores = [evaluate_individual(ind, circuit, backend, fitness_cache) for ind in population]

        min_score = min(scores)
        best_in_gen = population[scores.index(min_score)]

        if min_score < best_overall_score:
            best_overall_score = min_score
            best_overall_mapping = best_in_gen.copy()
            stagnation = 0
        else:
            stagnation += 1

        print(f"Génération {gen} | Meilleur score (profondeur) : {min_score} "
              f"| {perf_counter() - t_debut:.0f} s")

        if stagnation >= PATIENCE:
            print(f"Arrêt anticipé : pas d'amélioration depuis {PATIENCE} générations.")
            break
        if TEMPS_MAX_AG is not None and perf_counter() - t_debut >= TEMPS_MAX_AG:
            print("Arrêt : limite de temps atteinte.")
            break

        new_population = [best_overall_mapping.copy()]   # élitisme

        while len(new_population) < POPULATION_SIZE:
            p1 = select_parent(population, scores)
            p2 = select_parent(population, scores)

            child = crossover(p1, p2, n, m)
            child = mutate(child, n, m)

            if randomGen.random() < LOCAL_SEARCH_RATE:
                child = local_search(child, circuit, backend, n, m,
                                     fitness_cache, temperature_depart)

            new_population.append(child)

        population = new_population

    # Évaluation finale de la dernière population
    scores = [evaluate_individual(ind, circuit, backend, fitness_cache) for ind in population]
    min_score = min(scores)
    if min_score < best_overall_score:
        best_overall_score = min_score
        best_overall_mapping = population[scores.index(min_score)].copy()

    print("\n--- OPTIMISATION TERMINÉE ---")
    print(f"Meilleur mapping trouvé : {best_overall_mapping}")
    print(f"Profondeur finale : {best_overall_score}")
    with open("outputs.txt", "a") as fout:
        fout.write(f"Instance : {instance_number} --- Meilleur mapping : "
                   f"{best_overall_mapping} --- Profondeur finale : {best_overall_score} \n")


# if __name__ == "__main__":
#     if len(sys.argv) < 2:
#         print("Usage : python script.py <numéro_instance>")
#         sys.exit(1)
#     run_evolution(int(sys.argv[1]))

if __name__ == "__main__":
    with open("outputs.txt", "a") as fout:
        fout.write(f"Seed = {SEED}\n")
    for i in list(range(1, 10)):
        run_evolution(i)