/* ================================================================
   THINK'UP — CONFIGURATION DE LA BOUTIQUE
   ================================================================
   C'est LE SEUL fichier à modifier pour activer la vente en ligne.
   Aucun backend : les paiements passent par des liens de paiement
   hébergés (Qonto Payment Links ou Stripe Payment Links).

   ── MODE D'EMPLOI ────────────────────────────────────────────────
   1. Créer le lien de paiement :
      · QONTO  : app Qonto → Facturation → Liens de paiement →
        « Créer un lien de paiement » → montant TTC, description =
        nom de l'offre → copier l'URL (https://pay.qonto.com/...).
      · STRIPE : dashboard Stripe → Liens de paiement → « + Nouveau »
        → produit + prix → copier l'URL (https://buy.stripe.com/...).
   2. Dans les options du lien, définir la page de confirmation
      (redirection après paiement) :
        https://www.think-up.fr/merci.html
   3. Coller l'URL ci-dessous dans `paymentUrl` de l'offre concernée
      et renseigner `prixEUR` (montant HORS TAXES, en euros).
   4. Enregistrer et déployer. C'est tout.

   ── COMPORTEMENT DES BOUTONS SUR boutique.html ──────────────────
   · prixEUR = null                → carte « Sur devis » (lien contact)
   · prixEUR renseigné, paymentUrl vide ("")
                                   → prix affiché + bouton désactivé
                                     « Bientôt disponible » + fallback
                                     commande par e-mail
   · prixEUR + paymentUrl renseignés
                                   → bouton « Acheter » actif
   ================================================================ */

window.BOUTIQUE_CONFIG = {

  /* TVA ──────────────────────────────────────────────────────────
     · tvaApplicable: true  → les prix saisis sont HT, le TTC est
       calculé et affiché automatiquement (taux ci-dessous).
     · tvaApplicable: false → à utiliser si Think'UP est en franchise
       en base de TVA (art. 293 B du CGI) : le prix saisi est affiché
       tel quel avec la mention légale « TVA non applicable ».
     ⚠ À FAIRE VALIDER par l'expert-comptable selon le statut réel. */
  tvaApplicable: true,
  tauxTVA: 0.20,

  /* E-mail de secours pour la commande tant que le lien de paiement
     n'est pas configuré. */
  emailCommande: "patrick@thinkupcom.com",

  offres: {

    /* ── Offre 1 : Atelier Déclic IA (2–3 h) ─────────────────────
       Achetable en ligne dès que prixEUR et paymentUrl sont remplis.
       Exemple : prixEUR: 1500, paymentUrl: "https://pay.qonto.com/..." */
    atelier: {
      label: "Atelier Déclic IA utile",
      prixEUR: null,      // ← montant HT en euros (ex. 1500). null = sur devis
      paymentUrl: ""      // ← coller ici l'URL Qonto/Stripe
    },

    /* ── Offre 2 : Diagnostic & cadrage Index Iceberg ────────────
       Peut être vendu en ligne à prix fixe (ex. acompte de cadrage)
       ou laissé sur devis si le prix dépend du périmètre. */
    diagnostic: {
      label: "Diagnostic & cadrage Index Iceberg",
      prixEUR: null,      // ← montant HT en euros. null = sur devis
      paymentUrl: ""      // ← coller ici l'URL Qonto/Stripe
    },

    /* ── Offre 3 : Pilotage IA & réseau de freelances ────────────
       Offre sur mesure (forfait ou régie) : le prix dépend du
       périmètre. Laisser prixEUR à null — la carte reste « sur
       devis » et renvoie vers le formulaire de contact. */
    pilotage: {
      label: "Pilotage IA & réseau de freelances",
      prixEUR: null,      // laisser null : offre sur mesure
      paymentUrl: ""
    }
  }
};
