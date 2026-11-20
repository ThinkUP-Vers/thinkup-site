# -*- coding: utf-8 -*-
"""Genere une version Markdown de chaque page du site, a cote du .html.

Pourquoi : les agents et les moteurs de reponse qui demandent
`Accept: text/markdown` recoivent le texte de la page sans le balisage, la
navigation ni les scripts. `.htaccess` sert ce .md par negociation de contenu
et annonce son existence dans un en-tete `Link` (RFC 8288).

Ou : lance par .github/workflows/deploy.yml AVANT le transfert FTP, donc les
.md sont toujours regeneres depuis le HTML reellement deploye. Ils ne sont pas
versionnes : il n'y a aucun moyen qu'ils derivent du HTML.

Aucune dependance : seule la bibliotheque standard. Le balisage du site est
homogene (un seul gabarit, un seul auteur), un convertisseur cible suffit et
evite d'ajouter un paquet tiers a la chaine de deploiement.

    python -I editorial/generer-markdown.py            # ecrit les .md
    python -I editorial/generer-markdown.py --lister    # n'ecrit rien
"""
from __future__ import annotations

import html
import io
import os
import re
import sys
from html.parser import HTMLParser

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://think-up.fr/'

# Pages a ne pas convertir : le fichier de verification Google (sans contenu)
# et la page 404 (aucune valeur pour un agent).
IGNOREES = re.compile(r'^(google[0-9a-f]+\.html|404\.html)$')

# Elements dont le contenu ne doit jamais apparaitre dans le texte.
MUETS = {'script', 'style', 'noscript', 'template', 'svg', 'select', 'option',
         'button', 'form', 'iframe', 'canvas'}

BLOCS = {'p', 'div', 'section', 'article', 'header', 'footer', 'aside', 'main',
         'ul', 'ol', 'table', 'tr', 'blockquote', 'details', 'figure',
         'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}


def absolu(url: str) -> str:
    """Rend une URL relative absolue : un .md peut etre lu hors du site."""
    url = url.strip()
    if not url or url.startswith(('http://', 'https://', 'mailto:', 'tel:')):
        return url
    if url.startswith('#'):
        return url
    return SITE + url.lstrip('/')


class Convertisseur(HTMLParser):
    """Transforme le contenu de <main> en Markdown."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.muet = 0            # profondeur dans un element muet
        self.pre = 0
        self.listes: list[dict] = []   # pile de listes imbriquees
        self.lien: str | None = None   # href du lien courant
        self.texte_lien: list[str] = []
        self.cellules: list[str] | None = None   # ligne de tableau en cours
        self.tableau: list[list[str]] | None = None
        self.entete_faite = False
        self.dans_cellule = False
        self.cellule: list[str] = []
        self.niveau_titre = 0
        self.titre: list[str] = []
        self.citation = 0

    # -- sorties -----------------------------------------------------------
    def ecrire(self, texte: str) -> None:
        if self.dans_cellule:
            self.cellule.append(texte)
        elif self.lien is not None:
            self.texte_lien.append(texte)
        elif self.niveau_titre:
            self.titre.append(texte)
        else:
            self.out.append(texte)

    def saut(self, n: int = 1) -> None:
        if self.dans_cellule or self.lien is not None or self.niveau_titre:
            return
        courant = ''.join(self.out[-3:])
        if not courant.strip() and not self.out:
            return
        deja = len(courant) - len(courant.rstrip('\n'))
        for _ in range(max(0, n - deja)):
            self.out.append('\n')

    # -- balises -----------------------------------------------------------
    def handle_starttag(self, tag: str, attrs_list) -> None:
        attrs = {k: (v or '') for k, v in attrs_list}

        if tag in MUETS:
            self.muet += 1
            return
        if self.muet:
            return

        # Un element explicitement cache n'a pas a figurer dans le texte.
        if 'hidden' in attrs or attrs.get('aria-hidden') == 'true':
            self.muet += 1
            return

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.saut(2)
            self.niveau_titre = int(tag[1])
            self.titre = []
        elif tag == 'summary':
            # L'intitule d'un accordeon (une question de FAQ) est un titre.
            self.saut(2)
            self.niveau_titre = 3
            self.titre = []
        elif tag == 'p':
            self.saut(2)
        elif tag == 'br':
            self.ecrire('  \n')
        elif tag == 'hr':
            self.saut(2)
            self.ecrire('---')
            self.saut(2)
        elif tag in ('ul', 'ol'):
            self.saut(2)
            self.listes.append({'ordonnee': tag == 'ol', 'n': 0})
        elif tag == 'li':
            if self.listes:
                self.saut(1)
                niveau = len(self.listes) - 1
                liste = self.listes[-1]
                liste['n'] += 1
                puce = f"{liste['n']}. " if liste['ordonnee'] else '- '
                self.ecrire('  ' * niveau + puce)
        elif tag in ('strong', 'b'):
            self.ecrire('**')
        elif tag in ('em', 'i'):
            self.ecrire('*')
        elif tag == 'code':
            self.ecrire('`')
        elif tag == 'blockquote':
            self.saut(2)
            self.citation += 1
        elif tag == 'a':
            href = attrs.get('href', '')
            if href and not href.startswith('javascript:'):
                self.lien = absolu(href)
                self.texte_lien = []
        elif tag == 'img':
            alt = attrs.get('alt', '').strip()
            src = absolu(attrs.get('src', ''))
            if alt and src:
                self.ecrire(f'![{alt}]({src})')
        elif tag == 'table':
            self.saut(2)
            self.tableau = []
            self.entete_faite = False
        elif tag == 'tr' and self.tableau is not None:
            self.cellules = []
        elif tag in ('td', 'th') and self.cellules is not None:
            self.dans_cellule = True
            self.cellule = []
        elif tag in BLOCS:
            self.saut(2)

    def handle_endtag(self, tag: str) -> None:
        if tag in MUETS:
            self.muet = max(0, self.muet - 1)
            return
        if self.muet:
            # Un element cache ferme aussi le compteur muet.
            self.muet = max(0, self.muet - 1)
            return

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'summary'):
            texte = re.sub(r'\s+', ' ', ''.join(self.titre)).strip()
            niveau, self.niveau_titre = self.niveau_titre, 0
            if texte:
                self.out.append('#' * niveau + ' ' + texte)
                self.saut(2)
        elif tag == 'a' and self.lien is not None:
            texte = re.sub(r'\s+', ' ', ''.join(self.texte_lien)).strip()
            href, self.lien = self.lien, None
            if texte:
                if href.startswith('#'):
                    self.ecrire(texte)
                else:
                    self.ecrire(f'[{texte}]({href})')
        elif tag in ('strong', 'b'):
            self.ecrire('**')
        elif tag in ('em', 'i'):
            self.ecrire('*')
        elif tag == 'code':
            self.ecrire('`')
        elif tag == 'blockquote':
            self.citation = max(0, self.citation - 1)
            self.saut(2)
        elif tag in ('ul', 'ol'):
            if self.listes:
                self.listes.pop()
            self.saut(2)
        elif tag in ('td', 'th') and self.cellules is not None:
            self.dans_cellule = False
            self.cellules.append(
                re.sub(r'\s+', ' ', ''.join(self.cellule)).strip().replace('|', r'\|'))
        elif tag == 'tr' and self.tableau is not None and self.cellules is not None:
            if any(self.cellules):
                self.tableau.append(self.cellules)
            self.cellules = None
        elif tag == 'table' and self.tableau is not None:
            self._vider_tableau()
        elif tag in ('p', 'li'):
            self.saut(1 if tag == 'li' else 2)
        elif tag in BLOCS:
            self.saut(2)

    def handle_data(self, data: str) -> None:
        if self.muet:
            return
        if not data.strip():
            # Un espace entre deux mots doit survivre, pas une indentation.
            if data and not self.out[-1:] == ['\n'] and ' ' in data:
                self.ecrire(' ')
            return
        self.ecrire(re.sub(r'\s+', ' ', data))

    def _vider_tableau(self) -> None:
        lignes, self.tableau = self.tableau or [], None
        if not lignes:
            return
        largeur = max(len(l) for l in lignes)
        lignes = [l + [''] * (largeur - len(l)) for l in lignes]
        self.out.append('| ' + ' | '.join(lignes[0]) + ' |\n')
        self.out.append('|' + '|'.join([' --- '] * largeur) + '|\n')
        for ligne in lignes[1:]:
            self.out.append('| ' + ' | '.join(ligne) + ' |\n')
        self.saut(2)

    def resultat(self) -> str:
        texte = ''.join(self.out)
        texte = re.sub(r'[ \t]+\n', '\n', texte)
        texte = re.sub(r'\n{3,}', '\n\n', texte)
        texte = re.sub(r'\n +([-*#\d])', r'\n\1', texte)
        return texte.strip() + '\n'


def entre_balises(source: str, balise: str) -> str:
    """Contenu du premier <balise ...> ... </balise>, imbrication comprise."""
    debut = re.search(r'<%s\b[^>]*>' % balise, source, re.I)
    if not debut:
        return ''
    i = debut.end()
    profondeur = 1
    motif = re.compile(r'</?%s\b[^>]*>' % balise, re.I)
    while profondeur:
        m = motif.search(source, i)
        if not m:
            return source[debut.end():]
        profondeur += -1 if m.group(0).startswith('</') else 1
        i = m.end()
        if not profondeur:
            return source[debut.end():m.start()]
    return ''


def meta(source: str, nom: str) -> str:
    """Valeur d'un <meta name="..."> .

    Le guillemet fermant est capture par retro-reference (\\2) et non par
    ["\\'] : 22 des 34 descriptions du site contiennent une apostrophe
    (« FAQ Think'UP »), qui coupait la valeur des le premier mot.
    """
    m = re.search(
        r'<meta\s+name=(["\'])%s\1\s+content=(["\'])(.*?)\2' % nom,
        source, re.I | re.S)
    return html.unescape(m.group(3)).strip() if m else ''


def convertir(chemin: str) -> str:
    with io.open(chemin, encoding='utf-8') as f:
        source = f.read()

    m = re.search(r'<title>(.*?)</title>', source, re.I | re.S)
    titre = html.unescape(m.group(1)).strip() if m else ''
    description = meta(source, 'description')

    m = re.search(r'<link\s+rel=["\']canonical["\']\s+href=(["\'])(.*?)\1',
                  source, re.I)
    canonique = m.group(2).strip() if m else SITE + os.path.basename(chemin)

    conv = Convertisseur()
    conv.feed(entre_balises(source, 'main'))
    conv.close()

    # En-tete YAML plutot qu'un titre « # » : chaque page porte deja un seul
    # <h1> dans son <main>, qui reste donc l'unique titre de niveau 1 du
    # document. Mettre le <title> en « # » en aurait cree un deuxieme.
    def yaml(valeur: str) -> str:
        return '"%s"' % valeur.replace('\\', r'\\').replace('"', r'\"')

    tete = ['---']
    if titre:
        tete.append('title: ' + yaml(titre))
    if description:
        tete.append('description: ' + yaml(description))
    tete.append('source: ' + canonique)
    tete.append('---')

    return '\n'.join(tete) + '\n\n' + conv.resultat()


def main(argv: list[str]) -> int:
    lister = '--lister' in argv
    pages = sorted(f for f in os.listdir(RACINE)
                   if f.endswith('.html') and not IGNOREES.match(f))
    if not pages:
        print('ERREUR : aucune page HTML trouvee dans %s' % RACINE,
              file=sys.stderr)
        return 1

    vides = []
    for page in pages:
        texte = convertir(os.path.join(RACINE, page))
        cible = page[:-5] + '.md'
        # Un .md quasi vide signale un gabarit que le convertisseur n'a pas
        # compris : mieux vaut casser le deploiement que servir une page creuse.
        if len(texte) < 400:
            vides.append('%s (%d octets)' % (cible, len(texte)))
        if not lister:
            with io.open(os.path.join(RACINE, cible), 'w',
                         encoding='utf-8', newline='\n') as f:
                f.write(texte)
        print('%-44s %6d octets' % (cible, len(texte)))

    if vides:
        print('\nERREUR : contenu insuffisant pour %s' % ', '.join(vides),
              file=sys.stderr)
        return 1

    print('\n%d pages converties%s.' % (len(pages), ' (simulation)' if lister else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
