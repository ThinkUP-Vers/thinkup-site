#!/usr/bin/env python3
"""Mise en forme de l'édition hebdomadaire de la veille outils.

  python3 rapport.py construire selection.json [--sortie DOSSIER]
      Contrôle selection.json, calcule score et verdict de chaque outil, trie,
      et écrit rapport.html (importé tel quel dans Google Docs) et index.txt.
      Code retour 1 et liste des erreurs si le fichier n'est pas conforme.

  python3 rapport.py mail selection.json --lien URL_DU_DOC [--sortie DOSSIER]
      Écrit sujet.txt, mail.html et mail.txt : l'essentiel de l'édition et le
      lien vers le document.

Aucun score ni verdict n'est saisi à la main : ils sont calculés ici à partir
des trois notes (barème dans SKILL.md et config.json).
"""

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
MODELES = {"open-source", "freemium", "payant"}
RISQUES = {"faible", "moyen", "élevé"}
HEBERGEMENTS = {"local", "UE", "hors UE", "inconnu"}
CHAMPS_TEXTE = ["nom", "id", "url", "editeur", "prix", "licence", "fonction", "utilite",
                "theme", "risque_motif", "signaux", "source", "prochaine_etape"]
NOTES = ["pertinence", "accessibilite", "maturite"]
ORDRE_VERDICT = {"À tester": 0, "À surveiller": 1, "Pour info": 2}


def date_fr(iso):
    d = dt.date.fromisoformat(iso)
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


def periode_fr(debut, fin):
    d, f = dt.date.fromisoformat(debut), dt.date.fromisoformat(fin)
    if (d.year, d.month) == (f.year, f.month):
        return f"du {d.day} au {date_fr(fin)}"
    if d.year == f.year:
        return f"du {d.day} {MOIS[d.month - 1]} au {date_fr(fin)}"
    return f"du {date_fr(debut)} au {date_fr(fin)}"


def e(texte):
    return html.escape(str(texte), quote=False)


def a(url, texte):
    return f'<a href="{html.escape(url, quote=True)}">{e(texte)}</a>'


def charger(chemin_selection, chemin_config):
    config = json.loads(Path(chemin_config).read_text(encoding="utf-8"))
    sel = json.loads(Path(chemin_selection).read_text(encoding="utf-8"))
    return config, sel


def controler(sel, config):
    """Renvoie (erreurs, avertissements, outils retenus enrichis du score et du verdict)."""
    erreurs, avert = [], []
    for champ in ["edition", "periode", "profil_perso", "sources", "candidats_examines", "outils"]:
        if champ not in sel:
            erreurs.append(f"champ racine manquant : {champ}")
    if erreurs:
        return erreurs, avert, []
    for champ in ["edition"]:
        try:
            dt.date.fromisoformat(sel[champ])
        except (TypeError, ValueError):
            erreurs.append(f"{champ} : date AAAA-MM-JJ attendue")
    for borne in ["debut", "fin"]:
        try:
            dt.date.fromisoformat(sel["periode"].get(borne, ""))
        except (TypeError, ValueError):
            erreurs.append(f"periode.{borne} : date AAAA-MM-JJ attendue")
    for i, s in enumerate(sel["sources"]):
        if not s.get("nom") or not isinstance(s.get("ok"), bool):
            erreurs.append(f"sources[{i}] : « nom » et « ok » (true/false) obligatoires")

    # Les thèmes perso viennent de la consigne (selection.json), jamais du dépôt public.
    themes = {k: set(sel["profil_perso"] if k == "perso" else v["themes"])
              for k, v in config["publics"].items()}
    seuils, retenus, ids = config["seuils"], [], set()
    for i, o in enumerate(sel["outils"]):
        nom = o.get("nom") or f"outils[{i}]"
        for champ in CHAMPS_TEXTE:
            if not str(o.get(champ, "")).strip():
                erreurs.append(f"{nom} : champ « {champ} » vide ou absent (écrire « non communiqué » si la source ne le donne pas)")
        if o.get("modele") not in MODELES:
            erreurs.append(f"{nom} : modele doit valoir {sorted(MODELES)}")
        if o.get("risque") not in RISQUES:
            erreurs.append(f"{nom} : risque doit valoir {sorted(RISQUES)}")
        if o.get("hebergement") not in HEBERGEMENTS:
            erreurs.append(f"{nom} : hebergement doit valoir {sorted(HEBERGEMENTS)}")
        if o.get("public") not in themes:
            erreurs.append(f"{nom} : public doit valoir {', '.join(themes)}")
        elif o.get("theme") not in themes[o["public"]]:
            erreurs.append(f"{nom} : thème « {o.get('theme')} » inconnu pour le public {o['public']} ; attendus : {sorted(themes[o['public']])}")
        if not str(o.get("url", "")).startswith("https://"):
            erreurs.append(f"{nom} : url doit commencer par https://")
        if not re.fullmatch(r"(github:[\w.-]+/[\w.-]+|web:[a-z0-9.-]+\.[a-z]{2,}(/[\w./-]*)?)", str(o.get("id", ""))):
            erreurs.append(f"{nom} : id attendu « github:proprietaire/depot » ou « web:domaine.tld »")
        elif o["id"] in ids:
            erreurs.append(f"{nom} : id en double ({o['id']})")
        ids.add(o.get("id"))
        notes_ok = True
        for n in NOTES:
            if not isinstance(o.get(n), int) or not 0 <= o[n] <= 3:
                erreurs.append(f"{nom} : {n} doit être un entier de 0 à 3")
                notes_ok = False
        if not notes_ok:
            continue
        score = 2 * o["pertinence"] + o["accessibilite"] + o["maturite"]
        if o["pertinence"] < config.get("pertinence_min", 0):
            avert.append(f"{nom} retiré : pertinence {o['pertinence']}/3 sous le minimum {config['pertinence_min']}, à mettre dans « ecartes » si l'outil est très visible")
            continue
        if score < config["score_min"]:
            avert.append(f"{nom} retiré : score {score}/12 sous le minimum {config['score_min']}")
            continue
        if score >= seuils["a_tester"] and o.get("risque") != "élevé":
            verdict = "À tester"
        elif score >= seuils["a_surveiller"]:
            verdict = "À surveiller"
        else:
            verdict = "Pour info"
        retenus.append(dict(o, score=score, verdict=verdict))

    # Un public peut avoir son propre plafond (« max ») ; les autres partagent max_outils.
    plafonnes = {k: v["max"] for k, v in config["publics"].items() if "max" in v}
    for public, plafond in plafonnes.items():
        n = sum(1 for o in retenus if o["public"] == public)
        if n > plafond:
            erreurs.append(f"{n} outils retenus pour le public {public}, maximum {plafond} : garder les meilleurs scores")
    n = sum(1 for o in retenus if o["public"] not in plafonnes)
    if n > config["max_outils"]:
        erreurs.append(f"{n} outils retenus pour un maximum de {config['max_outils']} : garder les meilleurs scores")
    for i, x in enumerate(sel.get("ecartes", [])):
        if not x.get("nom") or not x.get("motif"):
            erreurs.append(f"ecartes[{i}] : « nom » et « motif » obligatoires")
    retenus.sort(key=lambda o: (ORDRE_VERDICT[o["verdict"]], -o["score"], o["nom"].lower()))
    return erreurs, avert, retenus


def fiche(o):
    lignes = [
        ("Fonction", e(o["fonction"])),
        ("Utilité", e(o["utilite"])),
        ("Thème", e(o["theme"])),
        ("Modèle et prix", e(f"{o['modele']} — {o['prix']}")),
        ("Éditeur et licence", e(f"{o['editeur']} — {o['licence']}")),
        ("Maturité", e(o["signaux"])),
        ("Risque", e(f"{o['risque']} — {o['risque_motif']}")),
        ("Données hébergées", e(o["hebergement"])),
        ("Notes", e(f"pertinence {o['pertinence']}/3, accessibilité {o['accessibilite']}/3, maturité {o['maturite']}/3")),
        ("Prochaine étape", e(o["prochaine_etape"])),
        ("Source", e(o["source"])),
        ("Lien", a(o["url"], o["url"])),
    ]
    if o.get("nouvelle_version"):
        lignes.insert(0, ("Déjà signalé", e(o["nouvelle_version"])))
    corps = "".join(
        f"<tr><td><b>{t}</b></td><td>{v}</td></tr>" for t, v in lignes)
    return (f"<h3>{e(o['nom'])} — {e(o['verdict'])} ({o['score']}/12)</h3>"
            f'<table border="1" cellpadding="5" style="border-collapse:collapse;width:100%">{corps}</table>')


def construire(sel, config, retenus):
    p = sel["periode"]
    libelles = {k: v["libelle"] for k, v in config["publics"].items()}
    compte = {v: sum(1 for o in retenus if o["verdict"] == v) for v in ORDRE_VERDICT}
    titre = f"{config['drive']['prefixe_titre']} — semaine {periode_fr(p['debut'], p['fin'])}"

    h = [f'<html><head><meta charset="utf-8"><title>{e(titre)}</title></head><body>',
         f"<h1>{e(titre)}</h1>",
         f"<p>Édition du {e(date_fr(sel['edition']))}. {sel['candidats_examines']} candidats examinés, "
         f"{len(retenus)} retenus : {compte['À tester']} à tester, {compte['À surveiller']} à surveiller, "
         f"{compte['Pour info']} pour information.</p>"]
    if sel.get("en_bref"):
        h.append(f"<h2>En bref</h2><p>{e(sel['en_bref'])}</p>")

    h.append("<h2>À tester en priorité</h2>")
    a_tester = [o for o in retenus if o["verdict"] == "À tester"]
    if a_tester:
        h.append('<table border="1" cellpadding="5" style="border-collapse:collapse;width:100%">'
                 '<tr style="background:#f2f2f2"><td><b>Outil</b></td><td><b>Pour</b></td>'
                 '<td><b>Pourquoi</b></td><td><b>Prochaine étape</b></td></tr>')
        for o in a_tester:
            h.append(f'<tr><td>{a(o["url"], o["nom"])} ({o["score"]}/12)</td>'
                     f'<td>{e(libelles[o["public"]])}</td><td>{e(o["utilite"])}</td>'
                     f'<td>{e(o["prochaine_etape"])}</td></tr>')
        h.append("</table>")
    else:
        h.append("<p>Aucun outil n'atteint le seuil « à tester » cette semaine.</p>")

    for public in config["publics"]:
        outils = [o for o in retenus if o["public"] == public]
        h.append(f"<h2>{e(libelles[public])}</h2>")
        if outils:
            h.extend(fiche(o) for o in outils)
        else:
            h.append("<p>Rien de pertinent cette semaine.</p>")

    if sel.get("ecartes"):
        h.append("<h2>Vus et écartés</h2><ul>")
        h.extend(f"<li><b>{e(x['nom'])}</b> : {e(x['motif'])}</li>" for x in sel["ecartes"])
        h.append("</ul>")

    s = config["seuils"]
    h.append("<h2>Méthode et limites</h2><ul>")
    h.append(f"<li>Période couverte : {e(periode_fr(p['debut'], p['fin']))}.</li>")
    for src in sel["sources"]:
        etat = "consultée" if src["ok"] else "en échec"
        note = f" — {src['note']}" if src.get("note") else ""
        h.append(f"<li>{e(src['nom'])} : {etat}{e(note)}.</li>")
    h.append(f"<li>Score sur 12 = 2 × pertinence + accessibilité + maturité. « À tester » à partir de {s['a_tester']} "
             f"sans risque élevé, « à surveiller » à partir de {s['a_surveiller']}, en dessous de "
             f"{config['score_min']} ou avec une pertinence inférieure à {config.get('pertinence_min', 0)}/3, "
             f"l'outil n'est pas retenu.</li>")
    h.append("<li>Aucun outil n'a été installé ni essayé : les informations viennent des pages publiques consultées "
             "à la date de l'édition. Prix et fonctions changent vite, à revérifier avant toute recommandation à un client.</li>")
    h.append("<li>Un projet récent et populaire n'est pas un projet sûr. Avant d'installer un outil open-source, vérifier "
             "l'éditeur et les accès demandés (mails, comptes, fichiers), et faire relire par un développeur ce qui touche "
             "aux données d'un client.</li></ul>")

    h.append("<h2>Index</h2><p>Identifiants des outils retenus, relus par l'édition suivante pour ne pas les répéter.</p><p>")
    h.append("<br>".join(e(o["id"]) for o in retenus) or "aucun")
    h.append("</p></body></html>")
    return titre, "".join(h)


def mail(sel, config, retenus, lien):
    p = sel["periode"]
    a_tester = [o for o in retenus if o["verdict"] == "À tester"]
    mis_en_avant = a_tester[:5] or retenus[:3]
    sujet = (f"{config['drive']['prefixe_titre']} — {len(a_tester)} à tester, {len(retenus)} retenus "
             f"(semaine {periode_fr(p['debut'], p['fin'])})")
    intro = (f"{sel['candidats_examines']} candidats examinés, {len(retenus)} retenus, dont "
             f"{len(a_tester)} à tester.")
    titre_liste = "À tester en priorité" if a_tester else "Les mieux notés (aucun n'atteint le seuil « à tester »)"
    h = [f"<p>{e(intro)}</p>"]
    t = [intro, ""]
    if sel.get("en_bref"):
        h.append(f"<p>{e(sel['en_bref'])}</p>")
        t += [sel["en_bref"], ""]
    if mis_en_avant:
        h.append(f"<p><b>{e(titre_liste)}</b></p><ul>")
        t.append(titre_liste + " :")
        for o in mis_en_avant:
            h.append(f'<li>{a(o["url"], o["nom"])} ({o["score"]}/12) : {e(o["utilite"])}</li>')
            t.append(f"- {o['nom']} ({o['score']}/12) : {o['utilite']} {o['url']}")
        h.append("</ul>")
        t.append("")
    else:
        h.append("<p>Rien de pertinent cette semaine.</p>")
        t += ["Rien de pertinent cette semaine.", ""]
    h.append(f"<p>Le document complet, avec les fiches et la méthode : {a(lien, lien)}</p>")
    t.append(f"Le document complet, avec les fiches et la méthode : {lien}")
    return sujet, "".join(h), "\n".join(t) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("commande", choices=["construire", "mail"])
    ap.add_argument("selection", type=Path)
    ap.add_argument("--config", type=Path, default=ICI.parent / "config.json")
    ap.add_argument("--sortie", type=Path)
    ap.add_argument("--lien")
    args = ap.parse_args()
    sortie = args.sortie or args.selection.parent
    sortie.mkdir(parents=True, exist_ok=True)

    config, sel = charger(args.selection, args.config)
    erreurs, avert, retenus = controler(sel, config)
    for a in avert:
        print(f"Avertissement : {a}")
    if erreurs:
        print(f"{len(erreurs)} erreur(s) dans {args.selection} :")
        for x in erreurs:
            print(f"  - {x}")
        return 1

    if args.commande == "construire":
        titre, page = construire(sel, config, retenus)
        (sortie / "rapport.html").write_text(page, encoding="utf-8")
        (sortie / "index.txt").write_text("\n".join(o["id"] for o in retenus) + "\n", encoding="utf-8")
        print(f"Titre du document : {titre}")
        for o in retenus:
            print(f"  {o['verdict']:<13} {o['score']:>2}/12  [{o['public']}] {o['nom']}")
        print(f"Écrit : {sortie / 'rapport.html'} ({len(page)} caractères) et {sortie / 'index.txt'}")
    else:
        if not args.lien or not args.lien.startswith("https://"):
            print("--lien URL_DU_DOC (https://...) est obligatoire pour le mail")
            return 1
        sujet, corps_html, corps_txt = mail(sel, config, retenus, args.lien)
        (sortie / "sujet.txt").write_text(sujet + "\n", encoding="utf-8")
        (sortie / "mail.html").write_text(corps_html, encoding="utf-8")
        (sortie / "mail.txt").write_text(corps_txt, encoding="utf-8")
        print(f"Sujet : {sujet}")
        print(f"Écrit : {sortie / 'mail.html'} et {sortie / 'mail.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
