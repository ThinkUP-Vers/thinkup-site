#!/usr/bin/env python3
"""Contrôle SEO statique du site Think'UP (bibliothèque standard uniquement).

Lit les pages HTML de la racine et de editorial/scheduled-blog/, ne modifie rien.
Usage : python3 controle_seo.py [--racine .] [--json]
"""
import argparse, json, re, sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

DOMAINE = "https://think-up.fr"
IGNORER = re.compile(r"^google[0-9a-f]*\.html$|^[0-9a-f]{20,}\.txt$")
# Pages volontairement hors index ou hors sitemap.
HORS_SITEMAP = {"404.html", "merci.html"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""; self._in_title = False
        self.meta = {}; self.canonical = None; self.h1 = 0
        self.jsonld = []; self._in_ld = False; self._ld = ""
        self.img_sans_alt = 0; self.liens = []; self.lang = None

    def handle_starttag(self, tag, a):
        a = dict(a)
        if tag == "html": self.lang = a.get("lang")
        elif tag == "title": self._in_title = True
        elif tag == "meta":
            k = a.get("name") or a.get("property")
            if k: self.meta[k] = a.get("content", "")
        elif tag == "link" and a.get("rel") == "canonical": self.canonical = a.get("href")
        elif tag == "h1": self.h1 += 1
        elif tag == "img" and "alt" not in a:  # alt="" = image décorative, valide
            self.img_sans_alt += 1
        elif tag == "a" and a.get("href"): self.liens.append(a["href"])
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True; self._ld = ""

    def handle_endtag(self, tag):
        if tag == "title": self._in_title = False
        elif tag == "script" and self._in_ld:
            self._in_ld = False; self.jsonld.append(self._ld)

    def handle_data(self, d):
        if self._in_title: self.title += d
        if self._in_ld: self._ld += d


def analyser(racine: Path):
    pages = {}
    for dossier, prefixe in ((racine, ""), (racine / "editorial" / "scheduled-blog", "editorial/scheduled-blog/")):
        for f in sorted(dossier.glob("*.html")):
            if IGNORER.match(f.name):
                continue
            p = Page(); p.feed(f.read_text(encoding="utf-8", errors="replace"))
            pages[prefixe + f.name] = p
    return pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--racine", default="."); ap.add_argument("--json", action="store_true")
    r = Path(ap.parse_args().racine).resolve(); args = ap.parse_args()
    pages = analyser(r)
    pb = []  # (gravité, fichier, message)

    sitemap = r / "sitemap.xml"
    urls_sm = set(re.findall(r"<loc>([^<]+)</loc>", sitemap.read_text(encoding="utf-8"))) if sitemap.exists() else set()
    fichiers_sm = {u.removeprefix(DOMAINE + "/") or "index.html" for u in urls_sm}
    for f in fichiers_sm:
        if f.endswith(".html") and not (r / f).exists():
            pb.append(("haute", "sitemap.xml", f"URL sans fichier : {f}"))

    liees = set()
    for nom, p in pages.items():
        racine_pub = not nom.startswith("editorial/")
        for h in p.liens:
            u = urlparse(h)
            if u.scheme in ("mailto", "tel", "javascript") or h.startswith("#"):
                continue
            if u.netloc and u.netloc not in ("think-up.fr", "www.think-up.fr"):
                continue
            cible = u.path.lstrip("/") or "index.html"
            if cible.endswith(".html") or "." not in cible:
                cible = cible if cible.endswith(".html") else cible + ".html"
                if racine_pub and cible != nom:
                    liees.add(cible)
                if racine_pub and not (r / cible).exists() and not (cible.startswith("documents")):
                    pb.append(("haute", nom, f"lien interne cassé : {h}"))

        if nom in HORS_SITEMAP or not racine_pub:
            pass
        else:
            if nom not in fichiers_sm and not (nom == "index.html" and DOMAINE + "/" in urls_sm):
                pb.append(("moyenne", nom, "absente du sitemap.xml"))
        noindex = "noindex" in p.meta.get("robots", "").lower()
        if noindex:
            continue
        t = p.title.strip()
        if not t: pb.append(("haute", nom, "title manquant"))
        elif len(t) > 65: pb.append(("basse", nom, f"title long ({len(t)} car.)"))
        d = p.meta.get("description", "").strip()
        if not d: pb.append(("haute", nom, "meta description manquante"))
        elif not 70 <= len(d) <= 165: pb.append(("basse", nom, f"meta description {len(d)} car. (cible 70-160)"))
        if p.h1 != 1: pb.append(("moyenne", nom, f"{p.h1} balises h1 (attendu 1)"))
        if not p.canonical: pb.append(("haute", nom, "canonical manquant"))
        elif racine_pub and nom != "index.html" and p.canonical != f"{DOMAINE}/{nom}":
            pb.append(("haute", nom, f"canonical inattendu : {p.canonical}"))
        if not p.meta.get("og:image"): pb.append(("basse", nom, "og:image manquante"))
        if not p.jsonld: pb.append(("moyenne", nom, "aucun JSON-LD"))
        for raw in p.jsonld:
            try: json.loads(raw)
            except ValueError: pb.append(("haute", nom, "JSON-LD invalide"))
        if p.img_sans_alt: pb.append(("basse", nom, f"{p.img_sans_alt} image(s) sans attribut alt"))
        if p.lang != "fr": pb.append(("basse", nom, f"lang={p.lang}"))

    for nom in pages:
        if nom.startswith("editorial/") or nom in HORS_SITEMAP or nom == "index.html":
            continue
        if nom not in liees:
            pb.append(("moyenne", nom, "page orpheline : aucun lien interne entrant"))

    ordre = {"haute": 0, "moyenne": 1, "basse": 2}
    pb.sort(key=lambda x: (ordre[x[0]], x[1]))
    if args.json:
        print(json.dumps([dict(gravite=g, fichier=f, probleme=m) for g, f, m in pb], ensure_ascii=False, indent=1))
    else:
        print(f"{len(pages)} pages analysées, {len(urls_sm)} URL au sitemap, {len(pb)} constats")
        for g, f, m in pb: print(f"[{g}] {f} : {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
