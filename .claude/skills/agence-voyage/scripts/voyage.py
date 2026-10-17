#!/usr/bin/env python3
"""agence-voyage : contrôles, budgets, proposition, carnet de voyage et calendrier.

Aucun total ne se calcule à la main : budget de chaque formule, écart au
budget, part des prix non confirmés, chronologie et échéances sont calculés
ici à partir de dossier.json (voir references/dossier-json.md).

  voyage.py init [racine] --objet "Lisbonne, séminaire" [--depart AAAA-MM-JJ]
  voyage.py verifier <dossier> [--etape brief|proposition|reservation|depart]
  voyage.py construire <dossier> [--etape proposition|reservation|depart]
  voyage.py echeances <dossier> [--jours 60]
  voyage.py archiver <dossier>                       # zip du dossier, à côté de lui
  voyage.py restaurer <archive.zip> [racine]

L'étape vaut par défaut celle du statut du dossier (meta.statut).
--aujourdhui AAAA-MM-JJ fixe la date du jour (contrôle de non-régression).

Code de sortie : 0 si aucune erreur, 1 sinon. Les alertes n'empêchent rien
mais doivent être lues.
"""
import argparse
import calendar
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

NBSP, NNBSP = "\u00a0", "\u202f"
ETAPES = ("brief", "proposition", "reservation", "depart")
ETAPE_DU_STATUT = {"brief": "brief", "proposition": "proposition", "reservation": "reservation",
                   "pret": "depart", "en_cours": "depart", "clos": "depart"}
TYPES = {"vol": "Vols", "train": "Trains", "bus": "Cars", "ferry": "Bateaux", "transfert": "Transferts",
         "location": "Location de véhicule", "hebergement": "Hébergement", "activite": "Activités",
         "restaurant": "Restaurants", "assurance": "Assurance", "formalite": "Formalités", "autre": "Divers"}
TRANSPORTS = ("vol", "train", "bus", "ferry", "transfert", "location")
CHRONO = ("vol", "train", "bus", "ferry", "transfert")      # la location s'étale sur plusieurs jours
HORAIRE_REQUIS = ("vol", "train", "bus", "ferry")
STATUTS = ("proposee", "retenue", "ecartee", "reservee", "annulee")
NATURES = {"constate": "constaté", "indicatif": "indicatif", "estime": "estimé"}
STATUTS_FORMALITE = ("ok", "a_faire", "bloquant", "sans_objet")

PRIX_VALIDE_J = 3             # soit 72 h : au-delà, un prix se reconfirme avant d'être présenté
FORMALITE_VALIDE_J = 30       # au-delà, une formalité se revérifie
NON_CONFIRME_MAX = 0.30       # part du montant d'une formule en prix indicatifs ou estimés
ANNULATION_PROCHE_J = 3
# Battement minimal avant un départ, selon (type précédent, type suivant), en minutes. Alerte seulement :
# le temps minimum de correspondance officiel de l'aéroport fait foi.
BATTEMENT_MIN = {("vol", "vol"): 60, ("*", "vol"): 90, ("*", "ferry"): 30, ("*", "train"): 15}

# Dépôt public, dossiers ignorés mais archivés et copiés sur Drive : aucun secret ni numéro de document.
CHAMP_INTERDIT = re.compile(r"(numero|num|no)_(de_)?(passeport|cni|carte|carte_bancaire)|(passeport|cni|carte)_(numero|num|no)"
                            r"|cvv|cvc|cryptogramme|mot_de_passe|password|code_pin|pin")
CARTE_RE = re.compile(r"(?<![\d-])[3-6]\d{3}(?:[ -]?\d{4}){2}[ -]?\d{3,4}(?![\d-])")

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

CSS = """
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:#1d2433;background:#fff;margin:0;line-height:1.5}
.feuille{max-width:920px;margin:0 auto;padding:32px 16px}
h1{font-size:1.7rem;margin:.2em 0 .4em}
h2{font-size:1.25rem;margin-top:2em;border-bottom:2px solid #e3e8f0;padding-bottom:.2em}
h3{font-size:1.05rem;margin-top:1.4em}
table{border-collapse:collapse;width:100%;font-size:.92rem;margin:.6em 0}
th,td{border:1px solid #d9dfe8;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#f3f6fa}
blockquote{margin:1em 0;padding:.6em 1em;background:#fff6e5;border-left:4px solid #e0a100}
a{color:#1f5fbf}
@media (max-width:640px){table{display:block;overflow-x:auto}}
@media print{.feuille{padding:0}a{color:inherit}}
"""


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


def euros(x):
    if x is None:
        return "n.c."
    signe = "−" if x < 0 else ""
    x = abs(x)
    if abs(x - round(x)) < 0.005:
        s = _milliers(int(round(x)))
    else:
        entier, dec = f"{x:.2f}".split(".")
        s = _milliers(int(entier)) + "," + dec
    return f"{signe}{s}{NBSP}€"


def pourcent(x):
    return f"{round(x * 100)}{NBSP}%"


def nombre(x):
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).replace(".", ",")


def date_fr(d, jour=False):
    j = "1er" if d.day == 1 else str(d.day)
    s = f"{j} {MOIS[d.month - 1]} {d.year}"
    return f"{JOURS[d.weekday()]} {s}" if jour else s


def jour_court(d):
    return f"{JOURS_COURTS[d.weekday()]} {d.day} {MOIS_COURTS[d.month - 1]}"


def jc(x):
    """Jour court d'une date AAAA-MM-JJ, ou le texte tel quel s'il est illisible (déjà signalé par les contrôles)."""
    try:
        return jour_court(dt.date.fromisoformat(str(x)[:10]))
    except ValueError:
        return str(x or "")


def heure(x):
    """09:30 (UTC+1) : l'écart à UTC lève toute ambiguïté entre fuseaux."""
    m = int((x.utcoffset() or dt.timedelta(0)).total_seconds() // 60)
    signe, m = ("+" if m >= 0 else "−"), abs(m)
    return f"{x:%H:%M} (UTC{signe}{m // 60}{f':{m % 60:02d}' if m % 60 else ''})"


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
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:40] or "voyage"


def lien(source):
    """Une source s'affiche comme un lien vers son domaine, suivi de son commentaire éventuel
    (« https://… (tarif 2026) »), ou telle quelle si ce n'est pas une adresse."""
    s = str(source or "").strip()
    adresse, _, reste = s.partition(" ")
    u = urlparse(adresse)
    if u.scheme in ("http", "https") and u.netloc:
        return f"[{u.netloc.removeprefix('www.')}]({adresse})" + (f" {reste.strip()}" if reste.strip() else "")
    return s


def plus_mois(d, m):
    a, mo = divmod(d.month - 1 + m, 12)
    a, mo = d.year + a, mo + 1
    return dt.date(a, mo, min(d.day, calendar.monthrange(a, mo)[1]))


def luhn(chiffres):
    s = 0
    for i, c in enumerate(reversed(chiffres)):
        n = int(c)
        if i % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        s += n
    return s % 10 == 0


# ── Chargement et lecture des dates ──────────────────────────────────────

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
        sortir(f"{f} illisible : {e}")


def jour(x, R, ou):
    if not x:
        return None
    try:
        return dt.date.fromisoformat(str(x)[:10])
    except ValueError:
        R.erreur(f"{ou} : date illisible « {x} » (format AAAA-MM-JJ)")
        return None


def instant(x, R, ou):
    """Échéance AAAA-MM-JJ ou AAAA-MM-JJTHH:MM, à l'heure locale du prestataire : renvoie (date, heure ou None)."""
    if not x:
        return None
    try:
        if len(str(x)) <= 10:
            return dt.date.fromisoformat(str(x)), None
        t = dt.datetime.fromisoformat(str(x))
        return t.date(), t.strftime("%H:%M")
    except ValueError:
        R.erreur(f"{ou} : date illisible « {x} » (format AAAA-MM-JJ ou AAAA-MM-JJTHH:MM)")
        return None


def fuseau(nom, R, ou):
    if not nom:
        R.erreur(f"{ou} : horaire sans fuseau (fuseau_debut, par exemple Europe/Lisbon)")
        return dt.timezone.utc
    try:
        return ZoneInfo(nom)
    except (ZoneInfoNotFoundError, ValueError):
        R.erreur(f"{ou} : fuseau inconnu « {nom} » (nom IANA, par exemple Europe/Lisbon)")
        return dt.timezone.utc


def lire_moments(d, R):
    """Ajoute à chaque prestation _debut, _fin (date, ou datetime avec fuseau) et _horaire."""
    for p in d.get("prestations") or []:
        ou = p.get("id", "prestation sans id")
        p["_horaire"], p["_debut"], p["_fin"] = False, None, None
        deb, fin = p.get("debut"), p.get("fin")
        if not deb:
            continue
        try:
            if p.get("type") == "hebergement" or len(str(deb)) <= 10:
                p["_debut"] = dt.date.fromisoformat(str(deb)[:10])
                p["_fin"] = dt.date.fromisoformat(str(fin)[:10]) if fin else None
                continue
            z1 = fuseau(p.get("fuseau_debut"), R, ou)
            z2 = fuseau(p.get("fuseau_fin"), R, ou) if p.get("fuseau_fin") else z1
            a = dt.datetime.fromisoformat(str(deb))
            p["_debut"] = a if a.tzinfo else a.replace(tzinfo=z1)
            if fin:
                b = dt.datetime.fromisoformat(str(fin))
                p["_fin"] = b if b.tzinfo else b.replace(tzinfo=z2)
            p["_horaire"] = True
        except ValueError as e:
            R.erreur(f"{ou} : date ou heure illisible ({e}) — format AAAA-MM-JJ ou AAAA-MM-JJTHH:MM")


def jour_local(p):
    x = p.get("_debut")
    return x.date() if isinstance(x, dt.datetime) else x


def cle_temps(p):
    x = p.get("_debut")
    if x is None:
        return (dt.date.max, "99")
    if isinstance(x, dt.datetime):
        return (x.date(), x.strftime("%H:%M"))
    return (x, "99")


def nom_p(p):
    return f"« {p.get('libelle', '?')} » ({p.get('id', '?')})"


# ── Montants et formules ─────────────────────────────────────────────────

def montant(p):
    pr = p.get("prix") or {}
    try:
        u, q = float(pr["unitaire"]), float(pr.get("quantite", 1))
    except (KeyError, TypeError, ValueError):
        return None
    taux = 1.0 if (pr.get("devise") or "EUR") == "EUR" else pr.get("taux_eur")
    if not isinstance(taux, (int, float)) or isinstance(taux, bool):
        return None
    return u * q * taux


def actives(d):
    return [p for p in d.get("prestations") or [] if p.get("statut") not in ("ecartee", "annulee")]


def plans(d, etape):
    """Une entrée par formule jusqu'à la proposition, puis le seul plan retenu."""
    if ETAPES.index(etape) <= 1:
        return {f"Formule {v.get('id')} — {v.get('nom', '')}": [p for p in actives(d) if v.get("id") in (p.get("variantes") or [])]
                for v in d.get("variantes") or []}
    return {"Plan retenu": [p for p in actives(d) if p.get("statut") in ("retenue", "reservee")]}


def totaux(plan, nb):
    t = {"total": 0.0, "par_type": {}, "non_confirme": 0.0}
    for p in plan:
        m = montant(p)
        if m is None:
            continue
        t["total"] += m
        t["par_type"][p.get("type")] = t["par_type"].get(p.get("type"), 0.0) + m
        if (p.get("prix") or {}).get("nature") != "constate":
            t["non_confirme"] += m
    t["par_personne"] = t["total"] / nb if nb else None
    t["part_non_confirmee"] = t["non_confirme"] / t["total"] if t["total"] else 0.0
    return t


def budget_total(d):
    b = (d.get("brief") or {}).get("budget") or {}
    m = b.get("montant")
    if not isinstance(m, (int, float)) or isinstance(m, bool):
        return None
    return m * len(d.get("voyageurs") or []) if b.get("base") == "par_personne" else float(m)


# ── Contrôles ────────────────────────────────────────────────────────────

class Analyse:
    def __init__(self, d, etape, auj):
        self.d, self.etape, self.auj, self.rang = d, etape, auj, ETAPES.index(etape)
        self.R = Rapport()
        self.attention = []      # points d'attention repris tels quels dans les documents
        b = d.get("brief") or {}
        self.aller = jour(b.get("date_aller"), self.R, "brief.date_aller")
        self.retour = jour(b.get("date_retour"), self.R, "brief.date_retour")
        self.voyageurs = {v.get("id"): v for v in d.get("voyageurs") or []}
        self.nb = len(self.voyageurs)
        lire_moments(d, self.R)
        self.plans = plans(d, etape)
        self.totaux = {nom: totaux(plan, self.nb) for nom, plan in self.plans.items()}
        self.budget = budget_total(d)

    def signaler(self, msg, erreur=False):
        (self.R.erreur if erreur else self.R.alerte)(msg)
        self.attention.append(msg)

    def lancer(self):
        self.structure()
        self.brief()
        if self.rang >= 1:
            self.prestations()
            for nom, plan in self.plans.items():
                self.chronologie(nom, plan)
                self.nuits(nom, plan)
                self.budget_plan(nom)
            self.formalites()
            self.conseils()
        if self.rang >= 2:
            self.reservations()
        if self.rang >= 3:
            self.depart()
        self.echeances = calculer_echeances(self.d, self.aller, self.R)
        return self

    def structure(self):
        R, d = self.R, self.d
        donnees_interdites(d, R)
        if not (d.get("meta") or {}).get("reference"):
            R.erreur("meta.reference absente")
        for cle in ("voyageurs", "variantes", "prestations", "formalites", "questions_ouvertes"):
            ids = [x.get("id") for x in d.get(cle) or []]
            if None in ids or "" in ids:
                R.erreur(f"{cle} : élément sans id")
            for i in {i for i in ids if ids.count(i) > 1}:
                R.erreur(f"{cle} : id « {i} » en double")
        for v in d.get("voyageurs") or []:
            doc = v.get("document") or {}
            if "numero" in doc:
                R.erreur(f"{v.get('id')} : numéro de document interdit dans le dossier — ne garder que le type et l'expiration")

    def brief(self):
        R, b, rang = self.R, self.d.get("brief") or {}, self.rang
        if not self.voyageurs:
            R.erreur("aucun voyageur")
        for v in self.voyageurs.values():
            exp = jour((v.get("document") or {}).get("expire_le"), R, f"{v.get('id')}.document.expire_le")
            if not exp:
                R.alerte(f"{v.get('nom', v.get('id'))} : date d'expiration du document d'identité inconnue")
            elif self.retour and exp < self.retour:
                self.signaler(f"{v.get('nom', v.get('id'))} : document d'identité expiré avant la fin du voyage "
                              f"(valable jusqu'au {date_fr(exp)})", erreur=rang >= 1)
        if not self.aller or not self.retour:
            R.erreur("brief : date_aller et date_retour obligatoires (AAAA-MM-JJ)")
        elif self.retour < self.aller:
            R.erreur("brief : date_retour antérieure à date_aller")
        elif self.aller < self.auj and rang < 3:
            R.alerte(f"brief : la date d'aller ({date_fr(self.aller)}) est passée")
        if not b.get("depart"):
            R.erreur("brief : ville de départ absente")
        if self.budget is None:
            R.alerte("brief : budget non chiffré — les formules ne seront pas comparées à un budget")
        elif ((b.get("budget") or {}).get("devise") or "EUR") != "EUR":
            R.erreur("brief.budget : exprimer le budget en EUR (les prix sont convertis en euros)")
        etapes = b.get("etapes") or []
        if not etapes:
            (R.erreur if rang >= 1 else R.alerte)("brief : aucune étape (lieu, pays, du, au, fuseau)")
        for e in etapes:
            ou = f"étape {e.get('lieu', '?')}"
            if not e.get("pays"):
                R.erreur(f"{ou} : code pays absent (ISO à deux lettres, par exemple PT)")
            du, au = jour(e.get("du"), R, f"{ou}.du"), jour(e.get("au"), R, f"{ou}.au")
            if self.aller and self.retour and ((du and du < self.aller) or (au and au > self.retour)):
                R.alerte(f"{ou} : en dehors des dates du voyage")
            if e.get("fuseau"):
                fuseau(e["fuseau"], R, ou)

    def prestations(self):
        R, d = self.R, self.d
        variantes = {v.get("id") for v in d.get("variantes") or []}
        if not variantes and self.rang == 1:
            R.erreur("aucune formule (variantes) : en définir au moins une")
        for p in d.get("prestations") or []:
            ou, t, st = p.get("id", "?"), p.get("type"), p.get("statut")
            if t not in TYPES:
                R.erreur(f"{ou} : type « {t} » inconnu ({', '.join(TYPES)})")
            if st not in STATUTS:
                R.erreur(f"{ou} : statut « {st} » inconnu ({', '.join(STATUTS)})")
            if st in ("ecartee", "annulee"):
                continue
            if not p.get("libelle"):
                R.erreur(f"{ou} : libellé absent")
            vs = p.get("variantes") or []
            if st == "proposee" and not vs:
                R.erreur(f"{ou} : rattachée à aucune formule")
            for v in set(vs) - variantes:
                R.erreur(f"{ou} : formule « {v} » inconnue")
            for v in set(p.get("voyageurs") or []) - set(self.voyageurs):
                R.erreur(f"{ou} : voyageur « {v} » inconnu")
            self.dates(p)
            self.prix(p)

    def dates(self, p):
        R, ou, t = self.R, p.get("id", "?"), p.get("type")
        if p["_debut"] is None:
            if t in TRANSPORTS or t in ("hebergement", "activite"):
                R.erreur(f"{ou} : date de début absente")
            return
        if t in HORAIRE_REQUIS and not p["_horaire"]:
            R.erreur(f"{ou} : horaire de départ obligatoire (AAAA-MM-JJTHH:MM)")
        if t in HORAIRE_REQUIS + ("hebergement",) and p["_fin"] is None:
            R.erreur(f"{ou} : {'date de départ de l’hébergement' if t == 'hebergement' else 'heure d’arrivée'} absente")
        if p["_fin"] is not None and type(p["_fin"]) is type(p["_debut"]):
            if p["_fin"] < p["_debut"] or (t == "hebergement" and p["_fin"] == p["_debut"]):
                R.erreur(f"{ou} : fin avant le début" + (" (vérifier les fuseaux)" if p["_horaire"] else ""))
        if t == "hebergement" and p["_fin"] and p["_fin"] > p["_debut"]:
            n, unite = (p["_fin"] - p["_debut"]).days, str((p.get("prix") or {}).get("unite", ""))
            q = (p.get("prix") or {}).get("quantite", 1)
            if "nuit" in unite and isinstance(q, (int, float)) and q % n:
                R.alerte(f"{ou} : {nombre(q)} unité(s) « {unite} » pour {n} nuit(s) — vérifier la quantité")
        j = jour_local(p)
        if self.aller and self.retour and not (self.aller <= j <= self.retour):
            R.alerte(f"{ou} : le {date_fr(j)}, en dehors des dates du voyage")

    def prix(self, p):
        R, ou, pr, st = self.R, p.get("id", "?"), p.get("prix") or {}, p.get("statut")
        if not pr:
            R.erreur(f"{ou} : prix absent (0 si gratuit ou déjà inclus)")
            return
        u, q = pr.get("unitaire"), pr.get("quantite", 1)
        if not isinstance(u, (int, float)) or isinstance(u, bool) or u < 0:
            R.erreur(f"{ou} : prix.unitaire doit être un nombre positif ou nul")
        if not isinstance(q, (int, float)) or isinstance(q, bool) or q <= 0:
            R.erreur(f"{ou} : prix.quantite doit être un nombre strictement positif")
        if (pr.get("devise") or "EUR") != "EUR":
            if not isinstance(pr.get("taux_eur"), (int, float)):
                R.erreur(f"{ou} : prix en {pr.get('devise')} sans taux_eur (valeur d'une unité de devise en euros)")
            elif not pr.get("taux_source"):
                R.alerte(f"{ou} : taux de change sans source ni date (taux_source)")
        if pr.get("nature") not in NATURES:
            R.erreur(f"{ou} : prix.nature doit valoir constate, indicatif ou estime")
        if not pr.get("source"):
            R.erreur(f"{ou} : prix sans source (adresse de la page, ou base de l'estimation)")
        rel = instant(pr.get("releve_le"), R, f"{ou}.prix.releve_le")
        if not rel:
            R.erreur(f"{ou} : prix sans date de relevé (prix.releve_le)")
            return
        age = (self.auj - rel[0]).days
        a_confirmer = st in ("proposee", "retenue") if self.rang == 1 else st == "retenue"
        if a_confirmer and age >= PRIX_VALIDE_J and self.rang < 3:
            self.signaler(f"Prix de {nom_p(p)} relevé le {date_fr(rel[0])} : à reconfirmer avant de réserver")
        if st == "reservee" and pr.get("nature") != "constate":
            R.alerte(f"{ou} : réservée mais prix « {pr.get('nature')} » — reporter le montant payé et passer en constate")

    def chronologie(self, nom, plan):
        tous, vus = list(self.voyageurs), set()
        for v in tous:
            seg = sorted((p for p in plan if p.get("type") in CHRONO and p["_horaire"] and p["_fin"]
                          and v in (p.get("voyageurs") or tous)), key=lambda p: p["_debut"])
            for a, b in zip(seg, seg[1:]):
                if (a.get("id"), b.get("id")) in vus:
                    continue
                vus.add((a.get("id"), b.get("id")))
                ecart = (b["_debut"] - a["_fin"]).total_seconds() / 60
                if ecart < 0:
                    self.R.erreur(f"{nom} : {nom_p(a)} et {nom_p(b)} se chevauchent (vérifier horaires et fuseaux)")
                    continue
                mini = BATTEMENT_MIN.get((a["type"], b["type"])) or BATTEMENT_MIN.get(("*", b["type"]), 0)
                if ecart < mini:
                    self.signaler(f"{nom} : {int(ecart)} min seulement entre l'arrivée de {nom_p(a)} et le départ de "
                                  f"{nom_p(b)} — prévoir au moins {mini} min")
                la, lb = slug(a.get("lieu_fin") or ""), slug(b.get("lieu_debut") or "")
                if la and lb and la != lb and a["type"] != "transfert" and b["type"] != "transfert" and ecart < 240:
                    self.signaler(f"{nom} : arrivée à {a.get('lieu_fin')} puis départ de {b.get('lieu_debut')} "
                                  f"{int(ecart)} min plus tard, sans transfert prévu")

    def nuits(self, nom, plan):
        if not self.aller or not self.retour or self.retour < self.aller:
            return
        for k in range((self.retour - self.aller).days):
            n = self.aller + dt.timedelta(days=k)
            couvert = any(p.get("type") == "hebergement" and p["_debut"] and p["_fin"] and p["_debut"] <= n < p["_fin"]
                          for p in plan) \
                or any(p.get("type") in CHRONO and p["_horaire"] and p["_fin"] and p["_debut"].date() <= n < p["_fin"].date()
                       for p in plan)
            if not couvert:
                self.signaler(f"{nom} : aucun hébergement pour la nuit du {date_fr(n, jour=True)}")

    def budget_plan(self, nom):
        t = self.totaux[nom]
        b = (self.d.get("brief") or {}).get("budget") or {}
        if self.budget is not None and t["total"] > self.budget + 0.005:
            self.signaler(f"{nom} : {euros(t['total'])}, soit {euros(t['total'] - self.budget)} au-dessus du budget "
                          f"de {euros(self.budget)}", erreur=bool(b.get("plafond_strict")))
        if t["part_non_confirmee"] > NON_CONFIRME_MAX:
            self.signaler(f"{nom} : {pourcent(t['part_non_confirmee'])} du montant repose sur des prix indicatifs ou "
                          "estimés — à confirmer avant de choisir")

    def formalites(self):
        R, d, rang = self.R, self.d, self.rang
        pays = {e.get("pays") for e in (d.get("brief") or {}).get("etapes") or [] if e.get("pays")} - {"FR"}
        fs = d.get("formalites") or []
        for f in fs:
            ou = f.get("id", "?")
            if f.get("statut") not in STATUTS_FORMALITE:
                R.erreur(f"{ou} : statut « {f.get('statut')} » inconnu ({', '.join(STATUTS_FORMALITE)})")
            if not f.get("exigence"):
                R.erreur(f"{ou} : exigence absente")
            if not f.get("source"):
                R.erreur(f"{ou} : formalité sans source officielle")
            ver = jour(f.get("verifie_le"), R, f"{ou}.verifie_le")
            if not ver:
                R.erreur(f"{ou} : formalité sans date de vérification (verifie_le)")
            elif (self.auj - ver).days > FORMALITE_VALIDE_J and rang < 3:
                R.alerte(f"{ou} : vérifiée le {date_fr(ver)}, il y a plus de {FORMALITE_VALIDE_J} jours — revérifier")
            for v in set(f.get("voyageurs") or []) - set(self.voyageurs):
                R.erreur(f"{ou} : voyageur « {v} » inconnu")
            if f.get("statut") in ("a_faire", "bloquant"):
                ech = f" avant le {date_fr(jour(f['echeance'], R, ou))}" if f.get("echeance") and jour(f["echeance"], R, ou) else ""
                quoi = "Formalité bloquante" if f["statut"] == "bloquant" else "Formalité à accomplir"
                self.signaler(f"{quoi}{ech} ({f.get('pays')}) : {f.get('exigence')}", erreur=rang >= 3)
            m = f.get("validite_min_mois")
            if isinstance(m, int) and self.retour:
                limite = plus_mois(self.retour, m)
                for vid in f.get("voyageurs") or list(self.voyageurs):
                    v = self.voyageurs.get(vid) or {}
                    exp = jour((v.get("document") or {}).get("expire_le"), R, f"{vid}.document.expire_le")
                    if exp and exp < limite and exp >= self.retour:      # expiré avant le retour : déjà signalé
                        self.signaler(f"{v.get('nom', vid)} : document valable jusqu'au {date_fr(exp)} ; {f.get('pays')} "
                                      f"exige {m} mois de validité après le retour, soit jusqu'au {date_fr(limite)} au moins",
                                      erreur=True)
        for p in sorted(pays - {f.get("pays") for f in fs}):
            (R.erreur if rang >= 2 else R.alerte)(f"{p} : aucune formalité vérifiée (entrée, document, visa)")

    def conseils(self):
        R, d = self.R, self.d
        pays = {e.get("pays") for e in (d.get("brief") or {}).get("etapes") or [] if e.get("pays")} - {"FR"}
        cs = d.get("conseils") or []
        for i, c in enumerate(cs):
            ou = f"conseils[{i}] ({c.get('theme', '?')})"
            if not c.get("texte"):
                R.erreur(f"{ou} : texte absent")
            if not c.get("source") or not c.get("verifie_le"):
                R.erreur(f"{ou} : source et verifie_le obligatoires")
            jour(c.get("verifie_le"), R, f"{ou}.verifie_le")
        for p in sorted(pays - {c.get("pays") for c in cs if c.get("theme") == "securite"}):
            R.alerte(f"{p} : aucun conseil de sécurité (fiche Conseils aux voyageurs du ministère)")

    def reservations(self):
        R, rang = self.R, self.rang
        plan = self.plans["Plan retenu"]
        if not plan:
            R.erreur("aucune prestation retenue ni réservée")
        for p in plan:
            ou, r = p.get("id", "?"), p.get("reservation") or {}
            if p.get("statut") == "retenue":
                self.signaler(f"À réserver : {nom_p(p)}", erreur=rang >= 3)
            elif not r.get("reference"):
                R.erreur(f"{ou} : réservée sans référence de réservation")
            du = r.get("reste_du") or 0
            sol = jour(r.get("solde_avant"), R, f"{ou}.reservation.solde_avant")
            if du and sol and sol < self.auj:
                R.erreur(f"{ou} : solde de {euros(du)} dû avant le {date_fr(sol)}, échéance dépassée")
            ann = instant((p.get("conditions") or {}).get("annulation_gratuite_jusqu_au"), R, f"{ou}.conditions")
            if p.get("statut") == "reservee" and ann and 0 <= (ann[0] - self.auj).days <= ANNULATION_PROCHE_J:
                self.signaler(f"Annulation sans frais de {nom_p(p)} possible jusqu'au {date_fr(ann[0])}"
                              f"{' à ' + ann[1] if ann[1] else ''} seulement : décider d'ici là")
        for q in self.d.get("questions_ouvertes") or []:
            if q.get("bloquante") and not q.get("reponse"):
                R.erreur(f"{q.get('id')} : question bloquante sans réponse — {q.get('question')}")

    def depart(self):
        if not self.d.get("contacts"):
            self.R.alerte("aucun contact utile (hébergements, assistance, assurance, consulat)")
        if not self.d.get("programme"):
            self.R.alerte("programme jour par jour vide")


def donnees_interdites(x, R, chemin="dossier"):
    if isinstance(x, dict):
        for k, v in x.items():
            cle = re.sub(r"[^a-z0-9]+", "_", unicodedata.normalize("NFKD", str(k)).encode("ascii", "ignore").decode().lower())
            if CHAMP_INTERDIT.fullmatch(cle):
                R.erreur(f"{chemin}.{k} : champ interdit (numéro de document ou de carte, secret) — le supprimer")
            donnees_interdites(v, R, f"{chemin}.{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            donnees_interdites(v, R, f"{chemin}[{i}]")
    elif isinstance(x, str):
        for m in CARTE_RE.finditer(x):
            if luhn(re.sub(r"\D", "", m.group())):
                R.erreur(f"{chemin} : ressemble à un numéro de carte bancaire — le supprimer")


def calculer_echeances(d, aller, R):
    """Liste triée de {date, heure, texte} : ce qui doit être fait ou décidé, et quand."""
    E = []
    for p in actives(d):
        c, r, st = p.get("conditions") or {}, p.get("reservation") or {}, p.get("statut")
        ann = instant(c.get("annulation_gratuite_jusqu_au"), R, f"{p.get('id')}.conditions")
        if st == "reservee" and ann:
            E.append({"date": ann[0], "heure": ann[1], "texte": f"Dernier délai d'annulation sans frais : {p.get('libelle')}"})
        sol = instant(r.get("solde_avant"), R, f"{p.get('id')}.reservation.solde_avant")
        if st == "reservee" and r.get("reste_du") and sol:
            E.append({"date": sol[0], "heure": sol[1], "texte": f"Régler le solde de {euros(r['reste_du'])} : {p.get('libelle')}"})
        if st in ("retenue", "reservee") and p.get("type") == "vol" and p.get("_horaire"):
            E.append({"date": p["_debut"].date() - dt.timedelta(days=2), "heure": None,
                      "texte": f"Vérifier l'enregistrement en ligne, les bagages et le terminal : {p.get('libelle')}"})
    for f in d.get("formalites") or []:
        ech = instant(f.get("echeance"), R, f"{f.get('id')}.echeance")
        if f.get("statut") in ("a_faire", "bloquant") and ech:
            E.append({"date": ech[0], "heure": ech[1], "texte": f"Formalité ({f.get('pays')}) : {f.get('exigence')}"})
    for i, inc in enumerate(d.get("incidents") or []):
        ech = instant(inc.get("echeance"), R, f"incidents[{i}].echeance")
        if inc.get("statut") != "clos" and ech:
            E.append({"date": ech[0], "heure": ech[1], "texte": f"Incident : {inc.get('demarche') or inc.get('nature')}"})
    if aller:
        E.append({"date": aller - dt.timedelta(days=7), "heure": None,
                  "texte": "J-7 : revérifier sécurité, formalités, grèves annoncées et météo"})
        E.append({"date": aller, "heure": None, "texte": "Départ"})
    return sorted(E, key=lambda e: (e["date"], e["heure"] or "99"))


# ── Documents ────────────────────────────────────────────────────────────

def detail(p):
    c, pr = p.get("conditions") or {}, p.get("prix") or {}
    morceaux = [p.get("fournisseur"), p.get("numero")]
    if p.get("lieu_debut") or p.get("lieu_fin"):
        morceaux.append(" → ".join(x for x in (p.get("lieu_debut"), p.get("lieu_fin")) if x))
    if p.get("adresse"):
        morceaux.append(p["adresse"])
    if pr.get("inclus"):
        morceaux.append(f"inclus : {pr['inclus']}")
    if c.get("bagages"):
        morceaux.append(f"bagages : {c['bagages']}")
    if c.get("annulation"):
        morceaux.append(f"annulation : {c['annulation']}")
    if p.get("notes"):
        morceaux.append(p["notes"])
    return " · ".join(str(m) for m in morceaux if m)


def quand(p):
    a, b = p.get("_debut"), p.get("_fin")
    if a is None:
        return "date à fixer"
    if not p.get("_horaire"):
        if p.get("type") == "hebergement" and b:
            n = (b - a).days
            return f"{jour_court(a)} → {jour_court(b)} ({n} nuit{'s' if n > 1 else ''})"
        return jour_court(a) + (f" → {jour_court(b)}" if b and b != a else "")
    s = f"{jour_court(a.date())} {heure(a)}"
    if b:
        s += f" → {heure(b)}" if b.date() == a.date() else f" → {jour_court(b.date())} {heure(b)}"
    return s


def prix_texte(p):
    pr, m = p.get("prix") or {}, montant(p)
    s = euros(m)
    q = pr.get("quantite", 1)
    if isinstance(q, (int, float)) and q != 1:
        unit = pr.get("unitaire")
        if (pr.get("devise") or "EUR") != "EUR":
            unit = f"{nombre(unit)} {pr.get('devise')}"
        else:
            unit = euros(unit)
        s += f" ({unit} × {nombre(q)} {pr.get('unite', '')})".replace(" )", ")")
    elif (pr.get("devise") or "EUR") != "EUR":
        s += f" ({nombre(pr.get('unitaire'))} {pr.get('devise')})"
    return s


def source_texte(p):
    pr = p.get("prix") or {}
    return f"{NATURES.get(pr.get('nature'), '?')}, {lien(pr.get('source'))}, {jc(pr.get('releve_le'))}"


def entete_voyage(d, an):
    b, m = d.get("brief") or {}, d.get("meta") or {}
    noms = ", ".join(v.get("nom", v.get("id", "")) for v in an.voyageurs.values())
    L = [f"- **Voyageurs** : {noms}"]
    if an.aller and an.retour:
        L.append(f"- **Dates** : du {date_fr(an.aller, jour=True)} au {date_fr(an.retour, jour=True)}"
                 + (f" (flexibilité : {b['flexibilite']})" if b.get("flexibilite") else ""))
    if b.get("depart"):
        L.append(f"- **Départ** : {b['depart']}" + (f", retour à {b['retour_a']}" if b.get("retour_a") and b.get("retour_a") != b.get("depart") else ""))
    etapes = [f"{e.get('lieu')} ({jc(e['du'])} → {jc(e['au'])})" if e.get("du") and e.get("au") else str(e.get("lieu"))
              for e in b.get("etapes") or []]
    if etapes:
        L.append("- **Étapes** : " + " ; ".join(etapes))
    return L


def doc_proposition(d, an):
    m, b = d.get("meta") or {}, d.get("brief") or {}
    L = [f"# Proposition de voyage — {m.get('objet', '')}", "",
         f"Référence {m.get('reference', '')} · établie le {date_fr(an.auj)}", ""]
    if an.R.erreurs:
        L += ["> **Brouillon : des contrôles sont en erreur, ne pas utiliser en l'état.**", ""]
    L += ["## Le voyage demandé", ""] + entete_voyage(d, an)
    bud = b.get("budget") or {}
    if an.budget is not None:
        L.append(f"- **Budget** : {euros(an.budget)} au total" + (f" ({euros(bud['montant'])} par personne)" if bud.get("base") == "par_personne" else "")
                 + (", plafond strict" if bud.get("plafond_strict") else ""))
    for cle, lib in (("objectif", "Objectif"), ("rythme", "Rythme"), ("hebergement", "Hébergement souhaité"),
                     ("transport", "Transport souhaité")):
        if b.get(cle):
            L.append(f"- **{lib}** : {b[cle]}")
    for cle, lib in (("incontournables", "Incontournables"), ("a_eviter", "À éviter")):
        if b.get(cle):
            L.append(f"- **{lib}** : " + " ; ".join(b[cle]))
    noms = list(an.plans)
    L += ["", "## Les formules en un coup d'œil", ""]
    lignes = []
    for t, lib in TYPES.items():
        if any(t in an.totaux[n]["par_type"] for n in noms):
            lignes.append([lib] + [euros(an.totaux[n]["par_type"][t]) if t in an.totaux[n]["par_type"] else "—" for n in noms])
    lignes.append(["**Total**"] + [f"**{euros(an.totaux[n]['total'])}**" for n in noms])
    lignes.append(["Par personne"] + [euros(an.totaux[n]["par_personne"]) for n in noms])
    if an.budget is not None:
        def ecart(n):
            e = an.totaux[n]["total"] - an.budget
            return f"{euros(e)} au-dessus" if e > 0.005 else f"{euros(-e)} sous le budget"
        lignes.append(["Écart au budget"] + [ecart(n) for n in noms])
    lignes.append(["Prix non confirmés"] + [pourcent(an.totaux[n]["part_non_confirmee"]) for n in noms])
    L.append(tableau(["", *[n.replace("Formule ", "") for n in noms]], lignes))
    variantes = {f"Formule {v.get('id')} — {v.get('nom', '')}": v for v in d.get("variantes") or []}
    for n in noms:
        L += ["", f"## {n}", ""]
        if variantes.get(n, {}).get("idee"):
            L += [variantes[n]["idee"], ""]
        L.append(tableau(["Quand", "Prestation", "Détail", "Prix", "Prix relevé"],
                         [[quand(p), p.get("libelle"), detail(p), prix_texte(p), source_texte(p)]
                          for p in sorted(an.plans[n], key=cle_temps)]))
    L += ["", "## Formalités et santé", ""] + formalites_tableau(d, an)
    L += ["", "## Conseils pratiques", ""] + conseils_liste(d)
    L += ["", "## Points d'attention", ""] + ([f"- {a}" for a in an.attention] or ["Aucun."])
    qs = [q for q in d.get("questions_ouvertes") or [] if not q.get("reponse")]
    if qs:
        L += ["", "## Questions à trancher", ""] + [f"- {q.get('question')}" + (" (bloquante)" if q.get("bloquante") else "") for q in qs]
    rels = sorted(r for n in noms for p in an.plans[n]
                  if (r := instant((p.get("prix") or {}).get("releve_le"), Rapport(), "")))
    L += ["", "## Validité des prix", ""]
    if rels:
        L.append(f"Prix relevés entre le {date_fr(rels[0][0])} et le {date_fr(rels[-1][0])}. "
                 "Les tarifs de transport et d'hébergement changent en permanence : chacun se reconfirme au moment de réserver. "
                 "Un prix « indicatif » n'a pas été vu pour ces dates exactes ; un prix « estimé » est un calcul dont la base "
                 "figure en source.")
    L += ["", "La réservation et le paiement se font sur les sites des prestataires, par le voyageur : "
          "l'outil ne réserve ni ne paie rien."]
    return "\n".join(L) + "\n"


def formalites_tableau(d, an):
    lignes = []
    for f in d.get("formalites") or []:
        qui = ", ".join(an.voyageurs.get(v, {}).get("nom", v) for v in f.get("voyageurs") or []) or "tous"
        etat = {"ok": "en règle", "a_faire": "à faire", "bloquant": "BLOQUANT", "sans_objet": "sans objet"}.get(f.get("statut"), "?")
        if f.get("echeance") and f.get("statut") in ("a_faire", "bloquant"):
            etat += f" avant le {jc(f['echeance'])}"
        lignes.append([f.get("pays"), qui, f.get("exigence"), etat, f"{lien(f.get('source'))}, {jc(f.get('verifie_le'))}"])
    return [tableau(["Pays", "Voyageurs", "Exigence", "État", "Vérifié"], lignes)]


def conseils_liste(d):
    cs = d.get("conseils") or []
    if not cs:
        return ["_Aucun conseil consigné._"]
    themes = {"securite": "Sécurité", "sante": "Santé", "meteo": "Météo", "argent": "Argent", "telephone": "Téléphone",
              "prises": "Électricité", "usages": "Usages", "transport_local": "Transport sur place", "autre": "Divers"}
    return [f"- **{themes.get(c.get('theme'), c.get('theme'))}" + (f" ({c['pays']})" if c.get("pays") else "")
            + f"** : {c.get('texte')} ({lien(c.get('source'))})" for c in cs]


def doc_carnet(d, an):
    m = d.get("meta") or {}
    plan = sorted(an.plans["Plan retenu"], key=cle_temps)
    a_reserver = [p for p in plan if p.get("statut") == "retenue"]
    L = [f"# Carnet de voyage — {m.get('objet', '')}", "", f"Référence {m.get('reference', '')} · mis à jour le {date_fr(an.auj)}", ""]
    if an.R.erreurs:
        L += ["> **Brouillon : des contrôles sont en erreur, ne pas utiliser en l'état.**", ""]
    if a_reserver:
        L += [f"> **Carnet provisoire : {len(a_reserver)} prestation(s) encore à réserver.**", ""]
    L += entete_voyage(d, an)
    t = an.totaux["Plan retenu"]
    L += [f"- **Budget engagé** : {euros(t['total'])}" + (f" sur {euros(an.budget)} prévus" if an.budget is not None else ""), ""]
    L += ["## Réservations", ""]
    lignes = []
    for p in plan:
        r = p.get("reservation") or {}
        ref = r.get("reference") or ("à réserver" if p.get("statut") == "retenue" else "")
        lignes.append([p.get("libelle"), p.get("fournisseur"), quand(p), ref,
                       euros(r["paye"]) if isinstance(r.get("paye"), (int, float)) else "",
                       euros(r["reste_du"]) if r.get("reste_du") else ""])
    L.append(tableau(["Prestation", "Fournisseur", "Quand", "Référence", "Payé", "Reste dû"], lignes))
    L += ["", "## Jour par jour"]
    programme = {str(x.get("date")): x for x in d.get("programme") or []}
    jours = []
    if an.aller and an.retour:
        jours = [an.aller + dt.timedelta(days=k) for k in range((an.retour - an.aller).days + 1)]
    for j in jours:
        prog = programme.get(j.isoformat(), {})
        L += ["", f"### {date_fr(j, jour=True)}" + (f" — {prog['titre']}" if prog.get("titre") else ""), ""]
        items = []
        for p in plan:
            if jour_local(p) != j:
                continue
            ref = (p.get("reservation") or {}).get("reference")
            suffixe = f" Réf. {ref}." if ref else (" **À réserver.**" if p.get("statut") == "retenue" else "")
            if p.get("_horaire"):
                arr = ""
                if p.get("_fin"):
                    arr = f", arrivée {heure(p['_fin'])}" + (f" le {jour_court(p['_fin'].date())}" if p["_fin"].date() != j else "")
                lieux = " → ".join(x for x in (p.get("lieu_debut"), p.get("lieu_fin")) if x)
                items.append(f"- **{heure(p['_debut'])}** {p.get('libelle')}" + (f" : {lieux}" if lieux else "") + f"{arr}.{suffixe}")
            elif p.get("type") == "hebergement":
                items.append(f"- **Arrivée** {p.get('libelle')}" + (f", {p['adresse']}" if p.get("adresse") else "") + f".{suffixe}")
            else:
                items.append(f"- {p.get('libelle')}.{suffixe}")
        for p in plan:
            if p.get("type") == "hebergement" and p.get("_debut") and p.get("_fin") and p["_debut"] <= j < p["_fin"]:
                items.append(f"- **Nuit** : {p.get('libelle')}")
        items += [f"- {x}" for x in prog.get("deroule") or []]
        L += items or ["- Journée libre."]
    hors = [p for p in plan if jour_local(p) and jours and jour_local(p) not in jours]
    if hors:
        L += ["", "### Hors des dates du voyage", ""] + [f"- {quand(p)} : {p.get('libelle')}" for p in hors]
    L += ["", "## Formalités avant le départ", ""]
    for f in d.get("formalites") or []:
        coche = "x" if f.get("statut") in ("ok", "sans_objet") else " "
        L.append(f"- [{coche}] {f.get('pays')} : {f.get('exigence')} ({lien(f.get('source'))})")
    if not d.get("formalites"):
        L.append("_Aucune formalité consignée._")
    L += ["", "## Échéances", ""]
    ech = [e for e in an.echeances if e["date"] >= an.auj]
    L.append(tableau(["Date", "À faire"], [[jour_court(e["date"]) + (f" {e['heure']}" if e["heure"] else ""), e["texte"]] for e in ech]))
    L += ["", "## Conseils pratiques", ""] + conseils_liste(d)
    L += ["", "## Contacts utiles", ""]
    L.append(tableau(["Nom", "Rôle", "Téléphone", "E-mail", "Adresse"],
                     [[c.get("nom"), c.get("role"), c.get("telephone"), c.get("email"), c.get("adresse")] for c in d.get("contacts") or []]))
    L += ["", "## En cas d'incident", "",
          "- Garder tous les justificatifs : cartes d'embarquement, billets, reçus, photos, échanges écrits.",
          "- Vol retardé ou annulé : demander sur place l'assistance (repas, hôtel si besoin) et une attestation écrite du retard ou de l'annulation.",
          "- Bagage perdu ou abîmé : faire la déclaration au comptoir bagages de l'aéroport avant de quitter la zone d'arrivée.",
          "- Urgence dans l'Union européenne : 112. Hors Union européenne : numéros de la fiche pays et du consulat (contacts ci-dessus).",
          "- Relancer l'agence avec le mot « incident » : solutions de remplacement, droits applicables et réclamation préparée."]
    return "\n".join(L) + "\n"


# ── Calendrier (.ics) ────────────────────────────────────────────────────

def ics_texte(t):
    return str(t or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def plier(ligne):
    b, morceaux, limite = ligne.encode("utf-8"), [], 75
    while len(b) > limite:
        i = limite
        while i > 0 and (b[i] & 0xC0) == 0x80:
            i -= 1
        morceaux.append(b[:i])
        b, limite = b[i:], 74
    morceaux.append(b)
    return "\r\n ".join(x.decode("utf-8") for x in morceaux)


def doc_ics(d, an):
    ref = (d.get("meta") or {}).get("reference", "voyage")
    maintenant = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    utc = lambda x: x.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    jourc = lambda x: x.strftime("%Y%m%d")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ThinkUP//agence-voyage//FR", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]

    def evenement(uid, debut, fin, titre, lieu="", description=""):
        L.extend(["BEGIN:VEVENT", f"UID:{uid}@agence-voyage.think-up.fr", f"DTSTAMP:{maintenant}", *debut, *fin,
                  f"SUMMARY:{ics_texte(titre)}"])
        if lieu:
            L.append(f"LOCATION:{ics_texte(lieu)}")
        if description:
            L.append(f"DESCRIPTION:{ics_texte(description)}")
        L.append("END:VEVENT")

    for p in an.plans["Plan retenu"]:
        if p.get("_debut") is None:
            continue
        r = p.get("reservation") or {}
        desc = "\n".join(x for x in (f"Réf. {r['reference']}" if r.get("reference") else "À réserver",
                                     detail(p)) if x)
        if p.get("_horaire"):
            debut, fin = [f"DTSTART:{utc(p['_debut'])}"], ([f"DTEND:{utc(p['_fin'])}"] if p.get("_fin") else [])
        else:
            f = p.get("_fin") if p.get("_fin") and p["_fin"] > p["_debut"] else p["_debut"] + dt.timedelta(days=1)
            debut, fin = [f"DTSTART;VALUE=DATE:{jourc(p['_debut'])}"], [f"DTEND;VALUE=DATE:{jourc(f)}"]
        evenement(f"{ref}-{p.get('id')}", debut, fin, p.get("libelle"), p.get("lieu_debut") or p.get("adresse") or "", desc)
    for i, e in enumerate(x for x in an.echeances if x["date"] >= an.auj and x["texte"] != "Départ"):
        evenement(f"{ref}-echeance-{i + 1}", [f"DTSTART;VALUE=DATE:{jourc(e['date'])}"],
                  [f"DTEND;VALUE=DATE:{jourc(e['date'] + dt.timedelta(days=1))}"],
                  f"À faire : {e['texte']}", "", f"Avant {e['heure']}" if e["heure"] else "")
    L.append("END:VCALENDAR")
    return "\r\n".join(plier(l) for l in L) + "\r\n"


# ── Mise en forme ────────────────────────────────────────────────────────

FORMAT_MD = "markdown-auto_identifiers-subscript-superscript-tex_math_dollars"


def md_vers_html(texte):
    if shutil.which("pandoc"):
        r = subprocess.run(["pandoc", "-f", FORMAT_MD, "-t", "html5", "--columns=100000"],
                           input=texte, capture_output=True, text=True, check=True)
        return r.stdout
    try:
        import markdown
    except ImportError:
        return None
    return markdown.markdown(texte, extensions=["tables", "sane_lists"])


def page_html(corps, titre):
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{html.escape(titre)}</title>'
            f'<meta name="viewport" content="width=device-width, initial-scale=1"><style>{CSS}</style></head>'
            f'<body><div class="feuille">{corps}</div></body></html>')


def ecrire(sortie, base, texte, titre, R):
    (sortie / f"{base}.md").write_text(texte, encoding="utf-8")
    print(f"  {sortie / base}.md")
    corps = md_vers_html(texte)
    if corps is None:
        R.alerte("ni pandoc ni le module Python markdown : HTML non produit")
    else:
        (sortie / f"{base}.html").write_text(page_html(corps, titre), encoding="utf-8")
        print(f"  {sortie / base}.html")
    if shutil.which("pandoc"):
        subprocess.run(["pandoc", "-f", FORMAT_MD, "-t", "docx", "-o", str(sortie / f"{base}.docx")],
                       input=texte, text=True, check=True)
        print(f"  {sortie / base}.docx")
    else:
        R.alerte("pandoc absent : DOCX non produit")


# ── Commandes ────────────────────────────────────────────────────────────

def aujourdhui(a):
    return dt.date.fromisoformat(a.aujourdhui) if a.aujourdhui else dt.date.today()


def etape_de(d, a):
    if getattr(a, "etape", None):
        return a.etape
    st = (d.get("meta") or {}).get("statut") or "brief"
    if st not in ETAPE_DU_STATUT:
        sortir(f"meta.statut « {st} » inconnu ({', '.join(ETAPE_DU_STATUT)})")
    return ETAPE_DU_STATUT[st]


def resume(an):
    for nom, t in an.totaux.items():
        pp = f", {euros(t['par_personne'])} par personne" if t["par_personne"] is not None else ""
        print(f"  {nom} : {euros(t['total'])}{pp}, {pourcent(t['part_non_confirmee'])} non confirmé")


def exiger_ignore(dossier, racine):
    """Dépôt public : un dossier de voyage suivi par git finirait en ligne. Hors dépôt git
    (code de retour 128), rien à vérifier."""
    r = subprocess.run(["git", "check-ignore", "-q", str(dossier)], capture_output=True)
    if r.returncode == 1:
        shutil.rmtree(dossier)
        sortir(f"{dossier} n'est pas ignoré par git : ajouter « {racine}/ » au .gitignore avant tout voyage")


def cmd_init(a):
    racine = Path(a.racine)
    date = a.depart or dt.date.today().isoformat()
    ref = f"{date}-{slug(a.objet)}"
    dossier = racine / ref
    if dossier.exists():
        sortir(f"{dossier} existe déjà")
    dossier.mkdir(parents=True)
    exiger_ignore(dossier, racine)
    squelette = {
        "meta": {"reference": ref, "objet": a.objet, "nature": "", "statut": "brief",
                 "cree_le": dt.date.today().isoformat(), "fuseau_reference": "Europe/Paris"},
        "voyageurs": [],
        "brief": {"depart": "", "retour_a": "", "etapes": [], "date_aller": a.depart or "", "date_retour": "",
                  "flexibilite": "", "budget": {"montant": None, "devise": "EUR", "base": "total", "plafond_strict": False},
                  "objectif": "", "rythme": "", "hebergement": "", "transport": "", "incontournables": [], "a_eviter": [],
                  "notes": ""},
        "variantes": [], "prestations": [], "formalites": [], "conseils": [], "programme": [], "contacts": [],
        "questions_ouvertes": [], "incidents": [],
    }
    (dossier / "dossier.json").write_text(json.dumps(squelette, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (dossier / "journal.md").write_text(f"# Journal — {ref}\n\n", encoding="utf-8")
    print(dossier)
    return 0


def cmd_verifier(a):
    d = charger(a.dossier)
    etape = etape_de(d, a)
    an = Analyse(d, etape, aujourdhui(a)).lancer()
    resume(an)
    return an.R.afficher(f"Vérification ({etape})")


def cmd_construire(a):
    d = charger(a.dossier)
    etape = etape_de(d, a)
    if etape == "brief":
        sortir("rien à construire à l'étape brief : passer meta.statut à proposition une fois les formules prêtes")
    an = Analyse(d, etape, aujourdhui(a)).lancer()
    sortie = Path(a.dossier) / "livrables"
    sortie.mkdir(exist_ok=True)
    m = d.get("meta") or {}
    ref, objet = m.get("reference", "voyage"), m.get("objet", "")
    if etape == "proposition":
        ecrire(sortie, f"{ref}-proposition", doc_proposition(d, an), f"Proposition — {objet}", an.R)
    else:
        ecrire(sortie, f"{ref}-carnet", doc_carnet(d, an), f"Carnet de voyage — {objet}", an.R)
        (sortie / f"{ref}.ics").write_text(doc_ics(d, an), encoding="utf-8", newline="")
        print(f"  {sortie / ref}.ics")
    resume(an)
    return an.R.afficher(f"Construction ({etape})")


def cmd_echeances(a):
    d = charger(a.dossier)
    auj = aujourdhui(a)
    an = Analyse(d, etape_de(d, a), auj)
    E = calculer_echeances(d, an.aller, an.R)
    fin = auj + dt.timedelta(days=a.jours)
    for e in E:
        if e["date"] <= fin:
            marque = "PASSÉE " if e["date"] < auj else ""
            print(f"  {e['date'].isoformat()}{' ' + e['heure'] if e['heure'] else '      '}  {marque}{e['texte']}")
    return an.R.afficher("Échéances") if an.R.erreurs else 0


def cmd_archiver(a):
    dossier = Path(a.dossier).resolve()
    if not (dossier / "dossier.json").exists():
        sortir(f"{dossier} n'est pas un dossier de voyage (dossier.json absent)")
    cible = dossier.parent / f"{dossier.name}.zip"
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dossier.rglob("*")):
            if f.is_file():
                z.write(f, Path(dossier.name) / f.relative_to(dossier))
    print(cible)
    return 0


def cmd_restaurer(a):
    racine = Path(a.racine)
    with zipfile.ZipFile(a.archive) as z:
        noms = z.namelist()
        tetes = {Path(n).parts[0] for n in noms if n}
        if len(tetes) != 1 or any(n.startswith("/") or ".." in Path(n).parts for n in noms):
            sortir("archive inattendue : elle doit contenir un seul dossier de voyage")
        dossier = racine / tetes.pop()
        if not any(n.endswith("dossier.json") for n in noms):
            sortir("archive inattendue : dossier.json absent")
        if dossier.exists():
            sortir(f"{dossier} existe déjà")
        dossier.mkdir(parents=True)
        exiger_ignore(dossier, racine)
        z.extractall(racine)
    print(dossier)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("init")
    i.add_argument("racine", nargs="?", default="voyages")
    i.add_argument("--objet", required=True)
    i.add_argument("--depart", help="date d'aller AAAA-MM-JJ, si elle est connue")
    for nom in ("verifier", "construire", "echeances"):
        c = sp.add_parser(nom)
        c.add_argument("dossier")
        c.add_argument("--etape", choices=ETAPES if nom == "verifier" else ETAPES[1:])
        c.add_argument("--aujourdhui", help="date du jour AAAA-MM-JJ (tests)")
        if nom == "echeances":
            c.add_argument("--jours", type=int, default=60)
    z = sp.add_parser("archiver")
    z.add_argument("dossier")
    r = sp.add_parser("restaurer")
    r.add_argument("archive")
    r.add_argument("racine", nargs="?", default="voyages")
    a = p.parse_args()
    return {"init": cmd_init, "verifier": cmd_verifier, "construire": cmd_construire, "echeances": cmd_echeances,
            "archiver": cmd_archiver, "restaurer": cmd_restaurer}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
