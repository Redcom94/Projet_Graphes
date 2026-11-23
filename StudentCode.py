import random
from source import instance_selector, fitness_inner
import sys
# --- PARAMÈTRES DE L'ALGORITHME ---
POPULATION_SIZE = 100     # Nombre de solutions par génération
GENERATIONS = 50           # Nombre de cycles d'évolution
MUTATION_RATE = 0.35       # Probabilité de mutation (20%)
TOURNAMENT_SIZE = 30        # Taille du tournoi pour la sélection
SEED = 42

randomGen = random.Random(SEED)

def evaluate_individual(mapping, circuit, backend, fitness_cache):
    """Évalue un individu avec le cache pour gagner énormément de temps."""
    # On transforme la liste en tuple car les clés de dictionnaire doivent être immuables
    mapping_tuple = tuple(mapping) 
    
    if mapping_tuple in fitness_cache:
        return fitness_cache[mapping_tuple]
    
    # Appel de la fonction de Jérôme Rouzé
    score = fitness_inner(mapping, circuit, backend, SEED) 
    fitness_cache[mapping_tuple] = score
    return score

def generate_initial_population(pop_size, n, m):
    """Crée la population de départ (des listes de n qubits physiques uniques pris parmi m)."""
    population = []
    for _ in range(pop_size):
        # randomGen.sample tire sans remise, garantissant qu'un qubit physique n'est utilisé qu'une fois
        individual = randomGen.sample(range(m), n)
        population.append(individual)
    return population

def select_parent(population, scores):
    """Sélection par tournoi : on prend quelques individus au hasard et on garde le meilleur."""
    contenders = randomGen.sample(list(zip(population, scores)), TOURNAMENT_SIZE)
    # On cherche le score minimum (la profondeur de circuit la plus faible)
    best_contender = min(contenders, key=lambda x: x[1])
    return best_contender[0]

def crossover(parent1, parent2, n, m):
    """Croisement : mélange les gènes de deux parents sans créer de doublons."""
    cut = randomGen.randint(1, n - 2)
    child = parent1[:cut] # Prend la première partie du parent 1
    
    # Complète avec les gènes du parent 2 qui ne sont pas encore dans l'enfant
    for gene in parent2:
        if gene not in child:
            child.append(gene)
        if len(child) == n:
            break
            
    # S'il manque des qubits (cas rare si les parents utilisaient des qubits physiques très différents)
    if len(child) < n:
        available = list(set(range(m)) - set(child))
        randomGen.shuffle(available)
        child.extend(available[:n - len(child)])
        
    return child

def mutate(individual, n, m):
    """Mutation : applique une petite modification aléatoire."""
    if randomGen.random() < MUTATION_RATE:
        if randomGen.random() < 0.5 or n == m:
            # Type de mutation 1 : On échange la place de deux qubits dans la liste
            idx1, idx2 = randomGen.sample(range(n), 2)
            individual[idx1], individual[idx2] = individual[idx2], individual[idx1]
        else:
            # Type de mutation 2 : On remplace un qubit par un qubit physique inutilisé
            idx_to_replace = randomGen.randrange(n)
            unused_qubits = list(set(range(m)) - set(individual))
            individual[idx_to_replace] = randomGen.choice(unused_qubits)
            
    return individual

def run_evolution(instance_number):
    # Dictionnaire pour mémoriser les scores et éviter de re-calculer les mêmes mappings
    fitness_cache = {}
    # 1. Charger l'instance via le code fourni
    print(f"Chargement de l'instance...{instance_number}")
    # Choisissons l'instance 1 par exemple
    backend, circuit, n, m = instance_selector(instance_number)
    print(f"Circuit à placer : {n} qubits logiques sur une machine de {m} qubits physiques.")
    
    # 2. Initialisation
    population = generate_initial_population(POPULATION_SIZE, n, m)
    best_overall_mapping = None
    best_overall_score = float('inf')

    # 3. Boucle principale
    for gen in range(GENERATIONS):
        # Évaluation
        scores = [evaluate_individual(ind, circuit, backend, fitness_cache) for ind in population]
        
        # Suivi du meilleur
        min_score = min(scores)
        best_in_gen = population[scores.index(min_score)]
        
        if min_score < best_overall_score:
            best_overall_score = min_score
            best_overall_mapping = best_in_gen.copy()
            
        print(f"Génération {gen} | Meilleur score (profondeur) : {min_score}")
        
        # Création de la nouvelle génération
        new_population = []
        
        # ÉLITISME : on garde toujours le meilleur individu tel quel
        new_population.append(best_overall_mapping.copy())
        
        while len(new_population) < POPULATION_SIZE:
            # Sélection
            p1 = select_parent(population, scores)
            p2 = select_parent(population, scores)
            
            # Croisement
            child = crossover(p1, p2, n, m)
            
            # Mutation
            child = mutate(child, n, m)
            
            new_population.append(child)
            
        population = new_population

    print("\n--- OPTIMISATION TERMINÉE ---")
    print(f"Meilleur mapping trouvé : {best_overall_mapping}")
    print(f"Profondeur finale : {best_overall_score}")
    with open("outputs.txt","a") as fout:
        fout.write(f"Instance : {instance_number} --- Meilleur mapping : {best_overall_mapping} --- Profondeur finale : {best_overall_score} \n")

# Pour lancer le script
#if __name__ == "__main__":
#    instance_number = int(sys.argv[1])
#    run_evolution(instance_number)

# Lancer toutes les instances:
if __name__ == "__main__":
    with open("outputs.txt","a") as fout:
        fout.write(f"Seed = {SEED}\n")
    for i in range(1,10):
        run_evolution(i)
