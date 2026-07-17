# Mise en production — boutique Think'UP + corrections SEO

## État du dépôt (depuis le 17/07/2026)

Ce dépôt a été **resynchronisé avec la production** (think-up.fr, hébergé
chez Hostinger) : les 13 pages du sitemap de prod, `style.css` (v8),
`consent.js`, les visuels SVG, images, `llms.txt`/`llms-full.txt`,
`robots.txt` et `sitemap.xml` ont été rapatriés tels quels, puis :

- la **boutique** a été intégrée (lien « Boutique » dans la nav, « CGV » en
  footer de toutes les pages) ;
- les **pages fantômes** identifiées par l'audit SEO ont été supprimées du
  dépôt (a-propos, cas-clients, mentions, confidentialite, index-iceberg,
  ressources, taches-invisibles, diagnostic-roi-ia, gains-rapides-ia,
  cadrage-adoption-ia, styles.css, og-thinkup.png) — leurs redirections 301
  sont dans `htaccess-redirections.txt` ;
- les **articles 4 et 5** (finis mais jamais publiés en prod, 404) ont été
  mis aux standards (canonical think-up.fr, e-mail, nav, liens légaux).

Limite connue : `envoi-contact.php` (traitement du formulaire) est un
fichier serveur **non récupérable** depuis l'extérieur — il n'existe que
chez Hostinger. Ne pas l'écraser lors des transferts.

## Déploiement, dans l'ordre

### 1. Compléter la configuration (`boutique-config.js`)

- [ ] Prix HT (`prixEUR`) des offres vendables en ligne.
- [ ] Liens de paiement Qonto/Stripe dans `paymentUrl` (mode d'emploi en
      tête du fichier) + redirection après paiement vers
      `https://think-up.fr/merci.html`.
- [ ] **Obligatoire** : case d'acceptation des CGV dans le checkout
      (`https://think-up.fr/cgv.html`) et, si la prestation peut démarrer
      sous 14 jours pour un consommateur, recueil du renoncement au droit
      de rétractation (CGV art. 8.3).
- [ ] Faire valider `tvaApplicable`/`tauxTVA` par l'expert-comptable.

### 2. Compléter et faire valider les CGV (`cgv.html`)

- [ ] Champs `<!-- ⚠ À COMPLÉTER -->` : SIREN/SIRET, forme juridique,
      adresse complète, n° TVA ou franchise (art. 293 B).
- [ ] Médiateur de la consommation (obligatoire avant toute vente à des
      particuliers — art. L612-1 code conso).
- [ ] Relecture par un conseil juridique.
- [ ] Au passage : compléter `mentions-legales.html` (SIREN manquant —
      obligation LCEN, indépendante de la boutique).

### 3. Téléverser chez Hostinger (hPanel → Gestionnaire de fichiers)

Fichiers **nouveaux** : `boutique.html`, `boutique-config.js`,
`merci.html`, `cgv.html`, et si publication du blog : `article-4.html`,
`article-5.html`.

Fichiers **modifiés** (lien Boutique/CGV ajouté) : `index.html`,
`methode.html`, `offres.html`, `resultats.html`, `patrick.html`,
`contact.html`, `faq.html`, `blog.html`, `article-1.html`,
`article-2.html`, `article-3.html`, `mentions-legales.html`,
`politique-confidentialite.html`, `sitemap.xml` (+ boutique et cgv).

- [ ] Vérifier ensuite `https://think-up.fr/boutique.html` (affichage,
      mobile, console sans erreur).

### 4. Redirections 301

- [ ] Ajouter le contenu de `htaccess-redirections.txt` à la fin du
      `.htaccess` existant chez Hostinger (ne pas remplacer le fichier).
      Ces redirections suppriment les 9 pages fantômes/doublons encore en
      ligne, puis supprimer les fichiers correspondants sur le serveur.

### 5. Tester le tunnel complet

- [ ] Boutique → lien de paiement → acceptation CGV → paiement test →
      redirection merci.html → e-mail de confirmation du prestataire.

### 6. Seulement ensuite : neutraliser le miroir GitHub Pages

- [ ] Dépublier `thinkup-vers.github.io/thinkup-site` (GitHub → Settings →
      Pages → désactiver) : le miroir concurrence think-up.fr dans Google.
      Ne pas le faire avant le déploiement, sous peine de n'avoir la
      boutique nulle part.

### 7. Optionnel mais recommandé (suite du plan SEO/GEO)

- [ ] Publier articles 4-5 : les téléverser + les ajouter à `blog.html`
      et au sitemap de prod.
- [ ] Paragraphe de désambiguïsation « Index Iceberg (méthode Think'UP) ≠
      Iceberg Index (étude MIT 2025) » sur methode.html.
- [ ] Ajouter un footer à `faq.html` (seule page de prod sans footer —
      le lien CGV n'a pas pu y être ajouté).
- [ ] Mentions tierces (France Num, CCI, Bpifrance, presse PME) — levier
      GEO n°1 d'après les études 2025-2026.
