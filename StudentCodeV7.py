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

# ---------------------------------------------------------------------------
# Recherche memetique multi-departs : GRASP + SABRE + recherche locale (VNS/ILS)
# + recombinaison par path relinking. La seule fonction objectif est fitness.
# Inspirations : Rouze et al. (2025), doi:10.1016/j.engappai.2025.112081 ;
# Li et al. (2019), SABRE ; recherche locale pour QAP (Benlic & Hao, 2013).
# Implementation originale adaptee au budget du projet.
# ---------------------------------------------------------------------------
import os
import sys
import time
import random
import math
import statistics
import multiprocessing as mp
from pathlib import Path
import numpy as np

# PARAMETRES A ADAPTER (uniquement sous "A vous de jouer !")
GROUPE = os.environ.get("QUBIT_GROUP", "GroupeXX")  # remplacer XX
BUDGET = min(300.0, float(os.environ.get("QUBIT_BUDGET", "300")))
SEED = int(os.environ.get("QUBIT_SEED", "42"))
STRUCTURE = os.environ.get("QUBIT_STRUCTURED", "1") != "0"
MODE = os.environ.get("QUBIT_MODE", "hybrid")  # random : temoin experimental
try:
    CPU = len(os.sched_getaffinity(0))
except AttributeError:
    CPU = os.cpu_count() or 1
WORKERS = max(1, min(8, int(os.environ.get("QUBIT_WORKERS", str(min(4, CPU))))))


def valide(p):
    return len(p) == n and len(set(p)) == n and all(0 <= x < m for x in p)


def tache(job):
    """Executee dans un processus isole ; ne modifie jamais la fonction fitness."""
    kind, arg = job
    if kind == "fitness":
        if not valide(arg):
            raise ValueError("Permutation non admissible")
        return int(fitness(list(arg)))
    # SABRE/VF2 ne servent QU'A proposer des permutations, jamais a les noter.
    try:
        from qiskit.transpiler import PassManager
        from qiskit.transpiler.passes import SabreLayout, VF2Layout
        cmap = backend.coupling_map
        if kind == "vf2":
            algo = VF2Layout(coupling_map=cmap, seed=arg, call_limit=15000)
        else:
            algo = SabreLayout(cmap, seed=arg, max_iterations=3,
                               layout_trials=4, swap_trials=4, skip_routing=True)
        pm = PassManager(algo)
        pm.run(circuit)
        layout = pm.property_set.get("layout")
        if layout is None:
            return None
        d = layout.get_virtual_bits()
        p = tuple(int(d[q]) for q in circuit.qubits)
        return p if valide(p) else None
    except Exception as exc:
        # La recherche reste utilisable si un generateur optionnel echoue.
        return ("seed_error", str(exc))


class Guide:
    """Proxy statique de graphe, uniquement pour ordonner les propositions."""
    def __init__(self, rng, enabled):
        self.rng = rng
        self.enabled = enabled
        self.moves = [(i, j) for i in range(n) for j in range(i+1, m)]
        self.ii = np.array([i for i, j in self.moves], dtype=int)
        self.jj = np.array([j for i, j in self.moves], dtype=int)
        self.D = np.zeros((m, m))
        self.W = []
        self.diff = []
        self.edges = set()
        if not enabled or not self.moves:
            return
        try:
            d = np.full((m, m), np.inf)
            np.fill_diagonal(d, 0)
            for a, b in backend.coupling_map.get_edges():
                d[a, b] = d[b, a] = 1
                self.edges.add((min(a,b), max(a,b)))
            for k in range(m):
                d = np.minimum(d, d[:, k, None] + d[None, k, :])
            if not np.isfinite(d).all():
                d[~np.isfinite(d)] = m * 2
            # Cout nul pour les voisins directs, penalisation de la distance.
            self.D = np.maximum(0, d-1)
            interactions = []
            for inst in circuit.data:
                if len(inst.qubits) == 2 and inst.operation.name != "barrier":
                    a,b = (circuit.find_bit(q).index for q in inst.qubits)
                    interactions.append((a,b))
            L = max(1, len(interactions))
            for decay in (0.12, 0.45, 10.0):
                w = np.zeros((m,m))
                for k,(a,b) in enumerate(interactions):
                    val = math.exp(-k/(L*decay))
                    w[a,b] += val
                    w[b,a] += val
                self.W.append(w)
                delta = (w[self.ii,:] - w[self.jj,:]).copy()
                delta[np.arange(len(self.moves)),self.ii] = 0
                delta[np.arange(len(self.moves)),self.jj] = 0
                self.diff.append(delta)
        except Exception as exc:
            print("Guide de graphe indisponible :", exc, flush=True)
            self.enabled = False

    def full(self,p):
        used = set(p)
        return list(p) + [x for x in range(m) if x not in used]

    def random(self):
        return tuple(self.rng.sample(range(m), n))

    def deltas(self,p,k):
        p = np.asarray(p, dtype=int)
        mat = self.D[p[:,None],p[None,:]]
        return np.sum(self.diff[k] * (mat[self.jj,:]-mat[self.ii,:]), axis=1)

    def grasp(self):
        if not self.enabled:
            return self.random()
        k = self.rng.randrange(len(self.W))
        w = self.W[k]
        degree = np.sum(w, axis=1)
        physical = list(range(m))
        remaining = list(range(n))
        p = [-1]*n
        assigned = []
        while remaining:
            # Priorite aux interactions avec les qubits deja affectes.
            scores = [(float(w[i,assigned].sum())*2+float(degree[i]),i)
                      for i in remaining]
            scores.sort(reverse=True)
            i = self.rng.choice(scores[:min(3,len(scores))])[1]
            values = []
            for x in physical:
                val = sum(w[i,j]*self.D[x,p[j]] for j in assigned)
                val += 0.035*degree[i]*float(np.mean(self.D[x,physical]))
                values.append((float(val),x))
            values.sort()
            rcl = self.rng.choice((1,2,3))
            x = self.rng.choice(values[:min(rcl,len(values))])[1]
            p[i] = x
            remaining.remove(i)
            physical.remove(x)
            assigned.append(i)
        # Descente rapide sur le proxy, avec plusieurs modeles temporels.
        p = self.full(p)
        for _ in range(24):
            delta = self.deltas(p,k)
            ix = int(np.argmin(delta))
            if delta[ix] >= -1e-9:
                break
            i,j = self.moves[ix]
            p[i],p[j] = p[j],p[i]
        return tuple(p[:n])

    def perturb(self,p,k):
        p = self.full(p)
        if not self.moves:
            return tuple(p[:n])
        for _ in range(k):
            i,j = self.rng.choice(self.moves)
            p[i],p[j] = p[j],p[i]
        return tuple(p[:n])

    def crossover(self,a,b):
        # Path relinking : rapproche progressivement a de b, sans doublon.
        p = self.full(a)
        diff = [i for i in range(n) if a[i] != b[i]]
        self.rng.shuffle(diff)
        for i in diff[:max(1,int(len(diff)*self.rng.uniform(.25,.75)))]:
            j = p.index(b[i])
            p[i],p[j] = p[j],p[i]
        return tuple(p[:n])

    def voisins(self,p,count,seen):
        full = self.full(p)
        indices = list(range(len(self.moves)))
        self.rng.shuffle(indices)
        guided = []
        if self.enabled and indices:
            # L'ordre du proxy est un indice, pas un filtre dur.
            k = self.rng.randrange(len(self.W))
            delta = self.deltas(full,k)
            guided = sorted(indices,key=lambda i:delta[i])
        near = [ix for ix in indices if tuple(sorted((full[self.moves[ix][0]],
                          full[self.moves[ix][1]]))) in self.edges]
        orders = [guided, near, indices, indices] if self.enabled else [indices]
        ptr = [0]*len(orders)
        result = []
        forbidden = set()
        for _ in range(max(1,count)):
            for off in range(len(orders)):
                z = (_+off)%len(orders)
                while ptr[z] < len(orders[z]):
                    ix = orders[z][ptr[z]]; ptr[z]+=1
                    i,j = self.moves[ix]
                    q = full.copy(); q[i],q[j] = q[j],q[i]
                    q = tuple(q[:n])
                    if q not in seen and q not in forbidden:
                        result.append(q); forbidden.add(q)
                        break
                else:
                    continue
                break
            else:
                break
        return result


def distance(a,b):
    return sum(x != y for x,y in zip(a,b))


class Search:
    def __init__(self, pool, start, deadline, rng):
        self.pool = pool
        self.start = start
        self.deadline = deadline
        self.rng = rng
        self.data = {}  # permutation -> toutes les observations de fitness
        self.calls = 0
        self.best = None
        self.best_cost = math.inf
        self.last_improvement = 0
        self.guide = Guide(rng, STRUCTURE and MODE != "random")
        self.path = Path(__file__).resolve().parent / "resultats_v7" / (
            f"{GROUPE}_{'Challenge' if instance_num >= 11 else 'Instance'}_{instance_num}.txt"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.errors = 0
        self.cost_time = 0.15

    def save(self,p,c):
        # Checkpoint atomique : un fichier complet existe des la premiere evaluation.
        temp = self.path.with_suffix(".tmp")
        temp.write_text(" ".join(map(str,(*p,int(c))))+"\n", encoding="utf-8")
        os.replace(temp,self.path)

    def record(self,p,c):
        self.data.setdefault(p,[]).append(c)
        self.calls+=1
        if c < self.best_cost:
            self.best, self.best_cost = p,c
            self.last_improvement = self.calls
            self.save(p,c)
            print(f"[{time.perf_counter()-self.start:6.1f}s] meilleur observe = {c} ; "
                  f"{self.calls} evaluations",flush=True)

    def batch(self,jobs,until):
        # Le parent ne se bloque jamais au-dela de la date limite, meme si
        # une evaluation individuelle ou un generateur prend trop de temps.
        if not jobs or time.perf_counter() >= until:
            return []
        pending = [(job,self.pool.apply_async(tache,(job,))) for job in jobs]
        results=[]
        t0=time.perf_counter()
        while pending and time.perf_counter()<until:
            rest=[]
            for job,async_result in pending:
                if not async_result.ready():
                    rest.append((job,async_result)); continue
                try:
                    value = async_result.get()
                    if job[0] == "fitness":
                        self.record(job[1],value)
                    elif isinstance(value,tuple) and value and value[0]=="seed_error":
                        if self.errors<3:
                            print("Generateur optionnel :",value[1],flush=True)
                        self.errors+=1
                        continue
                    results.append((job,value))
                except Exception as exc:
                    if job[0] == "fitness":
                        raise RuntimeError("Echec de la fonction fitness imposee") from exc
                    print("Generateur optionnel :",exc,flush=True)
            pending=rest
            if pending:
                time.sleep(min(.01,max(0,until-time.perf_counter())))
        if jobs[0][0]=="fitness" and results:
            per_wave=(time.perf_counter()-t0)/max(1,math.ceil(len(results)/WORKERS))
            self.cost_time=.75*self.cost_time+.25*per_wave
        return results

    def evaluate(self,ps,until,repeat=False):
        unique=list(dict.fromkeys(p for p in ps if valide(p) and (repeat or p not in self.data)))
        if not unique:
            return []
        return [(job[1],v) for job,v in self.batch([("fitness",p) for p in unique],until)]

    def score(self,p):
        # Median_low est toujours un cout effectivement observe.
        return statistics.median_low(self.data[p])

    def rank(self):
        return sorted(self.data,key=lambda p:(self.score(p),min(self.data[p]),p))

    def elite(self):
        rank=self.rank()[:80]
        if not rank:
            return []
        result=[]
        # Conserver la qualite et une diversite minimale dans la population.
        for p in rank:
            if not result or all(distance(p,q)>=max(2,n//5) for q in result):
                result.append(p)
            if len(result)>=12:
                break
        return result

    def run(self):
        end=self.deadline
        # Reserve de validation (et marge de fermeture hors de cette limite).
        explore=end-max(.5,(end-self.start)*.08)
        batch_size=max(4,WORKERS*2)
        initial=[tuple(range(n))]
        for _ in range(batch_size-1):
            initial.append(self.guide.grasp() if self.guide.enabled and self.rng.random()<.7
                           else self.guide.random())
        self.evaluate(initial,explore)
        if not self.data:
            raise RuntimeError("Aucune evaluation terminee dans le budget")
        # Amorces de haut niveau Qiskit (sous le controle du meme chronometre).
        if self.guide.enabled and time.perf_counter()<explore:
            jobs=[("vf2",self.rng.randrange(2**31))]+[("sabre",self.rng.randrange(2**31))
                   for _ in range(max(3,WORKERS-1))]
            seed_end=min(explore,time.perf_counter()+max(.4,(end-self.start)*.09))
            seeds=self.batch(jobs,seed_end)
            self.evaluate([p for _,p in seeds if p is not None],explore)
        current=self.rank()[0]
        stagnation=0
        rounds=0
        while True:
            # Ajuster la reserve aux temps de transpilation effectivement mesures.
            duration=end-self.start
            waves=2*math.ceil(max(3,min(8,WORKERS*2))/WORKERS)+6*math.ceil(3/WORKERS)+1
            reserve=max(.25,min(duration*.30,max(duration*.025,self.cost_time*waves)))
            explore=end-reserve
            if time.perf_counter()>=explore:
                break
            restart=False
            # Budget souple de generation ; les evaluations ont une borne stricte.
            if MODE=="random":
                candidates=[self.guide.random() for _ in range(batch_size)]
            else:
                elite=self.elite()
                if stagnation>=5 or current not in self.data:
                    restart=True
                    stagnation=0
                    base=self.rng.choice(elite[:min(5,len(elite))])
                    candidates=[self.guide.perturb(base,self.rng.randint(2,min(8,max(2,n))))
                                for _ in range(batch_size//2)]
                    candidates += [self.guide.grasp() if self.rng.random()<.65 else self.guide.random()
                                   for _ in range(batch_size-len(candidates))]
                else:
                    candidates=self.guide.voisins(current,max(2,batch_size-2),self.data)
                    if len(elite)>1:
                        a=self.rng.choice(elite[:min(4,len(elite))]); b=self.rng.choice(elite)
                        candidates.append(self.guide.crossover(a,b))
                    candidates.append(self.guide.perturb(current,self.rng.choice((2,2,3,4))))
                    if rounds%4==0:
                        candidates.append(self.guide.grasp())
            candidates=list(dict.fromkeys(p for p in candidates if p not in self.data))
            attempts=0
            while len(candidates)<batch_size and attempts<batch_size*4:
                q=self.guide.random(); attempts+=1
                if q not in self.data and q not in candidates:
                    candidates.append(q)
            if not candidates:
                break
            results=self.evaluate(candidates[:batch_size],explore)
            if not results:
                break
            rounds+=1
            if MODE=="random":
                continue
            winner=min((p for p,c in results),key=self.score)
            gap=self.score(winner)-self.score(current)
            if restart or gap<0:
                current=winner; stagnation=0
            else:
                stagnation+=1
                # Acceptation de seuil / recuit leger : permet de traverser les plateaux.
                temp=max(0.6,.035*self.score(current))*(1-.75*min(1,(time.perf_counter()-self.start)/max(1,end-self.start)))
                if gap==0 or self.rng.random()<math.exp(-gap/max(.15,temp)):
                    current=winner
            # Retour regulier au meilleur bassin, sans perdre les autres elites.
            if rounds%8==0:
                current=self.rank()[0]
        # Validation : top candidats par mediane, observations independantes.
        # Au moins deux tours si le temps le permet ; puis course des finalistes.
        shortlist=self.rank()[:max(3,min(8,WORKERS*2))]
        for _ in range(2):
            if time.perf_counter()>=end: break
            self.evaluate(shortlist,end,repeat=True)
        finalists=sorted(shortlist,key=lambda p:(self.score(p),-len(self.data[p])))[:min(3,len(shortlist))]
        while finalists and time.perf_counter()+max(.05,self.cost_time*.7)<end:
            if min(len(self.data[p]) for p in finalists)>=9:
                break
            to_check=[p for p in finalists if len(self.data[p])<9]
            if not self.evaluate(to_check,end,repeat=True):
                break
            finalists.sort(key=lambda p:(self.score(p),-len(self.data[p])))
        # Preferer les solutions confirmees ; en cas de temps court, garder
        # la meilleure observation disponible. Cout exporte = valeur observee.
        confirmed=[p for p in shortlist if len(self.data[p])>=3]
        p=min(confirmed or shortlist,key=lambda p:(self.score(p),-len(self.data[p]),min(self.data[p])))
        cost=self.score(p)
        self.save(p,cost)
        print(f"Solution : {list(p)}\nCout retenu (mediane basse) : {cost}"
              f"\nObservations de la solution : {self.data[p]}"
              f"\nMeilleur cout brut : {self.best_cost}"
              f"\nEvaluations : {self.calls} ; allocations distinctes : {len(self.data)}"
              f"\nTemps recherche : {time.perf_counter()-self.start:.2f}s"
              f"\nFichier : {self.path}",flush=True)
        return p,cost


def main():
    if BUDGET<=0:
        raise ValueError("Budget positif requis")
    start=time.perf_counter()
    # Une marge de 3 s (ou 5 % sur les petits tests) pour fermer les workers.
    deadline=start+BUDGET-min(3.0,BUDGET*.05)
    rng=random.Random(SEED)
    print(f"Instance {instance_num} : n={n}, m={m}, budget={BUDGET}s, workers={WORKERS}, mode={MODE}",flush=True)
    # spawn : compatible Windows/Linux, pas de fork d'un runtime Rust multithread.
    pool=mp.get_context("spawn").Pool(WORKERS)
    try:
        Search(pool,start,deadline,rng).run()
    finally:
        pool.terminate()
        pool.join()
    print(f"Temps total optimisation : {time.perf_counter()-start:.2f}s",flush=True)


if __name__ == "__main__":
    mp.freeze_support()
    main()
