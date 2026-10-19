#!/usr/bin/env python3
"""Filtre et note des entreprises issues de l'API Recherche d'entreprises (pages JSON déjà collectées).

Usage : python3 -I prospection-score.py PAGES_DIR --dept 78 --tranches 12,21 --out prospection/AAAA-MM-JJ-slug [--top 30]
Écrit <out>.csv (colonnes de prospection-b2b) et <out>.txt (ciblage, barème, décompte).
"""
import argparse, csv, datetime, glob, json, os

TAILLE = {"11": 8, "12": 18, "21": 25, "22": 25, "31": 25, "32": 20, "41": 12}  # /25 ; NN = 10
BAREME = ("score /100 = taille 25 (50-249 salariés = 25, 250-499 = 20, 20-49 = 18, 500-999 = 12, 10-19 = 8, NN = 10)"
          " + dirigeant 25 (président ou gérant personne physique = 25, directeur général seul = 12, président société = 8)"
          " + santé 20 (marge nette proportionnelle de 0 à 20 entre 0 %% et 8 %% ou plus, négative = 0, non publiée = 8)"
          " + fraîcheur des comptes 10 (publiés N-1 = 10, N-2 = 8, N-3 = 5, plus ancien = 2, aucun = 3)"
          " + ancienneté 10 (plus de 10 ans = 10, 3 à 10 ans = 6, moins de 3 ans = 0)"
          " + structure 10 (3 établissements ouverts ou plus = 10, 2 = 7, 1 = 4) ; départage par chiffre d'affaires.")
HYP = {"41": "promotion/construction avec forte charge documentaire (permis, contrats, suivi de chantiers) ; l'IA pourrait aider à la rédaction et au classement",
       "42": "travaux publics avec dossiers d'appels d'offres et rapports de chantier répétitifs ; l'IA pourrait aider à la réponse aux AO et aux comptes rendus",
       "43": "devis, factures, relevés de chantier et réponses clients saisis à la main ; l'IA pourrait aider à chiffrer, rédiger et classer"}


def dirigeant(r):
    """Meilleur dirigeant décisionnaire : (dirigeant, points) ou None."""
    ds = [d for d in r.get("dirigeants") or [] if d.get("qualite", "").startswith(("Président", "Gérant", "Directeur Général"))]
    pp = [d for d in ds if d["type_dirigeant"] == "personne physique"]
    top = [d for d in pp if d["qualite"].startswith(("Président", "Gérant"))]
    if top:
        return top[0], 25
    if pp:
        return pp[0], 12
    return (ds[0], 8) if ds else None


def note(r, today):
    d = dirigeant(r)
    if not d:
        return None
    s = TAILLE.get(r["tranche_effectif_salarie"], 10) + d[1]
    f = r.get("finances") or {}
    yr = max(f) if f else None
    ca = f[yr].get("ca") if yr else None
    rn = f[yr].get("resultat_net") if yr else None
    if ca and rn is not None:
        m = rn / ca
        s += round(20 * min(max(m, 0), .08) / .08)
    else:
        s += 8
    age = today.year - int(yr) if yr else None
    s += 3 if age is None else 10 if age <= 1 else 8 if age == 2 else 5 if age == 3 else 2
    anc = (today - datetime.date.fromisoformat(r["date_creation"])).days / 365.25
    s += 10 if anc > 10 else 6 if anc >= 3 else 0
    n = r.get("nombre_etablissements_ouverts") or 1
    s += 10 if n >= 3 else 7 if n == 2 else 4
    return s, d[0], d[1], ca, rn, yr


def main():
    a = argparse.ArgumentParser()
    a.add_argument("pages"); a.add_argument("--dept", required=True); a.add_argument("--tranches", required=True)
    a.add_argument("--out", required=True); a.add_argument("--top", type=int, default=30)
    a.add_argument("--today", default=datetime.date.today().isoformat())
    a = a.parse_args()
    today = datetime.date.fromisoformat(a.today)
    tr = set(a.tranches.split(","))
    seen, stats, rows = set(), {"bruts": 0, "hors_departement": 0, "hors_tranche_ou_fermee": 0, "ge": 0, "sans_dirigeant": 0}, []
    for p in sorted(glob.glob(os.path.join(a.pages, "*.json"))):
        for r in json.load(open(p))["results"]:
            if r["siren"] in seen:
                continue
            seen.add(r["siren"]); stats["bruts"] += 1
            if r["siege"]["departement"] != a.dept:
                stats["hors_departement"] += 1; continue
            if r["etat_administratif"] != "A" or r["tranche_effectif_salarie"] not in tr or r.get("statut_diffusion") != "O":
                stats["hors_tranche_ou_fermee"] += 1; continue
            if r["categorie_entreprise"] == "GE":
                stats["ge"] += 1; continue
            n = note(r, today)
            if not n:
                stats["sans_dirigeant"] += 1; continue
            rows.append((n, r))
    rows.sort(key=lambda x: (-x[0][0], -(x[0][3] or 0)))
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + ".csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow("score;siren;nom;ville;departement;naf;effectif;ca;resultat_net;dirigeant;qualite;date_creation;hypothese_besoin;url_annuaire".split(";"))
        for (s, d, pts, ca, rn, yr), r in rows[:a.top]:
            ident = f"{d.get('prenoms') or ''} {d.get('nom') or d.get('denomination') or ''}".strip().title()
            if pts == 8:
                ident += " (société : dirigeant à identifier)"
            w.writerow([s, r["siren"], r["nom_complet"], r["siege"]["libelle_commune"], a.dept, r["activite_principale"],
                        f"{r['tranche_effectif_salarie']} ({r.get('annee_tranche_effectif_salarie')})",
                        "" if ca is None else f"{ca} ({yr})", "" if rn is None else rn, ident, d["qualite"], r["date_creation"],
                        "Hypothèse : " + HYP.get(r["activite_principale"][:2], "processus documentaires répétitifs ; l'IA pourrait aider à les accélérer"),
                        "https://annuaire-entreprises.data.gouv.fr/entreprise/" + r["siren"]])
    with open(a.out + ".txt", "w", encoding="utf-8") as fh:
        fh.write(f"Ciblage : siège dans le {a.dept}, tranches {a.tranches}, actives, diffusion complète ; requête du {a.today}\n")
        fh.write(f"Décompte : {stats} ; retenues après filtres : {len(rows)} ; fichier : {min(a.top, len(rows))} meilleures\n")
        fh.write(BAREME.replace("%%", "%") + "\n")
    print(stats, len(rows))
    for (s, d, *_), r in rows[:a.top]:
        print(s, r["nom_complet"], r["siege"]["libelle_commune"], r["tranche_effectif_salarie"])


if __name__ == "__main__":
    main()
