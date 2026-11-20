import random
from source import instance_selector, fitness_inner
import sys
# --- PARAMÈTRES DE L'ALGORITHME ---
POPULATION_SIZE = 100       # Nombre de solutions par génération
GENERATIONS = 50           # Nombre de cycles d'évolution
MUTATION_RATE = 0.2        # Probabilité de mutation (20%)
TOURNAMENT_SIZE = 3        # Taille du tournoi pour la sélection

# Dictionnaire pour mémoriser les scores et éviter de re-calculer les mêmes mappings
fitness_cache = {}

def evaluate_individual(mapping, circuit, backend):
    """Évalue un individu avec le cache pour gagner énormément de temps."""
    # On transforme la liste en tuple car les clés de dictionnaire doivent être immuables
    mapping_tuple = tuple(mapping) 
    
    if mapping_tuple in fitness_cache:
        return fitness_cache[mapping_tuple]
    
    # Appel de la fonction de Jérôme Rouzé
    score = fitness_inner(mapping, circuit, backend) 
    fitness_cache[mapping_tuple] = score
    return score

def generate_initial_population(pop_size, n, m):
    """Crée la population de départ (des listes de n qubits physiques uniques pris parmi m)."""
    population = []
    for _ in range(pop_size):
        # random.sample tire sans remise, garantissant qu'un qubit physique n'est utilisé qu'une fois
        individual = random.sample(range(m), n)
        population.append(individual)
    return population

def select_parent(population, scores):
    """Sélection par tournoi : on prend quelques individus au hasard et on garde le meilleur."""
    contenders = random.sample(list(zip(population, scores)), TOURNAMENT_SIZE)
    # On cherche le score minimum (la profondeur de circuit la plus faible)
    best_contender = min(contenders, key=lambda x: x[1])
    return best_contender[0]

def crossover(parent1, parent2, n, m):
    """Croisement : mélange les gènes de deux parents sans créer de doublons."""
    cut = random.randint(1, n - 2)
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
        random.shuffle(available)
        child.extend(available[:n - len(child)])
        
    return child

def mutate(individual, n, m):
    """Mutation : applique une petite modification aléatoire."""
    if random.random() < MUTATION_RATE:
        if random.random() < 0.5 or n == m:
            # Type de mutation 1 : On échange la place de deux qubits dans la liste
            idx1, idx2 = random.sample(range(n), 2)
            individual[idx1], individual[idx2] = individual[idx2], individual[idx1]
        else:
            # Type de mutation 2 : On remplace un qubit par un qubit physique inutilisé
            idx_to_replace = random.randrange(n)
            unused_qubits = list(set(range(m)) - set(individual))
            individual[idx_to_replace] = random.choice(unused_qubits)
            
    return individual

def run_evolution(instance_number):
    # 1. Charger l'instance via le code fourni
    print("Chargement de l'instance...")
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
        scores = [evaluate_individual(ind, circuit, backend) for ind in population]
        
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

# Pour lancer le script
if __name__ == "__main__":
    instance_number = int(sys.argv[2])
    run_evolution(instance_number)