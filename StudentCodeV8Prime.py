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
# V8 prime : memes operateurs que V8, exploration prolongee avec arret sur stagnation.
# La seule fonction objectif est fitness ; le minimum observe est le critere de recherche et de sortie.
# Inspirations : Rouze et al. (2025), doi:10.1016/j.engappai.2025.112081 ;
# Li et al. (2019), SABRE ; recherche locale pour QAP (Benlic & Hao, 2013).
# Variante experimentale hors du budget officiel de 5 minutes.
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
# V8 prime : arret sur stagnation apres une duree minimale, avec plafond de securite.
# Variables distinctes de QUBIT_BUDGET pour ne pas heriter du plafond V8.
BUDGET = float(os.environ.get("QUBIT_LONG_MAX_SECONDS", "1200"))  # 20 min
MIN_SEARCH = float(os.environ.get("QUBIT_LONG_MIN_SECONDS", str(min(600.0, BUDGET * .5))))
PATIENCE = float(os.environ.get("QUBIT_LONG_PATIENCE_SECONDS", str(min(300.0, BUDGET * .25))))
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

    def repair(self, p, size, related=False):
        """ALNS : retire des affectations, puis reconstruit sans doublon."""
        size = min(n, max(1, size))
        if not self.enabled:
            q = list(p)
            ids = self.rng.sample(range(n), size)
            free = list(set(range(m)) - {q[i] for i in range(n) if i not in ids})
            for i, x in zip(ids, self.rng.sample(free, size)):
                q[i] = x
            return tuple(q)
        k = self.rng.randrange(len(self.W))
        w = self.W[k]
        if related:
            a = self.rng.randrange(n)
            ids = sorted(range(n), key=lambda i: (i != a, -w[a,i] * self.rng.uniform(.5,1.5), self.rng.random()))[:size]
        else:
            ids = self.rng.sample(range(n), size)
        q = list(p)
        assigned = [i for i in range(n) if i not in ids]
        free = list(set(range(m)) - {q[i] for i in assigned})
        while ids:
            # Reconstruire d'abord les qubits les plus lies au sous-mapping fixe.
            i = max(ids, key=lambda j: (float(w[j,assigned].sum()) + .2*float(w[j].sum())) * self.rng.uniform(.8,1.2))
            ranked = sorted((sum(w[i,j]*self.D[x,q[j]] for j in assigned), x) for x in free)
            # RCL par rang, de taille variable, pas de choix glouton impose.
            rcl = min(len(ranked), self.rng.choice((1,2,3)))
            x = self.rng.choice(ranked[:rcl])[1]
            q[i] = x; free.remove(x); ids.remove(i); assigned.append(i)
        return tuple(q)

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
        self.path = Path(__file__).resolve().parent / "resultats_v8_prime" / (
            f"{GROUPE}_{'Challenge' if instance_num >= 11 else 'Instance'}_{instance_num}.txt"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.errors = 0
        self.cost_time = 0.15
        self.keys = {}  # cache du classement, actualise seulement apres une evaluation
        self.archive = set()  # candidats competitifs, borne par un nettoyage periodique
        self.weights = {a: 1.0 for a in ("local", "repair", "related", "cross", "shake", "grasp", "random")}
        self.usage = {a: 0 for a in self.weights}
        self.racing_calls = 0
        self.last_record = start

    def save(self,p,c):
        # Checkpoint atomique : un fichier complet existe des la premiere evaluation.
        temp = self.path.with_suffix(".tmp")
        temp.write_text(" ".join(map(str,(*p,int(c))))+"\n", encoding="utf-8")
        os.replace(temp,self.path)

    def record(self,p,c):
        self.data.setdefault(p,[]).append(c)
        self.calls+=1
        self.archive.add(p)
        v = self.data[p]
        # Classement par minimum observe ; aucun critere median.
        self.keys[p] = (min(v), p)
        if c < self.best_cost:
            self.best, self.best_cost = p,c
            self.last_improvement = self.calls
            self.last_record = time.perf_counter()
            self.save(p,c)
            print(f"[{self.last_record-self.start:6.1f}s] meilleur observe = {c} ; "
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
        # Le minimum est toujours un cout effectivement observe.
        return self.keys[p][0]

    def key(self,p):
        return self.keys[p]

    def rank(self):
        return sorted(self.archive,key=self.key)

    def prune(self):
        # Ne pas trier les dizaines de milliers de solutions deja visitees a chaque tour.
        if len(self.archive) > 320:
            ranked = self.rank()
            self.archive = set(ranked[:240])

    def elite(self, ranked=None):
        if ranked is None: ranked = self.rank()
        result = []
        for p in ranked[:100]:
            if p not in result and all(distance(p,q)>=max(2,n//5) for q in result):
                result.append(p)
            if len(result)>=12:
                break
        return result

    def race(self, candidates, until, target, cap):
        # Une seule observation par candidat ordinaire ; seuls les prometteurs
        # recoivent des evaluations supplementaires, en vagues paralleles.
        candidates = list(dict.fromkeys(p for p in candidates if p in self.data))
        remaining = cap
        while remaining > 0 and time.perf_counter() + self.cost_time*.6 < until:
            pending = [p for p in candidates if len(self.data[p]) < target]
            if not pending:
                break
            pending.sort(key=self.key)
            todo = pending[:min(WORKERS,remaining)]
            results = self.evaluate(todo,until,repeat=True)
            self.racing_calls += len(results)
            remaining -= len(results)
            if not results:
                break

    def propose(self, op, base, elite, count, strength):
        if op == "local":
            return self.guide.voisins(base,count,self.data)
        if op == "cross" and len(elite)>1:
            return [self.guide.crossover(base,self.rng.choice(elite)) for _ in range(count)]
        if op in ("repair","related"):
            return [self.guide.repair(base,self.rng.randint(2,max(2,min(n,int(n*strength)))),op=="related") for _ in range(count)]
        if op == "shake" or op == "cross":
            return [self.guide.perturb(base,self.rng.randint(2,max(2,min(m,int(m*strength))))) for _ in range(count)]
        if op == "grasp":
            return [self.guide.grasp() for _ in range(count)]
        return [self.guide.random() for _ in range(count)]

    def choose_op(self, stale):
        ops = list(self.weights)
        # Un plancher de probabilite preserve l'exploration de tous les operateurs.
        if self.rng.random() < .15:
            return self.rng.choice(ops)
        return self.rng.choices(ops,weights=[self.weights[o]*(1.5 if stale and o in ("repair","related","shake","grasp") else 1.0) for o in ops])[0]

    def run(self):
        end=self.deadline
        duration=end-self.start
        # Conserver les cadences V8 (stagnation locale, amorces, reserve) meme
        # lorsque le plafond est prolonge. Le recuit, lui, refroidit sur le plafond.
        phase_duration=min(duration,297.0)
        # Reserve initiale pour les evaluations finales, independante du plafond long.
        explore=end-max(.5,phase_duration*.07)
        batch_size=max(4,WORKERS*2)
        initial=[tuple(range(n))]
        for _ in range(batch_size-1):
            initial.append(self.guide.grasp() if self.guide.enabled and self.rng.random()<.7 else self.guide.random())
        self.evaluate(initial,explore)
        if not self.data:
            raise RuntimeError("Aucune evaluation terminee dans le budget")
        if self.guide.enabled and time.perf_counter()<explore:
            jobs=[("vf2",self.rng.randrange(2**31))]+[("sabre",self.rng.randrange(2**31)) for _ in range(max(3,WORKERS-1))]
            seeds=self.batch(jobs,min(explore,time.perf_counter()+max(.4,phase_duration*.09)))
            self.evaluate([p for _,p in seeds if p is not None],explore)
        self.race(self.rank()[:min(4,WORKERS)],explore,3,2*WORKERS)
        current=min(self.archive,key=self.key)
        rounds=0; stagnation=0; recent=[]; last_seed=time.perf_counter()
        last_status=self.start
        stop_reason="plafond de securite"
        while True:
            # Reserve pour les derniers essais, extensible si fitness est lente.
            reserve=max(.35,min(duration*.25,max(phase_duration*.055,self.cost_time*(math.ceil(72/WORKERS)+4))))
            explore=end-reserve
            now=time.perf_counter()
            if now+self.cost_time*1.5>=explore:
                break
            # La stagnation globale est distincte des redemarrages locaux V8.
            # On surveille le record historique du minimum observe.
            if now-self.start>=MIN_SEARCH and now-self.last_record>=PATIENCE:
                stop_reason="stagnation du meilleur cout observe"
                end=min(end,now+reserve)
                break
            if now-last_status>=60:
                print(f"[{now-self.start:6.1f}s] suivi : {self.calls} evaluations ; "
                      f"meilleur cout observe = {self.best_cost} ; "
                      f"sans nouveau record = {now-self.last_record:.1f}s",flush=True)
                last_status=now
            self.prune()
            ranked=self.rank()
            elite=self.elite(ranked)
            stale=stagnation>=8 or now-self.last_record>max(3,phase_duration*.10)
            strength=.55 if stale else .30
            # Trajectoires multi-departs : changer de bassin sans revenir aussitot au champion.
            if MODE!="random" and (stagnation>=8 or rounds%17==16):
                choices=[p for p in elite if p not in recent] or elite
                current=self.rng.choice(choices)
                recent=(recent+[current])[-6:]
                stagnation=0
            # Nouvelles amorces SABRE en cours de route, au maximum quelques appels.
            if MODE!="random" and self.guide.enabled and stale and now-last_seed>max(5,phase_duration*.17):
                last_seed=now
                seeds=self.batch([("sabre",self.rng.randrange(2**31)) for _ in range(min(2,WORKERS))],min(explore,now+max(.3,phase_duration*.025)))
                self.evaluate([p for _,p in seeds if p is not None],explore)
            candidates={}
            if MODE=="random":
                for _ in range(batch_size): candidates[self.guide.random()]="random"
            else:
                # Maintenir un socle de voisinage, puis distribuer les places restantes.
                local_count=max(1,batch_size//(4 if stale else 2))
                for p in self.propose("local",current,elite,local_count,strength): candidates[p]="local"
                for _ in range(batch_size*2):
                    if len(candidates)>=batch_size: break
                    op=self.choose_op(stale)
                    base=current if self.rng.random()<.65 else self.rng.choice(elite)
                    for p in self.propose(op,base,elite,min(2,batch_size-len(candidates)),strength):
                        if p not in self.data: candidates.setdefault(p,op)
            candidates={p:op for p,op in candidates.items() if p not in self.data}
            for _ in range(batch_size*4):
                if len(candidates)>=batch_size: break
                p=self.guide.random()
                if p not in self.data: candidates.setdefault(p,"random")
            if not candidates:
                stop_reason="aucun nouveau candidat genere"
                end=min(end,time.perf_counter()+reserve)
                break
            results=self.evaluate(list(candidates)[:batch_size],explore)
            if not results:
                stop_reason="aucune evaluation terminee avant echeance"
                break
            rounds+=1
            new=sorted((p for p,c in results),key=self.key)
            # Racing : donner quelques essais supplementaires aux candidats
            # prometteurs pour tenter d'abaisser leur minimum observe.
            if MODE!="random":
                threshold=min(self.score(current),self.best_cost)
                margin=max(1.0,.035*threshold)
                promising=[p for p in new if self.score(p)<=threshold+margin][:2]
                if not promising and rounds%5==0: promising=new[:1]
                racing_allowed=self.calls<40 or self.racing_calls<.28*self.calls
                if racing_allowed: self.race(promising,explore,3,4)
                if racing_allowed and rounds%5==0:
                    self.race(self.rank()[:2],explore,5,2)
                winner=min(new,key=self.key)
                old=self.score(current)
                gap=self.score(winner)-old
                # Credit selon la qualite du minimum observe.
                by_op={}
                for p in new:
                    op=candidates[p]; self.usage[op]+=1
                    gain=max(0,(old-self.score(p))/max(1,old))
                    reward=.25+min(3,15*gain)
                    if self.score(p)<=old: reward+=.30
                    by_op.setdefault(op,[]).append(reward)
                for op, rewards in by_op.items():
                    self.weights[op]=max(.20,.88*self.weights[op]+.12*statistics.mean(rewards))
                if gap<0:
                    current=winner; stagnation=0
                else:
                    stagnation+=1
                    temp=max(.5,.035*old)*(1-.75*min(1,(time.perf_counter()-self.start)/max(1,duration)))
                    if (gap>=0 and (gap==0 or self.rng.random()<math.exp(-gap/max(.15,temp)))):
                        current=winner
            # Reevaluation periodique des meilleurs candidats pour tenter un nouveau record.
            if rounds%12==0 and self.racing_calls<.28*self.calls:
                self.race(self.rank()[:4],explore,3,4)
                if MODE!="random":
                    self.race(self.rank()[:2],explore,7,4)
        print(f"Arret de l'exploration : {stop_reason} ; "
              f"{time.perf_counter()-self.start:.2f}s ; derniers essais",flush=True)
        # Derniers essais sur les meilleurs candidats. Le champion historique
        # reste garanti : aucun resultat plus eleve ne peut l'ecraser.
        all_rank=sorted(self.data,key=self.key)
        shortlist=list(dict.fromkeys([self.best]+all_rank[:14]))[:14]
        self.race(shortlist,end,3,2*len(shortlist))
        finalists=sorted(shortlist,key=self.key)[:5]
        self.race(finalists,end,9,9*len(finalists))
        p,cost=self.best,self.best_cost
        self.save(p,cost)
        print(f"Solution : {list(p)}\nCout retenu (minimum observe) : {cost}"
              f"\nObservations de la solution : {self.data[p]}"
              f"\nMeilleur cout brut : {self.best_cost}"
              f"\nMapping brut (diagnostic) : {list(self.best)}"
              f"\nEvaluations : {self.calls} ; allocations distinctes : {len(self.data)}"
              f"\nReevaluations racing : {self.racing_calls}"
              f"\nOperateurs (propositions evaluees) : {self.usage}"
              f"\nTemps recherche : {time.perf_counter()-self.start:.2f}s"
              f"\nFichier : {self.path}",flush=True)
        return p,cost


def main():
    if (not all(math.isfinite(v) for v in (BUDGET, MIN_SEARCH, PATIENCE))
            or not 0 <= MIN_SEARCH < BUDGET or not 0 < PATIENCE < BUDGET):
        raise ValueError("Durees finies requises : 0 <= minimum < plafond, 0 < patience < plafond")
    start=time.perf_counter()
    # Une marge de 3 s (ou 5 % sur les petits tests) pour fermer les workers.
    deadline=start+BUDGET-min(3.0,BUDGET*.05)
    rng=random.Random(SEED)
    print(f"Instance {instance_num} : n={n}, m={m}, plafond={BUDGET}s, workers={WORKERS}, mode={MODE}",flush=True)
    print(f"V8 prime : exploration minimale visee={MIN_SEARCH}s ; patience={PATIENCE}s ; "
          "derniers essais inclus dans le plafond",flush=True)
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
