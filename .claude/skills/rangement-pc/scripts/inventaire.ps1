<#
 inventaire.ps1 - Inventaire LECTURE SEULE du poste, pour le skill rangement-pc.

 Ce que le script lit : noms, tailles, dates de modification des fichiers des dossiers personnels
 (Bureau, Documents, Telechargements, Images, Videos, Musique, OneDrive, plus ceux que tu ajoutes),
 les disques, les applications installees, les programmes lances au demarrage, les noms des skills Claude.
 Empreinte SHA-256 uniquement pour les fichiers de meme taille (detection des doublons).
 Ce que le script NE FAIT PAS : il n'ouvre aucun fichier pour en lire le contenu (sauf le calcul d'empreinte),
 ne modifie, ne deplace et ne supprime rien, n'envoie rien sur Internet.
 Sortie : un dossier "inventaire-rangement" dans Documents, avec un .json et un .zip.
 Fichier volontairement sans accents (PowerShell 5.1 lit mal l'UTF-8 sans BOM).
#>
param(
    [string[]]$RacinesSupplementaires = @(),
    [switch]$SansEmpreintes,
    [int]$TailleMaxEmpreinteMo = 500
)

$ErrorActionPreference = 'SilentlyContinue'
$debut = Get-Date

function Json-Texte([string]$s) {
    if ($null -eq $s) { return 'null' }
    $s = $s.Replace('\', '\\').Replace('"', '\"')
    $s = $s -replace "[\x00-\x1f]", ' '
    return '"' + $s + '"'
}

# --- Dossiers racines (les dossiers rediriges vers OneDrive sont resolus par Windows) ---
$candidats = New-Object System.Collections.ArrayList
function Ajouter-Racine([string]$chemin, [string]$role) {
    if ($chemin -and (Test-Path -LiteralPath $chemin)) {
        $complet = (Resolve-Path -LiteralPath $chemin).ProviderPath.TrimEnd('\')
        foreach ($c in $candidats) { if ($c.chemin -ieq $complet) { return } }
        [void]$candidats.Add([pscustomobject]@{ chemin = $complet; role = $role })
    }
}
Ajouter-Racine ([Environment]::GetFolderPath('Desktop')) 'bureau'
Ajouter-Racine ([Environment]::GetFolderPath('MyDocuments')) 'documents'
try { Ajouter-Racine ((New-Object -ComObject Shell.Application).NameSpace('shell:Downloads').Self.Path) 'telechargements' } catch {}
Ajouter-Racine (Join-Path $env:USERPROFILE 'Downloads') 'telechargements'
Ajouter-Racine ([Environment]::GetFolderPath('MyPictures')) 'images'
Ajouter-Racine ([Environment]::GetFolderPath('MyVideos')) 'videos'
Ajouter-Racine ([Environment]::GetFolderPath('MyMusic')) 'musique'
Ajouter-Racine $env:OneDrive 'onedrive'
Ajouter-Racine $env:OneDriveCommercial 'onedrive'
foreach ($r in $RacinesSupplementaires) { Ajouter-Racine $r 'autre' }

# Racines a parcourir : on retire celles qui sont contenues dans une autre (pas de double parcours)
$aParcourir = New-Object System.Collections.ArrayList
foreach ($c in $candidats) {
    $contenue = $false
    foreach ($d in $candidats) {
        if ($c.chemin -ine $d.chemin -and $c.chemin.StartsWith($d.chemin + '\', [StringComparison]::OrdinalIgnoreCase)) { $contenue = $true }
    }
    if (-not $contenue) { [void]$aParcourir.Add($c.chemin) }
}

$sortieDossier = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'inventaire-rangement'
New-Item -ItemType Directory -Force -Path $sortieDossier | Out-Null
$stamp = Get-Date -Format 'yyyy-MM-dd'
$jsonChemin = Join-Path $sortieDossier ("inventaire-$stamp.json")

$ignorerContenu = @('node_modules', '.git', '.venv', 'venv', '__pycache__', '$RECYCLE.BIN', 'System Volume Information', 'inventaire-rangement')

$fichiers = New-Object System.Collections.Generic.List[object]
$dossiers = New-Object System.Collections.Generic.List[string]
$depotsGit = New-Object System.Collections.Generic.List[string]
$ignores = 0

Write-Host "Parcours en cours (peut prendre plusieurs minutes)..."
foreach ($racine in $aParcourir) {
    $pile = New-Object System.Collections.Generic.Stack[string]
    $pile.Push($racine)
    while ($pile.Count -gt 0) {
        $dir = $pile.Pop()
        $info = New-Object System.IO.DirectoryInfo($dir)
        $entrees = $null
        try { $entrees = $info.EnumerateFileSystemInfos() } catch { continue }
        foreach ($e in $entrees) {
            try {
                if ($e.Attributes -band [IO.FileAttributes]::ReparsePoint) { $ignores++; continue }
                if ($e.Attributes -band [IO.FileAttributes]::Directory) {
                    if ($e.Name -eq '.git') { $depotsGit.Add($dir); continue }
                    $dossiers.Add($e.FullName)
                    if ($ignorerContenu -contains $e.Name) { $ignores++; continue }
                    $pile.Push($e.FullName)
                } else {
                    $fichiers.Add([pscustomobject]@{ c = $e.FullName; t = [int64]$e.Length; m = $e.LastWriteTime.ToString('yyyy-MM-dd'); h = $null })
                }
            } catch {}
        }
    }
}
Write-Host ("{0} fichiers, {1} dossiers." -f $fichiers.Count, $dossiers.Count)

# --- Empreintes : seulement pour les fichiers dont la taille existe en plusieurs exemplaires ---
if (-not $SansEmpreintes) {
    Write-Host "Calcul des empreintes (doublons possibles)..."
    $max = [int64]$TailleMaxEmpreinteMo * 1MB
    $groupes = $fichiers | Where-Object { $_.t -ge 1024 -and $_.t -le $max } | Group-Object t | Where-Object { $_.Count -gt 1 }
    foreach ($g in $groupes) {
        foreach ($f in $g.Group) {
            try { $f.h = (Get-FileHash -LiteralPath $f.c -Algorithm SHA256).Hash.Substring(0, 24) } catch {}
        }
    }
}

# --- Machine ---
$disques = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
    [pscustomobject]@{ lettre = $_.DeviceID; taille = [int64]$_.Size; libre = [int64]$_.FreeSpace } })
$cles = @('HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
          'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
          'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*')
$apps = @(Get-ItemProperty $cles | Where-Object { $_.DisplayName -and -not $_.SystemComponent } |
    Select-Object @{n='nom';e={$_.DisplayName}}, @{n='version';e={$_.DisplayVersion}}, @{n='editeur';e={$_.Publisher}},
                  @{n='taille_mo';e={[math]::Round(($_.EstimatedSize / 1024), 0)}}, @{n='installe';e={$_.InstallDate}} |
    Sort-Object nom -Unique)
$demarrage = @(Get-CimInstance Win32_StartupCommand | Select-Object @{n='nom';e={$_.Name}}, @{n='commande';e={$_.Command}})
$skills = @()
$dossierSkills = Join-Path $env:USERPROFILE '.claude\skills'
if (Test-Path $dossierSkills) { $skills = @(Get-ChildItem $dossierSkills -Directory | ForEach-Object { $_.Name }) }
$os = (Get-CimInstance Win32_OperatingSystem).Caption

# --- Ecriture du JSON (a la main : ConvertTo-Json est trop lent et plafonne sur de gros volumes) ---
$w = New-Object System.IO.StreamWriter($jsonChemin, $false, (New-Object System.Text.UTF8Encoding($false)))
$w.Write('{"version":1,"genere":' + (Json-Texte (Get-Date -Format 's')) + ',"os":' + (Json-Texte $os))
$w.Write(',"racines":[' + (($candidats | ForEach-Object { '{"chemin":' + (Json-Texte $_.chemin) + ',"role":' + (Json-Texte $_.role) + '}' }) -join ',') + ']')
$w.Write(',"disques":[' + (($disques | ForEach-Object { '{"lettre":' + (Json-Texte $_.lettre) + ',"taille":' + $_.taille + ',"libre":' + $_.libre + '}' }) -join ',') + ']')
$w.Write(',"applications":[' + (($apps | ForEach-Object {
    $tm = if ($_.taille_mo) { [int]$_.taille_mo } else { 0 }
    '{"nom":' + (Json-Texte $_.nom) + ',"version":' + (Json-Texte $_.version) + ',"editeur":' + (Json-Texte $_.editeur) + ',"taille_mo":' + $tm + ',"installe":' + (Json-Texte $_.installe) + '}' }) -join ',') + ']')
$w.Write(',"demarrage":[' + (($demarrage | ForEach-Object { '{"nom":' + (Json-Texte $_.nom) + ',"commande":' + (Json-Texte $_.commande) + '}' }) -join ',') + ']')
$w.Write(',"claude_skills":[' + (($skills | ForEach-Object { Json-Texte $_ }) -join ',') + ']')
$w.Write(',"depots_git":[' + (($depotsGit | ForEach-Object { Json-Texte $_ }) -join ',') + ']')
$w.Write(',"ignores":' + $ignores)
$w.Write(',"dossiers":[')
$premier = $true
foreach ($d in $dossiers) { if (-not $premier) { $w.Write(',') }; $w.Write((Json-Texte $d)); $premier = $false }
$w.Write('],"fichiers":[')
$premier = $true
foreach ($f in $fichiers) {
    if (-not $premier) { $w.Write(',') }
    $w.Write('{"c":' + (Json-Texte $f.c) + ',"t":' + $f.t + ',"m":"' + $f.m + '","h":' + (Json-Texte $f.h) + '}')
    $premier = $false
}
$w.Write(']}')
$w.Close()

$zipChemin = [IO.Path]::ChangeExtension($jsonChemin, 'zip')
if (Test-Path $zipChemin) { Remove-Item -LiteralPath $zipChemin }
Compress-Archive -LiteralPath $jsonChemin -DestinationPath $zipChemin

$duree = [math]::Round(((Get-Date) - $debut).TotalMinutes, 1)
Write-Host ""
Write-Host "Termine en $duree min."
Write-Host "Fichier a me transmettre : $zipChemin"
Start-Process explorer.exe "/select,`"$zipChemin`""
