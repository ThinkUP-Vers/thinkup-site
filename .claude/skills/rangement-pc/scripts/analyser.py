#!/usr/bin/env python3
"""Analyse d'un inventaire de poste Windows (produit par inventaire.ps1) pour le skill rangement-pc.

    analyser.py analyser <inventaire.json|.zip> --sortie DOSSIER [--aujourdhui AAAA-MM-JJ]

Produit dans DOSSIER : rapport.md, rapport.docx, plan.csv (déplacements proposés), appliquer-plan.ps1
(à lancer sur le poste : simulation par défaut), stats.json.

Principes : le script ne supprime rien et ne propose que des déplacements vers deux dossiers de
quarantaine / de tri ; tout le reste est une recommandation à décider. Il n'écrit jamais dans un dépôt git
(les noms de fichiers peuvent contenir des noms de clients).
"""
import argparse
import collections
import csv
import datetime as dt
import json
import re
import sys
import zipfile
from pathlib import Path, PureWindowsPath

JOURS_RECENT = 14          # modifié depuis moins de N jours : jamais touché
JOURS_INSTALLEUR = 60      # installeur dans Téléchargements plus vieux que N jours : quarantaine
JOURS_VIEUX_TELECH = 180   # autre fichier de Téléchargements plus vieux que N jours : à trier
JOURS_ARCHIVE = 365 * 3    # non modifié depuis N jours : candidat à l'archivage (recommandation seule)
TAILLE_MIN_DOUBLON = 10 * 1024
SEUIL_DISQUE_LIBRE = 0.15

CATEGORIES = {
    "Documents": {"doc", "docx", "odt", "rtf", "txt", "md", "pdf", "pages"},
    "Tableurs": {"xls", "xlsx", "xlsm", "csv", "ods", "numbers"},
    "Presentations": {"ppt", "pptx", "odp", "key"},
    "Images": {"jpg", "jpeg", "png", "gif", "bmp", "webp", "heic", "svg", "tif", "tiff", "psd", "ai", "raw"},
    "Videos": {"mp4", "mov", "avi", "mkv", "wmv", "webm"},
    "Audio": {"mp3", "wav", "m4a", "flac", "aac", "ogg"},
    "Archives": {"zip", "rar", "7z", "tar", "gz"},
    "Installeurs": {"exe", "msi", "iso", "dmg", "msix", "appx"},
    "Code-et-donnees": {"py", "js", "ts", "html", "css", "json", "xml", "php", "ps1", "sh", "sql", "yml", "yaml"},
}
EXT_VERS_CAT = {e: c for c, es in CATEGORIES.items() for e in es}
TEMPORAIRES = re.compile(r"(\.tmp$|^~\$|\.crdownload$|\.part$)", re.I)
IGNORES = {"desktop.ini", "thumbs.db", ".ds_store"}
MOTIFS_NOMS = [
    ("copie / doublon manuel", re.compile(r"(\(\d+\)|[ _-]copie\b|^copie de |[ _-]copy\b)", re.I)),
    ("version floue (final, v2, nouveau)", re.compile(r"(final|definitif|définitif|nouveau|new|v\d+|version\d*)(?=[ ._-]|$)", re.I)),
    ("sans titre / générique", re.compile(r"^(sans titre|untitled|document\d*|nouveau document|image\d*|scan\d*|img[_-]?\d+)", re.I)),
]
STRUCTURE = [
    "00_Inbox : tout ce qui arrive (téléchargements, exports) ; vidé chaque semaine",
    "10_ThinkUP : Clients\\<Client>\\<AAAA-MM_Mission>, Offres, Marketing, Admin-Compta",
    "20_PL-Holding : Juridique, Compta, Participations",
    "30_Perso : Administratif, Voyages (voyages hors du dépôt), Santé, Finances",
    "40_Ressources : modèles, documentation, formations",
    "90_Archives\\AAAA : tout ce qui est clos, rangé par année de clôture",
]


# ---------------------------------------------------------------- utilitaires
def norm(p):
    return (p or "").replace("/", "\\").rstrip("\\")


def cle(p):
    return norm(p).casefold()


def depot_git(chemin):
    chemin = Path(chemin).expanduser().resolve()
    for dossier in (chemin, *chemin.parents):
        if (dossier / ".git").exists():
            return dossier
    return None


def taille_h(o):
    o = float(o or 0)
    for u in ("o", "Ko", "Mo", "Go", "To"):
        if o < 1024 or u == "To":
            return ("%d %s" % (o, u)) if u == "o" else ("%.1f %s" % (o, u))
        o /= 1024


def charger(chemin):
    chemin = Path(chemin).expanduser()
    if chemin.suffix.lower() == ".zip":
        with zipfile.ZipFile(chemin) as z:
            noms = [n for n in z.namelist() if n.lower().endswith(".json")]
            if not noms:
                sys.exit("Aucun .json dans l'archive.")
            return json.loads(z.read(noms[0]).decode("utf-8-sig"))
    return json.loads(chemin.read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------- préparation
def preparer(inv, aujourdhui):
    racines = sorted(inv.get("racines", []), key=lambda r: -len(norm(r["chemin"])))
    git = [cle(g) for g in inv.get("depots_git", [])]
    fichiers = []
    for f in inv.get("fichiers", []):
        chemin = norm(f["c"])
        p = PureWindowsPath(chemin)
        c = cle(chemin)
        role, racine = "autre", None
        for r in racines:
            rc = cle(r["chemin"])
            if c.startswith(rc + "\\"):
                role, racine = r["role"], norm(r["chemin"])
                break
        try:
            age = (aujourdhui - dt.date.fromisoformat(f["m"])).days
        except (ValueError, TypeError):
            age = 0
        ext = p.suffix.lower().lstrip(".")
        fichiers.append({
            "chemin": chemin, "nom": p.name, "ext": ext, "taille": int(f.get("t") or 0),
            "modifie": f.get("m"), "age": age, "hash": f.get("h"), "role": role, "racine": racine,
            "dossier": norm(str(p.parent)), "cat": EXT_VERS_CAT.get(ext, "Autres"),
            "git": any(c.startswith(g + "\\") for g in git),
        })
    return fichiers, racines


def racine_de(racines, role):
    for r in racines:
        if r["role"] == role:
            return norm(r["chemin"])
    return None


# ---------------------------------------------------------------- analyses
def doublons(fichiers):
    groupes = collections.defaultdict(list)
    for f in fichiers:
        if f["hash"] and f["taille"] >= TAILLE_MIN_DOUBLON and not f["git"] and f["nom"].casefold() not in IGNORES:
            groupes[(f["taille"], f["hash"])].append(f)
    sortie = []
    for (taille, h), lot in groupes.items():
        if len(lot) < 2:
            continue
        def vrac(f):
            return f["role"] in ("bureau", "telechargements") and f["dossier"].casefold() == (f["racine"] or "").casefold()
        lot.sort(key=lambda f: (vrac(f), f["role"] == "telechargements", -f["chemin"].count("\\"), len(f["chemin"])))
        sortie.append({"taille": taille, "hash": h, "garder": lot[0], "autres": lot[1:]})
    sortie.sort(key=lambda g: -g["taille"] * len(g["autres"]))
    return sortie


def construire_plan(fichiers, racines, grp_doublons, aujourdhui):
    # Destination locale, hors OneDrive : y déplacer des Go les ferait synchroniser dans le nuage.
    dl = racine_de(racines, "telechargements")
    base = norm(str(PureWindowsPath(dl).parent)) + "\\Rangement" if dl else racine_de(racines, "documents") + "\\Rangement"
    jour = aujourdhui.isoformat()
    quarantaine = "%s\\_Quarantaine\\%s" % (base, jour)
    a_trier = "%s\\_A-trier\\%s" % (base, jour)
    plan, pris = [], set()

    def ajouter(f, type_, dest, raison):
        # Seuls les fichiers posés à la racine d'un dossier suivi sont déplacés : les sous-dossiers
        # (projets, archives décompressées) se décident à la main, sinon on les casse.
        if SECRET_FICHIER.match(f["nom"]):
            return  # traité par le plan de sécurité, jamais par le plan général
        if f["chemin"] in pris or f["age"] < JOURS_RECENT or f["git"] or f["dossier"].casefold() != (f["racine"] or "").casefold():
            return
        pris.add(f["chemin"])
        plan.append({"type": type_, "source": f["chemin"], "destination": dest, "taille": f["taille"], "raison": raison})

    for f in fichiers:
        if f["nom"].casefold() in IGNORES:
            continue
        if TEMPORAIRES.search(f["nom"]):
            ajouter(f, "temporaire", "%s\\temporaires\\%s" % (quarantaine, f["nom"]), "fichier temporaire ou verrou Office")
    for g in grp_doublons:
        for f in g["autres"]:
            ajouter(f, "doublon", "%s\\doublons\\%s_%s" % (quarantaine, g["hash"][:8], f["nom"]),
                    "copie identique de %s" % g["garder"]["chemin"])
    for f in fichiers:
        if f["nom"].casefold() in IGNORES or f["ext"] in ("lnk", "url", "bat", "cmd"):
            continue
        if f["role"] == "telechargements" and f["cat"] == "Installeurs" and f["age"] > JOURS_INSTALLEUR:
            ajouter(f, "installeur", "%s\\installeurs\\%s" % (quarantaine, f["nom"]),
                    "installeur de plus de %d jours" % JOURS_INSTALLEUR)
        elif f["role"] == "bureau" and f["dossier"].casefold() == (f["racine"] or "").casefold():
            ajouter(f, "bureau", "%s\\Bureau\\%s\\%s" % (a_trier, f["cat"], f["nom"]), "fichier posé en vrac sur le Bureau")
        elif f["role"] == "telechargements" and f["age"] > JOURS_VIEUX_TELECH:
            ajouter(f, "telechargement", "%s\\Telechargements\\%s\\%s" % (a_trier, f["cat"], f["nom"]),
                    "téléchargement de plus de %d jours" % JOURS_VIEUX_TELECH)
    return plan, quarantaine, a_trier


def plan_securite(fichiers, racines):
    """Secrets (jetons, clés) hors OneDrive et Téléchargements ; .pst hors OneDrive. Déplacements seulement."""
    dl = racine_de(racines, "telechargements")
    profil = norm(str(PureWindowsPath(dl).parent)) if dl else "C:\\Users"
    bruit = ("\\vendor\\", "\\node_modules\\", "\\wp-includes\\", "\\wp-content\\", "\\site-packages\\")
    plan = []
    for f in fichiers:
        c = f["chemin"].casefold()
        if f["git"] or any(b in c for b in bruit):
            continue
        dans_nuage = "\\onedrive\\" in c
        if SECRET_FICHIER.match(f["nom"]) and (dans_nuage or f["role"] == "telechargements"):
            plan.append({"type": "secret", "source": f["chemin"], "destination": "%s\\.secrets\\a-classer\\%s_%s" % (profil, f["modifie"], f["nom"]),
                         "taille": f["taille"], "raison": "secret ou clé hors dossier synchronisé"})
        elif f["ext"] == "pst" and dans_nuage:
            plan.append({"type": "pst", "source": f["chemin"], "destination": "%s\\Sauvegardes-locales\\pst\\%s" % (profil, f["nom"]),
                         "taille": f["taille"], "raison": "archive Outlook : à garder hors OneDrive (Outlook fermé)"})
    return plan


def dossiers_vides(inv, fichiers):
    ancetres = set()
    for f in fichiers:
        p = PureWindowsPath(f["chemin"])
        for a in p.parents:
            ancetres.add(cle(str(a)))
    git = [cle(g) for g in inv.get("depots_git", [])]
    vides = []
    for d in inv.get("dossiers", []):
        c = cle(d)
        if c not in ancetres and not any(c == g or c.startswith(g + "\\") for g in git):
            vides.append(norm(d))
    return vides


def dossiers_du_bureau(fichiers, racine_bureau):
    if not racine_bureau:
        return []
    cumul = {}
    for f in fichiers:
        if f["role"] != "bureau":
            continue
        rel = f["chemin"][len(racine_bureau) + 1:]
        if "\\" not in rel:
            continue
        haut = rel.split("\\", 1)[0]
        d = cumul.setdefault(haut, {"nom": haut, "fichiers": 0, "taille": 0, "recent": 10 ** 9})
        d["fichiers"] += 1
        d["taille"] += f["taille"]
        d["recent"] = min(d["recent"], f["age"])
    return sorted(cumul.values(), key=lambda d: -d["recent"])


def poids_dossiers(fichiers):
    cumul = collections.Counter()
    for f in fichiers:
        if f["racine"] and not f["git"]:
            rel = f["chemin"][len(f["racine"]) + 1:]
            haut = rel.split("\\", 1)[0] if "\\" in rel else "(à la racine)"
            cumul["%s\\%s" % (f["racine"], haut) if haut != "(à la racine)" else f["racine"] + " (en vrac)"] += f["taille"]
    return cumul.most_common(10)


SENSIBLES = re.compile(r"(credential|secret|token|api[_-]?key|\.env$|id_rsa|\.pem$|\.pfx$|\.p12$|\.kdbx$|\.pst$|password|mot ?de ?passe|\bmdp\b|"
                       r"passeport|passport|carte.?d.?identit|\bcni\b|avis.?d.?imposition|\brib\b|\biban\b|\bsepa\b|mandat|\bkbis\b|acte.?de.?(naissance|d[eé]c[eè]s))", re.I)


SECRET_FICHIER = re.compile(r"^(credentials?([ _-]?\(\d+\))?\.json|token([ _-]?\(\d+\))?\.json|client_secrets?[^\\]*\.json|\.env|id_rsa|id_ed25519|.*\.(pem|pfx|p12|kdbx|key))$", re.I)


def sensibles_nuage(fichiers):
    """Noms évoquant des secrets ou des pièces d'identité/bancaires dans un dossier synchronisé OneDrive."""
    code = {"php", "js", "mjs", "css", "map", "ts", "tsx", "py", "pyc", "html", "htm", "md", "twig", "scss", "less", "svg", "po", "mo"}
    bruit = ("\\vendor\\", "\\node_modules\\", "\\wp-includes\\", "\\wp-content\\", "\\site-packages\\")
    sortie = []
    for f in fichiers:
        c = f["chemin"].casefold()
        if f["git"] or "\\onedrive\\" not in c:
            continue
        if f["nom"].casefold() == "wp-config.php" or (f["ext"] not in code and not any(b in c for b in bruit) and SENSIBLES.search(f["nom"])):
            sortie.append(f)
    return sortie


def apps_a_revoir(apps):
    bruit = re.compile(r"(redistributable|runtime|update|c\+\+|\.net|driver|pilote|webview)", re.I)
    familles = collections.defaultdict(list)
    for a in apps:
        if bruit.search(a.get("nom", "")):
            continue
        mot = re.split(r"[\s\-_]+", a["nom"].strip())[0].casefold()
        if len(mot) >= 3:
            familles[mot].append(a)
    multi = {k: v for k, v in familles.items() if len(v) > 1}
    return multi


# ---------------------------------------------------------------- rapport
def rapport_blocs(inv, fichiers, racines, grp, plan, vides, bureau_dossiers, aujourdhui, quarantaine, a_trier):
    b = [("titre", "Rapport de rangement du poste")]
    actifs = [f for f in fichiers if not f["git"]]
    total = sum(f["taille"] for f in fichiers)
    b.append(("p", "Inventaire du %s (analysé le %s) : %d fichiers, %s, dans %d dossiers racines. %d dépôts git détectés "
              "et laissés intacts. Données issues des noms, tailles et dates ; aucun contenu n'a été lu."
              % ((inv.get("genere") or "?")[:10], aujourdhui.isoformat(), len(fichiers), taille_h(total),
                 len(racines), len(inv.get("depots_git", [])))))

    # Synthèse
    gain_dbl = sum(g["taille"] * len(g["autres"]) for g in grp)
    n_dbl = sum(len(g["autres"]) for g in grp)
    par_type = collections.Counter(p["type"] for p in plan)
    b.append(("h1", "1. Synthèse"))
    b.append(("table", ["Constat", "Mesure"], [
        ["Fichiers en vrac sur le Bureau", str(sum(1 for p in plan if p["type"] == "bureau")) + " à ranger (hors fichiers de moins de %d jours et raccourcis)" % JOURS_RECENT],
        ["Doublons exacts (même taille et même empreinte, ≥ 10 Ko)", "%d copies superflues dans %d groupes, %s récupérables" % (n_dbl, len(grp), taille_h(gain_dbl))],
        ["Installeurs anciens dans Téléchargements", "%d fichiers, %s" % (par_type["installeur"], taille_h(sum(p["taille"] for p in plan if p["type"] == "installeur")))],
        ["Téléchargements anciens (> %d jours)" % JOURS_VIEUX_TELECH, "%d fichiers à trier" % par_type["telechargement"]],
        ["Fichiers temporaires / verrous Office", "%d fichiers" % par_type["temporaire"]],
        ["Dossiers vides", str(len(vides))],
        ["Déplacements proposés au total", "%d (%s), aucun fichier supprimé" % (len(plan), taille_h(sum(p["taille"] for p in plan)))],
    ], [4200, 5400]))

    # Disques
    b.append(("h1", "2. Disques"))
    lignes, alertes = [], []
    for d in inv.get("disques", []):
        part = d["libre"] / d["taille"] if d["taille"] else 0
        lignes.append([d["lettre"], taille_h(d["taille"]), taille_h(d["libre"]), "%d %%" % round(part * 100)])
        if part < SEUIL_DISQUE_LIBRE:
            alertes.append(d["lettre"])
    if lignes:
        b.append(("table", ["Disque", "Taille", "Libre", "Part libre"], lignes, [1800, 2600, 2600, 2600]))
    if alertes:
        b.append(("p", "Attention : moins de %d %% d'espace libre sur %s. Windows et les mises à jour ralentissent nettement sous ce seuil."
                  % (SEUIL_DISQUE_LIBRE * 100, ", ".join(alertes))))

    # Bureau
    rb = racine_de(racines, "bureau")
    b.append(("h1", "3. Bureau"))
    vrac = [f for f in fichiers if f["role"] == "bureau" and rb and f["dossier"].casefold() == rb.casefold()]
    raccourcis = [f for f in vrac if f["ext"] == "lnk"]
    cats = collections.Counter(f["cat"] for f in vrac if f["ext"] != "lnk" and f["nom"].casefold() not in IGNORES)
    b.append(("p", "%d fichiers en vrac (dont %d raccourcis, conservés) et %d sous-dossiers. Répartition des fichiers en vrac : %s."
              % (len(vrac), len(raccourcis), len(bureau_dossiers), ", ".join("%s %d" % c for c in cats.most_common()) or "aucun")))
    if bureau_dossiers:
        b.append(("table", ["Sous-dossier du Bureau", "Fichiers", "Taille", "Dernière modif. (jours)"],
                  [[d["nom"], str(d["fichiers"]), taille_h(d["taille"]), str(d["recent"])] for d in bureau_dossiers[:15]],
                  [4200, 1400, 1800, 2200]))
        b.append(("p", "Les sous-dossiers du Bureau ne sont pas déplacés automatiquement : tu décides, dossier par dossier, entre rangement "
                  "dans la structure cible, archivage ou suppression."))

    # Doublons
    b.append(("h1", "4. Doublons exacts"))
    if grp:
        b.append(("table", ["Taille", "Copies", "Copie conservée", "Copies à mettre en quarantaine"],
                  [[taille_h(g["taille"]), str(len(g["autres"]) + 1), g["garder"]["chemin"], "; ".join(f["chemin"] for f in g["autres"][:3]) +
                    (" …" if len(g["autres"]) > 3 else "")] for g in grp[:15]], [1200, 900, 3600, 3900]))
        b.append(("p", "La copie conservée est celle qui est rangée (hors vrac à la racine du Bureau ou de Téléchargements), la plus profonde en cas d'égalité. Seules les copies à la racine du Bureau, de Téléchargements ou de Documents sont déplacées. "
                  "Vérifie les cas où deux copies sont dans des dossiers de clients différents : l'identité du contenu ne dit pas laquelle fait foi."))
    else:
        b.append(("p", "Aucun doublon détecté. Si l'inventaire a été lancé avec -SansEmpreintes, cette analyse est vide par construction."))

    # Poids et ancienneté
    b.append(("h1", "5. Où est la place, et ce qui dort"))
    b.append(("table", ["Dossier", "Poids"], [[c, taille_h(t)] for c, t in poids_dossiers(fichiers)], [7000, 2600]))
    gros = sorted((f for f in actifs), key=lambda f: -f["taille"])[:12]
    b.append(("table", ["Plus gros fichiers", "Taille", "Modifié"], [[f["chemin"], taille_h(f["taille"]), f["modifie"] or "?"] for f in gros], [6200, 1500, 1900]))
    dormants = [f for f in actifs if f["age"] > JOURS_ARCHIVE and f["role"] in ("documents", "onedrive", "autre")]
    b.append(("p", "%d fichiers (%s) de Documents / OneDrive / autres racines n'ont pas été modifiés depuis plus de %d ans. Recommandation : "
              "les ranger dans 90_Archives\\AAAA après ton coup d'œil, pas les supprimer sur la seule ancienneté."
              % (len(dormants), taille_h(sum(f["taille"] for f in dormants)), JOURS_ARCHIVE // 365)))
    b.append(("p", "%d dossiers vides détectés (liste dans stats.json) : suppression sans risque après vérification." % len(vides)))

    # Sensibles
    sens = sensibles_nuage(fichiers)
    b.append(("h1", "Fichiers au nom sensible dans OneDrive"))
    if sens:
        b.append(("p", "%d fichiers dont le nom évoque un secret, une pièce d'identité ou un document bancaire sont dans un dossier synchronisé "
                  "dans le nuage. Le contenu n'a pas été lu : un nom ne prouve rien, mais les fichiers de type credentials, clés et .pst sont "
                  "à sortir de OneDrive d'abord." % len(sens)))
        secret = re.compile(r"(credential|secret|token|api[_-]?key|\.env$|id_rsa|\.pem$|\.pfx$|\.p12$|\.kdbx$|\.pst$|wp-config|password|mot ?de ?passe|\bmdp\b)", re.I)
        sens.sort(key=lambda f: (not secret.search(f["nom"]), f["chemin"]))
        b.append(("table", ["Fichier", "Modifié"], [[f["chemin"], f["modifie"] or "?"] for f in sens[:60]], [8000, 1600]))
        if len(sens) > 60:
            b.append(("p", "%d autres fichiers du même type non listés." % (len(sens) - 60)))
    else:
        b.append(("p", "Aucun nom de ce type détecté."))

    # Nommage
    b.append(("h1", "6. Nommage"))
    lignes = []
    for libelle, motif in MOTIFS_NOMS:
        trouves = [f for f in actifs if motif.search(PureWindowsPath(f["nom"]).stem)]
        if trouves:
            lignes.append([libelle, str(len(trouves)), "; ".join(f["nom"] for f in trouves[:3])])
    b.append(("table", ["Motif", "Fichiers", "Exemples"], lignes or [["aucun", "0", ""]], [3200, 1200, 5200]))
    b.append(("p", "Convention proposée : AAAA-MM-JJ_Client_Objet_vN.ext (date en tête pour le tri chronologique, pas d'accent ni d'espace). "
              "Le renommage de masse n'est pas automatisé : il casserait les liens et les raccourcis."))

    # Applications et démarrage
    apps = inv.get("applications", [])
    b.append(("h1", "7. Applications et démarrage"))
    b.append(("p", "%d applications installées, %d programmes lancés au démarrage." % (len(apps), len(inv.get("demarrage", [])))))
    gros_apps = sorted(apps, key=lambda a: -(a.get("taille_mo") or 0))[:10]
    b.append(("table", ["Application", "Version", "Taille (Mo)"], [[a["nom"], a.get("version") or "", str(a.get("taille_mo") or "?")] for a in gros_apps], [5600, 2000, 2000]))
    multi = apps_a_revoir(apps)
    if multi:
        b.append(("p", "Familles présentes en plusieurs exemplaires (à vérifier, versions ou doublons) : " +
                  " ; ".join("%s (%d)" % (v[0]["nom"].split()[0], len(v)) for v in multi.values()) + "."))
    if inv.get("demarrage"):
        b.append(("table", ["Lancé au démarrage", "Commande"], [[d["nom"], d["commande"][:80]] for d in inv["demarrage"]], [3000, 6600]))
    b.append(("p", "Le script ne mesure pas l'usage réel d'une application : la liste des candidats à la désinstallation vient de toi "
              "(dernière fois utilisée ?), pas de l'inventaire."))
    if inv.get("claude_skills"):
        b.append(("p", "Skills Claude présents sur le poste : %s." % ", ".join(inv["claude_skills"])))

    # Plan
    b.append(("h1", "8. Structure cible"))
    for s in STRUCTURE:
        b.append(("li", s))
    b.append(("h1", "9. Marche à suivre"))
    for etape in [
        "Dans le dossier du rapport, ouvre plan.csv avec Excel : une ligne par déplacement proposé (type, source, destination, raison). Supprime les lignes que tu ne veux pas, enregistre.",
        "Ferme Word, Excel et PowerPoint (les fichiers ouverts ne se déplacent pas).",
        "Simulation : ouvre PowerShell (menu Démarrer, tape PowerShell, Entrée), puis lance : powershell -ExecutionPolicy Bypass -File \"<chemin>\\appliquer-plan.ps1\". Résultat attendu : la liste des déplacements, marquée SIMULATION, rien n'a bougé.",
        "Exécution réelle : même commande avec -Appliquer à la fin. Résultat attendu : un fichier journal-deplacements.csv à côté du script.",
        "Contrôle : ouvre %s et %s, vérifie que ce qui s'y trouve est bien à sa place." % (quarantaine, a_trier),
        "Retour arrière si besoin : même commande avec -Annuler à la fin ; chaque déplacement du journal est rejoué en sens inverse.",
        "Attendre 30 jours, puis supprimer toi-même le dossier _Quarantaine s'il n'a rien fait manquer. Le script ne supprime jamais rien.",
        "Reprends l'inventaire dans un mois : le Bureau et Téléchargements se re-remplissent si la règle « vidé chaque semaine » n'est pas tenue.",
    ]:
        b.append(("ol", etape))
    if inv.get("ignores_liste"):
        b.append(("h1", "Éléments ignorés par l'inventaire"))
        b.append(("p", "%d éléments (liens symboliques, jonctions) n'ont pas été parcourus, ce qui peut cacher des dossiers entiers : %s."
                  % (inv.get("ignores", 0), " ; ".join(inv["ignores_liste"][:15]))))
    b.append(("h1", "10. Limites"))
    for l in [
        "Les doublons ne sont détectés qu'entre fichiers de même taille et de même empreinte SHA-256 tronquée à 96 bits : fiable, mais une copie modifiée d'un octet n'est pas un doublon.",
        "La date de dernière modification n'est pas la date de dernière ouverture : un modèle utilisé chaque mois mais jamais modifié paraît dormant.",
        "Les fichiers « Disponibles en ligne uniquement » d'OneDrive apparaissent avec leur vraie taille mais ne sont pas sur le disque ; les déplacer les télécharge.",
        "Hors périmètre : mails, Drive, Notion, navigateurs, téléphone. Drive peut être inventorié séparément par le connecteur (métadonnées).",
    ]:
        b.append(("li", l))
    return b


def blocs_md(blocs):
    sortie, n = [], 0
    for bloc in blocs:
        g = bloc[0]
        if g == "titre":
            sortie.append("# " + bloc[1])
        elif g == "h1":
            sortie.append("\n## " + bloc[1])
        elif g == "li":
            sortie.append("- " + bloc[1])
        elif g == "ol":
            n += 1
            sortie.append("%d. %s" % (n, bloc[1]))
        elif g == "table":
            sortie.append("\n| " + " | ".join(bloc[1]) + " |")
            sortie.append("|" + "---|" * len(bloc[1]))
            for l in bloc[2]:
                sortie.append("| " + " | ".join(c.replace("|", "/") for c in l) + " |")
            sortie.append("")
        else:
            sortie.append("\n" + bloc[1])
        if g != "ol":
            n = 0
    return "\n".join(sortie) + "\n"


def blocs_docx(blocs, chemin):
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError:
        print("python-docx absent : rapport.docx non produit (rapport.md disponible).")
        return False
    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(10.5)
    for bloc in blocs:
        g = bloc[0]
        if g == "titre":
            doc.add_heading(bloc[1], 0)
        elif g == "h1":
            doc.add_heading(bloc[1], 1)
        elif g == "li":
            doc.add_paragraph(bloc[1], style="List Bullet")
        elif g == "ol":
            doc.add_paragraph(bloc[1], style="List Number")
        elif g == "table":
            t = doc.add_table(rows=1, cols=len(bloc[1]))
            t.style = "Light Grid Accent 1"
            for i, h in enumerate(bloc[1]):
                t.rows[0].cells[i].text = h
            for l in bloc[2]:
                cells = t.add_row().cells
                for i, c in enumerate(l):
                    cells[i].text = c
            doc.add_paragraph()
        else:
            doc.add_paragraph(bloc[1])
    doc.save(chemin)
    return True


PS_APPLIQUER = r'''<#
 appliquer-plan.ps1 - Applique plan.csv : DEPLACE des fichiers, ne supprime rien.
   (sans option)  simulation, rien ne bouge
   -Appliquer     deplace et ecrit journal-deplacements.csv
   -Annuler       rejoue le journal en sens inverse
 Fichier volontairement sans accents (PowerShell 5.1 lit mal l'UTF-8 sans BOM).
#>
param([switch]$Appliquer, [switch]$Annuler)
$ErrorActionPreference = 'Continue'
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
$plan = Join-Path $ici 'plan.csv'
$journal = Join-Path $ici 'journal-deplacements.csv'

function Chemin-Libre([string]$cible) {
    if (-not (Test-Path -LiteralPath $cible)) { return $cible }
    $dir = Split-Path -Parent $cible
    $base = [IO.Path]::GetFileNameWithoutExtension($cible)
    $ext = [IO.Path]::GetExtension($cible)
    $i = 1
    do { $essai = Join-Path $dir ("{0} ({1}){2}" -f $base, $i, $ext); $i++ } while (Test-Path -LiteralPath $essai)
    return $essai
}

if ($Annuler) {
    if (-not (Test-Path $journal)) { Write-Host "Pas de journal : rien a annuler."; exit }
    $lignes = @(Import-Csv -LiteralPath $journal -Encoding UTF8)
    [array]::Reverse($lignes)
    foreach ($l in $lignes) {
        if (Test-Path -LiteralPath $l.destination) {
            $retour = Chemin-Libre $l.source
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $retour) | Out-Null
            Move-Item -LiteralPath $l.destination -Destination $retour
            Write-Host "RETABLI  $retour"
        }
    }
    exit
}

$lignes = @(Import-Csv -LiteralPath $plan -Encoding UTF8)
$mode = if ($Appliquer) { 'EXECUTION' } else { 'SIMULATION' }
Write-Host ("{0} : {1} deplacements" -f $mode, $lignes.Count)
$faits = New-Object System.Collections.ArrayList
foreach ($l in $lignes) {
    if (-not (Test-Path -LiteralPath $l.source)) { Write-Host "ABSENT   $($l.source)"; continue }
    $dest = Chemin-Libre $l.destination
    if ($Appliquer) {
        try {
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
            Move-Item -LiteralPath $l.source -Destination $dest -ErrorAction Stop
            [void]$faits.Add([pscustomobject]@{ source = $l.source; destination = $dest; date = (Get-Date -Format s) })
            Write-Host "DEPLACE  $($l.source) -> $dest"
        } catch { Write-Host "ECHEC    $($l.source) : $($_.Exception.Message)" }
    } else {
        Write-Host "SIMULATION  $($l.source) -> $dest"
    }
}
if ($Appliquer -and $faits.Count -gt 0) {
    $faits | Export-Csv -LiteralPath $journal -NoTypeInformation -Encoding UTF8 -Append
    Write-Host ("{0} deplacements journalises dans {1}" -f $faits.Count, $journal)
}
'''


def commande_analyser(args):
    sortie = Path(args.sortie).expanduser().resolve()
    depot = depot_git(sortie)
    if depot:
        sys.exit("REFUS : %s est dans le dépôt git %s. Les noms de fichiers peuvent contenir des noms de clients ; "
                 "choisis un dossier hors dépôt." % (sortie, depot))
    sortie.mkdir(parents=True, exist_ok=True)
    aujourdhui = dt.date.fromisoformat(args.aujourdhui) if args.aujourdhui else dt.date.today()
    inv = charger(args.inventaire)
    fichiers, racines = preparer(inv, aujourdhui)
    if not fichiers:
        sys.exit("Inventaire vide.")
    grp = doublons(fichiers)
    plan, quarantaine, a_trier = construire_plan(fichiers, racines, grp, aujourdhui)
    vides = dossiers_vides(inv, fichiers)
    bureau_dossiers = dossiers_du_bureau(fichiers, racine_de(racines, "bureau"))
    blocs = rapport_blocs(inv, fichiers, racines, grp, plan, vides, bureau_dossiers, aujourdhui, quarantaine, a_trier)
    (sortie / "rapport.md").write_text(blocs_md(blocs), encoding="utf-8")
    blocs_docx(blocs, sortie / "rapport.docx")
    with open(sortie / "plan.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["type", "source", "destination", "taille", "raison"])
        w.writeheader()
        w.writerows(plan)
    (sortie / "appliquer-plan.ps1").write_text(PS_APPLIQUER, encoding="ascii")
    securite = plan_securite(fichiers, racines)
    if securite:
        (sortie / "securite").mkdir(exist_ok=True)
        with open(sortie / "securite" / "plan.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["type", "source", "destination", "taille", "raison"])
            w.writeheader()
            w.writerows(securite)
        (sortie / "securite" / "appliquer-plan.ps1").write_text(PS_APPLIQUER, encoding="ascii")
    (sortie / "stats.json").write_text(json.dumps({
        "fichiers": len(fichiers), "plan": len(plan), "doublons_groupes": len(grp), "dossiers_vides": vides[:200],
        "quarantaine": quarantaine, "a_trier": a_trier}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK : %d fichiers analysés, %d déplacements proposés, %d groupes de doublons, %d dossiers vides, %d déplacements de sécurité -> %s"
          % (len(fichiers), len(plan), len(grp), len(vides), len(securite), sortie))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("analyser")
    a.add_argument("inventaire")
    a.add_argument("--sortie", required=True)
    a.add_argument("--aujourdhui")
    a.set_defaults(fn=commande_analyser)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
