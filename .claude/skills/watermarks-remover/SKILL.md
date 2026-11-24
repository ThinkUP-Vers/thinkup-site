---
name: watermarks-remover
description: Audite et retire les caractères Unicode invisibles ou trompeurs (zéro-largeur, contrôles bidirectionnels, espaces exotiques, homoglyphes) d'un texte, d'un fichier Markdown ou d'une page HTML. Déclencher sur « caractères invisibles », « nettoie ce texte », « watermark Unicode », « /watermarks-remover ». Ne réécrit JAMAIS la prose sans accord explicite de Patrick ; n'efface aucune marque de provenance IA (C2PA, métadonnées) ni ne vise à contourner un détecteur.
---

# Nettoyage Unicode (audit d'abord)

Copie réduite de `guillaumemeyer/watermarks-remover` (MIT, voir `LICENSE` et `ORIGINE.md`). Seule la couche déterministe est conservée : scripts Python locaux, sans réseau.

## Règles

1. Auditer avant de modifier. Rendre le décompte par type de caractère et leur position.
2. Nettoyer vers un nouveau fichier `*.cleaned.*`, jamais sur place sans demande.
3. Aucune réécriture de la prose, aucune « humanisation » ni passe anti-détection, sauf demande explicite de Patrick pour ce texte précis. Pour le style, utiliser `stop-slop`.
4. Ne pas présenter un texte nettoyé comme « écrit par un humain » : un retrait de caractères ne dit rien sur l'origine. Conserver toute mention de transparence requise (AI Act, article 50, ou autre).
5. Dans du HTML ou du Markdown, si une occurrence tombe dans du code, un attribut ou une URL, ne pas nettoyer le fichier entier : traiter les seuls passages de prose.
6. Pas de PDF, DOCX, image ni archive : le script ne traite que du texte.

## Commandes

`SCRIPTS` = le dossier `scripts/` de ce skill.

```bash
python3 -I "$SCRIPTS/inspect_text.py" --audit FICHIER
python3 -I "$SCRIPTS/clean_text.py" FICHIER -o FICHIER.cleaned --stats --no-normalize-spaces
python3 -I "$SCRIPTS/inspect_text.py" --audit FICHIER.cleaned
```

`--no-normalize-spaces` garde les espaces insécables, utiles en français avant « : », « ; », « ! » et « ? ». N'utiliser `--aggressive-homoglyphs`, `--nfkc` ni `--strip-emoji-glue` que sur demande, car ils peuvent altérer le français, les emojis ou la typographie.

## Compte rendu

Séparer ce qui est vérifié (caractères retirés, avec le décompte du script) de ce qui n'est pas établi (origine du texte, résistance à un détecteur). Contexte et limites : `references/watermark-notes.md`, `references/responsible-use.md`.
