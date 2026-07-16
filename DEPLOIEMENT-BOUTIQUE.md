# Mise en production de la boutique Think'UP

⚠ **Contexte important** : le site en production `https://think-up.fr` est
hébergé chez **Hostinger** et son code est plus récent que ce dépôt (qui
alimente un miroir GitHub Pages périmé, `thinkup-vers.github.io/thinkup-site`).
Pousser ce dépôt ne publie donc **rien** sur think-up.fr : les fichiers de la
boutique doivent être téléversés chez Hostinger. Suivre l'ordre ci-dessous.

## 1. Compléter la configuration (`boutique-config.js`)

- [ ] Renseigner les prix HT (`prixEUR`) des offres vendables en ligne.
- [ ] Créer les liens de paiement Qonto ou Stripe (mode d'emploi détaillé en
      tête du fichier) et coller chaque URL dans `paymentUrl`.
- [ ] Configurer la redirection après paiement vers `https://think-up.fr/merci.html`.
- [ ] **Obligatoire** : activer la case d'acceptation des CGV
      (`https://think-up.fr/cgv.html`) dans le checkout Qonto/Stripe, et le
      recueil du renoncement au droit de rétractation si la prestation peut
      démarrer sous 14 jours pour un client consommateur (CGV art. 8.3).
- [ ] Faire valider `tvaApplicable`/`tauxTVA` par l'expert-comptable.

## 2. Compléter et faire valider les CGV (`cgv.html`)

- [ ] Remplir tous les champs marqués `<!-- ⚠ À COMPLÉTER -->` : SIREN/SIRET,
      forme juridique, adresse complète, n° TVA (ou franchise art. 293 B).
- [ ] Désigner un **médiateur de la consommation** (obligatoire avant toute
      vente à des particuliers — art. L612-1 code de la consommation).
- [ ] Faire relire l'ensemble par un conseil juridique.
- [ ] Au passage : compléter aussi `mentions-legales.html` (SIREN manquant —
      obligation LCEN, indépendamment de la boutique).

## 3. Téléverser chez Hostinger

- [ ] Déposer à la racine du site : `boutique.html`, `boutique-config.js`,
      `merci.html`, `cgv.html`.
- [ ] Vérifier que `https://think-up.fr/boutique.html` s'affiche correctement
      (design, mobile, sans erreur console).

## 4. Intégrer la boutique aux pages de la PROD

Les pages de production (plus récentes que ce dépôt) doivent recevoir :

- [ ] Lien « Boutique » dans la navigation : index, offres, methode,
      resultats, blog, patrick, contact, faq, articles.
- [ ] Lien « CGV » dans le footer des mêmes pages.

## 5. Sitemap de la PROD

- [ ] Ajouter `https://think-up.fr/boutique.html` et
      `https://think-up.fr/cgv.html` au sitemap servi par Hostinger.
- [ ] Ne PAS y ajouter `merci.html` (page en noindex).

## 6. Tester le tunnel complet

- [ ] Paiement test de bout en bout : boutique → lien de paiement →
      acceptation CGV → paiement → redirection vers merci.html → e-mail de
      confirmation du prestataire.

## 7. Seulement ensuite : neutraliser le miroir GitHub Pages

- [ ] Une fois la boutique en ligne sur think-up.fr, dépublier
      `thinkup-vers.github.io/thinkup-site` (Settings → Pages → désactiver)
      pour supprimer le site dupliqué qui concurrence le domaine principal.
      Ne pas le faire avant, sous peine de n'avoir la boutique nulle part.
