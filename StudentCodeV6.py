# -*- coding: utf-8 -*-
"""V6 : recherche à voisinages variables autour des élites, budget intégral.

Les constructeurs génériques de V5 sont partagés ; source.py reste inchangé.
"""
import math
import random
from collections import Counter
from pathlib import Path
from statistics import median
from time import perf_counter
from source import instance_selector, fitness_inner
from StudentCodeV5 import analyser_structure, construire, voisins, score_rapide, pas_vers

instance_num = 3
NUMERO_GROUPE = "X"
DUREE_SECONDES = 300
GRAINE = 42
TAILLE_ELITE = 6
ACTIVER_RELIAGE = True


def perturber(placement, m, force, rng):
    """Permute plusieurs affectations, y compris avec des positions libres."""
    n = len(placement)
    complet = list(placement) + [x for x in range(m) if x not in placement]
    if m < 2:
        return tuple(placement)
    indices = rng.sample(range(m), min(m, max(2, force)))
    # Inclure au moins un qubit logique, pas uniquement des positions libres.
    if all(i >= n for i in indices):
        indices[0] = rng.randrange(n)
    valeurs = [complet[i] for i in indices]
    for i, valeur in zip(indices, valeurs[1:] + valeurs[:1]):
        complet[i] = valeur
    return tuple(complet[:n])


def optimiser(evaluer, circuit, backend, duree_secondes=300, graine=42,
              taille_elite=6, activer_reliage=True,
              afficher=True):
    """Renvoie placement, meilleur coût observé et bilan détaillé.

    La préparation est incluse dans le temps. Un appel déjà commencé termine.
    Une évaluation initiale est toujours faite, même avec un budget très court.
    """
    if not math.isfinite(duree_secondes) or duree_secondes <= 0:
        raise ValueError('La durée doit être positive et finie.')
    if not isinstance(taille_elite, int) or taille_elite < 2:
        raise ValueError('Il faut au moins deux places dans les élites.')
    debut = perf_counter()
    fin = debut + duree_secondes
    fin_recherche = fin
    rng = random.Random(graine)
    n, m = circuit.num_qubits, backend.num_qubits
    if not 1 <= n <= m:
        raise ValueError('Il faut 1 <= n <= m.')
    observations = {}
    appels = 0
    evaluations_par_phase = Counter()
    archive = []
    dernier_record = debut
    record = math.inf
    redemarrages = 0

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
        nonlocal appels, record, dernier_record
        if not forcer and perf_counter() >= limite:
            return False
        if len(p) != n or len(set(p)) != n or any(not 0 <= x < m for x in p):
            raise ValueError('Placement invalide.')
        valeur = evaluer(list(p))
        if not math.isfinite(valeur):
            raise ValueError('Coût non fini.')
        if valeur < record:
            record = valeur
            dernier_record = perf_counter()
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
        # Une petite part des appels explore le hasard du compilateur, sans
        # répéter indéfiniment un placement dont les mesures sont identiques.
        if tour % 10 == 0:
            incertains = [p for p in archive if len(observations[p]) < 5
                         and (len(observations[p]) < 2 or len(set(observations[p])) > 1)]
            if incertains:
                mesurer(rng.choice(incertains), fin, 'reevaluation')
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
            redemarrages += 1
            # Deux reprises près des élites, puis une construction indépendante.
            if redemarrages % 3 and archive:
                stagnation = (perf_counter() - dernier_record) / duree_secondes
                force = min(n, max(2, 2 + int(stagnation * n)))
                courant = perturber(rng.choice(archive), m, force, rng)
            else:
                courant = construire(structure, rng, fin_recherche, tour % 2,
                                      structurel=bool(redemarrages % 2))
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
        largeur = max(1, math.isqrt(len(candidats)))
        selection = list(dict.fromkeys([candidats[0], rng.choice(candidats[:largeur]), aleatoire]))
        mesures = []
        for p in selection:
            if mesurer(p, fin_recherche, 'recherche'):
                mesures.append(p)
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

    # Aucun quota de validation : la recherche emploie tout le budget.
    finalistes = sorted(observations, key=lambda p: (score(p), p))[:4]
    gagnant = min(observations, key=lambda p: (score(p), median(observations[p]), p))
    bilan = dict(secondes=perf_counter() - debut, evaluations=appels,
                 phases=dict(evaluations_par_phase), reliages=reliages, redemarrages=redemarrages,
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
    print(f'V6 - Instance {instance_num} : {n} qubits sur {m} positions')
    placement, meilleur_cout, bilan = optimiser(
        lambda p: fitness_inner(p, circuit, backend), circuit, backend,
        duree_secondes=DUREE_SECONDES, graine=GRAINE,
        taille_elite=TAILLE_ELITE,
        activer_reliage=ACTIVER_RELIAGE)
    dossier = Path(__file__).resolve().parent / 'resultats_v6'
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
