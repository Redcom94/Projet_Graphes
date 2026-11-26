# -*- coding: utf-8 -*-
"""V5 : construction structurelle, recherche tabou et solutions élites.

La fonction du professeur reste la seule mesure de qualité réelle.
"""
import math
import random
from collections import Counter, deque
from pathlib import Path
from statistics import median
from time import perf_counter

from source import instance_selector, fitness_inner

instance_num = 9     # Entre 1 et 9 ; aucun comportement ne dépend de ce numéro.
NUMERO_GROUPE = "X"
DUREE_SECONDES = 300
GRAINE = 42
TAILLE_ELITE = 6
FRACTION_VALIDATION = 0.10
ACTIVER_RELIAGE = True


def analyser_structure(circuit, backend):
    """Lecture seule des interactions, de leur ordre et du graphe physique."""
    n, m = circuit.num_qubits, backend.num_qubits
    physique = [set() for _ in range(m)]
    for a, b in backend.coupling_map.get_edges():
        physique[a].add(b)
        physique[b].add(a)
    distances = []
    for racine in range(m):
        d = [m + 1] * m
        d[racine] = 0
        file = deque([racine])
        while file:
            a = file.popleft()
            for b in physique[a]:
                if d[b] > d[a] + 1:
                    d[b] = d[a] + 1
                    file.append(b)
        distances.append(d)
    portes = [tuple(circuit.find_bit(q).index for q in op.qubits)
              for op in circuit.data if len(op.qubits) == 2]
    logique = [set() for _ in range(n)]
    frequences, precoces = Counter(), Counter()
    for k, (a, b) in enumerate(portes):
        logique[a].add(b)
        logique[b].add(a)
        paire = tuple(sorted((a, b)))
        frequences[paire] += 1
        precoces[paire] += math.exp(-4 * k / max(1, len(portes)))
    composants = []
    restant = set(range(n))
    while restant:
        depart = min(restant)
        composant, pile = set(), [depart]
        while pile:
            a = pile.pop()
            if a not in composant:
                composant.add(a)
                pile.extend(logique[a] - composant)
        restant -= composant
        composants.append(composant)
    return dict(n=n, m=m, physique=physique, distances=distances,
                logique=logique, composants=composants,
                poids=[frequences, precoces])


def ordre_chaine(composant, logique):
    """Renvoie un ordre pour une chaîne ou un cycle simple, sinon None."""
    if len(composant) == 1:
        return [next(iter(composant))], False
    if any(not 1 <= len(logique[q]) <= 2 for q in composant):
        return None
    extremites = sorted(q for q in composant if len(logique[q]) == 1)
    if len(extremites) not in (0, 2):
        return None
    ordre = [extremites[0] if extremites else min(composant)]
    visites = set(ordre)
    while len(ordre) < len(composant):
        suivants = sorted(logique[ordre[-1]] - visites)
        if not suivants:
            return None
        ordre.append(suivants[0])
        visites.add(suivants[0])
    return ordre, not extremites


def chemin_physique(structure, libres, longueur, cycle, rng, echeance):
    """Recherche bornée en temps ; un chemin partiel reste utilisable."""
    adj = structure['physique']
    meilleur = []

    def explorer(chemin, utilises):
        nonlocal meilleur
        if len(chemin) > len(meilleur):
            meilleur = chemin.copy()
        if len(chemin) == longueur:
            return not cycle or chemin[0] in adj[chemin[-1]]
        if perf_counter() >= echeance:
            return False
        choix = sorted((adj[chemin[-1]] & libres) - utilises)
        rng.shuffle(choix)
        choix.sort(key=lambda p: len((adj[p] & libres) - utilises))
        for p in choix:
            if explorer(chemin + [p], utilises | {p}):
                meilleur = chemin + [p] if len(chemin) + 1 == longueur else meilleur
                return True
            if perf_counter() >= echeance:
                break
        return False

    racines = sorted(libres)
    rng.shuffle(racines)
    for racine in racines:
        if perf_counter() >= echeance:
            break
        if explorer([racine], {racine}):
            break
    return meilleur


def score_rapide(placement, structure, variante=0):
    d = structure['distances']
    return sum(w * d[placement[a]][placement[b]]
               for (a, b), w in structure['poids'][variante].items())


def construire(structure, rng, echeance, variante=0, structurel=True):
    n, m = structure['n'], structure['m']
    placement = [-1] * n
    libres = set(range(m))
    if structurel:
        composants = sorted(structure['composants'], key=len, reverse=True)
        for composant in composants:
            ordre = ordre_chaine(composant, structure['logique'])
            if ordre is None or len(composant) < 2:
                continue
            qubits, cycle = ordre
            chemin = chemin_physique(structure, libres, len(qubits), cycle, rng,
                                     min(echeance, perf_counter() + 0.08))
            for q, p in zip(qubits, chemin):
                placement[q] = p
                libres.remove(p)
    poids = structure['poids'][variante]
    degres = Counter()
    for (a, b), w in poids.items():
        degres[a] += w
        degres[b] += w
    ordre = sorted((q for q in range(n) if placement[q] < 0),
                   key=lambda q: degres[q] * rng.uniform(.8, 1.2), reverse=True)
    d = structure['distances']
    for q in ordre:
        if perf_counter() >= echeance:
            # Compléter reste indispensable pour rendre un placement valide.
            reste = sorted(libres)
            rng.shuffle(reste)
            for a, p in zip((a for a in range(n) if placement[a] < 0), reste):
                placement[a] = p
            break
        def cout(p):
            return sum(poids.get(tuple(sorted((q, a))), 0) * d[p][placement[a]]
                       for a in range(n) if placement[a] >= 0)
        candidats = sorted(libres, key=lambda p: (cout(p), sum(d[p]), rng.random()))
        p = rng.choice(candidats[:min(3, len(candidats))])
        placement[q] = p
        libres.remove(p)
    return tuple(placement)


def voisins(placement, m):
    n = len(placement)
    for i in range(n):
        for j in range(i + 1, n):
            v = list(placement)
            v[i], v[j] = v[j], v[i]
            yield tuple(v)
    libres = sorted(set(range(m)) - set(placement))
    for i in range(n):
        for p in libres:
            v = list(placement)
            v[i] = p
            yield tuple(v)


def pas_vers(source, cible, rng):
    """Un pas de reliage : corrige une affectation sans créer de doublon."""
    positions = [i for i in range(len(source)) if source[i] != cible[i]]
    if not positions:
        return source
    i = rng.choice(positions)
    v = list(source)
    if cible[i] in v:
        j = v.index(cible[i])
        v[i], v[j] = v[j], v[i]
    else:
        v[i] = cible[i]
    return tuple(v)


def optimiser(evaluer, circuit, backend, duree_secondes=300, graine=42,
              taille_elite=6, fraction_validation=.10, activer_reliage=True,
              afficher=True):
    """Renvoie placement, meilleur coût observé et bilan détaillé.

    La préparation est incluse dans le temps. Un appel déjà commencé termine.
    Une évaluation initiale est toujours faite, même avec un budget très court.
    """
    if not math.isfinite(duree_secondes) or duree_secondes <= 0:
        raise ValueError('La durée doit être positive et finie.')
    if not isinstance(taille_elite, int) or taille_elite < 2:
        raise ValueError('Il faut au moins deux places dans les élites.')
    if not 0 < fraction_validation < .5:
        raise ValueError('La fraction de validation doit être dans ]0, 0,5[.')
    debut = perf_counter()
    fin = debut + duree_secondes
    fin_recherche = debut + duree_secondes * (1 - fraction_validation)
    rng = random.Random(graine)
    n, m = circuit.num_qubits, backend.num_qubits
    if not 1 <= n <= m:
        raise ValueError('Il faut 1 <= n <= m.')
    observations = {}
    appels = 0
    evaluations_par_phase = Counter()
    archive = []

    def score(p):
        return min(observations[p])

    def mettre_a_jour(p):
        nonlocal archive
        candidats = sorted(set(archive + [p]), key=lambda x: (score(x), x))
        selection = []
        for c in candidats:
            if all(sum(a != b for a, b in zip(c, autre)) >= max(1, n // 5)
                   for autre in selection):
                selection.append(c)
            if len(selection) == taille_elite:
                break
        archive = selection

    def mesurer(p, limite, phase, forcer=False):
        nonlocal appels
        if not forcer and perf_counter() >= limite:
            return False
        if len(p) != n or len(set(p)) != n or any(not 0 <= x < m for x in p):
            raise ValueError('Placement invalide.')
        valeur = evaluer(list(p))
        if not math.isfinite(valeur):
            raise ValueError('Coût non fini.')
        observations.setdefault(p, []).append(valeur)
        appels += 1
        evaluations_par_phase[phase] += 1
        mettre_a_jour(p)
        return True

    # Solution de secours avant tout prétraitement.
    courant = tuple(rng.sample(range(m), n))
    mesurer(courant, fin, 'initialisation', forcer=True)
    structure = analyser_structure(circuit, backend) if perf_counter() < fin_recherche else None
    if afficher:
        print(f'Budget : {duree_secondes:.1f} s | coût initial : {score(courant)}', flush=True)
    fin_construction = min(fin_recherche, debut + .12 * duree_secondes)
    for k in range(16):
        if structure is None or perf_counter() >= fin_construction:
            break
        p = (tuple(rng.sample(range(m), n)) if k % 5 == 4 else
             construire(structure, rng, fin_construction, k % 2, k % 4 < 2))
        if p not in observations:
            mesurer(p, fin_construction, 'construction')
    if archive:
        courant = archive[0]
    tabou = {}
    tour = 0
    sans_progres = 0
    prochain_affichage = perf_counter() + 10
    reliages = 0
    while structure is not None and perf_counter() < fin_recherche:
        tour += 1
        precedent = score(archive[0])
        # Recombinaison courte : au plus quatre pas, pas une génération entière.
        if activer_reliage and tour % 15 == 0 and len(archive) > 1:
            a, b = rng.sample(archive, 2)
            for _ in range(min(4, n)):
                if perf_counter() >= fin_recherche or a == b:
                    break
                a = pas_vers(a, b, rng)
                if a not in observations:
                    mesurer(a, fin_recherche, 'reliage')
            reliages += 1
        candidats = []
        for v in voisins(courant, m):
            if perf_counter() >= fin_recherche:
                break
            if v in observations:
                continue  # Cache de visite ; réévaluations réservées aux élites.
            if any(tabou.get((i, v[i]), 0) > tour for i in range(n) if v[i] != courant[i]):
                continue
            candidats.append(v)
        if perf_counter() >= fin_recherche:
            break
        if not candidats or sans_progres >= 18:
            # Diversification construite, plutôt qu'un grand réchauffage.
            courant = construire(structure, rng, fin_recherche, tour % 2,
                                  structurel=bool(tour % 3))
            if courant not in observations:
                mesurer(courant, fin_recherche, 'diversification')
            if courant not in observations:
                break
            sans_progres = 0
            tabou.clear()
            continue
        rng.shuffle(candidats)
        aleatoire = candidats[0]
        candidats.sort(key=lambda p: score_rapide(p, structure, tour % 2))
        # Deux propositions guidées + une proposition indépendante du guide.
        selection = list(dict.fromkeys(candidats[:2] + [aleatoire]))
        mesures = []
        for p in selection:
            if mesurer(p, fin_recherche, 'recherche'):
                mesures.append(p)
                # Réessayer les bons placements ; une mesure supérieure ne dégrade pas leur record.
                if score(p) <= precedent:
                    while len(observations[p]) < 3:
                        if not mesurer(p, fin_recherche, 'confirmation'):
                            break
            else:
                break
        if not mesures:
            break
        suivant = min(mesures, key=score)
        for i in range(n):
            if courant[i] != suivant[i]:
                tabou[i, courant[i]] = tour + 7
        tabou = {cle: expiration for cle, expiration in tabou.items() if expiration > tour}
        courant = suivant  # Une détérioration est permise ; les élites sont conservées.
        sans_progres = 0 if score(archive[0]) < precedent else sans_progres + 1
        if afficher and perf_counter() >= prochain_affichage:
            print(f'Temps {perf_counter() - debut:.1f}/{duree_secondes:.1f} s | '
                  f'évaluations = {appels} | meilleur coût observé = {score(archive[0])}', flush=True)
            prochain_affichage = perf_counter() + 10

    # Validation équilibrée de quatre finalistes, choisis parmi toutes les observations.
    finalistes = sorted(observations, key=lambda p: (score(p), -len(observations[p]), p))[:4]
    while perf_counter() < fin:
        incomplets = [p for p in finalistes if len(observations[p]) < 5]
        if not incomplets:
            break
        p = min(incomplets, key=lambda p: (len(observations[p]), score(p)))
        if not mesurer(p, fin, 'validation'):
            break
    gagnant = min(observations, key=lambda p: (score(p), median(observations[p]), p))
    bilan = dict(secondes=perf_counter() - debut, evaluations=appels,
                 phases=dict(evaluations_par_phase), reliages=reliages,
                 couts_gagnant=observations[gagnant].copy(),
                 meilleur_cout_observe=min(min(v) for v in observations.values()),
                 finalistes=[dict(placement=list(p), couts=observations[p].copy(),
                                 mediane=median(observations[p]), meilleur_cout=score(p)) for p in finalistes])
    if afficher:
        print(f'Terminé : {bilan["secondes"]:.2f} s | {appels} évaluations', flush=True)
        print(f'Coûts du placement retenu : {bilan["couts_gagnant"]}', flush=True)
    return list(gagnant), score(gagnant), bilan


if __name__ == '__main__':
    backend, circuit, n, m = instance_selector(instance_num)
    print(f'V5 - Instance {instance_num} : {n} qubits sur {m} positions')
    placement, meilleur_cout, bilan = optimiser(
        lambda p: fitness_inner(p, circuit, backend), circuit, backend,
        duree_secondes=DUREE_SECONDES, graine=GRAINE,
        taille_elite=TAILLE_ELITE, fraction_validation=FRACTION_VALIDATION,
        activer_reliage=ACTIVER_RELIAGE)
    dossier = Path(__file__).resolve().parent / 'resultats_v5'
    dossier.mkdir(exist_ok=True)
    fichier = dossier / f'Groupe{NUMERO_GROUPE}_Challenge_{instance_num}.txt'
    # Conserver le meilleur coût réellement mesuré pour le placement retenu.
    cout_observe = meilleur_cout
    fichier.write_text(' '.join(map(str, placement + [cout_observe])) + '\n', encoding='utf-8')
    detail = dossier / f'Groupe{NUMERO_GROUPE}_Challenge_{instance_num}_bilan.txt'
    detail.write_text(
        f'Budget : {DUREE_SECONDES} s\nGraine : {GRAINE}\n'
        f'Temps réel : {bilan["secondes"]:.3f} s\nÉvaluations : {bilan["evaluations"]}\n'
        f'Placement : {placement}\nMédiane informative : {median(bilan["couts_gagnant"])}\n'
        f'Coût inscrit dans la solution (meilleur observé) : {cout_observe}\n'
        f'Coûts observés pour ce placement : {bilan["couts_gagnant"]}\n'
        f'Meilleur coût isolé de toute la recherche : {bilan["meilleur_cout_observe"]}\n'
        f'Évaluations par phase : {bilan["phases"]}\n'
        f'Finalistes : {bilan["finalistes"]}\n', encoding='utf-8')
    print(f'Placement retenu : {placement} | meilleur coût observé : {meilleur_cout}')
    print(f'Solution : {fichier}\nDétails : {detail}')
