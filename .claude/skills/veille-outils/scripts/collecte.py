#!/usr/bin/env python3
"""Collecte automatique de la veille outils : Hacker News et flux Product Hunt.

Usage : python3 collecte.py --sortie DOSSIER [--config config.json] [--jours 7]

Écrit DOSSIER/candidats.json et affiche une liste compacte des candidats.
Les sources que ce script ne peut pas lire (GitHub Trending, classement
hebdomadaire Product Hunt, annonces des éditeurs) sont lues par l'agent avec
WebFetch et WebSearch : le script affiche les adresses à consulter.

Une source en échec n'arrête pas la collecte : elle est notée « ok: false »
avec le message d'erreur, et doit apparaître dans la section « Méthode et
limites » de l'édition.
"""

import argparse
import datetime as dt
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ICI = Path(__file__).resolve().parent
HN_API = "https://hn.algolia.com/api/v1/"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
AGENT = "thinkup-veille-outils/1.0"


def lire(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as rep:
        return rep.read()


def hn(chemin, **params):
    return json.loads(lire(HN_API + chemin + "?" + urllib.parse.urlencode(params)))


def collecter_hn(cfg, debut_ts):
    vus, sortie = set(), []

    def ajouter(hit, type_):
        if hit["objectID"] in vus:
            return
        vus.add(hit["objectID"])
        sortie.append({
            "source": "Hacker News",
            "type": type_,
            "titre": hit.get("title") or "",
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "discussion": f"https://news.ycombinator.com/item?id={hit['objectID']}",
            "points": hit.get("points") or 0,
            "commentaires": hit.get("num_comments") or 0,
            "date": dt.datetime.fromtimestamp(hit["created_at_i"], dt.timezone.utc).date().isoformat(),
        })

    rep = hn("search_by_date", tags="show_hn", hitsPerPage=200,
             numericFilters=f"created_at_i>{debut_ts},points>={cfg['show_hn_points_min']}")
    for hit in rep["hits"]:
        ajouter(hit, "Show HN")
    for requete in cfg["requetes"]:
        rep = hn("search", query=requete, tags="story", hitsPerPage=50,
                 numericFilters=f"created_at_i>{debut_ts},points>={cfg['articles_points_min']}")
        # Algolia cherche aussi dans l'URL et le texte : on ne garde que les titres qui portent le mot.
        mot = re.compile(r"\b" + re.escape(requete) + r"\b", re.I)
        for hit in rep["hits"]:
            if mot.search(hit.get("title") or ""):
                ajouter(hit, "article")
    sortie.sort(key=lambda c: -c["points"])
    return sortie


def collecter_product_hunt(url, debut):
    racine = ET.fromstring(lire(url))
    sortie = []
    for e in racine.findall("a:entry", ATOM):
        publie = dt.datetime.fromisoformat(e.find("a:published", ATOM).text)
        if publie.astimezone(dt.timezone.utc) < debut:
            continue
        contenu = e.find("a:content", ATOM)
        accroche = ""
        if contenu is not None and contenu.text:
            premier = re.search(r"<p>(.*?)</p>", contenu.text, re.S)
            if premier:
                accroche = html.unescape(re.sub(r"\s+", " ", premier.group(1))).strip()
        sortie.append({
            "source": "Product Hunt",
            "type": "lancement",
            "titre": e.find("a:title", ATOM).text,
            "accroche": accroche,
            "url": e.find("a:link", ATOM).get("href").split("?")[0],
            "date": publie.date().isoformat(),
        })
    return sortie


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sortie", required=True, type=Path)
    ap.add_argument("--config", type=Path, default=ICI.parent / "config.json")
    ap.add_argument("--jours", type=int)
    args = ap.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    jours = args.jours or config["fenetre_jours"]
    maintenant = dt.datetime.now(dt.timezone.utc)
    debut = maintenant - dt.timedelta(days=jours)
    sources = config["sources"]

    resultat = {
        "genere": maintenant.isoformat(timespec="seconds"),
        "fenetre": {"debut": debut.date().isoformat(), "fin": maintenant.date().isoformat()},
        "sources": {},
        "candidats": [],
    }

    for nom, fonction in (
        ("Hacker News", lambda: collecter_hn(sources["hacker_news"], int(debut.timestamp()))),
        ("Product Hunt (flux)", lambda: collecter_product_hunt(sources["product_hunt_feed"], debut)),
    ):
        try:
            trouves = fonction()
            resultat["sources"][nom] = {"ok": True, "candidats": len(trouves)}
            resultat["candidats"].extend(trouves)
        except Exception as exc:  # une source en panne ne bloque pas la veille
            resultat["sources"][nom] = {"ok": False, "erreur": f"{type(exc).__name__}: {exc}"}

    args.sortie.mkdir(parents=True, exist_ok=True)
    fichier = args.sortie / "candidats.json"
    fichier.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")

    # Semaine ISO complète précédant la date du jour : celle du classement Product Hunt à lire.
    annee, semaine, _ = (maintenant.date() - dt.timedelta(days=7)).isocalendar()

    print(f"Fenêtre : {resultat['fenetre']['debut']} → {resultat['fenetre']['fin']}")
    for nom, etat in resultat["sources"].items():
        print(f"  {nom} : " + (f"{etat['candidats']} candidats" if etat["ok"] else f"ÉCHEC — {etat['erreur']}"))
    print(f"Écrit : {fichier}\n")
    for c in resultat["candidats"]:
        detail = f"{c['points']} pts" if "points" in c else c.get("accroche", "")
        print(f"[{c['source']} · {c['type']}] {c['titre']} | {detail} | {c['url']}")
    print("\nÀ lire avec WebFetch :")
    for url in sources["github_trending"]:
        print(f"  {url}")
    print("  " + sources["product_hunt_hebdo"].format(annee=annee, semaine=semaine))
    print("À chercher avec WebSearch :")
    for requete in sources["recherches_web"]:
        print(f"  {requete}")
    return 0 if any(e["ok"] for e in resultat["sources"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
