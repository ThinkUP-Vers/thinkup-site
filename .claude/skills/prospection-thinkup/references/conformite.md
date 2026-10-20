# Conformité de la prospection B2B

Ce n'est pas un avis juridique. Tout point de fond relève de Patrick ou du skill `compliance-rgpd-ia-act`.
Les pages publiques `rgpd.html` et `politique-confidentialite.html` du site font foi pour ce que Think'UP
affirme de ses propres traitements : ne les contredis pas, et ne les modifie pas depuis cet outil.

Principes retenus pour l'outil (hypothèses de travail, à faire valider une fois par Patrick) :

1. Données de départ : répertoires publics (Sirene, RNE, BODACC). Les noms de dirigeants sont des données
   personnelles même quand elles sont publiques : usage limité à un premier contact professionnel
   justifié par leur fonction.
2. Prospection par e-mail à un professionnel : admise quand le message a un rapport avec sa fonction, avec
   information sur l'origine des données et moyen simple de s'opposer. Prospection par LinkedIn :
   mêmes principes, et les conditions d'utilisation de LinkedIn s'appliquent (limites des outils Yadulink).
3. Au premier contact, indique : qui écrit, d'où vient l'adresse ou le profil (par exemple « répertoire
   public des entreprises »), pourquoi cette personne, comment s'opposer (répondre « stop » suffit).
4. Opposition : consignée dans `prospection/registre.csv` (colonne `opposition`), prise en compte
   immédiatement, jamais retirée. Aucune relance après un refus.
5. Conservation : durée à fixer par Patrick (à confirmer avec la CNIL ; une durée de l'ordre de trois ans
   après le dernier contact est la référence habituelle, niveau « probable », non vérifiée ici). Sans suite,
   purger la ligne du registre au terme de la durée.
6. Aucune donnée sensible, aucune donnée sur la vie privée, aucune adresse personnelle.

Modèle de mention à ajouter à un premier e-mail (à adapter à l'origine réelle de l'adresse : retire « et de
votre site » si l'adresse n'y figure pas ; si elle vient de Clay, dis-le) :
« Vos coordonnées professionnelles proviennent du répertoire public des entreprises et de votre site. Je
les utilise uniquement pour vous proposer un échange sur l'IA dans votre activité. Pour ne plus recevoir de
message, répondez "stop" : je ne vous écrirai plus. Patrick Langlais, Think'UP. »
