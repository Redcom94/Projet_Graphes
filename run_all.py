# -*- coding: utf-8 -*-
"""Exécute Tabu Search sur les 9 instances et génère un rapport CSV/TXT.

Prérequis : tabu_search.py, source.py, dossiers Instances/ ou Instances-*/.
Exemples : python run_all.py ; python run_all.py --runs 3
"""
import argparse
import csv
import statistics
import time
from pathlib import Path

from source import instance_selector, fitness_inner
from StudentCode import tabu_search


def main():
    parser = argparse.ArgumentParser(description="Évaluer Tabu Search sur les instances 1 à 9")
    parser.add_argument("--runs", type=int, default=1, help="Répétitions par instance (défaut : 1)")
    parser.add_argument("--iterations", type=int, default=80)
    parser.add_argument("--candidates", type=int, default=24)
    parser.add_argument("--tenure", type=int, default=7)
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs doit être >= 1")

    report_dir = Path(__file__).resolve().parent / "resultats_tabu"
    report_dir.mkdir(exist_ok=True)
    trials, summaries = [], []

    for instance_num in range(1, 10):
        print(f"\n=== Instance {instance_num}/9 ===", flush=True)
        try:
            backend, circuit, n, m = instance_selector(instance_num)
        except Exception as exc:
            print(f"Erreur de chargement : {exc}", flush=True)
            summaries.append({"instance": instance_num, "status": f"ERREUR: {exc}"})
            continue

        def objective(mapping):
            return fitness_inner(mapping, circuit, backend)

        successful = []
        for rep in range(args.runs):
            seed = 42 + rep
            started = time.perf_counter()
            try:
                mapping, fitness = tabu_search(
                    objective, n, m,
                    max_iterations=args.iterations,
                    candidate_count=args.candidates,
                    tabu_tenure=args.tenure,
                    seed=seed,
                )
                elapsed = time.perf_counter() - started
                row = {
                    "instance": instance_num, "essai": rep + 1, "seed": seed,
                    "n": n, "m": m, "fitness": fitness,
                    "temps_s": round(elapsed, 3), "mapping": str(mapping),
                }
                trials.append(row)
                successful.append(row)
                print(f"  Essai {rep + 1}: fitness={fitness}, temps={elapsed:.2f}s", flush=True)
            except Exception as exc:
                print(f"  Essai {rep + 1} échoué : {exc}", flush=True)

        if successful:
            best = min(successful, key=lambda x: x["fitness"])
            times = [r["temps_s"] for r in successful]
            fitnesses = [r["fitness"] for r in successful]
            summaries.append({
                "instance": instance_num, "status": "OK", "n": n, "m": m,
                "essais_ok": len(successful),
                "meilleure_fitness": best["fitness"],
                "fitness_moyenne": round(statistics.mean(fitnesses), 3),
                "fitness_ecart_type": round(statistics.pstdev(fitnesses), 3),
                "temps_moyen_s": round(statistics.mean(times), 3),
                "meilleur_mapping": best["mapping"],
            })
            (report_dir / f"Groupeabdou_Instance_{instance_num}.txt").write_text(
                best["mapping"] + "\n", encoding="utf-8"
            )
        else:
            summaries.append({"instance": instance_num, "status": "ERREUR: aucun essai réussi", "n": n, "m": m})

    def write_csv(filename, rows, columns):
        with (report_dir / filename).open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)

    write_csv("mesures_detaillees.csv", trials,
              ["instance", "essai", "seed", "n", "m", "fitness", "temps_s", "mapping"])
    write_csv("resume_instances.csv", summaries,
              ["instance", "status", "n", "m", "essais_ok", "meilleure_fitness",
               "fitness_moyenne", "fitness_ecart_type", "temps_moyen_s", "meilleur_mapping"])

    lines = ["RAPPORT - RECHERCHE TABOU", "=" * 45,
             f"Instances : 1 à 9 | Répétitions : {args.runs}",
             f"Itérations max : {args.iterations} | Candidats : {args.candidates} | Tenure : {args.tenure}",
             "Fitness = profondeur du circuit transpile (a minimiser)", ""]
    for r in summaries:
        lines.append(f"Instance {r['instance']} : {r['status']}")
        if r["status"] == "OK":
            lines.extend([
                f"  Qubits logiques/physiques : {r['n']}/{r['m']}",
                f"  Meilleure fitness : {r['meilleure_fitness']}",
                f"  Moyenne ± écart-type fitness : {r['fitness_moyenne']} ± {r['fitness_ecart_type']}",
                f"  Temps moyen (s) : {r['temps_moyen_s']}",
                f"  Mapping : {r['meilleur_mapping']}",
            ])
        lines.append("")
    (report_dir / "rapport.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nTerminé. Résultats : {report_dir}")


if __name__ == "__main__":
    main()
