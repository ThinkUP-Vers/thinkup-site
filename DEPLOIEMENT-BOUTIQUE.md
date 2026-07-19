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

Depuis le 17/07/2026, le dépôt contient aussi `envoi-contact.php`,
`.htaccess` (fournis par le client, redirections des pages fantômes
fusionnées dedans) et `404.html` : le dépôt est la source de vérité
complète. Restent uniquement côté serveur : `publish-blog.php`,
`editorial-content/`, `scheduled-blog/` (l'automate de publication du
blog) — jamais touchés par le déploiement.

⚠ Interaction avec l'automate du blog : s'il publie un article, il modifie
`sitemap.xml` et `blog.html` SUR LE SERVEUR ; le déploiement suivant les
écrasera avec la version du dépôt. Après chaque article publié par
l'automate, rapatrier ces fichiers dans le dépôt (ou me le signaler).

## Déploiement, dans l'ordre

### 1. Compléter la configuration (`boutique-config.js`)

- [x] Prix nets fixés (17/07/2026) : Atelier 1 200 €, Diagnostic 6 900 €,
      Pilotage sur devis. TVA non applicable (art. 293 B), `tvaApplicable:false`.
- [ ] Liens de paiement dans `paymentUrl` — ⚠ à créer depuis un compte
      détenu par **Think'UP (EI, SIREN 944 966 613)**, PAS depuis le Qonto
      de PL HOLDING (entité différente : c'est elle qui encaisserait).
      Redirection après paiement vers `https://think-up.fr/merci.html`.
- [ ] **Obligatoire** : case d'acceptation des CGV dans le checkout
      (`https://think-up.fr/cgv.html`) et, si la prestation peut démarrer
      sous 14 jours pour un consommateur, recueil du renoncement au droit
      de rétractation (CGV art. 8.3).
- [ ] Point de vigilance expert-comptable : au rythme de ces prix, le
      plafond de la franchise en base de TVA (services) peut être atteint
      en quelques ventes — surveiller le seuil.

### 2. Compléter et faire valider les CGV (`cgv.html`)

- [x] Identité vendeur complétée (17/07/2026) : EI Think'UP, SIREN
      944 966 613, SIRET 944 966 613 00019, 22 rue Victor Hugo 78000
      Versailles, TVA non applicable art. 293 B. Idem `mentions-legales.html`.
- [ ] Médiateur de la consommation (obligatoire avant toute vente à des
      particuliers — art. L612-1 code conso).
- [ ] Assurance RCP : compléter l'article si souscrite.
- [ ] Relecture par un conseil juridique.

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

- [x] Intégrées au `.htaccess` du dépôt (section 2d) — déployées
      automatiquement. Après déploiement : supprimer sur le serveur les 9
      fichiers fantômes correspondants (index-iceberg, mentions,
      cas-clients, a-propos, ressources, taches-invisibles,
      diagnostic-roi-ia, gains-rapides-ia, cadrage-adoption-ia .html).

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
