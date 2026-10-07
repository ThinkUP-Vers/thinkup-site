<?php
declare(strict_types=1);

/**
 * Réaligne les <lastmod> de sitemap.xml sur la date de dernière modification
 * réelle de chaque fichier, lue dans l'historique Git.
 *
 * Pourquoi ce script existe (07/10/2026) : les lastmod des pages fixes étaient
 * écrits à la main et ne bougeaient plus. faq.html annonçait encore le
 * 2026-08-25 alors que son contenu avait changé le 2026-09-20 — Google n'avait
 * donc aucun signal de fraîcheur pour venir reprendre la correction. Le bloc
 * SCHEDULED_ARTICLES, lui, portait la date de PUBLICATION de l'article, qui
 * cesse d'être vraie dès qu'on retouche le texte ensuite.
 *
 * Ce script ne régénère pas le sitemap : il réécrit uniquement la valeur des
 * <lastmod>, en place. L'ordre des entrées, les <priority> choisis à la main et
 * les marqueurs du bloc automatique sont conservés tels quels.
 *
 * Il tourne après publish-blog.php : celui-ci crée les entrées des articles
 * publiés, celui-ci corrige leur date. Lancé deux fois de suite, il ne change
 * rien la seconde fois.
 */

$root = dirname(__DIR__);
$sitemap = $root . '/sitemap.xml';

/**
 * Exécute une commande Git dans le dépôt et renvoie sa sortie, ou null si la
 * commande a échoué.
 */
function git(string $root, string ...$arguments): ?string {
    $command = 'git -C ' . escapeshellarg($root);
    foreach ($arguments as $argument) {
        $command .= ' ' . escapeshellarg($argument);
    }
    $output = [];
    $status = 0;
    // 2>&1 plutôt que 2>/dev/null : la sortie n'est lue que si Git a réussi,
    // et la forme reste valable sur un shell Windows comme sur Linux.
    exec($command . ' 2>&1', $output, $status);
    return $status === 0 ? trim(implode("\n", $output)) : null;
}

// Garde-fou indispensable. actions/checkout clone en profondeur 1 par défaut :
// `git log` ne voit alors qu'un seul commit, ne retourne rien pour la quasi
// totalité des fichiers, et le repli « date du jour » daterait TOUT le sitemap
// d'aujourd'hui — à chaque exécution. Mieux vaut échouer bruyamment que publier
// un sitemap qui ment sur 33 pages. Le workflow doit passer fetch-depth: 0.
if (git($root, 'rev-parse', '--is-shallow-repository') !== 'false') {
    fwrite(STDERR, "refresh-sitemap: historique Git superficiel ou absent.\n"
        . "Les dates de dernière modification sont illisibles dans cet état.\n"
        . "Dans GitHub Actions, passer `fetch-depth: 0` à actions/checkout.\n");
    exit(1);
}

$today = (new DateTimeImmutable('now', new DateTimeZone('Europe/Paris')))->format('Y-m-d');

/**
 * Date de dernière modification d'un fichier, au format AAAA-MM-JJ.
 *
 * Un fichier encore non commité (l'article que publish-blog.php vient de copier
 * à la racine, par exemple) n'a pas d'historique : sa modification est en train
 * d'avoir lieu, la date du jour est la bonne réponse.
 */
function last_modified(string $root, string $file, string $today): string {
    $status = git($root, 'status', '--porcelain', '--', $file);
    if ($status === null) {
        // Git a échoué là où il vient pourtant de répondre au garde-fou : on
        // préfère s'arrêter plutôt que de deviner une date.
        fwrite(STDERR, 'refresh-sitemap: git status a echoue sur ' . $file . "\n");
        exit(1);
    }
    if ($status !== '') {
        return $today;
    }
    $date = git($root, 'log', '-1', '--format=%cs', '--', $file);
    // Chaîne vide = fichier suivi mais sans commit le concernant (cas d'un
    // ajout mis en index au cours du même passage) : sa date est aujourd'hui.
    return ($date === null || $date === '') ? $today : $date;
}

$contents = file_get_contents($sitemap);
if ($contents === false) {
    fwrite(STDERR, "refresh-sitemap: sitemap.xml illisible.\n");
    exit(1);
}

$missing = [];
$updated = 0;

$result = preg_replace_callback(
    '#<loc>https://think-up\.fr/([^<]*)</loc><lastmod>([^<]*)</lastmod>#',
    function (array $match) use ($root, $today, &$missing, &$updated): string {
        // La racine du site est servie par index.html.
        $file = $match[1] === '' ? 'index.html' : $match[1];

        if (!is_file($root . '/' . $file)) {
            $missing[] = $match[1];
            return $match[0];
        }

        $date = last_modified($root, $file, $today);
        if ($date !== $match[2]) {
            $updated++;
        }
        return '<loc>https://think-up.fr/' . $match[1] . '</loc><lastmod>' . $date . '</lastmod>';
    },
    $contents
);

if ($result === null) {
    fwrite(STDERR, "refresh-sitemap: echec de la reecriture du sitemap.\n");
    exit(1);
}

// Une entrée sans fichier derrière elle est une 404 annoncée à Google. On ne la
// supprime pas en silence — c'est au mainteneur de trancher.
if ($missing !== []) {
    fwrite(STDERR, "refresh-sitemap: entrees sans fichier correspondant :\n");
    foreach ($missing as $entry) {
        fwrite(STDERR, '  https://think-up.fr/' . $entry . "\n");
    }
    exit(1);
}

if ($result !== $contents && file_put_contents($sitemap, $result) === false) {
    fwrite(STDERR, "refresh-sitemap: ecriture de sitemap.xml impossible.\n");
    exit(1);
}

echo 'refresh-sitemap: ' . $updated . " date(s) mise(s) a jour.\n";
