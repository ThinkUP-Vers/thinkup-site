#!/usr/bin/env python3
"""Extraction des signaux des sessions Claude Code et rapport improve-system.

  python3 analyser.py extraire [--jours 7] [--racine ~/.claude/projects]
                               [--aujourdhui AAAA-MM-JJ] --sortie DOSSIER
      Lit les transcripts .jsonl en lecture seule et écrit DOSSIER/signaux.json
      (données complètes) et DOSSIER/resume.txt (vue compacte à lire en entier).
      Chaque signal porte un identifiant stable : D demande, C commande,
      E erreur d'outil, R refus d'une action, I interruption, A erreur d'API.

  python3 analyser.py cloud-sessions LISTE [LISTE…] [--jours 7] --sortie DOSSIER_CLOUD
      Mode cloud : lit la sortie enregistrée de list_sessions, garde les sessions actives
      sur la période (hors session en cours) et écrit DOSSIER_CLOUD/sessions-cloud.json.

  python3 analyser.py extraire --cloud DOSSIER_CLOUD [--jours 7] --sortie DOSSIER
      Mode cloud : même sortie que ci-dessus, à partir des tours écrits par les agents
      lecteurs (agent lecteur-session-cloud), un fichier .jsonl par session.

  python3 analyser.py rapport PROPOSITIONS.json --signaux DOSSIER/signaux.json
                              --sortie ~/rapports-improve-system
      Contrôle les propositions (deux exemples tirés des signaux, de deux
      sessions distinctes) et écrit improve-system-AAAA-MM-JJ.md et .json.
      Code retour 1 et liste des erreurs si le fichier n'est pas conforme.

  python3 analyser.py paquet DOSSIER_SKILL --sortie DOSSIER
      Contrôle l'en-tête d'un skill (nom, description d'une ligne de 200 caractères au plus)
      et écrit DOSSIER/<nom>.zip, à téléverser dans claude.ai (Personnaliser > Skills).

Aucune date ni citation n'est saisie à la main : elles viennent des
transcripts. Le script n'écrit jamais dans un dépôt git : les extraits
peuvent contenir des noms de clients ou des données personnelles.
"""

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import zipfile
import zlib
from pathlib import Path

FORMES = {
    "nouveau-skill": "Nouveau skill",
    "skill-existant": "Amélioration d'un skill existant",
    "regle": "Règle (CLAUDE.md ou préférences)",
    "hook": "Hook (automatisme)",
}
NATURES = {"echec": "échec", "correction": "correction répétée", "recurrence": "tâche récurrente"}
PRIORITES = ("haute", "moyenne", "basse")
CERTITUDES = ("confirmé", "probable", "incertain", "spéculatif")
MAX_PROPOSITIONS = 7

COMMANDES_INTEGREES = {
    "add-dir", "agents", "bug", "clear", "compact", "config", "context", "cost", "doctor", "exit",
    "export", "help", "hooks", "init", "login", "logout", "mcp", "memory", "model", "permissions",
    "plugin", "pr-comments", "release-notes", "resume", "review", "rewind", "status", "statusline",
    "terminal-setup", "usage", "vim", "fast", "ide", "theme", "upgrade",
}

# Secrets courants : masqués avant toute écriture. (motif, garder le préfixe capturé)
SECRETS = [
    (re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{16,}"), False),
    (re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"), False),
    (re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"), False),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), False),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"), False),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{16,}"), True),
    (re.compile(r"(?i)\b((?:api[_-]?key|token|secret|password|passwd|mot de passe|mdp)\s*[:=]\s*)\S{6,}"), True),
]

# Indices d'une correction (après la première demande d'une session). Le jugement final
# revient au modèle : ce sont des présomptions.
CORRECTIONS = [
    (r"^(?:non|nan|no|nope)\b", "non"),
    (r"^(?:stop|arr[eê]te)\b", "stop"),
    (r"\bpas (?:ça|ca|comme ça|ce que)\b", "pas ça"),
    (r"\bje (?:t'|vous )?(?:ai|avais) (?:déjà |pourtant )?(?:dit|demandé|précisé|expliqué)\b", "je t'ai dit"),
    (r"\bj'avais (?:dit|demandé|précisé)\b|\bcomme (?:je l'ai|déjà) dit\b", "je t'ai dit"),
    (r"\b(?:encore une fois|une fois de plus|de nouveau)\b", "encore"),
    (r"\btoujours pas\b", "toujours pas"),
    (r"\b(?:ça|ca|cela) ne (?:marche|fonctionne) (?:toujours )?pas\b|\b(?:ça|ca) marche pas\b", "ne marche pas"),
    (r"\btu (?:as|avais) (?:encore |de nouveau |quand même )?(?:oublié|ignoré|mis|remis|cassé|supprimé|inventé|changé)\b", "tu as…"),
    (r"\btu n'as (?:pas|rien|jamais)\b", "tu n'as pas"),
    (r"\bc'est (?:faux|pas ça|n'importe quoi|inexact|incorrect)\b|\bce n'est pas (?:ça|ce que|correct|bon)\b", "c'est faux"),
    (r"\b(?:recommence|refais|reprends tout|annule)\b", "refais"),
    (r"\bau lieu de\b", "au lieu de"),
    (r"\bpourquoi (?:tu|as-tu|est-ce que tu|t'as)\b", "pourquoi tu"),
    (r"\bne (?:fais|mets|touche|modifie|change|ajoute|invente) (?:pas|plus|rien|jamais)\b|\barr[eê]te de\b", "ne fais pas"),
    (r"\bje (?:ne )?veux pas\b|\bje ne voulais pas\b", "je ne veux pas"),
    (r"\b(?:that's|that is) (?:wrong|not)\b|\bi (?:said|told you|asked)\b|\bstill (?:not|doesn't|broken)\b|\binstead\b", "en"),
]
CORRECTIONS = [(re.compile(m, re.I), etiquette) for m, etiquette in CORRECTIONS]

REFUS = re.compile(r"doesn't want to proceed|tool use was rejected|user (?:has )?(?:rejected|denied|declined)"
                   r"|l'utilisateur a refusé", re.I)
RE_RAPPEL = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
RE_COLLE = re.compile(r"<pasted_content[^>]*>(.*?)</pasted_content[^>]*>", re.S)
RE_COMMANDE = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
RE_ARGUMENTS = re.compile(r"<command-args>(.*?)</command-args>", re.S)
PREFIXES_IGNORES = (
    "<local-command-", "Caveat:", "<bash-input>", "<bash-stdout>", "<bash-stderr>", "<task-notification>",
    "Base directory for this skill", "This session is being continued", "<user-prompt-submit-hook>",
    "<other-session", "<command-message>",
)

MOTS_VIDES = set("""
avec dans pour sans cette ceci cela faire fais fait faites peux peut veux voudrais être avoir tout tous
toute toutes aussi alors donc mais comme quand puis encore déjà merci chose choses elle elles nous vous
leur leurs notre votre même autre autres faut doit sont était avait plus moins très bien quoi dont
ensuite maintenant juste vraiment besoin veut celui celle ceux rien jamais toujours après avant depuis
entre chez vers sous selon pendant parce pourquoi comment combien voici voilà ainsi trop beaucoup chaque
quel quelle quels quelles quelque quelques peux-tu pourrais pourrait est-ce qu'il qu'elle c'est n'est
d'un d'une l'on lequel laquelle oui non stp svp okay this that with from have what your please would
could should there their they them then than into about will just like make want need also only some
more when which here were been does dont can't fichier fichiers
""".split())


# --------------------------------------------------------------------------- outils

def masquer(texte):
    for motif, garder in SECRETS:
        texte = motif.sub((lambda m: m.group(1) + "[secret masqué]") if garder else "[secret masqué]", texte)
    return texte


def nettoyer(texte):
    texte = RE_RAPPEL.sub(" ", texte)
    texte = RE_COLLE.sub(lambda m: " [texte collé : %d caractères] " % len(m.group(1)), texte)
    return masquer(re.sub(r"\s+", " ", texte).strip())


def couper(texte, n):
    return texte if len(texte) <= n else texte[: n - 1].rstrip() + "…"


def horodatage(valeur):
    if not isinstance(valeur, str) or not valeur:
        return None
    for essai in (valeur, re.sub(r"\.\d+", "", valeur)):
        try:
            d = dt.datetime.fromisoformat(essai.replace("Z", "+00:00"))
        except ValueError:
            continue
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone()
    return None


def date_fr(d, heure=True):
    return d.strftime("%d/%m/%Y %H:%M" if heure else "%d/%m/%Y")


def blocs(contenu):
    return [b for b in contenu if isinstance(b, dict)] if isinstance(contenu, list) else []


def texte_humain(contenu):
    if isinstance(contenu, str):
        return contenu
    return "\n".join(b.get("text", "") for b in blocs(contenu) if b.get("type") == "text")


def texte_resultat(contenu):
    if isinstance(contenu, str):
        texte = contenu
    else:
        texte = "\n".join(b.get("text", "") for b in blocs(contenu) if b.get("type") == "text")
    return re.sub(r"</?tool_use_error>", "", texte)


def resume_entree(entree):
    if not isinstance(entree, dict):
        return ""
    for cle in ("command", "file_path", "notebook_path", "path", "url", "pattern", "skill", "query",
                "subagent_type", "description", "prompt"):
        valeur = entree.get(cle)
        if isinstance(valeur, str) and valeur.strip():
            return couper(nettoyer(valeur), 140)
    return couper(nettoyer(json.dumps(entree, ensure_ascii=False)), 100)


def signature(texte):
    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    lignes = [l for l in lignes if not re.match(r"(?i)^exit code \d+$", l)] or lignes or [""]
    l = lignes[0].lower()
    l = re.sub(r"(?:[a-z]:)?[/\\][^\s'\"`:,)]+", "<chemin>", l)
    l = re.sub(r"\d+", "0", l)
    return couper(re.sub(r"\s+", " ", l).strip(), 90)


def mots(texte):
    sortie = set()
    for brut in re.findall(r"[\w'’.-]+", texte.lower()):
        mot = re.split(r"['’]", brut)[-1].strip(".-_")
        if len(mot) >= 4 and not mot.isdigit() and mot not in MOTS_VIDES and not re.search(r"\d{3,}", mot):
            sortie.add(mot)
    return sortie


def depot_git(chemin):
    chemin = Path(chemin).expanduser().resolve()
    for dossier in (chemin, *chemin.parents):
        if (dossier / ".git").exists():
            return dossier
    return None


def refuser_si_depot(chemin):
    depot = depot_git(chemin)
    if depot:
        sys.exit("REFUS : %s est dans le dépôt git %s. Les extraits de sessions ne doivent jamais "
                 "être versionnés ; choisis un dossier hors dépôt (par défaut ~/rapports-improve-system)."
                 % (chemin, depot))


def entete_skill(fichier):
    try:
        texte = fichier.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not texte.startswith("---"):
        return None
    tete = texte.split("---", 2)[1] if texte.count("---") >= 2 else ""
    nom, description, lignes = fichier.parent.name, "", tete.splitlines()
    for i, ligne in enumerate(lignes):
        if ligne.startswith("name:"):
            nom = ligne[5:].strip().strip("'\"") or nom
        elif ligne.startswith("description:"):
            valeur = ligne[12:].strip()
            if valeur in ("", ">", "|", ">-", "|-"):
                suite = []
                for autre in lignes[i + 1:]:
                    if autre and not autre[0].isspace():
                        break
                    suite.append(autre.strip())
                valeur = " ".join(suite)
            description = valeur.strip("'\"")
    return nom, couper(re.sub(r"\s+", " ", description), 160)


def inventaire_skills(projets):
    lieux = [("personnel", Path.home() / ".claude" / "skills")]
    lieux += [("projet " + Path(p).name, Path(p) / ".claude" / "skills") for p in sorted(projets)]
    vus, sortie = set(), []
    for source, base in lieux:
        if not base.is_dir():
            continue
        for fichier in sorted(base.rglob("SKILL.md")):
            if len(fichier.relative_to(base).parts) > 4 or "exemple" in fichier.parts:
                continue
            entete = entete_skill(fichier)
            if entete and (entete[0], source) not in vus:
                vus.add((entete[0], source))
                sortie.append({"nom": entete[0], "source": source, "description": entete[1]})
    plugins = Path.home() / ".claude" / "plugins"
    if plugins.is_dir():
        for fichier in sorted(plugins.rglob("skills/*/SKILL.md")):
            entete = entete_skill(fichier)
            if entete and (entete[0], "plugin") not in vus:
                vus.add((entete[0], "plugin"))
                sortie.append({"nom": entete[0], "source": "plugin", "description": entete[1]})
    return sortie


# --------------------------------------------------------------------------- extraire

def periode(args):
    if args.aujourdhui:
        fin = dt.datetime.combine(dt.date.fromisoformat(args.aujourdhui), dt.time(23, 59, 59)).astimezone()
    else:
        fin = dt.datetime.now().astimezone()
    return fin - dt.timedelta(days=args.jours), fin


def libelle(s):
    return s.get("libelle") or (Path(s["projet"]).name if s.get("projet") else "")


def arrondi(cout):
    return round(cout, 2) if cout is not None else None


def lire_cloud(dossier, debut, fin, sessions, ajouter, commandes):
    """Tours des sessions cloud écrits par les agents lecteurs. Renvoie le nombre de lignes illisibles."""
    if not dossier.is_dir():
        sys.exit("Dossier introuvable : %s" % dossier)
    titres, invalides = {}, 0
    try:
        titres = {s["id"]: s.get("titre", "")
                  for s in json.loads((dossier / "sessions-cloud.json").read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    par_session = collections.defaultdict(list)
    for fichier in sorted(dossier.glob("*.jsonl")):
        with open(fichier, encoding="utf-8", errors="replace") as flux:
            for ligne in flux:
                if not ligne.strip():
                    continue
                try:
                    r = json.loads(ligne)
                except ValueError:
                    r = None
                quand = horodatage(r.get("horodatage")) if isinstance(r, dict) else None
                if quand is None or not r.get("session"):
                    invalides += 1
                elif debut <= quand <= fin:
                    par_session[str(r["session"])].append((quand, r))

    for sid, tours in sorted(par_session.items()):
        tours.sort(key=lambda t: t[0])
        titre = titres.get(sid) or str(tours[0][1].get("titre") or "")
        s = sessions.setdefault(sid, {"id": "S-" + sid.split("_", 1)[-1][:8], "session": sid, "projet": "",
                                      "libelle": couper(titre, 40) if titre else "cloud", "debut": tours[0][0],
                                      "fin": tours[-1][0], "demandes": 0, "premiere_demande": ""})
        rang, question, cumul = 0, False, None
        for quand, r in tours:
            ident = str(r.get("uuid") or "")[:8] or "%08x" % zlib.crc32(json.dumps(r, sort_keys=True).encode())
            # Le coût est cumulé par processus : l'écart entre deux tours donne celui du tour.
            cout = None
            try:
                total = float(r["cout_cumule"])
            except (KeyError, TypeError, ValueError):
                total = None
            if total is not None:
                if cumul is not None:
                    cout = total - cumul if total >= cumul else total
                elif not r.get("tour_processus"):
                    cout = total
                cumul = total

            brut = str(r.get("demande") or "") if r.get("origine") in (None, "", "human") else ""
            texte, demande = nettoyer(brut), None
            balise = RE_COMMANDE.search(brut)
            barre = None if balise else re.match(r"/([\w:.-]+)(?:\s+(.*))?$", texte, re.S)
            if balise or barre:
                nom = (balise or barre).group(1).strip("/")
                arguments = RE_ARGUMENTS.search(brut) if balise else None
                reste = (arguments.group(1) if arguments else "") if balise else (barre.group(2) or "")
                if nom != "improve-system":
                    commandes[nom] += 1
                    demande = "C-" + ident
                    ajouter("commande", demande, quand, sid, s, commande=nom, integree=nom in COMMANDES_INTEGREES,
                            texte=couper(nettoyer(reste), 300), cout=arrondi(cout), uuid=r.get("uuid"))
            elif texte:
                rang += 1
                motifs = []
                if rang > 1:
                    motifs = sorted({etiquette for motif, etiquette in CORRECTIONS if motif.search(texte)})
                    if question and motifs == ["non"]:
                        motifs = []
                s["demandes"] += 1
                if not s["premiere_demande"]:
                    s["premiere_demande"] = couper(texte, 90)
                demande = "D-" + ident
                ajouter("demande", demande, quand, sid, s, rang=rang, texte=couper(texte, 300), longueur=len(texte),
                        correction=motifs, apres_question=question, cout=arrondi(cout), uuid=r.get("uuid"))

            for x in r.get("refus") or []:
                if isinstance(x, dict):
                    ajouter("refus", "R-" + str(x.get("tool_use_id") or ident)[-8:], quand, sid, s,
                            outil=str(x.get("outil") or "?"), entree=couper(nettoyer(str(x.get("entree") or "")), 140),
                            sous_agent=False, commentaire="")
            if r.get("is_error") or r.get("api_error_status"):
                statut = " (statut %s)" % r["api_error_status"] if r.get("api_error_status") else ""
                ajouter("erreur_api", "A-" + ident, quand, sid, s,
                        texte=couper(nettoyer("Tour en échec%s : %s" % (statut, r.get("reponse_debut") or "")), 300))
            elif r.get("fin") not in (None, "", "completed"):
                ajouter("interruption", "I-" + ident, quand, sid, s, outil="tour", entree="arrêt : %s" % r["fin"],
                        apres=demande)
            if texte:
                question = "?" in str(r.get("reponse_fin") or "")[-300:]
    return invalides


def cloud_sessions(args):
    debut, _ = periode(args)
    sortie = Path(args.sortie).expanduser()
    refuser_si_depot(sortie)
    liste, page = [], {}
    for fichier in args.fichiers:
        try:
            texte = Path(fichier).expanduser().read_text(encoding="utf-8", errors="replace")
            i = texte.find('{"ccr"')
            donnees = json.JSONDecoder().raw_decode(texte[i if i >= 0 else texte.find("{"):])[0]
        except (OSError, ValueError) as e:
            sys.exit("Liste des sessions illisible (%s) : %s" % (fichier, e))
        page = donnees.get("ccr", donnees)
        liste += page.get("data") or []
    courante = os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID", "").split("_", 1)[-1]
    retenues, creations, vues = [], [], set()
    for s in liste:
        creee, active = horodatage(s.get("created_at")), horodatage(s.get("updated_at"))
        if creee:
            creations.append(creee)
        sid = str(s.get("id") or "")
        if not sid or sid in vues or not (active or creee) or (active or creee) < debut:
            continue
        vues.add(sid)
        if courante and sid.split("_", 1)[-1] == courante:
            print("Session en cours exclue : %s" % sid)
            continue
        retenues.append({"id": sid, "titre": s.get("title") or "", "creee": date_fr(creee) if creee else "",
                         "active": date_fr(active or creee)})
    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "sessions-cloud.json").write_text(json.dumps(retenues, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in retenues:
        print("%s | créée %s | active %s | %s" % (s["id"], s["creee"], s["active"], s["titre"]))
    print("%d session(s) active(s) depuis le %s. Écrit : %s" % (len(retenues), date_fr(debut),
                                                               sortie / "sessions-cloud.json"))
    if page.get("has_more") and creations and min(creations) >= debut:
        print("ATTENTION : la liste continue. Rappeler list_sessions avec after_id=%s, puis relancer cette "
              "commande avec tous les fichiers de pages." % page.get("last_id"))


def extraire(args):
    racine_defaut = args.racine is None
    lire_local = not args.cloud or not racine_defaut
    racine = Path(args.racine or "~/.claude/projects").expanduser()
    debut, fin = periode(args)
    sortie = Path(args.sortie).expanduser()
    refuser_si_depot(sortie)
    if lire_local and not racine.is_dir():
        sys.exit("Dossier introuvable : %s" % racine)

    exclue = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    sessions, signaux = {}, []
    etats = collections.defaultdict(lambda: {"rang": 0, "question": False, "outil": None, "demande": None})
    commandes, skills_utilises = collections.Counter(), collections.Counter()
    nb_fichiers = lignes_invalides = 0

    def session(sid, entree, quand):
        s = sessions.setdefault(sid, {"id": "S-" + sid[:8], "session": sid, "projet": "", "libelle": "",
                                      "debut": quand, "fin": quand, "demandes": 0, "premiere_demande": ""})
        if entree.get("cwd") and not s["projet"]:
            s["projet"] = entree["cwd"]
        s["debut"], s["fin"] = min(s["debut"], quand), max(s["fin"], quand)
        return s

    def ajouter(type_, ident, quand, sid, s, **champs):
        signaux.append(dict({"id": ident, "type": type_, "horodatage": quand.isoformat(timespec="minutes"),
                             "date": date_fr(quand), "session": s["id"],
                             "projet": libelle(s)}, **champs))

    for fichier in sorted(racine.rglob("*.jsonl")) if lire_local else []:
        try:
            if dt.datetime.fromtimestamp(fichier.stat().st_mtime).astimezone() < debut:
                continue
            flux = open(fichier, encoding="utf-8", errors="replace")
        except OSError:
            continue
        nb_fichiers += 1
        outils = {}
        with flux:
            for ligne in flux:
                try:
                    entree = json.loads(ligne)
                except ValueError:
                    lignes_invalides += 1
                    continue
                if not isinstance(entree, dict) or entree.get("type") not in ("user", "assistant"):
                    continue
                sid = entree.get("sessionId") or fichier.stem
                if sid == exclue:
                    continue
                etat, contenu = etats[sid], (entree.get("message") or {}).get("content")
                quand = horodatage(entree.get("timestamp"))
                dedans = quand is not None and debut <= quand <= fin
                annexe = bool(entree.get("isSidechain"))
                uuid = (entree.get("uuid") or "")[:8] or "%08x" % zlib.crc32(ligne.encode("utf-8"))

                if entree["type"] == "assistant":
                    texte = ""
                    for b in blocs(contenu):
                        if b.get("type") == "tool_use":
                            outils[b.get("id")] = (b.get("name", "?"), resume_entree(b.get("input")))
                            if not annexe:
                                etat["outil"] = outils[b.get("id")]
                            if dedans and b.get("name") == "Skill" and isinstance(b.get("input"), dict):
                                skills_utilises[str(b["input"].get("skill", "?"))] += 1
                        elif b.get("type") == "text":
                            texte += b.get("text", "")
                    if not annexe and texte.strip():
                        etat["question"] = "?" in texte.strip()[-300:]
                    if dedans and not annexe:
                        s = session(sid, entree, quand)
                        if entree.get("isApiErrorMessage"):
                            ajouter("erreur_api", "A-" + uuid, quand, sid, s,
                                    texte=couper(nettoyer(texte_humain(contenu)), 300))
                    continue

                if not dedans:
                    continue
                s = session(sid, entree, quand) if not annexe else sessions.get(sid) or session(sid, entree, quand)

                for b in blocs(contenu):
                    if b.get("type") != "tool_result" or not b.get("is_error"):
                        continue
                    texte = texte_resultat(b.get("content"))
                    nom, resume = outils.get(b.get("tool_use_id"), ("?", ""))
                    ident = str(b.get("tool_use_id") or uuid)[-8:]
                    if REFUS.search(texte):
                        dit = re.split(r"(?i)the user said:", texte, maxsplit=1)
                        ajouter("refus", "R-" + ident, quand, sid, s, outil=nom, entree=resume, sous_agent=annexe,
                                commentaire=couper(nettoyer(dit[1]), 300) if len(dit) > 1 else "")
                    else:
                        ajouter("erreur", "E-" + ident, quand, sid, s, outil=nom, entree=resume,
                                erreur=couper(nettoyer(texte), 300), signature=signature(texte), sous_agent=annexe)

                origine = entree.get("origin")
                if (annexe or entree.get("isMeta") or entree.get("isCompactSummary")
                        or entree.get("isVisibleInTranscriptOnly")
                        or (isinstance(origine, dict) and origine.get("kind") not in (None, "human"))):
                    continue
                brut = texte_humain(contenu).strip()
                if not brut:
                    continue
                if brut.startswith("[Request interrupted by user"):
                    outil = etat["outil"] or ("?", "")
                    ajouter("interruption", "I-" + uuid, quand, sid, s, outil=outil[0], entree=outil[1],
                            apres=etat["demande"])
                    continue
                trouve = RE_COMMANDE.search(brut)
                if trouve:
                    nom = trouve.group(1).strip("/")
                    if nom == "improve-system":
                        continue
                    commandes[nom] += 1
                    arguments = RE_ARGUMENTS.search(brut)
                    ajouter("commande", "C-" + uuid, quand, sid, s, commande=nom,
                            integree=nom in COMMANDES_INTEGREES,
                            texte=couper(nettoyer(arguments.group(1)), 300) if arguments else "")
                    continue
                if brut.startswith(PREFIXES_IGNORES):
                    continue
                texte = nettoyer(brut)
                if not texte:
                    continue
                etat["rang"] += 1
                motifs = []
                if etat["rang"] > 1:
                    motifs = sorted({etiquette for motif, etiquette in CORRECTIONS if motif.search(texte)})
                    if etat["question"] and motifs == ["non"]:
                        motifs = []
                s["demandes"] += 1
                if not s["premiere_demande"]:
                    s["premiere_demande"] = couper(texte, 90)
                ajouter("demande", "D-" + uuid, quand, sid, s, rang=etat["rang"], texte=couper(texte, 300),
                        longueur=len(texte), correction=motifs, apres_question=etat["question"])
                etat["demande"], etat["question"] = "D-" + uuid, False

    invalides_cloud = lire_cloud(Path(args.cloud).expanduser(), debut, fin, sessions, ajouter, commandes) \
        if args.cloud else 0

    signaux.sort(key=lambda x: (x["horodatage"], x["id"]))
    liste_sessions = sorted(sessions.values(), key=lambda x: x["debut"])
    for s in liste_sessions:
        s["debut"], s["fin"] = date_fr(s["debut"]), date_fr(s["fin"])

    groupes = collections.defaultdict(list)
    for x in signaux:
        if x["type"] == "erreur":
            groupes[(x["outil"], x["signature"])].append(x)
    groupes_erreurs = sorted(
        ({"outil": o, "signature": sig, "occurrences": len(v), "sessions": len({x["session"] for x in v}),
          "ids": [x["id"] for x in v][:12]} for (o, sig), v in groupes.items()),
        key=lambda g: (-g["sessions"], -g["occurrences"], g["outil"]))

    par_mot = collections.defaultdict(lambda: collections.defaultdict(list))
    for x in signaux:
        if x["type"] in ("demande", "commande") and x.get("texte"):
            for mot in mots(x["texte"]):
                par_mot[mot][x["session"]].append(x["id"])
    themes = sorted(({"mot": m, "sessions": len(v), "ids": [i for ids in v.values() for i in ids][:8]}
                     for m, v in par_mot.items() if len(v) >= 2), key=lambda t: (-t["sessions"], t["mot"]))[:30]

    avertissements = []
    if racine_defaut and not args.cloud and os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        avertissements.append("Session cloud : ~/.claude/projects ne contient ici que les sessions de ce conteneur. "
                              "Tes autres sessions (poste local, autres sessions cloud) ne sont pas lues.")
    if args.cloud:
        avertissements.append("Sessions cloud lues par l'API des sessions : les erreurs d'outil une à une n'y "
                              "figurent pas, seulement les actions refusées, les tours en échec et les tours "
                              "inachevés. Coûts au tarif public indicatif, pas la facturation réelle.")
    if invalides_cloud:
        avertissements.append("%d enregistrement(s) cloud illisible(s) ignoré(s)." % invalides_cloud)
    if exclue and lire_local:
        avertissements.append("La session en cours (%s) est exclue de l'analyse." % ("S-" + exclue[:8]))
    if len(liste_sessions) < 3:
        avertissements.append("Seulement %d session(s) sur la période : trop peu pour parler de récurrence."
                              % len(liste_sessions))
    if lignes_invalides:
        avertissements.append("%d ligne(s) illisible(s) ignorée(s) dans les transcripts." % lignes_invalides)

    compte = collections.Counter(x["type"] for x in signaux)
    corrections = sum(1 for x in signaux if x.get("correction"))
    meta = {"genere": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
            "debut": date_fr(debut), "fin": date_fr(fin), "jours": args.jours,
            "source": "+".join(n for n, oui in (("local", lire_local), ("cloud", bool(args.cloud))) if oui),
            "racine": str(racine) if lire_local else "", "cloud": str(args.cloud or ""),
            "cout_total": round(sum(x.get("cout") or 0 for x in signaux), 2),
            "fichiers_lus": nb_fichiers, "sessions": len(liste_sessions), "demandes": compte["demande"],
            "corrections_presumees": corrections, "erreurs": compte["erreur"], "refus": compte["refus"],
            "interruptions": compte["interruption"], "erreurs_api": compte["erreur_api"],
            "commandes": compte["commande"]}
    projets = {s["projet"] for s in liste_sessions if s["projet"] and Path(s["projet"]).is_dir()}
    if (Path.cwd() / ".claude" / "skills").is_dir():
        projets.add(str(Path.cwd()))
    donnees = {"meta": meta, "avertissements": avertissements, "sessions": liste_sessions, "signaux": signaux,
               "groupes_erreurs": groupes_erreurs, "themes": themes, "commandes": dict(commandes.most_common()),
               "skills_utilises": dict(skills_utilises.most_common()),
               "inventaire_skills": inventaire_skills(projets)}

    sortie.mkdir(parents=True, exist_ok=True)
    (sortie / "signaux.json").write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    (sortie / "resume.txt").write_text(vue_compacte(donnees), encoding="utf-8")
    print("Période %s → %s : %d sessions, %d demandes, %d corrections présumées, %d erreurs d'outil, "
          "%d refus, %d interruptions." % (meta["debut"], meta["fin"], meta["sessions"], meta["demandes"],
                                           corrections, meta["erreurs"], meta["refus"], meta["interruptions"]))
    for a in avertissements:
        print("AVERTISSEMENT : " + a)
    print("Écrit : %s et %s" % (sortie / "signaux.json", sortie / "resume.txt"))


def vue_compacte(d):
    m, lignes = d["meta"], []
    lignes.append("PÉRIODE %s → %s · %d sessions · %d demandes · %d corrections présumées · %d erreurs d'outil "
                  "· %d refus · %d interruptions · %d erreurs d'API"
                  % (m["debut"], m["fin"], m["sessions"], m["demandes"], m["corrections_presumees"], m["erreurs"],
                     m["refus"], m["interruptions"], m["erreurs_api"]))
    if d["avertissements"]:
        lignes += ["", "AVERTISSEMENTS"] + ["- " + a for a in d["avertissements"]]
    lignes += ["", "SESSIONS"]
    for s in d["sessions"]:
        lignes.append("%s | %s → %s | %s | %d demandes | « %s »" % (
            s["id"], s["debut"], s["fin"][-5:], libelle(s) or "?",
            s["demandes"], s["premiere_demande"]))
    sig = d["signaux"]
    lignes += ["", "DEMANDES (#rang dans la session ; CORR = correction présumée ; ?= suit une question de Claude)"]
    for x in sig:
        if x["type"] == "demande":
            drapeaux = (" CORR[%s]" % ", ".join(x["correction"]) if x["correction"] else "") + \
                       (" ?" if x["apres_question"] else "")
            cout = " | %.2f $" % x["cout"] if x.get("cout") is not None else ""
            lignes.append("%s | %s | %s #%d%s%s | %s" % (x["id"], x["date"], x["session"], x["rang"], drapeaux,
                                                        cout, x["texte"]))
    lignes += ["", "COMMANDES ET SKILLS (hors commandes intégrées)"]
    for x in sig:
        if x["type"] == "commande" and not x["integree"]:
            lignes.append("%s | %s | %s | /%s %s" % (x["id"], x["date"], x["session"], x["commande"], x["texte"]))
    lignes.append("Comptes : commandes %s ; skills appelés par Claude %s" % (
        json.dumps(d["commandes"], ensure_ascii=False), json.dumps(d["skills_utilises"], ensure_ascii=False)))
    lignes += ["", "INTERRUPTIONS (dernière action de Claude avant l'arrêt)"]
    lignes += ["%s | %s | %s | %s « %s » | après %s" % (x["id"], x["date"], x["session"], x["outil"], x["entree"],
                                                          x["apres"] or "-")
               for x in sig if x["type"] == "interruption"]
    lignes += ["", "REFUS (actions de Claude refusées)"]
    lignes += ["%s | %s | %s | %s « %s »%s%s" % (
        x["id"], x["date"], x["session"], x["outil"], x["entree"], " [sous-agent]" if x["sous_agent"] else "",
        " | commentaire : « %s »" % x["commentaire"] if x["commentaire"] else "")
        for x in sig if x["type"] == "refus"]
    lignes += ["", "ERREURS D'OUTIL GROUPÉES (sessions · occurrences · outil · signature · ids)"]
    lignes += ["%d · %d · %s · %s · %s" % (g["sessions"], g["occurrences"], g["outil"], g["signature"],
                                            " ".join(g["ids"])) for g in d["groupes_erreurs"][:25]]
    lignes += ["", "ERREURS D'API"]
    lignes += ["%s | %s | %s | %s" % (x["id"], x["date"], x["session"], x["texte"])
               for x in sig if x["type"] == "erreur_api"]
    couteux = sorted((x for x in sig if x.get("cout")), key=lambda x: -x["cout"])[:10]
    if couteux:
        lignes += ["", "TOURS LES PLUS COÛTEUX (tarif public indicatif ; total période %.2f $)" % m["cout_total"]]
        lignes += ["%s | %s | %s | %.2f $ | %s" % (x["id"], x["date"], x["session"], x["cout"], couper(x["texte"], 120))
                   for x in couteux]
    lignes += ["", "THÈMES (mot présent dans au moins 2 sessions · ids)"]
    lignes += ["%s (%d sessions) : %s" % (t["mot"], t["sessions"], " ".join(t["ids"])) for t in d["themes"]]
    lignes += ["", "SKILLS EXISTANTS"]
    lignes += ["%s [%s] : %s" % (k["nom"], k["source"], k["description"]) for k in d["inventaire_skills"]]
    return "\n".join(lignes) + "\n"


# --------------------------------------------------------------------------- rapport

def citation(x):
    if x["type"] in ("demande", "commande"):
        prefixe = "/%s " % x["commande"] if x["type"] == "commande" else ""
        return "« %s%s »" % (prefixe, couper(x.get("texte", ""), 220))
    if x["type"] == "erreur":
        return "erreur de `%s` sur « %s » : %s" % (x["outil"], couper(x["entree"], 90), couper(x["erreur"], 160))
    if x["type"] == "refus":
        suite = " — commentaire : « %s »" % couper(x["commentaire"], 160) if x.get("commentaire") else ""
        return "action refusée : `%s` « %s »%s" % (x["outil"], couper(x["entree"], 120), suite)
    if x["type"] == "interruption":
        return "interruption pendant `%s` « %s »" % (x["outil"], couper(x["entree"], 120))
    return couper(x.get("texte", ""), 220)


def ligne_exemple(x):
    return "%s · %s · session %s (%s) — %s" % (x["date"], x["projet"] or "?", x["session"], x["id"],
                                                 citation(x).replace("\n", " "))


def controler(props, donnees):
    index = {x["id"]: x for x in donnees["signaux"]}
    existants = {k["nom"] for k in donnees.get("inventaire_skills", [])}
    erreurs, alertes = [], []
    liste = props.get("propositions")
    if not isinstance(liste, list):
        return ["« propositions » doit être une liste (vide si rien ne tient)."], alertes
    if not isinstance(props.get("synthese"), str) or not props["synthese"].strip():
        erreurs.append("« synthese » manquante : deux à cinq phrases sur ce que montre la semaine.")
    if len(liste) > MAX_PROPOSITIONS:
        alertes.append("%d propositions : au-delà de %d, garder les plus rentables." % (len(liste), MAX_PROPOSITIONS))
    noms = set()
    for i, p in enumerate(liste, 1):
        ici = "Proposition %d" % i
        if not isinstance(p, dict):
            erreurs.append(ici + " : doit être un objet.")
            continue
        nom = p.get("nom", "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,48}", str(nom)):
            erreurs.append(ici + " : nom « %s » invalide (minuscules, chiffres, tirets)." % nom)
        if nom in noms:
            erreurs.append(ici + " : nom « %s » en double." % nom)
        noms.add(nom)
        forme = p.get("forme")
        if forme not in FORMES:
            erreurs.append(ici + " : forme « %s » inconnue (%s)." % (forme, ", ".join(FORMES)))
        if forme == "nouveau-skill" and nom in existants:
            erreurs.append(ici + " : un skill « %s » existe déjà ; forme skill-existant ou autre nom." % nom)
        if forme == "skill-existant" and nom not in existants:
            erreurs.append(ici + " : « %s » n'est pas dans l'inventaire des skills existants." % nom)
        natures = p.get("natures")
        if not isinstance(natures, list) or not natures or any(n not in NATURES for n in natures):
            erreurs.append(ici + " : natures doit lister au moins un de %s." % ", ".join(NATURES))
        for champ in ("constat", "solution", "gain", "limite"):
            if not isinstance(p.get(champ), str) or not p[champ].strip():
                erreurs.append(ici + " : champ « %s » manquant." % champ)
        if not isinstance(p.get("etapes"), list) or not p["etapes"]:
            erreurs.append(ici + " : « etapes » doit lister ce que ferait la solution.")
        if forme in ("nouveau-skill", "skill-existant") and (
                not isinstance(p.get("declencheurs"), list) or not p["declencheurs"]):
            erreurs.append(ici + " : « declencheurs » requis pour un skill.")
        if p.get("priorite") not in PRIORITES:
            erreurs.append(ici + " : priorite parmi %s." % ", ".join(PRIORITES))
        if p.get("certitude") not in CERTITUDES:
            erreurs.append(ici + " : certitude parmi %s." % ", ".join(CERTITUDES))
        if not isinstance(p.get("occurrences", []), list):
            erreurs.append(ici + " : « occurrences » doit être une liste d'identifiants.")
            continue
        exemples = p.get("exemples")
        if not isinstance(exemples, list) or len(exemples) != 2:
            erreurs.append(ici + " : exactement 2 exemples (identifiants de signaux).")
            continue
        inconnus = [e for e in exemples + list(p.get("occurrences") or []) if e not in index]
        if inconnus:
            erreurs.append(ici + " : identifiants absents de signaux.json : %s." % ", ".join(map(str, inconnus)))
            continue
        if index[exemples[0]]["session"] == index[exemples[1]]["session"]:
            erreurs.append(ici + " : les 2 exemples viennent de la même session (%s) ; un cas isolé va dans "
                                 "« a_surveiller »." % index[exemples[0]]["session"])
    if props.get("rapport") and (not re.fullmatch(r"improve-system-\d{4}-\d{2}-\d{2}(?:-\d+)?", str(props["rapport"]))
                                 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(props.get("genere_le", "")))):
        erreurs.append("« rapport » et « genere_le » sont écrits par le script : ne pas les modifier.")
    for j, x in enumerate(props.get("installations") or [], 1):
        if (not isinstance(x, dict) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", str(x.get("date", "")))
                or not isinstance(x.get("noms"), list) or not x["noms"] or any(n not in noms for n in x["noms"])):
            erreurs.append("Installation %d : objet {date : JJ/MM/AAAA, noms : [noms de propositions]} attendu." % j)
    for j, a in enumerate(props.get("a_surveiller") or [], 1):
        if not isinstance(a, dict) or not a.get("sujet") or not isinstance(a.get("ids"), list) or not a["ids"]:
            erreurs.append("À surveiller %d : objet {sujet, ids} attendu." % j)
        elif any(e not in index for e in a["ids"]):
            erreurs.append("À surveiller %d : identifiant absent de signaux.json." % j)
    return erreurs, alertes


def construire_blocs(props, donnees, jour):
    """Contenu du rapport, commun aux sorties Markdown et DOCX. Le texte porte les marques en ligne
    **gras** et `code`."""
    index, m = {x["id"]: x for x in donnees["signaux"]}, donnees["meta"]
    b = [("titre", "Améliorer le système — rapport du %s" % jour.strftime("%d/%m/%Y")),
         ("p", "Période analysée : %s → %s (%d jours) · %d sessions · %d demandes · %d corrections présumées · "
               "%d erreurs d'outil · %d refus · %d interruptions." % (
                   m["debut"], m["fin"], m["jours"], m["sessions"], m["demandes"], m["corrections_presumees"],
                   m["erreurs"], m["refus"], m["interruptions"]))]
    if donnees["avertissements"]:
        b += [("p", "Limites de la lecture :")] + [("li", a) for a in donnees["avertissements"]]
    b += [("h1", "Synthèse"), ("p", props["synthese"].strip()), ("h1", "Propositions")]
    if not props["propositions"]:
        b.append(("p", "Aucun schéma ne revient dans au moins deux sessions : rien à proposer cette fois."))
    for i, p in enumerate(props["propositions"], 1):
        occurrences = sorted(set(p.get("occurrences") or []) | set(p["exemples"]),
                             key=lambda e: index[e]["horodatage"])
        sessions = {index[e]["session"] for e in occurrences}
        cout = sum(index[e].get("cout") or 0 for e in occurrences)
        b += [("h2", "%d. `%s` — %s" % (i, p["nom"], FORMES[p["forme"]])),
              ("p", "Priorité %s · %s · %s. %d occurrence(s) dans %d session(s), du %s au %s." % (
                  p["priorite"], p["certitude"], ", ".join(NATURES[n] for n in p["natures"]), len(occurrences),
                  len(sessions), index[occurrences[0]]["date"][:10], index[occurrences[-1]]["date"][:10])
                  + (" Coût indicatif cumulé : %.2f $." % cout if cout else "")),
              ("p", "**Constat.** " + p["constat"].strip()),
              ("p", "**Ce que ferait la solution.** " + p["solution"].strip())]
        if p.get("declencheurs"):
            b.append(("p", "**Déclencheurs.** " + " ; ".join("« %s »" % d for d in p["declencheurs"])))
        b += [("p", "**Étapes envisagées.**")] + [("ol", e) for e in p["etapes"]]
        b += [("p", "**Exemples datés.**")] + [("li", ligne_exemple(index[e])) for e in p["exemples"]]
        b += [("p", "**Gain attendu.** " + p["gain"].strip()), ("p", "**Limite.** " + p["limite"].strip())]
    if props.get("a_surveiller"):
        b.append(("h1", "À surveiller (cas isolés, pas encore une tendance)"))
        for a in props["a_surveiller"]:
            premier = index[a["ids"][0]]
            b.append(("li", "%s — %s, %s" % (a["sujet"], premier["date"][:10], citation(premier))))
    groupes = [g for g in donnees["groupes_erreurs"] if g["occurrences"] >= 2][:10]
    if groupes:
        b += [("h1", "Échecs d'outils les plus fréquents (données brutes)"),
              ("table", ["Outil", "Erreur", "Occurrences", "Sessions"],
               [[g["outil"], g["signature"], str(g["occurrences"]), str(g["sessions"])] for g in groupes],
               [1300, 5338, 1700, 1300])]
    b.append(("h1", "Installation"))
    if props.get("installations"):
        b += [("li", "Installé le %s : %s." % (x["date"], ", ".join("`%s`" % n for n in x["noms"])))
              for x in props["installations"]]
        b.append(("p", "Les autres propositions restent à décider."))
    else:
        b.append(("p", "Rien n'a été installé. Pour installer, réponds avec les numéros retenus (par exemple "
                       "« installe 1 et 3 »). " + (
                           "Un skill est remis en zip, à téléverser dans claude.ai (Personnaliser > Skills)."
                           if "cloud" in m.get("source", "") else
                           "Destination par défaut : `~/.claude/skills/<nom>/`. Un dossier existant n'est jamais "
                           "écrasé sans ton accord.")))
    return b


def en_markdown(blocs_rapport):
    lignes, precedent, rang = [], None, 0
    for bloc in blocs_rapport:
        genre = bloc[0]
        rang = rang + 1 if genre == "ol" and precedent == "ol" else 1
        if lignes and not (genre in ("li", "ol") and precedent == genre):
            lignes.append("")
        if genre == "titre":
            lignes.append("# " + bloc[1])
        elif genre in ("h1", "h2"):
            lignes.append(("## " if genre == "h1" else "### ") + bloc[1])
        elif genre == "li":
            lignes.append("- " + bloc[1])
        elif genre == "ol":
            lignes.append("%d. %s" % (rang, bloc[1]))
        elif genre == "table":
            lignes.append("| " + " | ".join(bloc[1]) + " |")
            lignes.append("|" + "---|" * len(bloc[1]))
            lignes += ["| " + " | ".join(c.replace("|", "/") for c in rangee) + " |" for rangee in bloc[2]]
        else:
            lignes.append(bloc[1])
        precedent = genre
    return "\n".join(lignes) + "\n"


W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
BORDURE = '<w:%s w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:styles xmlns:w="%s">'
          '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" '
          'w:cs="Calibri"/><w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="fr-FR"/></w:rPr></w:rPrDefault>'
          '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
          '</w:docDefaults>'
          '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
          '<w:style w:type="paragraph" w:styleId="Titre"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
          '<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="240"/></w:pPr><w:rPr><w:b/>'
          '<w:color w:val="1F3864"/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr></w:style>'
          '<w:style w:type="paragraph" w:styleId="Titre1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>'
          '<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="360" w:after="120"/>'
          '<w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="30"/>'
          '<w:szCs w:val="30"/></w:rPr></w:style>'
          '<w:style w:type="paragraph" w:styleId="Titre2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>'
          '<w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="280" w:after="100"/>'
          '<w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:color w:val="2F5496"/><w:sz w:val="26"/>'
          '<w:szCs w:val="26"/></w:rPr></w:style>'
          '<w:style w:type="paragraph" w:styleId="Paragraphedeliste"><w:name w:val="List Paragraph"/>'
          '<w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="60"/><w:ind w:left="720"/>'
          '<w:contextualSpacing/></w:pPr></w:style>'
          '<w:style w:type="character" w:styleId="Code"><w:name w:val="Code"/><w:rPr><w:rFonts w:ascii="Consolas" '
          'w:hAnsi="Consolas" w:cs="Consolas"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>'
          '<w:style w:type="table" w:styleId="Grille"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders>%s'
          '</w:tblBorders><w:tblCellMar><w:top w:w="40" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
          '<w:bottom w:w="40" w:type="dxa"/><w:right w:w="100" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
          '</w:styles>') % (W_NS, "".join(BORDURE % c for c in ("top", "left", "bottom", "right", "insideH",
                                                                "insideV")))
NIVEAU = ('<w:abstractNum w:abstractNumId="%d"><w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0">'
          '<w:start w:val="1"/><w:numFmt w:val="%s"/><w:lvlText w:val="%s"/><w:lvlJc w:val="left"/>'
          '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl></w:abstractNum>')


def xml(texte):
    texte = re.sub("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]", "", texte)
    return texte.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def runs(texte, gras=False):
    sortie = []
    for morceau in re.split(r"(\*\*[^*\n]+?\*\*|`[^`\n]+`)", texte):
        if not morceau:
            continue
        proprietes = []
        if len(morceau) > 2 and morceau[0] == morceau[-1] == "`":
            morceau = morceau[1:-1]
            proprietes.append('<w:rStyle w:val="Code"/>')
        elif len(morceau) > 4 and morceau.startswith("**") and morceau.endswith("**"):
            morceau = morceau[2:-2]
            proprietes.append("<w:b/>")
        if gras and "<w:b/>" not in proprietes:
            proprietes.append("<w:b/>")
        rpr = "<w:rPr>%s</w:rPr>" % "".join(proprietes) if proprietes else ""
        sortie.append('<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, xml(morceau)))
    return "".join(sortie)


def paragraphe(contenu, style=None, numero=None, apres=None):
    ppr = ""
    if style:
        ppr += '<w:pStyle w:val="%s"/>' % style
    if numero:
        ppr += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="%d"/></w:numPr>' % numero
    if apres is not None:
        ppr += '<w:spacing w:after="%d"/>' % apres
    return "<w:p>%s%s</w:p>" % ("<w:pPr>%s</w:pPr>" % ppr if ppr else "", contenu)


def tableau(entetes, rangees, largeurs):
    def cellule(texte, largeur, entete):
        fond = '<w:shd w:val="clear" w:color="auto" w:fill="E8ECF4"/>' if entete else ""
        return '<w:tc><w:tcPr><w:tcW w:w="%d" w:type="dxa"/>%s</w:tcPr>%s</w:tc>' % (
            largeur, fond, paragraphe(runs(texte, gras=entete), apres=0))
    lignes = ['<w:tr><w:trPr><w:tblHeader/></w:trPr>%s</w:tr>'
              % "".join(cellule(t, l, True) for t, l in zip(entetes, largeurs))]
    lignes += ["<w:tr>%s</w:tr>" % "".join(cellule(t, l, False) for t, l in zip(r, largeurs)) for r in rangees]
    return ('<w:tbl><w:tblPr><w:tblStyle w:val="Grille"/><w:tblW w:w="%d" w:type="dxa"/></w:tblPr>'
            '<w:tblGrid>%s</w:tblGrid>%s</w:tbl>' % (sum(largeurs), "".join('<w:gridCol w:w="%d"/>' % l
                                                                           for l in largeurs), "".join(lignes)))


def en_docx(blocs_rapport, chemin, titre):
    """DOCX écrit avec la bibliothèque standard : aucune dépendance à installer sur le poste."""
    corps, listes, precedent = [], 0, None
    for bloc in blocs_rapport:
        genre = bloc[0]
        if genre == "titre":
            corps.append(paragraphe(runs(bloc[1]), "Titre"))
        elif genre in ("h1", "h2"):
            corps.append(paragraphe(runs(bloc[1]), "Titre1" if genre == "h1" else "Titre2"))
        elif genre == "li":
            corps.append(paragraphe(runs(bloc[1]), "Paragraphedeliste", 1))
        elif genre == "ol":
            if precedent != "ol":
                listes += 1
            corps.append(paragraphe(runs(bloc[1]), "Paragraphedeliste", 1 + listes))
        elif genre == "table":
            corps += [tableau(bloc[1], bloc[2], bloc[3]), paragraphe("", apres=0)]
        else:
            corps.append(paragraphe(runs(bloc[1])))
        precedent = genre
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="%s"><w:body>%s'
                '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" '
                'w:left="1134" w:header="567" w:footer="567" w:gutter="0"/></w:sectPr></w:body></w:document>'
                % (W_NS, "".join(corps)))
    numerotation = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:numbering xmlns:w="%s">%s%s'
                    '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>%s</w:numbering>' % (
                        W_NS, NIVEAU % (0, "bullet", "•"), NIVEAU % (1, "decimal", "%1."),
                        "".join('<w:num w:numId="%d"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0">'
                                '<w:startOverride w:val="1"/></w:lvlOverride></w:num>' % (2 + k)
                                for k in range(listes))))
    types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org'
             '/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-'
             'package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'
             '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.'
             'wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/'
             'vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/numbering.'
             'xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
             '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-'
             'properties+xml"/></Types>')
    racine = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%s">'
              '<Relationship Id="rId1" Type="%sofficeDocument" Target="word/document.xml"/>'
              '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
              'core-properties" Target="docProps/core.xml"/></Relationships>' % (REL_NS, OFFICE_REL))
    liens = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="%s">'
             '<Relationship Id="rId1" Type="%sstyles" Target="styles.xml"/>'
             '<Relationship Id="rId2" Type="%snumbering" Target="numbering.xml"/></Relationships>'
             % (REL_NS, OFFICE_REL, OFFICE_REL))
    proprietes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://'
                  'schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/'
                  'elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/'
                  'XMLSchema-instance"><dc:title>%s</dc:title><dc:creator>improve-system</dc:creator>'
                  '<dc:language>fr-FR</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>'
                  '</cp:coreProperties>' % (xml(titre), dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", types)
        z.writestr("_rels/.rels", racine)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/numbering.xml", numerotation)
        z.writestr("word/_rels/document.xml.rels", liens)
        z.writestr("docProps/core.xml", proprietes)


def rapport(args):
    source = Path(args.propositions).expanduser()
    props = json.loads(source.read_text(encoding="utf-8"))
    donnees = json.loads(Path(args.signaux).expanduser().read_text(encoding="utf-8"))
    sortie = Path(args.sortie).expanduser()
    refuser_si_depot(sortie)
    erreurs, alertes = controler(props, donnees)
    for a in alertes:
        print("ALERTE : " + a)
    if erreurs:
        print("NON CONFORME (%d) :" % len(erreurs))
        for e in erreurs:
            print("- " + e)
        sys.exit(1)

    sortie.mkdir(parents=True, exist_ok=True)
    if props.get("rapport"):
        base, jour = props["rapport"], dt.date.fromisoformat(props["genere_le"])
    else:
        jour = dt.date.today()
        base, n = "improve-system-%s" % jour.isoformat(), 1
        while any((sortie / (base + ext)).exists() for ext in (".md", ".docx", ".json")):
            n += 1
            base = "improve-system-%s-%d" % (jour.isoformat(), n)
        props["rapport"], props["genere_le"] = base, jour.isoformat()
    blocs_rapport = construire_blocs(props, donnees, jour)
    (sortie / (base + ".md")).write_text(en_markdown(blocs_rapport), encoding="utf-8")
    en_docx(blocs_rapport, sortie / (base + ".docx"), blocs_rapport[0][1])
    (sortie / (base + ".json")).write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Rapport : %s" % (sortie / (base + ".docx")))
    print("Version texte : %s" % (sortie / (base + ".md")))
    print("Propositions : %s" % (sortie / (base + ".json")))


def paquet(args):
    dossier = Path(args.dossier).expanduser().resolve()
    try:
        texte = (dossier / "SKILL.md").read_text(encoding="utf-8")
    except OSError:
        sys.exit("SKILL.md introuvable dans %s" % dossier)
    erreurs, entete = [], re.match(r"---\r?\n(.*?)\r?\n---\r?\n", texte, re.S)
    if not entete:
        erreurs.append("en-tête YAML absent.")
    else:
        champs = dict(re.findall(r"^([\w-]+):[ \t]*(.*)$", entete.group(1), re.M))
        nom = champs.get("name", "").strip()
        if nom != dossier.name or not re.fullmatch(r"[a-z0-9-]{1,64}", nom):
            erreurs.append("name doit valoir « %s » (minuscules, chiffres, tirets)." % dossier.name)
        description = champs.get("description", "").strip().strip("'\"")
        if not description or description in (">", "|", ">-", "|-"):
            erreurs.append("description absente ou sur plusieurs lignes : l'écrire sur une seule ligne.")
        elif len(description) > 200:
            erreurs.append("description de %d caractères, 200 au plus pour claude.ai." % len(description))
    if erreurs:
        print("NON CONFORME (%d) :" % len(erreurs))
        for e in erreurs:
            print("- " + e)
        sys.exit(1)
    sortie = Path(args.sortie).expanduser()
    refuser_si_depot(sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    cible, fichiers = sortie / (dossier.name + ".zip"), 0
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(dossier.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                z.write(f, "%s/%s" % (dossier.name, f.relative_to(dossier).as_posix()))
                fichiers += 1
    print("Paquet : %s (%d fichier(s)), à téléverser dans claude.ai > Personnaliser > Skills." % (cible, fichiers))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = p.add_subparsers(dest="action", required=True)
    e = sous.add_parser("extraire")
    e.add_argument("--jours", type=int, default=7)
    e.add_argument("--racine", help="dossier des transcripts (défaut ~/.claude/projects)")
    e.add_argument("--aujourdhui", help="AAAA-MM-JJ, fin de période (tests)")
    e.add_argument("--cloud", help="dossier des tours écrits par les agents lecteurs (mode cloud)")
    e.add_argument("--sortie", required=True)
    c = sous.add_parser("cloud-sessions")
    c.add_argument("fichiers", nargs="+", help="sortie(s) de list_sessions enregistrée(s) dans un fichier")
    c.add_argument("--jours", type=int, default=7)
    c.add_argument("--aujourdhui", help="AAAA-MM-JJ, fin de période (tests)")
    c.add_argument("--sortie", required=True)
    k = sous.add_parser("paquet")
    k.add_argument("dossier")
    k.add_argument("--sortie", required=True)
    r = sous.add_parser("rapport")
    r.add_argument("propositions")
    r.add_argument("--signaux", required=True)
    r.add_argument("--sortie", default="~/rapports-improve-system")
    args = p.parse_args()
    if args.action in ("extraire", "cloud-sessions") and not 1 <= args.jours <= 60:
        sys.exit("--jours entre 1 et 60.")
    {"extraire": extraire, "cloud-sessions": cloud_sessions, "paquet": paquet, "rapport": rapport}[args.action](args)


if __name__ == "__main__":
    main()
