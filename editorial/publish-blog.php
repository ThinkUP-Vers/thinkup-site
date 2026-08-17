<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}

$atelier = __DIR__;            // editorial/ : calendrier et articles en attente
$root = dirname(__DIR__);      // racine du site : pages, blog, sitemap
$calendar = json_decode((string) file_get_contents($atelier . '/editorial-calendar.json'), true, 512, JSON_THROW_ON_ERROR);
$articles = $calendar['articles'];
$timezone = new DateTimeZone((string) $calendar['timezone']);
$dateOverride = null;
foreach ($argv ?? [] as $argument) {
    if (str_starts_with($argument, '--date=')) {
        $dateOverride = substr($argument, 7);
    }
}
$today = new DateTimeImmutable($dateOverride ?: 'now', $timezone);
$todayString = $today->format('Y-m-d');

function html_escape(string $value): string {
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function atomic_write(string $file, string $content): void {
    if (is_file($file) && file_get_contents($file) === $content) {
        return;
    }
    $temporary = $file . '.tmp';
    if (file_put_contents($temporary, $content, LOCK_EX) === false) {
        throw new RuntimeException('Unable to write ' . $temporary);
    }
    if (!@rename($temporary, $file)) {
        if (is_file($file) && !unlink($file)) {
            throw new RuntimeException('Unable to remove previous version of ' . $file);
        }
        if (!rename($temporary, $file)) {
            throw new RuntimeException('Unable to replace ' . $file);
        }
    }
}

function replace_block(string $file, string $start, string $end, string $replacement): void {
    $content = (string) file_get_contents($file);
    $startIndex = strpos($content, $start);
    $endIndex = strpos($content, $end);
    if ($startIndex === false || $endIndex === false || $endIndex < $startIndex) {
        // Un bloc absent n'est pas une erreur : la refonte d'aout 2026 a supprime
        // les vignettes de blog de l'accueil. Faire echouer toute la publication
        // pour ca priverait le site de ses articles a leur date.
        fwrite(STDERR, "Marqueurs absents dans " . basename($file) . " — bloc ignore.\n");
        return;
    }
    $next = substr($content, 0, $startIndex + strlen($start)) . "\n" . $replacement . "\n" . substr($content, $endIndex);
    atomic_write($file, $next);
}

function format_date_fr(string $date): string {
    $months = [
        '01' => 'janvier', '02' => 'février', '03' => 'mars', '04' => 'avril',
        '05' => 'mai', '06' => 'juin', '07' => 'juillet', '08' => 'août',
        '09' => 'septembre', '10' => 'octobre', '11' => 'novembre', '12' => 'décembre'
    ];
    [$year, $month, $day] = explode('-', $date);
    return (string) ((int) $day) . ' ' . $months[$month] . ' ' . $year;
}

function categorie_slug(string $categorie): string {
    $c = strtolower(strtr($categorie, [
        'é' => 'e', 'è' => 'e', 'ê' => 'e', 'à' => 'a', 'ç' => 'c', 'ô' => 'o', 'û' => 'u', 'î' => 'i',
    ]));
    foreach ([
        'strategie' => 'strategie', 'roi' => 'roi', 'finance' => 'roi', 'methode' => 'methode',
        'gouvernance' => 'gouvernance', 'productivite' => 'productivite', 'donnees' => 'donnees',
        'reglementation' => 'reglementation', 'management' => 'management', 'budget' => 'budget',
        'comparatif' => 'comparatifs', 'terrain' => 'terrain', 'diagnostic' => 'methode',
    ] as $motif => $slug) {
        if (str_contains($c, $motif)) { return $slug; }
    }
    return preg_replace('/[^a-z0-9]+/', '', $c) ?: 'autre';
}

function render_card(array $article): string {
    return '        <article class="post" data-cat="' . html_escape(categorie_slug($article['category'])) . '">' . "
"
        . '          <span class="tag">' . html_escape($article['category']) . '</span>' . "
"
        . '          <h3 class="serif"><a href="' . html_escape($article['slug']) . '.html">' . html_escape($article['title']) . '</a></h3>' . "
"
        . '          <p>' . html_escape($article['summary']) . '</p>' . "
"
        . '          <p class="meta">' . html_escape($article['readTime']) . ' de lecture</p>' . "
"
        . '        </article>';
}

function render_upcoming(array $articles): string {
    if ($articles === []) {
        return '    <div class="blog-upcoming"><p>Le calendrier éditorial 2026 est intégralement publié.</p></div>';
    }
    $lines = [];
    foreach ($articles as $article) {
        $lines[] = '<strong>' . html_escape(format_date_fr($article['publishDate'])) . '</strong> : ' . html_escape($article['title']);
    }
    return '    <div class="blog-upcoming"><p><span class="label">Prochainement</span><br>' . implode('<br>', $lines) . '</p></div>';
}

function render_llms(array $articles): string {
    $lines = [];
    foreach ($articles as $article) {
        $lines[] = '- ' . $article['title'] . ': https://think-up.fr/' . $article['slug'] . '.html';
    }
    return implode("\n", $lines);
}

function render_sitemap(array $articles): string {
    $lines = [];
    foreach ($articles as $article) {
        $lines[] = '  <url><loc>https://think-up.fr/' . $article['slug'] . '.html</loc><lastmod>' . $article['publishDate'] . '</lastmod><priority>0.6</priority></url>';
    }
    return implode("\n", $lines);
}

$published = [];
$scheduledPublished = [];
$upcoming = [];
foreach ($articles as $article) {
    if (!$article['scheduled'] || $article['publishDate'] <= $todayString) {
        $published[] = $article;
        if ($article['scheduled']) {
            $scheduledPublished[] = $article;
            $source = $atelier . '/scheduled-blog/' . $article['slug'] . '.html';
            $destination = $root . '/' . $article['slug'] . '.html';
            atomic_write($destination, (string) file_get_contents($source));
        }
    } elseif ($article['scheduled']) {
        $upcoming[] = $article;
    }
}

usort($published, fn(array $a, array $b): int => strcmp($b['publishDate'], $a['publishDate']));
usort($scheduledPublished, fn(array $a, array $b): int => strcmp($b['publishDate'], $a['publishDate']));
usort($upcoming, fn(array $a, array $b): int => strcmp($a['publishDate'], $b['publishDate']));

$blogCards = array_filter($published, fn(array $article): bool => $article['slug'] !== $calendar['featured']);
$homeCards = array_slice($published, 0, 3);

replace_block($root . '/blog.html', '<!-- BLOG_AUTO_START -->', '<!-- BLOG_AUTO_END -->', implode("\n", array_map('render_card', $blogCards)));
replace_block($root . '/blog.html', '<!-- BLOG_UPCOMING_START -->', '<!-- BLOG_UPCOMING_END -->', render_upcoming(array_slice($upcoming, 0, 2)));
replace_block($root . '/index.html', '<!-- HOME_BLOG_AUTO_START -->', '<!-- HOME_BLOG_AUTO_END -->', implode("\n", array_map('render_card', $homeCards)));
replace_block($root . '/sitemap.xml', '<!-- SCHEDULED_ARTICLES_START -->', '<!-- SCHEDULED_ARTICLES_END -->', render_sitemap($scheduledPublished));
replace_block($root . '/llms.txt', '<!-- PUBLISHED_ARTICLES_START -->', '<!-- PUBLISHED_ARTICLES_END -->', render_llms($published));
replace_block($root . '/llms-full.txt', '<!-- PUBLISHED_ARTICLES_START -->', '<!-- PUBLISHED_ARTICLES_END -->', render_llms($published));

echo 'ThinkUP blog publisher: ' . $todayString . "\n";
echo 'Published scheduled articles: ' . count($scheduledPublished) . "\n";
echo $upcoming === [] ? "Editorial calendar fully published.\n" : 'Next publication: ' . $upcoming[0]['publishDate'] . ' ' . $upcoming[0]['slug'] . "\n";
