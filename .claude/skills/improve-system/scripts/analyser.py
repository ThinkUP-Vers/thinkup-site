#!/usr/bin/env python3
"""Extraction des signaux des sessions Claude Code et rapport improve-system.

  python3 analyser.py extraire [--jours 7] [--racine ~/.claude/projects]
                               [--aujourdhui AAAA-MM-JJ] --sortie DOSSIER
      Lit les transcripts .jsonl en lecture seule et écrit DOSSIER/signaux.json
      (données complètes) et DOSSIER/resume.txt (vue compacte à lire en entier).
      Chaque signal porte un identifiant stable : D demande, C commande,
      E erreur d'outil, R refus d'une action, I interruption, A erreur d'API.

  python3 analyser.py rapport PROPOSITIONS.json --signaux DOSSIER/signaux.json
                              --sortie ~/rapports-improve-system
      Contrôle les propositions (deux exemples tirés des signaux, de deux
      sessions distinctes) et écrit improve-system-AAAA-MM-JJ.md et .json.
      Code retour 1 et liste des erreurs si le fichier n'est pas conforme.

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

def extraire(args):
    racine_defaut = args.racine is None
    racine = Path(args.racine or "~/.claude/projects").expanduser()
    if args.aujourdhui:
        fin = dt.datetime.combine(dt.date.fromisoformat(args.aujourdhui), dt.time(23, 59, 59)).astimezone()
    else:
        fin = dt.datetime.now().astimezone()
    debut = fin - dt.timedelta(days=args.jours)
    sortie = Path(args.sortie).expanduser()
    refuser_si_depot(sortie)
    if not racine.is_dir():
        sys.exit("Dossier introuvable : %s" % racine)

    exclue = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    sessions, signaux = {}, []
    etats = collections.defaultdict(lambda: {"rang": 0, "question": False, "outil": None, "demande": None})
    commandes, skills_utilises = collections.Counter(), collections.Counter()
    nb_fichiers = lignes_invalides = 0

    def session(sid, entree, quand):
        s = sessions.setdefault(sid, {"id": "S-" + sid[:8], "session": sid, "projet": "", "debut": quand,
                                      "fin": quand, "demandes": 0, "premiere_demande": ""})
        if entree.get("cwd") and not s["projet"]:
            s["projet"] = entree["cwd"]
        s["debut"], s["fin"] = min(s["debut"], quand), max(s["fin"], quand)
        return s

    def ajouter(type_, ident, quand, sid, s, **champs):
        signaux.append(dict({"id": ident, "type": type_, "horodatage": quand.isoformat(timespec="minutes"),
                             "date": date_fr(quand), "session": s["id"],
                             "projet": Path(s["projet"]).name if s["projet"] else ""}, **champs))

    for fichier in sorted(racine.rglob("*.jsonl")):
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
    if racine_defaut and os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        avertissements.append("Session cloud : ~/.claude/projects ne contient ici que les sessions de ce conteneur. "
                              "Tes autres sessions (poste local, autres sessions cloud) ne sont pas lues.")
    if exclue:
        avertissements.append("La session en cours (%s) est exclue de l'analyse." % ("S-" + exclue[:8]))
    if len(liste_sessions) < 3:
        avertissements.append("Seulement %d session(s) sur la période : trop peu pour parler de récurrence."
                              % len(liste_sessions))
    if lignes_invalides:
        avertissements.append("%d ligne(s) illisible(s) ignorée(s) dans les transcripts." % lignes_invalides)

    compte = collections.Counter(x["type"] for x in signaux)
    corrections = sum(1 for x in signaux if x.get("correction"))
    meta = {"genere": dt.datetime.now().astimezone().isoformat(timespec="minutes"),
            "debut": date_fr(debut), "fin": date_fr(fin), "jours": args.jours, "racine": str(racine),
            "fichiers_lus": nb_fichiers, "sessions": len(liste_sessions), "demandes": compte["demande"],
            "corrections_presumees": corrections, "erreurs": compte["erreur"], "refus": compte["refus"],
            "interruptions": compte["interruption"], "erreurs_api": compte["erreur_api"],
            "commandes": compte["commande"]}
    projets = {s["projet"] for s in liste_sessions if s["projet"] and Path(s["projet"]).is_dir()}
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
            s["id"], s["debut"], s["fin"][-5:], Path(s["projet"]).name if s["projet"] else "?",
            s["demandes"], s["premiere_demande"]))
    sig = d["signaux"]
    lignes += ["", "DEMANDES (#rang dans la session ; CORR = correction présumée ; ?= suit une question de Claude)"]
    for x in sig:
        if x["type"] == "demande":
            drapeaux = (" CORR[%s]" % ", ".join(x["correction"]) if x["correction"] else "") + \
                       (" ?" if x["apres_question"] else "")
            lignes.append("%s | %s | %s #%d%s | %s" % (x["id"], x["date"], x["session"], x["rang"], drapeaux,
                                                      x["texte"]))
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
    return "- %s · %s · session %s (%s) — %s" % (x["date"], x["projet"] or "?", x["session"], x["id"],
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
    for j, a in enumerate(props.get("a_surveiller") or [], 1):
        if not isinstance(a, dict) or not a.get("sujet") or not isinstance(a.get("ids"), list) or not a["ids"]:
            erreurs.append("À surveiller %d : objet {sujet, ids} attendu." % j)
        elif any(e not in index for e in a["ids"]):
            erreurs.append("À surveiller %d : identifiant absent de signaux.json." % j)
    return erreurs, alertes


def rapport(args):
    props = json.loads(Path(args.propositions).expanduser().read_text(encoding="utf-8"))
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

    index, m = {x["id"]: x for x in donnees["signaux"]}, donnees["meta"]
    aujourd_hui = dt.date.today()
    lignes = ["# Améliorer le système — rapport du %s" % aujourd_hui.strftime("%d/%m/%Y"), "",
              "Période analysée : %s → %s (%d jours) · %d sessions · %d demandes · %d corrections présumées · "
              "%d erreurs d'outil · %d refus · %d interruptions." % (
                  m["debut"], m["fin"], m["jours"], m["sessions"], m["demandes"], m["corrections_presumees"],
                  m["erreurs"], m["refus"], m["interruptions"]), ""]
    if donnees["avertissements"]:
        lignes += ["Limites de la lecture :"] + ["- " + a for a in donnees["avertissements"]] + [""]
    lignes += ["## Synthèse", "", props["synthese"].strip(), "", "## Propositions", ""]
    if not props["propositions"]:
        lignes += ["Aucun schéma ne revient dans au moins deux sessions : rien à proposer cette fois.", ""]
    for i, p in enumerate(props["propositions"], 1):
        occurrences = sorted(set(p.get("occurrences") or []) | set(p["exemples"]),
                             key=lambda e: index[e]["horodatage"])
        sessions = {index[e]["session"] for e in occurrences}
        lignes += [
            "### %d. `%s` — %s" % (i, p["nom"], FORMES[p["forme"]]), "",
            "Priorité %s · %s · %s. %d occurrence(s) dans %d session(s), du %s au %s." % (
                p["priorite"], p["certitude"], ", ".join(NATURES[n] for n in p["natures"]), len(occurrences),
                len(sessions), index[occurrences[0]]["date"][:10], index[occurrences[-1]]["date"][:10]), "",
            "**Constat.** " + p["constat"].strip(), "",
            "**Ce que ferait la solution.** " + p["solution"].strip(), ""]
        if p.get("declencheurs"):
            lignes += ["**Déclencheurs.** " + " ; ".join("« %s »" % d for d in p["declencheurs"]), ""]
        lignes += ["**Étapes envisagées.**", ""] + ["%d. %s" % (k, e) for k, e in enumerate(p["etapes"], 1)] + [""]
        lignes += ["**Exemples datés.**", ""] + [ligne_exemple(index[e]) for e in p["exemples"]] + [""]
        lignes += ["**Gain attendu.** " + p["gain"].strip(), "", "**Limite.** " + p["limite"].strip(), ""]
    if props.get("a_surveiller"):
        lignes += ["## À surveiller (cas isolés, pas encore une tendance)", ""]
        for a in props["a_surveiller"]:
            premier = index[a["ids"][0]]
            lignes.append("- %s — %s, %s" % (a["sujet"], premier["date"][:10], citation(premier)))
        lignes.append("")
    groupes = [g for g in donnees["groupes_erreurs"] if g["occurrences"] >= 2][:10]
    if groupes:
        lignes += ["## Échecs d'outils les plus fréquents (données brutes)", "",
                   "| Outil | Erreur | Occurrences | Sessions |", "|---|---|---|---|"]
        lignes += ["| %s | %s | %d | %d |" % (g["outil"], g["signature"].replace("|", "/"), g["occurrences"],
                                              g["sessions"]) for g in groupes]
        lignes.append("")
    lignes += ["## Installation", "",
               "Rien n'a été installé. Pour installer, réponds avec les numéros retenus (par exemple « installe 1 "
               "et 3 »). Destination par défaut : `~/.claude/skills/<nom>/`. Un dossier existant n'est jamais "
               "écrasé sans ton accord.", ""]

    sortie.mkdir(parents=True, exist_ok=True)
    base, n = "improve-system-%s" % aujourd_hui.isoformat(), 1
    while (sortie / (base + ".md")).exists():
        n += 1
        base = "improve-system-%s-%d" % (aujourd_hui.isoformat(), n)
    (sortie / (base + ".md")).write_text("\n".join(lignes), encoding="utf-8")
    (sortie / (base + ".json")).write_text(json.dumps(props, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Rapport : %s" % (sortie / (base + ".md")))
    print("Propositions : %s" % (sortie / (base + ".json")))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sous = p.add_subparsers(dest="action", required=True)
    e = sous.add_parser("extraire")
    e.add_argument("--jours", type=int, default=7)
    e.add_argument("--racine", help="dossier des transcripts (défaut ~/.claude/projects)")
    e.add_argument("--aujourdhui", help="AAAA-MM-JJ, fin de période (tests)")
    e.add_argument("--sortie", required=True)
    r = sous.add_parser("rapport")
    r.add_argument("propositions")
    r.add_argument("--signaux", required=True)
    r.add_argument("--sortie", default="~/rapports-improve-system")
    args = p.parse_args()
    if args.action == "extraire":
        if not 1 <= args.jours <= 60:
            sys.exit("--jours entre 1 et 60.")
        extraire(args)
    else:
        rapport(args)


if __name__ == "__main__":
    main()
