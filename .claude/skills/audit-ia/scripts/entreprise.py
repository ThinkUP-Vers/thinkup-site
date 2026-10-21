#!/usr/bin/env python3
"""Vérification des informations officielles d'une entreprise (Sirene, RNE, BODACC).

Sources, toutes publiques et sans clé : API Recherche d'entreprises (data.gouv.fr) et annonces BODACC
(DILA). Rien d'autre n'est interrogé : pas de moteur de recherche, pas de site tiers.

  entreprise.py SIREN [--json sortie.json] [--md sortie.md] [--client dossier.json] [--pappers]
  entreprise.py --chercher "Nom" [--departement 78]     # liste de candidats, à confirmer par Patrick

--pappers ajoute les données de l'API Pappers (service commercial tiers, clé dans PAPPERS_API_KEY, 1 crédit par
entreprise) : option désactivée par défaut, SIREN seul transmis. Réponse non testée sans clé : voir references.
Un SIREN est obligatoire pour la vérification. La recherche par nom envoie le nom à l'API officielle :
elle n'est lancée que sur demande explicite (--chercher), car les dossiers d'audit sont confidentiels.
Code de sortie : 0 si la vérification a abouti, 1 sinon (réseau, SIREN introuvable).
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

API = "https://recherche-entreprises.api.gouv.fr/search"
BODACC = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"
ANNUAIRE = "https://annuaire-entreprises.data.gouv.fr/entreprise/"

# Seules les catégories juridiques les plus courantes sont traduites ; les autres restent en code.
FORMES = {"5710": "SAS", "5720": "SASU", "5498": "EURL", "5499": "SARL", "5599": "SA", "1000": "Entrepreneur individuel"}
TRANCHES = {"00": (0, 0), "01": (1, 2), "02": (3, 5), "03": (6, 9), "11": (10, 19), "12": (20, 49), "21": (50, 99),
            "22": (100, 199), "31": (200, 249), "32": (250, 499), "41": (500, 999), "42": (1000, 1999),
            "51": (2000, 4999), "52": (5000, 9999), "53": (10000, None)}
SOCIETE = re.compile(r"\b(SAS|SASU|SARL|EURL|SCI|SA|HOLDING|GROUPE|FINANCIERE)\b")
DECISIONNAIRES = ("Président", "Gérant", "Directeur Général", "Directeur général")
PROC = ("ouverture", "redressement", "liquidation", "sauvegarde")


class ErreurReseau(Exception):
    pass


def _masque(texte):
    """Retire tout jeton d'API d'un message d'erreur."""
    return re.sub(r"(api_token=)[^&\s)]+", r"\1***", str(texte))


def _get(url, essais=10, pause=2):
    """GET JSON avec réessais : les ruptures de connexion sont fréquentes derrière certains proxys."""
    dernier = None
    for i in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "thinkup-verification/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 402, 403, 404):
                raise ErreurReseau(f"HTTP {e.code} sur {_masque(url)}")
            dernier = e
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError, json.JSONDecodeError) as e:
            dernier = e
        time.sleep(pause)
    raise ErreurReseau(f"{essais} essais sans réponse ({_masque(dernier)})")


def siren_valide(s):
    """Contrôle de Luhn sur 9 chiffres."""
    s = re.sub(r"\s", "", str(s))
    if not re.fullmatch(r"\d{9}", s):
        return False
    total = 0
    for i, c in enumerate(reversed(s)):
        n = int(c) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def est_personne(d):
    """Vraie personne physique : type déclaré, année de naissance présente, nom sans forme sociale.

    L'API déclare parfois une société comme personne physique (constaté le 20/10/2026)."""
    nom = f"{d.get('prenoms') or ''} {d.get('nom') or ''}".upper()
    return d.get("type_dirigeant") == "personne physique" and bool(d.get("annee_de_naissance")) and not SOCIETE.search(nom)


def _norm(t):
    t = unicodedata.normalize("NFD", str(t or "")).encode("ascii", "ignore").decode().upper()
    return re.sub(r"[^A-Z0-9 ]", " ", t)


def chercher(nom, departement=None):
    q = {"q": nom, "per_page": 10}
    if departement:
        q["departement"] = departement
    d = _get(API + "?" + urllib.parse.urlencode(q))
    return [{"siren": r["siren"], "nom": r["nom_complet"], "ville": (r.get("siege") or {}).get("libelle_commune"),
             "departement": (r.get("siege") or {}).get("departement"), "etat": r.get("etat_administratif"),
             "effectif": r.get("tranche_effectif_salarie")} for r in d.get("results", [])]


def bodacc(siren, mois=24):
    depuis = (dt.date.today() - dt.timedelta(days=30 * mois)).isoformat()
    q = {"where": f'registre like "{siren}" and dateparution>="{depuis}"', "order_by": "dateparution desc", "limit": 50,
         "select": "dateparution,familleavis_lib,typeavis_lib,commercant,url_complete,jugement"}
    d = _get(BODACC + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote))
    sortie = []
    for r in d.get("results", []):
        j = r.get("jugement")
        if isinstance(j, str):
            try:
                j = json.loads(j)
            except json.JSONDecodeError:
                j = {"nature": j}
        sortie.append({"date": r.get("dateparution"), "famille": r.get("familleavis_lib"), "type": r.get("typeavis_lib"),
                       "nature": (j or {}).get("nature") if isinstance(j, dict) else None, "url": r.get("url_complete")})
    return sortie


def verifier(siren):
    """Interroge les sources officielles et renvoie la fiche (dict). Lève ErreurReseau."""
    siren = re.sub(r"\s", "", str(siren))
    alertes = []
    if not siren_valide(siren):
        raise ErreurReseau(f"SIREN {siren} invalide (9 chiffres, clé de contrôle Luhn) : vérifier la saisie")
    d = _get(API + "?" + urllib.parse.urlencode({"q": siren, "per_page": 5}))
    r = next((x for x in d.get("results", []) if x.get("siren") == siren), None)
    if not r or not r.get("nom_complet"):
        raise ErreurReseau(f"SIREN {siren} introuvable dans l'API Recherche d'entreprises")
    siege = r.get("siege") or {}
    dirigeants = []
    for x in r.get("dirigeants") or []:
        q = x.get("qualite") or ""
        if "ommissaire" in q:
            continue
        morale = x.get("type_dirigeant") == "personne morale" or not est_personne(x)
        dirigeants.append({"nom": (f"{x.get('prenoms') or ''} {x.get('nom') or ''}".strip().title()
                                   if not x.get("denomination") else x["denomination"]),
                           "qualite": q, "personne_physique": not morale, "siren": x.get("siren"),
                           "annee_naissance": x.get("annee_de_naissance")})
    f = r.get("finances") or {}
    an = int(max(f, key=int)) if f else None
    ca = f[str(an)].get("ca") if an else None
    rn = f[str(an)].get("resultat_net") if an else None
    try:
        annonces = bodacc(siren)
    except ErreurReseau as e:
        annonces = None
        alertes.append(f"BODACC non consulté ({e}) : ne rien conclure sur les procédures collectives")
    fiche = {
        "siren": siren, "interroge_le": dt.date.today().isoformat(), "sources": [API, BODACC, ANNUAIRE + siren],
        "identite": {"nom": r.get("nom_complet"), "forme_code": r.get("nature_juridique"),
                     "forme": FORMES.get(r.get("nature_juridique")), "date_creation": r.get("date_creation"),
                     "etat": r.get("etat_administratif"), "categorie": r.get("categorie_entreprise"),
                     "naf": r.get("activite_principale"), "etablissements_ouverts": r.get("nombre_etablissements_ouverts"),
                     "adresse": siege.get("adresse"), "code_postal": siege.get("code_postal"),
                     "ville": siege.get("libelle_commune"), "diffusion": r.get("statut_diffusion"),
                     "tva": (r.get("tva") or [None])[0]},
        "effectif": {"tranche": r.get("tranche_effectif_salarie"), "annee": r.get("annee_tranche_effectif_salarie")},
        "finances": {"annee": an, "ca": ca, "resultat_net": rn},
        "dirigeants": dirigeants, "bodacc": annonces,
    }
    ident = fiche["identite"]
    if ident["etat"] != "A":
        alertes.append("Entreprise cessée ou non active selon Sirene")
    if ident["diffusion"] not in (None, "O"):
        alertes.append("Diffusion partielle : certaines données (dirigeants, adresse) sont masquées")
    if not dirigeants or not any(x["personne_physique"] and x["qualite"].startswith(DECISIONNAIRES) for x in dirigeants):
        alertes.append("Aucun dirigeant décisionnaire personne physique identifié (société présidente ou donnée absente) : à identifier")
    if not fiche["effectif"]["tranche"] or fiche["effectif"]["tranche"] == "NN":
        alertes.append("Effectif non renseigné (NN) : ne pas en déduire zéro salarié")
    if an is None:
        alertes.append("Comptes non publiés : aucun chiffre d'affaires officiel")
    elif an < dt.date.today().year - 2:
        alertes.append(f"Derniers comptes publiés : exercice {an} (ancien)")
    if rn is not None and rn < 0:
        alertes.append(f"Résultat net négatif sur l'exercice {an}")
    if ident["date_creation"] and (dt.date.today() - dt.date.fromisoformat(ident["date_creation"])).days < 730:
        alertes.append("Entreprise de moins de deux ans")
    proc = [a for a in (annonces or []) if a["famille"] == "Procédures collectives"]
    fiche["procedure_collective"] = None
    if proc:
        derniere = proc[0]
        nature = (derniere.get("nature") or "").lower()
        close = "clôture" in nature or "cloture" in nature
        fiche["procedure_collective"] = {"date": derniere["date"], "nature": derniere.get("nature"), "url": derniere.get("url"),
                                         "ouverte": (not close) and any(p in nature for p in PROC) or not nature}
        alertes.append(("PROCÉDURE COLLECTIVE EN COURS PROBABLE" if fiche["procedure_collective"]["ouverte"]
                        else "Procédure collective passée, clôturée") +
                       f" : {derniere.get('nature') or derniere.get('type')} ({derniere['date']}), à vérifier sur {derniere.get('url')}")
    fiche["alertes"] = alertes
    return fiche


def pappers(siren):
    """Données de l'API Pappers (option). Lève ErreurReseau si la clé manque ou si l'appel échoue.

    Champs lus avec prudence (.get partout) : le format n'a pas été vérifié sans clé le 21/10/2026."""
    cle = os.environ.get("PAPPERS_API_KEY")
    if not cle:
        raise ErreurReseau("PAPPERS_API_KEY absente : créer une clé sur pappers.fr/api et la déclarer comme variable d'environnement")
    d = _get("https://api.pappers.fr/v2/entreprise?" + urllib.parse.urlencode({"api_token": cle, "siren": siren}), essais=3)
    exercices = []
    for x in d.get("finances") or []:
        if isinstance(x, dict):
            exercices.append({k: x.get(k) for k in ("annee", "date_cloture_exercice", "chiffre_affaires", "resultat", "effectif",
                                                    "excedent_brut_exploitation", "fonds_propres", "endettement") if x.get(k) is not None})
    exercices.sort(key=lambda x: x.get("annee") or 0, reverse=True)
    return {"exercices": exercices[:5], "capital": d.get("capital"), "effectif": d.get("effectif") or d.get("tranche_effectif"),
            "procedure_en_cours": d.get("procedure_collective_en_cours"), "procedure_existe": d.get("procedure_collective_existe"),
            "entreprise_cessee": d.get("entreprise_cessee"),
            "beneficiaires_effectifs": len(d.get("beneficiaires_effectifs") or []) or None,
            "cles_recues": sorted(d.keys())[:40]}


def ajouter_pappers(fiche):
    """Greffe les données Pappers sur la fiche et recoupe avec les registres officiels."""
    try:
        p = pappers(fiche["siren"])
    except ErreurReseau as e:
        fiche["pappers"] = None
        fiche["alertes"].append(f"Pappers non consulté ({_masque(e)})")
        return
    fiche["pappers"] = p
    fiche["sources"].append("https://api.pappers.fr/v2/entreprise")
    off = fiche["finances"]
    ex = next((x for x in p["exercices"] if x.get("annee") == off["annee"]), None)
    if ex and off["ca"] and ex.get("chiffre_affaires") and abs(ex["chiffre_affaires"] - off["ca"]) > 0.02 * off["ca"]:
        fiche["alertes"].append(f"Chiffre d'affaires {off['annee']} différent : {off['ca']} (Sirene) contre {ex['chiffre_affaires']} (Pappers)")
    pc = fiche.get("procedure_collective")
    if p["procedure_en_cours"] is True and not (pc and pc.get("ouverte")):
        fiche["procedure_collective"] = {"date": None, "nature": "signalée en cours par Pappers", "url": None, "ouverte": True}
        fiche["alertes"].append("PROCÉDURE COLLECTIVE EN COURS PROBABLE : signalée par Pappers, absente du BODACC des 24 derniers mois")
    elif p["procedure_en_cours"] is False and pc and pc.get("ouverte"):
        fiche["alertes"].append("BODACC signale une procédure ouverte que Pappers donne comme terminée : vérifier au greffe, ne pas lever le blocage sur cette seule base")
    if p["entreprise_cessee"] is True and fiche["identite"]["etat"] == "A":
        fiche["alertes"].append("Pappers donne l'entreprise comme cessée alors que Sirene la donne active")


def comparer(client, fiche):
    """Écarts entre ce que le client a déclaré (bloc client du dossier) et le registre. Liste d'alertes."""
    ecarts = []
    ident = fiche["identite"]
    a, b = set(_norm(client.get("raison_sociale")).split()), set(_norm(ident["nom"]).split())
    mots_vides = {"SAS", "SARL", "SA", "SASU", "EURL", "SCI", "DE", "LA", "LE", "ET", "DES", "DU", "GROUPE"}
    a, b = a - mots_vides, b - mots_vides
    if a and b and len(a & b) / len(a | b) < 0.4:
        ecarts.append(f"Raison sociale déclarée « {client.get('raison_sociale')} » ≠ registre « {ident['nom']} »")
    fj = _norm(client.get("forme_juridique")).strip()
    if fj and ident["forme"] and ident["forme"].upper() not in fj.replace(" ", "") and ident["forme"].upper() not in fj:
        ecarts.append(f"Forme juridique déclarée « {client.get('forme_juridique')} » ≠ registre « {ident['forme']} »")
    adr = client.get("adresse") or ""
    if adr and ident["code_postal"] and ident["code_postal"] not in adr:
        ecarts.append(f"Adresse déclarée sans le code postal du siège ({ident['code_postal']} {ident['ville']}) : autre établissement ?")
    eff, tr = client.get("effectif"), TRANCHES.get(fiche["effectif"]["tranche"])
    if isinstance(eff, (int, float)) and tr and not (tr[0] * 0.5 <= eff <= (tr[1] * 1.5 if tr[1] else 10 ** 9)):
        ecarts.append(f"Effectif déclaré {eff} hors de la tranche officielle {tr[0]}-{tr[1]} (année {fiche['effectif']['annee']})")
    return ecarts


def _eur(x):
    return "non publié" if x is None else f"{x:,}".replace(",", " ") + " €"


def en_markdown(fiche, ecarts=None):
    i, e, f = fiche["identite"], fiche["effectif"], fiche["finances"]
    tr = TRANCHES.get(e["tranche"])
    L = [f"# Vérification officielle — {i['nom']} (SIREN {fiche['siren']})", "",
         f"Interrogé le {fiche['interroge_le']} · sources : Recherche d'entreprises (Sirene, RNE), BODACC. "
         "Données déclaratives : effectif par tranche et comptes parfois anciens.", ""]
    if fiche["alertes"] or ecarts:
        L.append("## Alertes")
        L += [f"- {x}" for x in fiche["alertes"]] + [f"- Écart client : {x}" for x in ecarts or []]
        L.append("")
    L += ["## Identité",
          f"- Forme juridique : {i['forme'] or 'code ' + str(i['forme_code'])} · création {i['date_creation']} · état {i['etat']} "
          f"· catégorie {i['categorie']}",
          f"- Siège : {i['adresse']} · NAF {i['naf']} · {i['etablissements_ouverts']} établissement(s) ouvert(s)",
          f"- TVA intracommunautaire : {i['tva'] or 'non renseignée'}",
          f"- Effectif : {'tranche ' + str(tr[0]) + '-' + str(tr[1]) if tr else 'non renseigné'} (année {e['annee']})",
          f"- Dernier exercice publié ({f['annee']}) : chiffre d'affaires {_eur(f['ca'])}, résultat net {_eur(f['resultat_net'])}", "",
          "## Dirigeants"]
    L += [f"- {x['nom']} — {x['qualite']}" + ("" if x["personne_physique"] else f" (société{' SIREN ' + x['siren'] if x.get('siren') else ''})")
          for x in fiche["dirigeants"]] or ["- aucun renseigné"]
    pp = fiche.get("pappers")
    if pp:
        L += ["", "## Pappers (service commercial tiers, option)"]
        for x in pp["exercices"]:
            L.append("- " + " · ".join(f"{k} {v}" for k, v in x.items()))
        if pp["capital"] is not None:
            L.append(f"- Capital : {pp['capital']}")
        if pp["beneficiaires_effectifs"]:
            L.append(f"- Bénéficiaires effectifs déclarés : {pp['beneficiaires_effectifs']}")
        if not pp["exercices"]:
            L.append("- aucun exercice renvoyé (champs reçus : " + ", ".join(pp["cles_recues"]) + ")")
    L += ["", "## BODACC (24 mois)"]
    if fiche["bodacc"] is None:
        L.append("- non consulté")
    else:
        sig = [a for a in fiche["bodacc"] if a["famille"] != "Dépôts des comptes"]
        L += [f"- {a['date']} · {a['famille']} · {a.get('nature') or a['type']} · {a['url']}" for a in sig] or ["- aucune annonce hors dépôts de comptes"]
    return "\n".join(L) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("siren", nargs="?")
    p.add_argument("--chercher")
    p.add_argument("--departement")
    p.add_argument("--json")
    p.add_argument("--md")
    p.add_argument("--pappers", action="store_true", help="ajoute l'API Pappers (clé PAPPERS_API_KEY, 1 crédit)")
    p.add_argument("--client", help="dossier.json d'un audit : compare le bloc client au registre")
    a = p.parse_args()
    try:
        if a.chercher:
            for c in chercher(a.chercher, a.departement):
                print(f"{c['siren']}  {c['nom']}  {c['ville']} ({c['departement']})  état {c['etat']}  effectif {c['effectif']}")
            return 0
        if not a.siren:
            p.error("SIREN requis (ou --chercher)")
        fiche = verifier(a.siren)
        if a.pappers:
            ajouter_pappers(fiche)
    except ErreurReseau as e:
        print(f"ERREUR  {_masque(e)}", file=sys.stderr)
        return 1
    ecarts = []
    if a.client:
        ecarts = comparer(json.load(open(a.client, encoding="utf-8")).get("client") or {}, fiche)
    if a.json:
        json.dump({**fiche, "ecarts_client": ecarts}, open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    md = en_markdown(fiche, ecarts)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md)
    print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
