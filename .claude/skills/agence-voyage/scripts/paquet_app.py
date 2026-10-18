#!/usr/bin/env python3
"""Construit le skill agence-voyage pour l'application Claude (claude.ai et application de bureau).

  paquet_app.py [--sortie DOSSIER]        # écrit DOSSIER/agence-voyage.zip

Une seule source : le paquet reprend les références, le script et l'exemple du skill Claude Code ;
seul SKILL.md diffère (app/SKILL.md). Après toute modification de ces fichiers, reconstruire le zip et
le téléverser à nouveau dans Personnaliser > Skills.

Code de sortie : 0 si le paquet est conforme, 1 sinon (rien n'est écrit).
"""
import argparse
import re
import sys
import zipfile
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
NOM = "agence-voyage"
CONTENU = ["references/*.md", "scripts/voyage.py", "exemple/dossier.json"]
DESCRIPTION_MAX = 200            # limite de l'aide claude.ai pour un skill téléversé
# Ce qui n'existe que dans Claude Code ou dans le dépôt du site.
PROPRE_AU_DEPOT = [r"\.claude/", r"AskUserQuestion", r"send_later", r"\bgit\b", r"voyages/profils"]


def controler(skill_md, fichiers):
    erreurs = []
    m = re.match(r"---\n(.*?)\n---\n", skill_md, re.S)
    if not m:
        return ["app/SKILL.md : en-tête YAML absent"]
    champs = dict(re.findall(r"^(\w+):\s*(.*)$", m.group(1), re.M))
    if champs.get("name") != NOM or not re.fullmatch(r"[a-z0-9-]{1,64}", champs.get("name", "")):
        erreurs.append(f"name doit valoir « {NOM} » (minuscules, chiffres, tirets, 64 caractères au plus)")
    desc = champs.get("description", "").strip()
    if not desc or desc in (">", "|"):
        erreurs.append("description absente ou sur plusieurs lignes : l'écrire sur une seule ligne")
    elif len(desc) > DESCRIPTION_MAX:
        erreurs.append(f"description de {len(desc)} caractères, {DESCRIPTION_MAX} au plus")
    for motif in PROPRE_AU_DEPOT:
        if re.search(motif, skill_md):
            erreurs.append(f"app/SKILL.md mentionne « {motif} », propre au dépôt ou à Claude Code")
    for chemin in sorted(set(re.findall(r"(?:references|scripts|exemple)/[\w.-]+\.\w+", skill_md))):
        if chemin not in fichiers:
            erreurs.append(f"app/SKILL.md cite {chemin}, absent du paquet")
    return erreurs


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sortie", default=".")
    a = p.parse_args()
    skill_md = (SKILL / "app" / "SKILL.md").read_text(encoding="utf-8")
    fichiers = {str(f.relative_to(SKILL)): f for motif in CONTENU for f in sorted(SKILL.glob(motif))}
    erreurs = controler(skill_md, fichiers)
    for e in erreurs:
        print(f"  ERREUR  {e}")
    if erreurs:
        return 1
    cible = Path(a.sortie) / f"{NOM}.zip"
    cible.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(cible, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{NOM}/SKILL.md", skill_md)
        for rel, f in fichiers.items():
            z.write(f, f"{NOM}/{rel}")
    print(cible)
    for n in zipfile.ZipFile(cible).namelist():
        print(f"  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
