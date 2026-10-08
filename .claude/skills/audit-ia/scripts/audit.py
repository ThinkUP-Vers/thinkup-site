#!/usr/bin/env python3
"""audit-ia : calculs, contrôles et mise en forme des livrables d'un audit.

Aucun chiffre des livrables ne se calcule à la main. Le business case et le
devis sont calculés ici à partir de dossier.json ; le texte des livrables les
appelle par des balises {{...}} (voir references/dossier-json.md).

  audit.py init [racine] --client "Nom" [--date AAAA-MM-JJ]
  audit.py calculer <dossier>
  audit.py verifier <dossier> [--etape extraction|redaction|final]
  audit.py construire <dossier> [--pdf]

Code de sortie : 0 si aucune erreur, 1 sinon. Les alertes n'empêchent rien
mais doivent être lues.
"""
import argparse
import base64
import datetime as dt
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

ICI = Path(__file__).resolve().parent
SKILL = ICI.parent
ASSETS = SKILL / "assets"
SCENARIOS = ("prudent", "central")
NBSP, NNBSP = "\u00a0", "\u202f"

# Fichiers d'un dossier d'audit
CR, SOL = "01-compte-rendu.md", "02-dossier-solution.md"

# Ce qui ne doit jamais apparaître dans un document remis au prospect.
INTERDITS_CLIENT = [
    (r"\bTJM\b", "taux journalier interne"),
    (r"\bma marge\b|marge (interne|think)", "marge de Think'UP"),
    (r"co[uû]t (jour )?freelance", "coût freelance"),
    (r"rentabilit[ée] interne", "rentabilité interne"),
    (r"\[[ÀA] COMPL[ÉE]TER\]|\bTODO\b|\bXXX\b|\?\?\?", "marqueur de brouillon"),
    (r"\{\{|\}\}", "balise non résolue"),
    (r"dossier de solution|document interne", "renvoi au dossier interne"),
]

# Tournures qui trahissent un texte généré : alerte seulement.
SLOP = [
    "il est important de noter", "il convient de noter", "dans un monde où",
    "à l'ère de", "en somme", "n'hésitez pas", "plongeons", "véritable levier",
    "révolutionner", "game changer", "booster", "incontournable", "sans plus attendre",
    "force est de constater", "au cœur de", "pierre angulaire", "en définitive",
    "un atout majeur", "tirer parti de tout le potentiel", "transformer en profondeur",
]

ID_RE = re.compile(r"\b([PSLHQ])(\d{1,3})\b(?!-)")  # (?!-) : pas « L441-10 » (Code de commerce)
BALISE_RE = re.compile(r"\{\{\s*([A-Za-z0-9_.:\-]+)\s*\}\}")
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


class ErreurDonnees(Exception):
    pass


class Rapport:
    def __init__(self):
        self.erreurs, self.alertes = [], []

    def erreur(self, msg):
        self.erreurs.append(msg)

    def alerte(self, msg):
        self.alertes.append(msg)

    def afficher(self, titre="Contrôle"):
        print(f"\n== {titre} : {len(self.erreurs)} erreur(s), {len(self.alertes)} alerte(s)")
        for m in self.erreurs:
            print(f"  ERREUR  {m}")
        for m in self.alertes:
            print(f"  alerte  {m}")
        return 1 if self.erreurs else 0


# ── Formats français ─────────────────────────────────────────────────────

def _milliers(n):
    return f"{n:,}".replace(",", NNBSP)


def euros(x, arrondi=None):
    if x is None:
        return "n.c."
    if arrondi:
        x = round(x / arrondi) * arrondi
    signe = "−" if x < 0 else ""
    x = abs(x)
    if abs(x - round(x)) < 0.005:
        s = _milliers(int(round(x)))
    else:
        entier, dec = f"{x:.2f}".split(".")
        s = _milliers(int(entier)) + "," + dec
    return f"{signe}{s}{NBSP}€"


def pourcent(x):
    if x is None:
        return "n.s."
    v = round(x * 100)
    return f"{'+' if v >= 0 else '−'}{abs(v)}{NBSP}%"


def heures(x):
    return "n.c." if x is None else f"{_milliers(int(round(x)))}{NBSP}h"


def retour(m):
    if m is None:
        return "non atteint"
    if m > 36:
        return "au-delà de 36 mois"
    if m < 1:
        return "moins d'un mois"
    return f"{math.ceil(m)} mois"


def date_fr(iso):
    try:
        d = dt.date.fromisoformat(str(iso))
    except ValueError:
        return str(iso)
    jour = "1er" if d.day == 1 else str(d.day)
    return f"{jour} {MOIS[d.month - 1]} {d.year}"


def nombre(x):
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, int):
        return _milliers(x)
    return str(x).replace(".", ",")


def cellule(x):
    return str(x if x is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def tableau(entetes, lignes):
    if not lignes:
        return "_Aucun élément._"
    out = ["| " + " | ".join(entetes) + " |", "|" + "|".join("---" for _ in entetes) + "|"]
    out += ["| " + " | ".join(cellule(c) for c in l) + " |" for l in lignes]
    return "\n".join(out)


def slug(texte):
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40] or "client"


# ── Chargement ───────────────────────────────────────────────────────────

def sortir(msg):
    print(f"ERREUR  {msg}", file=sys.stderr)
    sys.exit(1)


def charger(dossier):
    f = Path(dossier) / "dossier.json"
    if not f.exists():
        sortir(f"{f} introuvable")
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sortir(f"dossier.json invalide : {e}")


def emetteur():
    return json.loads((ASSETS / "emetteur.json").read_text(encoding="utf-8"))


def tarifs():
    """Tarifs internes : jamais versionnés (dépôt public)."""
    brut = os.environ.get("THINKUP_TARIFS")
    if brut:
        p = Path(brut)
        return json.loads(p.read_text(encoding="utf-8") if p.exists() else brut)
    f = SKILL / "tarifs.local.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def racine_depot():
    for p in [SKILL, *SKILL.parents]:
        if (p / "cgv.html").exists():
            return p
    return None


def par_id(liste):
    return {x["id"]: x for x in liste or [] if isinstance(x, dict) and "id" in x}


# ── Calculs ──────────────────────────────────────────────────────────────

def valeur(x, scen, hyps, ctx, defaut=None):
    """Nombre, {"prudent": a, "central": b}, ou référence "H3" à une hypothèse."""
    if x is None:
        if defaut is None:
            raise ErreurDonnees(f"{ctx} : valeur manquante")
        return float(defaut)
    if isinstance(x, str):
        h = hyps.get(x)
        if h is None:
            raise ErreurDonnees(f"{ctx} : hypothèse {x} inconnue")
        x = h.get("valeur")
    if isinstance(x, dict):
        if scen not in x:
            raise ErreurDonnees(f"{ctx} : scénario « {scen} » manquant")
        x = x[scen]
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ErreurDonnees(f"{ctx} : valeur numérique attendue, reçu {x!r}")
    return float(x)


def calc_devis(d):
    dv = d.get("devis") or {}
    em = emetteur()
    lots = []
    for l in dv.get("lots", []):
        try:
            montant = round(float(l.get("quantite", 1)) * float(l["prix_unitaire"]), 2)
        except (KeyError, TypeError, ValueError):
            raise ErreurDonnees(f"lot {l.get('id', '?')} : quantite × prix_unitaire impossible")
        lots.append({"id": l["id"], "montant": montant, "option": bool(l.get("option")),
                     "solutions": l.get("solutions") or []})
    total = round(sum(l["montant"] for l in lots if not l["option"]), 2)
    options = round(sum(l["montant"] for l in lots if l["option"]), 2)

    plan = dv.get("echeancier") or [
        {"libelle": "Acompte à la commande", "pourcentage": em["acompte_pct"]},
        {"libelle": "Solde à la livraison des livrables", "pourcentage": 100 - em["acompte_pct"]},
    ]
    ech, reste = [], total
    for i, e in enumerate(plan):
        m = reste if i == len(plan) - 1 else round(total * e["pourcentage"] / 100, 2)
        reste = round(reste - m, 2)
        ech.append({"libelle": e["libelle"], "pourcentage": e["pourcentage"], "montant": m})

    emission = validite = None
    if dv.get("date_emission"):
        emission = dt.date.fromisoformat(dv["date_emission"])
        validite = emission + dt.timedelta(days=int(dv.get("validite_jours", em["validite_jours"])))
    tiers = dv.get("budget_tiers") or []
    return {
        "lots": lots, "total": total, "options": options, "echeancier": ech,
        "date_emission": emission.isoformat() if emission else None,
        "date_validite": validite.isoformat() if validite else None,
        "tiers_min": sum(t["min"] for t in tiers if not t.get("option")),
        "tiers_max": sum(t["max"] for t in tiers if not t.get("option")),
    }


def part_tiers(t, scen):
    return t["max"] if scen == "prudent" else (t["min"] + t["max"]) / 2


def indicateurs(gain, gain_an1, recurrent, mise, interne, h_annuelles, h_liberees):
    inv = mise + interne
    roi12 = (gain_an1 - recurrent - inv) / (inv + recurrent) if inv + recurrent > 0 else None
    roi36 = ((gain_an1 + 2 * gain - 3 * recurrent - inv) / (inv + 3 * recurrent)
             if inv + 3 * recurrent > 0 else None)
    m1, m2 = (gain_an1 - recurrent) / 12, (gain - recurrent) / 12
    if inv <= 0:
        mois = 0.0
    elif m1 > 0 and 12 * m1 >= inv:
        mois = inv / m1
    elif m2 > 0:
        mois = 12 + (inv - 12 * m1) / m2
    else:
        mois = None
    return {"heures_annuelles": h_annuelles, "heures_liberees": h_liberees, "gain_annuel": gain,
            "gain_an1": gain_an1, "mise_en_place": mise, "recurrent_annuel": recurrent,
            "cout_interne": interne, "roi_12": roi12, "roi_36": roi36, "retour_mois": mois}


def calc_bc(d, dev):
    hyps = par_id(d.get("hypotheses"))
    tiers = (d.get("devis") or {}).get("budget_tiers") or []
    res = {}
    for s in d.get("solutions", []):
        bc = s.get("business_case")
        if not bc or s.get("statut") == "écartée":
            continue
        sid, res[sid] = s["id"], {}
        for scen in SCENARIOS:
            ctx = f"{sid}.business_case"
            v = lambda k, defaut=None: valeur(bc.get(k), scen, hyps, f"{ctx}.{k}", defaut)
            if bc.get("heures_annuelles") is not None:
                h = v("heures_annuelles")
            else:
                vol = bc.get("volume") or {}
                h = 1.0
                for k in ("duree_h", "frequence_an", "personnes"):
                    h *= valeur(vol.get(k), scen, hyps, f"{ctx}.volume.{k}")
            h_lib = h * v("taux_automatisation") * (1 - v("taux_supervision"))
            gain = h_lib * v("cout_horaire") + v("gains_autres_annuels", 0)
            recurrent = sum(float(o.get("cout_mensuel") or 0) * float(o.get("quantite") or 1) * 12
                            for o in s.get("outils", [])) + v("maintenance_annuelle", 0)
            mise = sum(l["montant"] / len(l["solutions"]) for l in dev["lots"] if sid in l["solutions"])
            mise += sum(part_tiers(t, scen) / len(t["solutions"]) for t in tiers
                        if sid in (t.get("solutions") or []))
            res[sid][scen] = indicateurs(gain, gain * v("adoption_an1"), recurrent, mise,
                                         v("cout_interne_client", 0), h, h_lib)
    retenues = [s["id"] for s in d.get("solutions", []) if s.get("statut") == "retenue" and s["id"] in res]
    if retenues:
        res["global"] = {}
        for scen in SCENARIOS:
            somme = lambda k: sum(res[i][scen][k] for i in retenues)
            mise = dev["total"] + sum(part_tiers(t, scen) for t in tiers if not t.get("option"))
            res["global"][scen] = indicateurs(somme("gain_annuel"), somme("gain_an1"),
                                              somme("recurrent_annuel"), mise, somme("cout_interne"),
                                              somme("heures_annuelles"), somme("heures_liberees"))
    return res


def calc_rentabilite(d, dev):
    t = tarifs() or {}
    tjm = t.get("tjm_thinkup")
    lignes = []
    montants = {l["id"]: l["montant"] for l in dev["lots"]}
    for l in (d.get("devis") or {}).get("lots", []):
        ci = l.get("chiffrage_interne")
        if not ci:
            continue
        j = float(ci.get("jours_thinkup") or 0)
        cout_free = float(ci.get("jours_freelance") or 0) * float(ci.get("cout_jour_freelance") or 0)
        net = montants[l["id"]] - cout_free
        effectif = net / j if j else None
        lignes.append({"lot": l["id"], "montant": montants[l["id"]], "jours_thinkup": j,
                       "cout_freelance": cout_free, "tjm_effectif": effectif, "tjm_cible": tjm,
                       "ecart": (effectif - tjm) * j if (effectif is not None and tjm) else None})
    return lignes


def calculer(d):
    dev = calc_devis(d)
    return {"devis": dev, "bc": calc_bc(d, dev), "rentabilite": calc_rentabilite(d, dev)}


# ── Balises et tableaux ──────────────────────────────────────────────────

FORMATS_BC = {"heures_annuelles": heures, "heures_liberees": heures,
              "gain_annuel": lambda x: euros(x, 100), "gain_an1": lambda x: euros(x, 100),
              "mise_en_place": euros, "recurrent_annuel": lambda x: euros(x, 10),
              "cout_interne": lambda x: euros(x, 10), "roi_12": pourcent, "roi_36": pourcent,
              "retour_mois": retour}


def fmt_hyp(h):
    v, u = h.get("valeur"), h.get("unite", "")
    if isinstance(v, dict):
        return " / ".join(f"{nombre(v[s])}{NBSP}{u} ({s})".strip() for s in SCENARIOS if s in v)
    return f"{nombre(v)}{NBSP}{u}".strip() if v is not None else ""


def contexte(d, calc):
    ctx = {}
    for bloc in ("client", "meta"):
        for k, v in (d.get(bloc) or {}).items():
            if isinstance(v, bool) or not isinstance(v, (str, int, float)):
                continue
            if isinstance(v, str):
                ctx[f"{bloc}.{k}"] = date_fr(v) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else v
            else:
                ctx[f"{bloc}.{k}"] = nombre(v)
    dv, dev = d.get("devis") or {}, calc["devis"]
    em = emetteur()
    ctx.update({
        "devis.numero": dv.get("numero", ""), "devis.objet": dv.get("objet", ""),
        "devis.date_emission": date_fr(dev["date_emission"]) if dev["date_emission"] else "",
        "devis.date_validite": date_fr(dev["date_validite"]) if dev["date_validite"] else "",
        "devis.validite_jours": str(dv.get("validite_jours", em["validite_jours"])),
        "devis.total": euros(dev["total"]), "devis.total_options": euros(dev["options"]),
        "devis.acompte": euros(dev["echeancier"][0]["montant"]) if dev["echeancier"] else "",
        "devis.budget_tiers_min": euros(dev["tiers_min"], 100),
        "devis.budget_tiers_max": euros(dev["tiers_max"], 100),
        "nb.problemes": str(len(d.get("problemes", []))),
        "nb.solutions_retenues": str(sum(1 for s in d.get("solutions", []) if s.get("statut") == "retenue")),
    })
    for s in d.get("solutions", []):
        ctx[f"sol.{s['id']}.titre"] = s.get("titre", "")
    for p in d.get("problemes", []):
        ctx[f"pb.{p['id']}.titre"] = p.get("titre", "")
    for h in d.get("hypotheses", []):
        ctx[f"hyp.{h['id']}.valeur"] = fmt_hyp(h)
    for cle, par_scen in calc["bc"].items():
        for scen, vals in par_scen.items():
            for k, f in FORMATS_BC.items():
                ctx[f"bc.{cle}.{k}.{scen}"] = f(vals[k])
    return ctx


def categorie(pr):
    i, e, r = pr.get("impact", 0), pr.get("effort", 0), pr.get("risque", 0)
    if i >= 4 and e <= 2:
        c = "Gain rapide"
    elif i >= 4:
        c = "Chantier structurant"
    elif e <= 2:
        c = "Amélioration opportuniste"
    else:
        c = "À reconsidérer"
    return c + (" — cadrage du risque d'abord" if r >= 4 else "")


ORDRE_CAT = ["Gain rapide", "Chantier structurant", "Amélioration opportuniste", "À reconsidérer"]


def tableaux(d, calc):
    P, S = d.get("problemes", []), d.get("solutions", [])
    lots_par_sol = {}
    for l in (d.get("devis") or {}).get("lots", []):
        for sid in l.get("solutions") or []:
            lots_par_sol.setdefault(sid, []).append(l["id"])
    sol_par_pb = {}
    for s in S:
        for pid in s.get("problemes", []):
            sol_par_pb.setdefault(pid, []).append(s)
    T = {}
    T["problemes"] = tableau(["Réf.", "Constat", "Processus", "Zone", "Certitude"],
                             [[p["id"], p.get("titre"), p.get("processus"), p.get("zone"), p.get("certitude")] for p in P])

    def cle_matrice(p):
        cat = categorie(p.get("priorisation") or {})
        return (ORDRE_CAT.index(cat.split(" — ")[0]), -(p.get("priorisation") or {}).get("impact", 0))
    T["matrice"] = tableau(["Réf.", "Constat", "Impact", "Effort", "Risque", "Lecture"],
                           [[p["id"], p.get("titre"), *[(p.get("priorisation") or {}).get(k, "") for k in ("impact", "effort", "risque")],
                             categorie(p.get("priorisation") or {})] for p in sorted(P, key=cle_matrice)])
    T["solutions"] = tableau(["Réf.", "Recommandation", "Répond à", "Statut"],
                             [[s["id"], s.get("titre"), ", ".join(s.get("problemes", [])), s.get("statut")] for s in S])
    trac = []
    for p in P:
        for s in sol_par_pb.get(p["id"], []) or [None]:
            if s is None:
                trac.append([f"{p['id']} {p.get('titre')}", p.get("hors_perimetre") or "AUCUNE SOLUTION", "—", "—"])
            else:
                trac.append([f"{p['id']} {p.get('titre')}", f"{s['id']} {s.get('titre')}",
                             ", ".join(lots_par_sol.get(s["id"], [])) or "—", s.get("statut")])
    T["tracabilite"] = tableau(["Constat", "Solution", "Lot(s) du devis", "Statut"], trac)

    bc_lignes = []
    titres = {s["id"]: s.get("titre") + (" (option)" if s.get("statut") == "option" else "") for s in S}
    for cle in [*(k for k in calc["bc"] if k != "global"), "global"]:
        if cle not in calc["bc"]:
            continue
        nom = "Ensemble des recommandations retenues" if cle == "global" else f"{cle} {titres.get(cle, '')}"
        for scen in SCENARIOS:
            v = calc["bc"][cle][scen]
            bc_lignes.append([nom if scen == "prudent" else "", scen, heures(v["heures_liberees"]),
                              euros(v["gain_annuel"], 100), euros(v["mise_en_place"]),
                              euros(v["recurrent_annuel"], 10), pourcent(v["roi_12"]),
                              pourcent(v["roi_36"]), retour(v["retour_mois"])])
    T["business_case"] = tableau(["Recommandation", "Scénario", "Heures libérées / an", "Gain annuel",
                                  "Investissement", "Coûts annuels", "ROI 12 mois", "ROI 36 mois",
                                  "Retour"], bc_lignes)
    T["hypotheses"] = tableau(["Réf.", "Hypothèse", "Valeur", "Origine", "À valider"],
                              [[h["id"], h.get("texte"), fmt_hyp(h), h.get("origine"),
                                "oui" if h.get("a_valider") else "non"] for h in d.get("hypotheses", [])])
    Q = d.get("questions_ouvertes", [])
    T["questions"] = tableau(["Réf.", "Question", "Pourquoi c'est utile"],
                             [[q["id"], q.get("question"), q.get("impact")] for q in Q
                              if q.get("destinataire", "client") == "client" and not q.get("reponse")])
    T["questions_internes"] = tableau(["Réf.", "Question", "Pour", "Bloquante", "Réponse"],
                                      [[q["id"], q.get("question"), q.get("destinataire", "client"),
                                        "oui" if q.get("bloquante") else "non", q.get("reponse") or "—"] for q in Q])
    outils = []
    for s in S:
        for o in s.get("outils", []):
            cout = (f"{euros(float(o['cout_mensuel']))} / {o.get('unite', 'mois')} × {nombre(o.get('quantite', 1))}"
                    if o.get("cout_mensuel") else o.get("note", "inclus"))
            outils.append([s["id"], o.get("nom"), o.get("usage"), cout, o.get("hebergement"),
                           date_fr(o["verifie_le"]) if o.get("verifie_le") else "NON VÉRIFIÉ", o.get("source")])
    T["outils"] = tableau(["Sol.", "Outil", "Usage", "Coût", "Hébergement des données", "Vérifié le", "Source"], outils)
    T["rentabilite"] = tableau(["Lot", "Montant", "Jours Think'UP", "Coût freelance", "TJM effectif", "Écart vs TJM cible"],
                               [[r["lot"], euros(r["montant"]), nombre(r["jours_thinkup"]), euros(r["cout_freelance"]),
                                 euros(r["tjm_effectif"]) if r["tjm_effectif"] is not None else "—",
                                 euros(r["ecart"]) if r["ecart"] is not None else "TJM cible non renseigné"]
                                for r in calc["rentabilite"]])
    return T


def interpoler(texte, ctx, T, rapport, nom):
    def table(m):
        cle = m.group(1)
        if cle not in T:
            rapport.erreur(f"{nom} : tableau inconnu {{{{TABLEAU:{cle}}}}}")
            return m.group(0)
        return "\n" + T[cle] + "\n"
    texte = re.sub(r"\{\{\s*TABLEAU:([a-z_]+)\s*\}\}", table, texte)

    def balise(m):
        cle = m.group(1)
        if cle not in ctx:
            rapport.erreur(f"{nom} : balise inconnue ou non calculable {{{{{cle}}}}}")
            return m.group(0)
        return ctx[cle]
    return BALISE_RE.sub(balise, texte)


def sans_commentaires(texte):
    return re.sub(r"<!--.*?-->", "", texte, flags=re.S)


# ── Devis (généré, jamais rédigé à la main) ──────────────────────────────

def devis_md(d, calc):
    em, c, dv, dev = emetteur(), d.get("client") or {}, d.get("devis") or {}, calc["devis"]
    S, P = par_id(d.get("solutions")), par_id(d.get("problemes"))
    decideur = next((i for i in c.get("interlocuteurs", []) if i.get("role") == "décideur"),
                    (c.get("interlocuteurs") or [{}])[0])
    e = html.escape
    client_lignes = [f"<strong>{e(c.get('raison_sociale', ''))}</strong>"]
    client_lignes += [e(x) for x in (c.get("forme_juridique"), c.get("adresse")) if x]
    client_lignes.append(f"SIREN {e(c['siren'])}" if c.get("siren") else "SIREN : à compléter")
    if decideur.get("nom"):
        client_lignes.append(f"À l'attention de {e(decideur['nom'])}"
                             + (f", {e(decideur['fonction'])}" if decideur.get("fonction") else ""))
    out = [
        f'<div class="entete-devis"><p class="titre-devis">Devis n° {e(dv.get("numero", ""))}</p>'
        f'<p>Émis le {date_fr(dev["date_emission"]) if dev["date_emission"] else "—"} · '
        f'valable jusqu\'au {date_fr(dev["date_validite"]) if dev["date_validite"] else "—"}</p></div>',
        "",
        '<div class="parties"><div class="partie"><p class="etiquette">Prestataire</p><p>'
        f'<strong>{e(em["nom_commercial"])}</strong> — {e(em["representant"])}<br>{e(em["forme"])}<br>'
        f'{e(em["adresse"])}<br>SIRET {e(em["siret"])}<br>{e(em["email"])} · {e(em["telephone"])}</p></div>'
        '<div class="partie"><p class="etiquette">Client</p><p>' + "<br>".join(client_lignes) + "</p></div></div>",
        "",
        "## Objet", "", dv.get("objet", ""), "",
    ]
    if dv.get("introduction"):
        out += [dv["introduction"], ""]

    lots_src = par_id(dv.get("lots"))
    montant = {l["id"]: l["montant"] for l in dev["lots"]}
    fermes = [l for l in dv.get("lots", []) if not l.get("option")]
    opts = [l for l in dv.get("lots", []) if l.get("option")]

    def ligne(l):
        q, u = l.get("quantite", 1), l.get("unite", "forfait")
        qte = "forfait" if u == "forfait" and q == 1 else f"{nombre(q)} {u}"
        return [l["id"], l.get("titre"), l.get("duree", ""), qte, euros(montant[l["id"]])]
    out += ["## Prestations", "", tableau(["Lot", "Désignation", "Durée indicative", "Quantité", "Montant net"],
                                          [ligne(l) for l in fermes] + [["", "**Total net**", "", "", f"**{euros(dev['total'])}**"]]),
            "", em["mention_tva"] + ".", ""]
    if opts:
        out += ["### Options, non comprises dans le total", "",
                tableau(["Lot", "Désignation", "Durée indicative", "Quantité", "Montant net"], [ligne(l) for l in opts]), ""]

    out += ["## Détail des prestations", ""]
    for l in fermes + opts:
        out += [f"### {l['id']} — {l.get('titre', '')}{' (option)' if l.get('option') else ''}", "", l.get("description", ""), ""]
        if l.get("livrables"):
            out += ["Livrables :", ""] + [f"- {x}" for x in l["livrables"]] + [""]
        sols = [S[s] for s in l.get("solutions") or [] if s in S]
        if sols:
            pbs = sorted({p for s in sols for p in s.get("problemes", []) if p in P}, key=lambda x: int(x[1:]))
            out += [f"Répond aux constats {', '.join(f'{p} ({P[p].get('titre')})' for p in pbs)} du compte rendu d'audit.", ""]

    tiers = dv.get("budget_tiers") or []
    if tiers:
        out += ["## Budget complémentaire à prévoir, hors devis", "",
                "Ces montants ne sont pas facturés par Think'UP. Ils correspondent aux prestations contractées "
                "directement par vos soins auprès des prestataires sélectionnés ; ce sont des fourchettes "
                "indicatives, à confirmer par leurs propres devis.", "",
                tableau(["Poste", "Fourchette indicative", "Pour"],
                        [[t["libelle"], f"{euros(t['min'], 100)} à {euros(t['max'], 100)}",
                          ", ".join(t.get("solutions") or []) or "ensemble du projet"] for t in tiers]), ""]
    abonnements = [[o.get("nom"), o.get("usage"),
                    f"{euros(float(o['cout_mensuel']))} / {o.get('unite', 'mois')} × {nombre(o.get('quantite', 1))}",
                    date_fr(o["verifie_le"]) if o.get("verifie_le") else ""]
                   for s in d.get("solutions", []) if s.get("statut") in ("retenue", "option")
                   for o in s.get("outils", []) if o.get("cout_mensuel")]
    if abonnements:
        out += ["## Abonnements à prévoir, payés directement à l'éditeur", "",
                tableau(["Outil", "Usage", "Coût indicatif", "Tarif public relevé le"], abonnements),
                "", "Tarifs publics des éditeurs à la date indiquée, susceptibles d'évoluer.", ""]
    if dv.get("hypotheses_chiffrage"):
        out += ["## Hypothèses de chiffrage", ""] + [f"- {x}" for x in dv["hypotheses_chiffrage"]] + [""]
    if dv.get("exclusions"):
        out += ["## Ce que ce devis ne comprend pas", ""] + [f"- {x}" for x in dv["exclusions"]] + [""]
    out += ["## Échéancier de facturation", "",
            tableau(["Échéance", "Part", "Montant net"],
                    [[x["libelle"], f"{nombre(x['pourcentage'])}{NBSP}%", euros(x["montant"])] for x in dev["echeancier"]]), ""]
    valid = dv.get("validite_jours", em["validite_jours"])
    out += ["## Conditions", "",
            f"- Devis valable {valid} jours, soit jusqu'au {date_fr(dev['date_validite']) if dev['date_validite'] else '—'}.",
            "- La commande est ferme à réception du devis accepté (signature ou accord écrit par e-mail) "
            "et de l'acompte prévu à l'échéancier (CGV, article 5.2).",
            f"- Factures payables à {em['delai_paiement_jours']} jours à compter de leur émission, par virement. "
            "Pénalités de retard et indemnité forfaitaire de recouvrement de 40 € selon l'article 5.3 des CGV "
            "(articles L441-10 et D441-5 du Code de commerce).",
            "- Frais de déplacement hors Île-de-France facturés en sus, après accord préalable (CGV, article 4).",
            "- Les estimations de gains figurant dans le compte rendu d'audit sont des analyses prospectives "
            "et non une garantie de résultat (CGV, article 7.1).",
            f"- {em['mention_tva']}.",
            f"- Conditions générales de vente, version du {em['cgv_version']}, consultables sur "
            f"{em['cgv_url']} : elles s'appliquent au présent devis."]
    out += [f"- {x}" for x in dv.get("conditions_particulieres", [])]
    out += ["", "## Bon pour accord", "",
            '<div class="signature"><p>Date :</p><p>Nom et fonction du signataire :</p>'
            "<p>Signature et cachet, précédés de la mention « Bon pour accord » :</p></div>", ""]
    return "\n".join(out)


# ── Contrôles ────────────────────────────────────────────────────────────

def verifier_donnees(d, etape, rapport):
    for cle in ("meta", "client", "faits", "problemes"):
        if cle not in d:
            rapport.erreur(f"dossier.json : bloc « {cle} » absent")
    if not (d.get("client") or {}).get("raison_sociale"):
        rapport.erreur("client.raison_sociale manquant")

    tous = {}
    for bloc, prefixe in (("faits", "F"), ("problemes", "P"), ("hypotheses", "H"), ("solutions", "S"),
                          ("questions_ouvertes", "Q")):
        for x in d.get(bloc, []) or []:
            i = x.get("id", "")
            if not re.fullmatch(prefixe + r"\d{1,3}", i):
                rapport.erreur(f"{bloc} : identifiant « {i} » invalide (attendu {prefixe}1, {prefixe}2…)")
            if i in tous:
                rapport.erreur(f"identifiant {i} en double")
            tous[i] = x
    for l in (d.get("devis") or {}).get("lots", []):
        if not re.fullmatch(r"L\d{1,3}", l.get("id", "")):
            rapport.erreur(f"devis.lots : identifiant « {l.get('id')} » invalide")
        tous[l.get("id")] = l

    F, P, H = par_id(d.get("faits")), par_id(d.get("problemes")), par_id(d.get("hypotheses"))
    for f in d.get("faits", []):
        if not (f.get("citation") or "").strip():
            rapport.erreur(f"{f.get('id')} : citation verbatim manquante")
        if not f.get("localisation"):
            rapport.erreur(f"{f.get('id')} : localisation dans la source manquante")
        if f.get("statut") not in ("mesuré", "déclaré", "estimé", "déduit"):
            rapport.erreur(f"{f.get('id')} : statut « {f.get('statut')} » (mesuré|déclaré|estimé|déduit)")
    for p in d.get("problemes", []):
        if not p.get("faits"):
            rapport.erreur(f"{p['id']} : aucun fait source")
        for fid in p.get("faits", []):
            if fid not in F:
                rapport.erreur(f"{p['id']} : fait {fid} inexistant")
        pr = p.get("priorisation") or {}
        for k in ("impact", "effort", "risque"):
            if not isinstance(pr.get(k), int) or not 1 <= pr[k] <= 5:
                rapport.erreur(f"{p['id']} : priorisation.{k} doit être un entier de 1 à 5")
        if p.get("certitude") not in ("confirmé", "probable", "incertain"):
            rapport.erreur(f"{p['id']} : certitude « {p.get('certitude')} » (confirmé|probable|incertain)")
    for h in d.get("hypotheses", []):
        if h.get("valeur") is None or not h.get("origine"):
            rapport.erreur(f"{h.get('id')} : valeur et origine obligatoires")
        for fid in re.findall(r"\bF\d+\b", str(h.get("origine", ""))):
            if fid not in F:
                rapport.erreur(f"{h['id']} : origine cite {fid}, inexistant")
    if etape == "extraction":
        return

    if not d.get("problemes"):
        rapport.erreur("aucun constat : rien ne justifie une recommandation")
    if not any(s.get("statut") == "retenue" for s in d.get("solutions", [])):
        rapport.alerte("aucune solution retenue : le compte rendu doit alors conclure qu'il n'y a rien à engager")
    S = par_id(d.get("solutions"))
    couverts = {pid for s in S.values() for pid in s.get("problemes", [])}
    for p in d.get("problemes", []):
        if p["id"] not in couverts and not p.get("hors_perimetre"):
            rapport.erreur(f"{p['id']} : ni solution, ni hors_perimetre motivé")
    lots = (d.get("devis") or {}).get("lots", [])
    sols_chiffrees = {sid for l in lots for sid in l.get("solutions") or []}
    for s in S.values():
        sid = s["id"]
        if s.get("statut") not in ("retenue", "option", "écartée"):
            rapport.erreur(f"{sid} : statut « {s.get('statut')} » (retenue|option|écartée)")
        for pid in s.get("problemes", []):
            if pid not in P:
                rapport.erreur(f"{sid} : constat {pid} inexistant")
        if s.get("statut") == "écartée" and not s.get("raison_ecart"):
            rapport.erreur(f"{sid} : écartée sans raison_ecart")
        if s.get("statut") in ("retenue", "option") and sid not in sols_chiffrees and not s.get("sans_lot"):
            rapport.erreur(f"{sid} : {s.get('statut')} mais aucun lot du devis (ou sans_lot motivé)")
        if s.get("statut") in ("retenue", "option") and not s.get("business_case") and not s.get("gains_qualitatifs"):
            rapport.erreur(f"{sid} : ni business_case ni gains_qualitatifs")
        if not s.get("alternatives_ecartees") and s.get("statut") != "écartée":
            rapport.alerte(f"{sid} : aucune alternative écartée documentée")
        for o in s.get("outils", []):
            if not o.get("verifie_le") or not o.get("source"):
                rapport.erreur(f"{sid} : outil « {o.get('nom')} » sans verifie_le ou source")
            else:
                age = (dt.date.today() - dt.date.fromisoformat(o["verifie_le"])).days
                if age > 30:
                    rapport.alerte(f"{sid} : tarif de « {o.get('nom')} » vérifié il y a {age} jours")
        bc = s.get("business_case") or {}
        for k in ("taux_automatisation", "taux_supervision", "cout_horaire", "adoption_an1"):
            if bc and bc.get(k) is None:
                rapport.erreur(f"{sid}.business_case.{k} manquant")
        for k, v in bc.items():
            if isinstance(v, (int, float)) and v != 0 and k not in ("taux_supervision", "adoption_an1"):
                rapport.alerte(f"{sid}.business_case.{k} = {v} : valeur en dur, la rattacher à une hypothèse H")
            if isinstance(v, str) and v not in H:
                rapport.erreur(f"{sid}.business_case.{k} : hypothèse {v} inexistante")
        for k in ("taux_automatisation", "taux_supervision", "adoption_an1"):
            for scen in SCENARIOS:
                try:
                    x = valeur(bc.get(k), scen, H, k) if bc.get(k) is not None else None
                except ErreurDonnees:
                    x = None
                if x is not None and not 0 <= x <= 1:
                    rapport.erreur(f"{sid}.business_case.{k} = {x} hors de [0 ; 1]")
    for l in lots:
        for sid in l.get("solutions") or []:
            if sid not in S:
                rapport.erreur(f"{l['id']} : solution {sid} inexistante")
            elif S[sid].get("statut") == "écartée":
                rapport.erreur(f"{l['id']} : chiffre la solution écartée {sid}")
            elif (S[sid].get("statut") == "option") != bool(l.get("option")):
                rapport.erreur(f"{l['id']} : option={bool(l.get('option'))} incohérent avec {sid} ({S[sid].get('statut')})")
        if not isinstance(l.get("prix_unitaire"), (int, float)) or l["prix_unitaire"] <= 0:
            rapport.erreur(f"{l.get('id')} : prix_unitaire absent ou nul")
        if not l.get("chiffrage_interne"):
            rapport.alerte(f"{l.get('id')} : pas de chiffrage_interne, rentabilité non contrôlée")
    dv = d.get("devis") or {}
    if lots:
        ech = dv.get("echeancier")
        if ech and abs(sum(e.get("pourcentage", 0) for e in ech) - 100) > 1e-6:
            rapport.erreur("devis.echeancier : la somme des pourcentages n'est pas 100")
        for k in ("numero", "date_emission", "objet"):
            if not dv.get(k):
                rapport.erreur(f"devis.{k} manquant")
        for t in dv.get("budget_tiers") or []:
            if not (isinstance(t.get("min"), (int, float)) and isinstance(t.get("max"), (int, float)) and t["min"] <= t["max"]):
                rapport.erreur(f"budget_tiers « {t.get('libelle')} » : min/max invalides")
        if dv.get("conditions_particulieres"):
            rapport.alerte("devis.conditions_particulieres : clause hors CGV, à faire valider par Patrick avant envoi")
    for q in d.get("questions_ouvertes", []):
        if q.get("bloquante") and not q.get("reponse"):
            (rapport.erreur if etape == "final" else rapport.alerte)(f"{q['id']} : question bloquante sans réponse")
    if etape == "final":
        c = d.get("client") or {}
        if not re.fullmatch(r"\d{9}", re.sub(r"\s", "", str(c.get("siren", "")))):
            rapport.erreur("client.siren absent ou invalide : obligatoire avant envoi du devis")
        if not c.get("adresse"):
            rapport.erreur("client.adresse absente")


def verifier_coherence_site(d, rapport):
    racine = racine_depot()
    if not racine:
        return
    em = emetteur()
    m = re.search(r"Version en vigueur au ([^<]+)", (racine / "cgv.html").read_text(encoding="utf-8"))
    if m and m.group(1).strip() != em["cgv_version"]:
        rapport.erreur(f"CGV du site en version « {m.group(1).strip()} », devis calé sur « {em['cgv_version']} » : "
                       "mettre à jour assets/emetteur.json et relire la section Conditions")
    bc = racine / "boutique-config.js"
    if bc.exists():
        prix = dict(re.findall(r"(\w+):\s*\{[^}]*?prixEUR:\s*(\d+)", bc.read_text(encoding="utf-8"), re.S))
        for l in (d.get("devis") or {}).get("lots", []):
            cat = l.get("catalogue")
            if cat and cat in prix and float(l.get("prix_unitaire", 0)) != float(prix[cat]):
                rapport.erreur(f"{l['id']} : offre catalogue « {cat} » à {l.get('prix_unitaire')} €, "
                               f"prix public {prix[cat]} € (boutique-config.js)")


def verifier_texte(nom, texte_brut, texte_final, client, ids, rapport):
    lignes = sans_commentaires(texte_brut).splitlines()
    titres = [(i, len(m.group(1)), m.group(2)) for i, l in enumerate(lignes)
              if (m := re.match(r"^(#{1,4})\s+(.*)", l))]
    for k, (i, niv, titre) in enumerate(titres):
        fin = titres[k + 1][0] if k + 1 < len(titres) else len(lignes)
        contenu = any(l.strip() for l in lignes[i + 1:fin])
        sous_partie = k + 1 < len(titres) and titres[k + 1][1] > niv
        if not contenu and not sous_partie:
            rapport.erreur(f"{nom} : section vide « {titre} »")
    for m in ID_RE.finditer(sans_commentaires(texte_brut)):
        if m.group(0) not in ids:
            rapport.erreur(f"{nom} : référence {m.group(0)} inexistante dans dossier.json")
    bas = texte_final.lower()
    if client:
        for motif, quoi in INTERDITS_CLIENT:
            if re.search(motif, texte_final, re.I):
                rapport.erreur(f"{nom} (document client) : {quoi} détecté")
    for s in SLOP:
        if s in bas:
            rapport.alerte(f"{nom} : tournure à reprendre « {s} »")


# ── Rendu HTML / PDF ─────────────────────────────────────────────────────

def md_vers_html(texte):
    if shutil.which("pandoc"):
        r = subprocess.run(["pandoc", "-f", "markdown-auto_identifiers-subscript-superscript-tex_math_dollars",
                            "-t", "html5", "--columns=100000"],
                           input=texte, capture_output=True, text=True, check=True)
        return r.stdout
    try:
        import markdown
    except ImportError:
        sortir("ni pandoc ni le module Python markdown : installer l'un des deux "
               "(apt install pandoc, ou pip install markdown)")
    return markdown.markdown(texte, extensions=["tables", "sane_lists", "md_in_html"])


def page_html(corps, titre, classe, d, sous_titre, interne=False):
    css = (ASSETS / "document.css").read_text(encoding="utf-8")
    logo = base64.b64encode((ASSETS / "logo.png").read_bytes()).decode()
    c, m = d.get("client") or {}, d.get("meta") or {}
    e = html.escape
    bandeau = '<p class="bandeau-interne">Document interne — ne pas transmettre au client</p>' if interne else ""
    couverture = ""
    if classe != "doc-devis":
        couverture = (
            f'<section class="couverture">{bandeau}<img class="logo" src="data:image/png;base64,{logo}" alt="Think\'UP">'
            f'<div><p class="surtitre">{e(sous_titre)}</p><h1 class="titre-couverture">{e(titre)}</h1>'
            f'<p class="client">{e(c.get("raison_sociale", ""))}</p></div>'
            f'<dl class="infos"><dt>Entretien</dt><dd>{e(date_fr(m.get("date_entretien", "")))}</dd>'
            f'<dt>Référence</dt><dd>{e(m.get("reference", ""))}</dd>'
            f'<dt>Établi par</dt><dd>Patrick Langlais, Think\'UP</dd></dl>'
            f'<p class="confidentiel">{"Usage interne" if interne else "Confidentiel — établi pour " + e(c.get("raison_sociale", ""))}</p>'
            "</section>")
    else:
        couverture = f'<img class="logo-devis" src="data:image/png;base64,{logo}" alt="Think\'UP">'
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{e(titre)} — {e(c.get("raison_sociale", ""))}</title>'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><style>{css}</style></head>'
            f'<body class="{classe}"><div class="feuille">{couverture}<main>{corps}</main></div></body></html>')


def rendre_pdf(html_path, pdf_path, pied):
    if not shutil.which("node"):
        return "node absent"
    r = subprocess.run(["node", str(ICI / "pdf.cjs"), str(html_path), str(pdf_path), pied],
                       capture_output=True, text=True)
    return None if r.returncode == 0 else (r.stderr.strip() or r.stdout.strip())


# ── Commandes ────────────────────────────────────────────────────────────

def cmd_init(a):
    racine = Path(a.racine)
    date = a.date or dt.date.today().isoformat()
    ref = f"{date}-{slug(a.client)}"
    dossier = racine / ref
    if dossier.exists():
        sortir(f"{dossier} existe déjà")
    dossier.mkdir(parents=True)
    # Dépôt public : un dossier d'audit suivi par git finirait en ligne.
    r = subprocess.run(["git", "check-ignore", "-q", str(dossier)], capture_output=True)
    if r.returncode == 1:
        shutil.rmtree(dossier)
        sortir(f"{dossier} n'est pas ignoré par git : ajouter « {racine}/ » au .gitignore avant tout audit")
    squelette = {
        "meta": {"reference": ref, "date_entretien": date, "type_entretien": "", "duree_min": None,
                 "participants_thinkup": ["Patrick Langlais"], "source": {"type": "", "ref": ""}, "mode": "complet"},
        "client": {"raison_sociale": a.client, "forme_juridique": "", "siren": "", "adresse": "", "secteur": "",
                   "effectif": None, "outils_en_place": [], "interlocuteurs": []},
        "faits": [], "problemes": [], "hypotheses": [], "solutions": [],
        "devis": {"numero": f"D-{date.replace('-', '')}-{slug(a.client)[:3].upper()}", "date_emission": "",
                  "objet": "", "introduction": "", "lots": [], "budget_tiers": [],
                  "hypotheses_chiffrage": [], "exclusions": []},
        "questions_ouvertes": [],
    }
    (dossier / "dossier.json").write_text(json.dumps(squelette, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.copy(ASSETS / "modele-compte-rendu.md", dossier / CR)
    shutil.copy(ASSETS / "modele-dossier-solution.md", dossier / SOL)
    (dossier / "00-source.md").write_text(
        f"# Source — {a.client}\n\nProvenance : \nDate de l'entretien : {date}\nParticipants : \n"
        "Nature : transcription verbatim | notes | document\n\n---\n\n", encoding="utf-8")
    (dossier / "journal.md").write_text(f"# Journal — {ref}\n\n", encoding="utf-8")
    print(dossier)
    return 0


def cmd_calculer(a):
    d = charger(a.dossier)
    try:
        calc = calculer(d)
    except ErreurDonnees as e:
        sortir(str(e))
    (Path(a.dossier) / "calculs.json").write_text(json.dumps(calc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(calc["bc"].get("global", {}), ensure_ascii=False, indent=2))
    print(f"Devis : total {euros(calc['devis']['total'])}, options {euros(calc['devis']['options'])}")
    return 0


def produire(dossier, etape, rapport):
    """Calcule, interpole et contrôle ; renvoie les textes finaux sans rien écrire."""
    d = charger(dossier)
    verifier_donnees(d, etape, rapport)
    verifier_coherence_site(d, rapport)
    if etape == "extraction":
        return d, None, {}
    try:
        calc = calculer(d)
    except ErreurDonnees as e:
        rapport.erreur(str(e))
        return d, None, {}
    ctx, T = contexte(d, calc), tableaux(d, calc)
    ids = set(par_id(d.get("problemes"))) | set(par_id(d.get("solutions"))) | set(par_id(d.get("hypotheses"))) \
        | set(par_id(d.get("questions_ouvertes"))) | set(par_id((d.get("devis") or {}).get("lots")))
    textes = {}
    for nom, client in ((CR, True), (SOL, False)):
        f = Path(dossier) / nom
        if not f.exists():
            rapport.erreur(f"{nom} absent")
            continue
        brut = f.read_text(encoding="utf-8")
        final = interpoler(sans_commentaires(brut), ctx, T, rapport, nom)
        verifier_texte(nom, brut, final, client, ids, rapport)
        textes[nom] = final
    if (d.get("devis") or {}).get("lots"):
        dm = devis_md(d, calc)
        verifier_texte("devis", dm, dm, True, ids, rapport)
        textes["devis"] = dm
    cr = textes.get(CR, "")
    for s in d.get("solutions", []):
        if s.get("statut") in ("retenue", "option") and s["id"] not in cr and s.get("titre", "@@") not in cr:
            rapport.alerte(f"{CR} : la solution {s['id']} n'est jamais mentionnée")
    if etape == "final":
        journal = Path(dossier) / "journal.md"
        if not journal.exists() or "Tour 1" not in journal.read_text(encoding="utf-8"):
            rapport.erreur("journal.md ne trace aucune relecture (« Tour 1 ») : passes de relecture non faites")
    return d, calc, textes


def cmd_verifier(a):
    rapport = Rapport()
    produire(a.dossier, a.etape, rapport)
    return rapport.afficher(f"Vérification ({a.etape})")


def cmd_construire(a):
    rapport = Rapport()
    d, calc, textes = produire(a.dossier, "final" if a.final else "redaction", rapport)
    if calc is None:
        return rapport.afficher("Construction impossible")
    dossier = Path(a.dossier)
    (dossier / "calculs.json").write_text(json.dumps(calc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sortie = dossier / "livrables"
    sortie.mkdir(exist_ok=True)
    ref = (d.get("meta") or {}).get("reference", "audit")
    rs = (d.get("client") or {}).get("raison_sociale", "")
    docs = [(CR, f"{ref}-compte-rendu", "Compte rendu d'audit", "doc-cr", "Audit IA", False),
            ("devis", f"{ref}-devis", "Devis", "doc-devis", "Proposition", False),
            (SOL, f"{ref}-dossier-solution-INTERNE", "Dossier de mise en œuvre", "doc-sol", "Solution IA", True)]
    for cle, base, titre, classe, sur, interne in docs:
        if cle not in textes:
            continue
        (sortie / f"{base}.md").write_text(textes[cle], encoding="utf-8")
        page = page_html(md_vers_html(textes[cle]), titre, classe, d, sur, interne)
        (sortie / f"{base}.html").write_text(page, encoding="utf-8")
        print(f"  {sortie / base}.html")
        if a.pdf and not rapport.erreurs:
            pied = f"Think'UP · {titre} · {rs}" + (" · INTERNE" if interne else "")
            err = rendre_pdf(sortie / f"{base}.html", sortie / f"{base}.pdf", pied)
            if err:
                rapport.alerte(f"PDF non produit pour {base} ({err}) : ouvrir le HTML et imprimer en PDF")
            else:
                print(f"  {sortie / base}.pdf")
    if a.pdf and rapport.erreurs:
        print("  PDF non produits : corriger d'abord les erreurs ci-dessous.")
    return rapport.afficher("Construction")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("init")
    i.add_argument("racine", nargs="?", default="audits")
    i.add_argument("--client", required=True)
    i.add_argument("--date")
    c = sp.add_parser("calculer")
    c.add_argument("dossier")
    v = sp.add_parser("verifier")
    v.add_argument("dossier")
    v.add_argument("--etape", choices=["extraction", "redaction", "final"], default="redaction")
    b = sp.add_parser("construire")
    b.add_argument("dossier")
    b.add_argument("--pdf", action="store_true")
    b.add_argument("--final", action="store_true", help="applique aussi les contrôles d'avant envoi")
    a = p.parse_args()
    return {"init": cmd_init, "calculer": cmd_calculer, "verifier": cmd_verifier,
            "construire": cmd_construire}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
